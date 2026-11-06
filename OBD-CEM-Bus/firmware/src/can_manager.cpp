#include "can_manager.h"

#include <cstring>
#include <esp_timer.h>

#include "usb_logger.h"

namespace volvo {

void CanManager::begin(Settings* settings) {
  settings_ = settings;
  // CAN bleibt beim Boot strikt deaktiviert. TXD (GPIO15) wird hochgehalten,
  // damit der Transceiver sicher rezessiv bleibt, bis START kommt.
  pinMode(kPinCanTx, INPUT_PULLUP);
  pinMode(kPinCanRx, INPUT);
  pinMode(kPinCanTwaiTx, INPUT);
  armed_ = false;
  source_ = Source::Can;
  bitrate_ = kDefaultBitrateKbps;
  mutex_ = xSemaphoreCreateMutex();
  if (mutex_ != nullptr) setDriverState(DriverState::Stopped);
  command_queue_ = xQueueCreate(8, sizeof(Command));
  size_t capacity = capture_.begin(kCaptureCapacity, kCaptureFallbackCapacity);
  usbLogger().diag("CAN", "Aufzeichnungspuffer: %u Frames (%s)",
                   static_cast<unsigned>(capacity),
                   capacity == kCaptureCapacity ? "PSRAM" : "interner RAM/Fallback");
  xTaskCreatePinnedToCore(taskEntry, "can", kCanTaskStack, this, 5, &task_handle_, 1);
}

void CanManager::taskEntry(void* arg) {
  static_cast<CanManager*>(arg)->taskLoop();
}

bool CanManager::lock(TickType_t timeout) {
  return mutex_ != nullptr && xSemaphoreTake(mutex_, timeout) == pdTRUE;
}

void CanManager::unlock() {
  if (mutex_ != nullptr) xSemaphoreGive(mutex_);
}

bool CanManager::sendCommand(CommandType type, uint32_t value) {
  if (command_queue_ == nullptr) return false;
  Command command{type, value};
  return xQueueSend(command_queue_, &command, 0) == pdTRUE;
}

bool CanManager::requestBitrate(uint32_t kbps) {
  if (!Settings::isSupportedBitrate(kbps)) return false;
  if (!sendCommand(CommandType::SetBitrate, kbps)) return false;
  settings_->setBitrate(kbps);
  return true;
}

bool CanManager::requestDemo(bool enabled) {
  if (!sendCommand(CommandType::SetDemo, enabled ? 1U : 0U)) return false;
  settings_->setDemo(enabled);
  return true;
}

bool CanManager::requestStart() {
  if (!kAllowCanStart) {
    usbLogger().diag("CAN", "START gesperrt (kAllowCanStart=false): Hardwarefreigabe fehlt.");
    return false;
  }
  return sendCommand(CommandType::Start, 0);
}

bool CanManager::requestStop() {
  return sendCommand(CommandType::Stop, 0);
}

void CanManager::logStatus() {
  twai_status_info_t info{};
  if (twai_get_status_info(&info) != ESP_OK) {
    usbLogger().diag("TWAI", "CAN deaktiviert (Treiber nicht installiert), armed=%d start_locked=%d",
                     armed_ ? 1 : 0, kAllowCanStart ? 0 : 1);
    return;
  }
  usbLogger().diag("TWAI",
                   "armed=%d start_locked=%d bitrate=%u brp=%u tseg1=%u tseg2=%u sjw=%u state=%d "
                   "rx_err=%u tx_err=%u bus_err=%u arb_lost=%u tx_failed=%u "
                   "rx_missed=%u rx_overrun=%u msgs_to_rx=%u alerts=0x%08X",
                   armed_ ? 1 : 0,
                   kAllowCanStart ? 0 : 1,
                   static_cast<unsigned>(bitrate_),
                   static_cast<unsigned>(last_timing_.brp),
                   static_cast<unsigned>(last_timing_.tseg_1),
                   static_cast<unsigned>(last_timing_.tseg_2),
                   static_cast<unsigned>(last_timing_.sjw),
                   static_cast<int>(info.state),
                   static_cast<unsigned>(info.rx_error_counter),
                   static_cast<unsigned>(info.tx_error_counter),
                   static_cast<unsigned>(info.bus_error_count),
                   static_cast<unsigned>(info.arb_lost_count),
                   static_cast<unsigned>(info.tx_failed_count),
                   static_cast<unsigned>(info.rx_missed_count),
                   static_cast<unsigned>(info.rx_overrun_count),
                   static_cast<unsigned>(info.msgs_to_rx),
                   static_cast<unsigned>(last_alerts_));
}

void CanManager::handleCommand(const Command& command) {
  if (command.type == CommandType::SetBitrate) {
    // Nur die feste Testbitrate ist zugelassen; ohne START bleibt CAN aus.
    if (!Settings::isSupportedBitrate(command.value)) return;
    bitrate_ = command.value;
    if (armed_) switchSource(Source::Can, bitrate_);
  } else if (command.type == CommandType::SetDemo) {
    if (command.value != 0) {
      armed_ = false;
      switchSource(Source::Demo, bitrate_);
    } else if (source_ == Source::Demo) {
      source_ = Source::Can;
      uninstallTwai();
    }
  } else if (command.type == CommandType::Start) {
    if (!kAllowCanStart) {
      armed_ = false;
      usbLogger().diag("CAN", "Start-Kommando verworfen: kAllowCanStart=false.");
      return;
    }
    armed_ = true;
    switchSource(Source::Can, kDefaultBitrateKbps);
    if (!twai_installed_) armed_ = false;
  } else if (command.type == CommandType::Stop) {
    armed_ = false;
    uninstallTwai();
    source_ = Source::Can;
  }
}

void CanManager::switchSource(Source source, uint32_t bitrate) {
  uninstallTwai();

  if (lock()) {
    source_ = source;
    bitrate_ = bitrate;
    live_.clear();
    capture_.clear();
    stats_.clear();
    phases_.reset();
    recording_ = false;
    capture_start_us_ = 0;
    capture_stop_us_ = 0;
    seq_ = 0;
    total_frames_ = 0;
    window_count_ = 0;
    msgs_per_sec_ = 0;
    errors_ = 0;
    rx_queue_full_ = 0;
    latest_seq_ = 0;
    bus_off_ = false;
    unlock();
  }

  // Alte Frames der vorherigen Quelle nicht in die neue Session mischen.
  usbLogger().discardQueued();

  if (source == Source::Demo) {
    demo_.reset(esp_timer_get_time());
    setDriverState(DriverState::Demo);
    usbLogger().diag("CAN", "Demo-Modus aktiv: alle Frames sind synthetisch (DEMO).");
  } else {
    setDriverState(DriverState::Installing);
    last_install_ms_ = millis();
    if (!installTwai(bitrate)) {
      armed_ = false;
      setDriverState(DriverState::Error);
      usbLogger().diag("CAN", "TWAI konnte nicht gestartet werden; kein Senden, kein Auto-Neuversuch.");
    }
  }
}

bool CanManager::installTwai(uint32_t bitrate) {
  // Der echte CAN-TXD bleibt hochgezogen; TWAI-TX geht auf einen Dummy-Pin.
  pinMode(kPinCanTx, INPUT_PULLUP);
  pinMode(kPinCanRx, INPUT);
  pinMode(kPinCanTwaiTx, INPUT);

  twai_general_config_t general =
      TWAI_GENERAL_CONFIG_DEFAULT(static_cast<gpio_num_t>(kPinCanTwaiTx),
                                  static_cast<gpio_num_t>(kPinCanRx),
                                  TWAI_MODE_LISTEN_ONLY);
  general.rx_queue_len = kTwaiRxQueueLength;

  twai_timing_config_t timing{};
  switch (bitrate) {
    case 1000:
      timing = TWAI_TIMING_CONFIG_1MBITS();
      break;
    case 800:
      timing = TWAI_TIMING_CONFIG_800KBITS();
      break;
    case 500:
      timing = TWAI_TIMING_CONFIG_500KBITS();
      break;
    case 250:
      timing = TWAI_TIMING_CONFIG_250KBITS();
      break;
    case 125:
      timing = TWAI_TIMING_CONFIG_125KBITS();
      break;
    case 100:
      timing = TWAI_TIMING_CONFIG_100KBITS();
      break;
    case 50:
      timing = TWAI_TIMING_CONFIG_50KBITS();
      break;
    case 83333:  // 83,333 kbit/s: 80 MHz / (60 * 16 tq)
      timing.brp = 60;
      timing.tseg_1 = 11;
      timing.tseg_2 = 4;
      timing.sjw = 2;
      timing.triple_sampling = false;
      break;
    case 33333:  // 33,333 kbit/s: 80 MHz / (150 * 16 tq)
      timing.brp = 150;
      timing.tseg_1 = 11;
      timing.tseg_2 = 4;
      timing.sjw = 2;
      timing.triple_sampling = false;
      break;
    case 666667:  // 666,667 kbit/s: 80 MHz / (10 * 12 tq)
      timing.brp = 10;
      timing.tseg_1 = 8;
      timing.tseg_2 = 3;
      timing.sjw = 1;
      timing.triple_sampling = false;
      break;
    default:
      return false;
  }
  twai_filter_config_t filter = TWAI_FILTER_CONFIG_ACCEPT_ALL();

  esp_err_t err = twai_driver_install(&general, &timing, &filter);
  if (err != ESP_OK) {
    usbLogger().diag("CAN", "twai_driver_install fehlgeschlagen: %s (%d)",
                     esp_err_to_name(err), static_cast<int>(err));
    return false;
  }
  err = twai_start();
  if (err != ESP_OK) {
    usbLogger().diag("CAN", "twai_start fehlgeschlagen: %s (%d)",
                     esp_err_to_name(err), static_cast<int>(err));
    twai_driver_uninstall();
    return false;
  }

  uint32_t alerts = TWAI_ALERT_RX_DATA | TWAI_ALERT_RX_QUEUE_FULL |
                    TWAI_ALERT_ERR_PASS | TWAI_ALERT_BUS_ERROR |
                    TWAI_ALERT_BUS_OFF | TWAI_ALERT_BUS_RECOVERED;
  err = twai_reconfigure_alerts(alerts, nullptr);
  if (err != ESP_OK) {
    usbLogger().diag("CAN", "twai_reconfigure_alerts: %s (%d)",
                     esp_err_to_name(err), static_cast<int>(err));
  }
  last_timing_ = timing;
  usbLogger().diag("CAN",
                   "TWAI LISTEN_ONLY gestartet: %u kbit/s, brp=%u tseg1=%u tseg2=%u sjw=%u; "
                   "echter TXD GPIO%u=INPUT_PULLUP, TWAI-TX=Dummy GPIO%u",
                   static_cast<unsigned>(bitrate),
                   static_cast<unsigned>(timing.brp),
                   static_cast<unsigned>(timing.tseg_1),
                   static_cast<unsigned>(timing.tseg_2),
                   static_cast<unsigned>(timing.sjw),
                   static_cast<unsigned>(kPinCanTx),
                   static_cast<unsigned>(kPinCanTwaiTx));
  twai_installed_ = true;
  bus_off_ = false;
  setDriverState(DriverState::Running);
  return true;
}

void CanManager::uninstallTwai() {
  if (twai_installed_) {
    esp_err_t err = twai_stop();
    if (err != ESP_OK) {
      usbLogger().diag("CAN", "twai_stop: %s (%d)", esp_err_to_name(err),
                       static_cast<int>(err));
    }
    err = twai_driver_uninstall();
    if (err != ESP_OK) {
      usbLogger().diag("CAN", "twai_driver_uninstall: %s (%d)", esp_err_to_name(err),
                       static_cast<int>(err));
    }
    twai_installed_ = false;
  }
  // Nach STOP bleibt der Transceiver passiv: TXD hochziehen, RX nicht treiben.
  pinMode(kPinCanTx, INPUT_PULLUP);
  pinMode(kPinCanRx, INPUT);
  pinMode(kPinCanTwaiTx, INPUT);
  bus_off_ = false;
  setDriverState(DriverState::Stopped);
}

void CanManager::handleAlerts(uint32_t alerts) {
  last_alerts_ |= alerts;
  if (alerts & TWAI_ALERT_RX_QUEUE_FULL) {
    if (lock()) {
      ++errors_;
      ++rx_queue_full_;
      unlock();
    }
  }
  if (alerts & (TWAI_ALERT_BUS_ERROR | TWAI_ALERT_ERR_PASS)) {
    if (lock()) {
      ++errors_;
      unlock();
    }
  }
  if (alerts & TWAI_ALERT_BUS_OFF) {
    bus_off_ = true;
    armed_ = false;
    if (lock()) {
      ++errors_;
      unlock();
    }
    setDriverState(DriverState::BusOff);
  }
  if (alerts & TWAI_ALERT_BUS_RECOVERED) {
    bus_off_ = false;
    setDriverState(DriverState::Running);
  }
}

void CanManager::ingest(const CanFrame& frame) {
  if (!lock()) return;
  live_.push(frame);
  if (recording_) capture_.push(frame);
  stats_.add(frame);
  phases_.add(frame);
  ++total_frames_;
  ++window_count_;
  if (frame.seq > latest_seq_) latest_seq_ = frame.seq;
  unlock();

  // USB-Logger bekommt jeden Frame, auch wenn der Live-Ring bereits
  // ueberlaufen ist. enqueue() ist nicht blockierend und zaehlt Verwuerfe.
  usbLogger().enqueue(frame);
}

void CanManager::updateRate() {
  uint32_t now = millis();
  if (now - last_rate_ms_ < 1000) return;
  if (lock()) {
    msgs_per_sec_ = window_count_;
    window_count_ = 0;
    unlock();
  }
  last_rate_ms_ = now;
}

void CanManager::taskLoop() {
  // Bootzustand: CAN bleibt aus. Erst START aktiviert den Empfang.
  source_ = Source::Can;
  bitrate_ = settings_->bitrateKbps();
  armed_ = false;
  setDriverState(DriverState::Stopped);
  last_rate_ms_ = millis();

  for (;;) {
    Command command;
    while (command_queue_ != nullptr && xQueueReceive(command_queue_, &command, 0) == pdTRUE) {
      handleCommand(command);
    }

    if (source_ == Source::Demo) {
      CanFrame frames[16];
      size_t count = demo_.poll(esp_timer_get_time(), frames, 16, seq_);
      for (size_t i = 0; i < count; ++i) ingest(frames[i]);
      vTaskDelay(pdMS_TO_TICKS(10));
    } else {
      if (twai_installed_) {
        twai_message_t message;
        for (int i = 0; i < kCanReceiveBurst; ++i) {
          if (twai_receive(&message, 0) != ESP_OK) break;
          CanFrame frame;
          frame.seq = ++seq_;
          frame.timestamp_us = static_cast<uint64_t>(esp_timer_get_time());
          frame.id = message.identifier;
          frame.dlc = message.data_length_code > kMaxDataBytes ? kMaxDataBytes : message.data_length_code;
          frame.extended = message.extd;
          frame.demo = false;
          std::memcpy(frame.data, message.data, frame.dlc);
          ingest(frame);
        }

        uint32_t alerts = 0;
        if (twai_read_alerts(&alerts, 0) == ESP_OK && alerts != 0) handleAlerts(alerts);

        if (bus_off_) {
          usbLogger().diag("CAN", "Bus-Off erkannt: CAN bleibt STOP; neuer START erforderlich.");
          armed_ = false;
          uninstallTwai();
        }
      }
      vTaskDelay(pdMS_TO_TICKS(5));
    }
    updateRate();
  }
}

void CanManager::setDriverState(DriverState state) {
  if (lock()) {
    driver_state_ = state;
    unlock();
  }
}

void CanManager::fillStatus(CanStatus& status) {
  uint64_t now_us = static_cast<uint64_t>(esp_timer_get_time());
  if (!lock()) return;
  status.demo_mode = source_ == Source::Demo;
  status.twai_installed = twai_installed_;
  status.armed = armed_;
  status.bitrate_kbps = bitrate_;
  status.total_frames = total_frames_;
  status.unique_ids = static_cast<uint32_t>(stats_.size());
  status.msgs_per_sec = msgs_per_sec_;
  status.dropped_live = live_.dropped();
  status.dropped_capture = capture_.dropped();
  status.twai_errors = errors_;
  status.rx_queue_full = rx_queue_full_;
  status.latest_seq = latest_seq_;
  status.uptime_ms = millis();
  status.free_heap = ESP.getFreeHeap();
  status.free_psram = ESP.getFreePsram();
  status.recording = recording_;
  status.capture_count = static_cast<uint32_t>(capture_.size());
  status.capture_capacity = static_cast<uint32_t>(capture_.capacity());
  status.capture_dropped = capture_.dropped();
  status.phase_a_active = phases_.active('A');
  status.phase_a_valid = phases_.valid('A');
  status.phase_b_active = phases_.active('B');
  status.phase_b_valid = phases_.valid('B');
  status.phase_a_frames = phases_.frames('A');
  status.phase_b_frames = phases_.frames('B');
  status.phase_a_duration_ms = phases_.durationUs('A', now_us) / 1000ULL;
  status.phase_b_duration_ms = phases_.durationUs('B', now_us) / 1000ULL;
  status.source_name = source_ == Source::Demo ? "DEMO" : "CAN";
  switch (driver_state_) {
    case DriverState::Demo: status.driver_state_name = "DEMO"; break;
    case DriverState::Installing: status.driver_state_name = "INSTALLING"; break;
    case DriverState::Running: status.driver_state_name = "RUNNING"; break;
    case DriverState::BusOff: status.driver_state_name = "BUS_OFF"; break;
    case DriverState::Error: status.driver_state_name = "ERROR"; break;
    default: status.driver_state_name = "STOPPED"; break;
  }
  unlock();
}

size_t CanManager::getMessagesSince(uint32_t since_seq, CanFrame* out, size_t max_messages,
                                    uint32_t& latest_seq, uint32_t& dropped) {
  if (out == nullptr || max_messages == 0) return 0;
  if (!lock()) return 0;
  latest_seq = latest_seq_;
  dropped = live_.dropped();
  size_t total = live_.size();
  size_t start = 0;
  if (since_seq == 0 && total > max_messages) start = total - max_messages;
  size_t copied = 0;
  for (size_t i = start; i < total && copied < max_messages; ++i) {
    const CanFrame& frame = live_.at(i);
    if (since_seq != 0 && frame.seq <= since_seq) continue;
    out[copied++] = frame;
  }
  unlock();
  return copied;
}

size_t CanManager::getIdStats(IdAggregate* out, size_t max_entries) {
  if (out == nullptr) return 0;
  if (!lock()) return 0;
  size_t n = stats_.size();
  if (n > max_entries) n = max_entries;
  for (size_t i = 0; i < n; ++i) out[i] = stats_.entries()[i];
  unlock();
  return n;
}

bool CanManager::phaseStart(char phase) {
  if (!lock()) return false;
  bool ok = phases_.start(phase, static_cast<uint64_t>(esp_timer_get_time()));
  unlock();
  return ok;
}

bool CanManager::phaseStop(char phase) {
  if (!lock()) return false;
  bool ok = phases_.stop(phase, static_cast<uint64_t>(esp_timer_get_time()));
  unlock();
  return ok;
}

void CanManager::phaseReset() {
  if (!lock()) return;
  phases_.reset();
  unlock();
}

void CanManager::compare(CompareResult& result) {
  if (!lock()) {
    result = CompareResult{};
    return;
  }
  phases_.compare(result, static_cast<uint64_t>(esp_timer_get_time()));
  unlock();
}

bool CanManager::recordStart() {
  if (!lock()) return false;
  if (!capture_.enabled()) {
    unlock();
    return false;
  }
  capture_.clear();
  recording_ = true;
  capture_start_us_ = static_cast<uint64_t>(esp_timer_get_time());
  capture_stop_us_ = 0;
  unlock();
  return true;
}

bool CanManager::recordStop() {
  if (!lock()) return false;
  recording_ = false;
  capture_stop_us_ = static_cast<uint64_t>(esp_timer_get_time());
  unlock();
  return true;
}

bool CanManager::isRecording() {
  if (!lock()) return false;
  bool value = recording_;
  unlock();
  return value;
}

void CanManager::clearMessages() {
  if (!lock()) return;
  live_.clear();
  unlock();
}

size_t CanManager::captureSnapshot(CanFrame* destination, size_t max_entries, uint32_t& dropped) {
  if (!lock()) return 0;
  size_t count = capture_.copyTo(destination, max_entries);
  dropped = capture_.dropped();
  unlock();
  return count;
}

}  // namespace volvo

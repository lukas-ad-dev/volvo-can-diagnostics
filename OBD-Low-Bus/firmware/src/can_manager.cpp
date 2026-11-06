#include "can_manager.h"

#include <cstring>
#include <esp_timer.h>

#include "usb_logger.h"

namespace volvo {

void CanManager::begin(Settings* settings) {
  settings_ = settings;
  mutex_ = xSemaphoreCreateMutex();
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

void CanManager::handleCommand(const Command& command) {
  if (command.type == CommandType::SetBitrate) {
    switchSource(source_, command.value);
  } else if (command.type == CommandType::SetDemo) {
    switchSource(command.value != 0 ? Source::Demo : Source::Can, bitrate_);
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
    if (installTwai(bitrate)) {
      usbLogger().diag("CAN", "TWAI LISTEN_ONLY gestartet, %u kbit/s.", static_cast<unsigned>(bitrate));
    } else {
      setDriverState(DriverState::Error);
      usbLogger().diag("CAN", "TWAI konnte nicht gestartet werden; kein Senden, nur Neuversuch.");
    }
  }
}

bool CanManager::installTwai(uint32_t bitrate) {
  twai_general_config_t general =
      TWAI_GENERAL_CONFIG_DEFAULT(static_cast<gpio_num_t>(kPinCanTx),
                                  static_cast<gpio_num_t>(kPinCanRx),
                                  TWAI_MODE_LISTEN_ONLY);
  general.rx_queue_len = kTwaiRxQueueLength;

  twai_timing_config_t timing;
  switch (bitrate) {
    case 125:
      timing = TWAI_TIMING_CONFIG_125KBITS();
      break;
    case 250:
      timing = TWAI_TIMING_CONFIG_250KBITS();
      break;
    case 500:
      timing = TWAI_TIMING_CONFIG_500KBITS();
      break;
    default:
      return false;
  }
  twai_filter_config_t filter = TWAI_FILTER_CONFIG_ACCEPT_ALL();

  if (twai_driver_install(&general, &timing, &filter) != ESP_OK) return false;
  if (twai_start() != ESP_OK) {
    twai_driver_uninstall();
    return false;
  }

  uint32_t alerts = TWAI_ALERT_RX_DATA | TWAI_ALERT_RX_QUEUE_FULL |
                    TWAI_ALERT_ERR_PASS | TWAI_ALERT_BUS_ERROR |
                    TWAI_ALERT_BUS_OFF | TWAI_ALERT_BUS_RECOVERED;
  twai_reconfigure_alerts(alerts, nullptr);
  twai_installed_ = true;
  bus_off_ = false;
  setDriverState(DriverState::Running);
  return true;
}

void CanManager::uninstallTwai() {
  if (twai_installed_) {
    twai_stop();
    twai_driver_uninstall();
    twai_installed_ = false;
  }
  bus_off_ = false;
  setDriverState(DriverState::Stopped);
}

void CanManager::handleAlerts(uint32_t alerts) {
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
  switchSource(settings_->demoEnabled() ? Source::Demo : Source::Can,
               settings_->bitrateKbps());
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
      if (!twai_installed_ && (millis() - last_install_ms_ > 5000)) {
        setDriverState(DriverState::Installing);
        last_install_ms_ = millis();
        if (!installTwai(bitrate_)) setDriverState(DriverState::Error);
      }

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

        if (bus_off_ && (millis() - last_install_ms_ > 5000)) {
          uninstallTwai();
          setDriverState(DriverState::Installing);
          last_install_ms_ = millis();
          if (installTwai(bitrate_)) {
            usbLogger().diag("CAN", "TWAI nach Bus-Off neu gestartet (weiterhin LISTEN_ONLY).");
          } else {
            setDriverState(DriverState::Error);
          }
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

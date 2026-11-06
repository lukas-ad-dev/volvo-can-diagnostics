#pragma once

#include <Arduino.h>
#include <driver/twai.h>

#include "app_config.h"
#include "capture_buffer.h"
#include "settings.h"
#include "volvo_core/can_frame.h"
#include "volvo_core/demo_generator.h"
#include "volvo_core/id_stats.h"
#include "volvo_core/phase_tracker.h"
#include "volvo_core/ring_buffer.h"

namespace volvo {

struct CanStatus {
  bool demo_mode = false;
  bool twai_installed = false;
  uint32_t bitrate_kbps = kDefaultBitrateKbps;
  uint32_t total_frames = 0;
  uint32_t unique_ids = 0;
  uint32_t msgs_per_sec = 0;
  uint32_t dropped_live = 0;
  uint32_t dropped_capture = 0;
  uint32_t twai_errors = 0;
  uint32_t rx_queue_full = 0;
  uint32_t latest_seq = 0;
  uint32_t uptime_ms = 0;
  uint32_t free_heap = 0;
  uint32_t free_psram = 0;
  bool recording = false;
  uint32_t capture_count = 0;
  uint32_t capture_capacity = 0;
  uint32_t capture_dropped = 0;
  bool phase_a_active = false;
  bool phase_a_valid = false;
  bool phase_b_active = false;
  bool phase_b_valid = false;
  uint32_t phase_a_frames = 0;
  uint32_t phase_b_frames = 0;
  uint64_t phase_a_duration_ms = 0;
  uint64_t phase_b_duration_ms = 0;
  const char* source_name = "CAN";
  const char* driver_state_name = "STOPPED";
};

class CanManager {
 public:
  void begin(Settings* settings);
  bool requestBitrate(uint32_t kbps);
  bool requestDemo(bool enabled);

  void fillStatus(CanStatus& status);
  size_t getMessagesSince(uint32_t since_seq, CanFrame* out, size_t max_messages,
                          uint32_t& latest_seq, uint32_t& dropped);
  size_t getIdStats(IdAggregate* out, size_t max_entries);

  bool phaseStart(char phase);
  bool phaseStop(char phase);
  void phaseReset();
  void compare(CompareResult& result);

  bool recordStart();
  bool recordStop();
  bool isRecording();
  void clearMessages();
  size_t captureSnapshot(CanFrame* destination, size_t max_entries, uint32_t& dropped);

 private:
  enum class Source : uint8_t { Can = 0, Demo = 1 };
  enum class DriverState : uint8_t { Stopped, Installing, Running, BusOff, Error, Demo };
  enum class CommandType : uint8_t { SetBitrate = 0, SetDemo = 1 };

  struct Command {
    CommandType type;
    uint32_t value;
  };

  static void taskEntry(void* arg);
  void taskLoop();
  bool sendCommand(CommandType type, uint32_t value);
  void handleCommand(const Command& command);
  void switchSource(Source source, uint32_t bitrate);
  bool installTwai(uint32_t bitrate);
  void uninstallTwai();
  void handleAlerts(uint32_t alerts);
  void ingest(const CanFrame& frame);
  void updateRate();
  void setDriverState(DriverState state);
  bool lock(TickType_t timeout = pdMS_TO_TICKS(100));
  void unlock();

  Settings* settings_ = nullptr;
  SemaphoreHandle_t mutex_ = nullptr;
  QueueHandle_t command_queue_ = nullptr;
  TaskHandle_t task_handle_ = nullptr;

  Source source_ = Source::Can;
  DriverState driver_state_ = DriverState::Stopped;
  uint32_t bitrate_ = kDefaultBitrateKbps;
  bool twai_installed_ = false;

  RingBuffer<CanFrame, kLiveRingCapacity> live_;
  CaptureBuffer capture_;
  IdStats stats_;
  PhaseTracker phases_;
  DemoGenerator demo_;

  uint32_t seq_ = 0;
  uint32_t total_frames_ = 0;
  uint32_t window_count_ = 0;
  uint32_t msgs_per_sec_ = 0;
  uint32_t last_rate_ms_ = 0;
  uint32_t errors_ = 0;
  uint32_t rx_queue_full_ = 0;
  uint32_t latest_seq_ = 0;

  bool recording_ = false;
  uint64_t capture_start_us_ = 0;
  uint64_t capture_stop_us_ = 0;

  uint32_t last_install_ms_ = 0;
  bool bus_off_ = false;
};

}  // namespace volvo

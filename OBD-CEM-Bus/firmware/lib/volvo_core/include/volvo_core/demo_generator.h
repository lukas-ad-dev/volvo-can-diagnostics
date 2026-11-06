#pragma once

#include <cstddef>
#include <cstdint>

#include "volvo_core/can_frame.h"

namespace volvo {

// Erzeugt synthetische, klar als DEMO markierte CAN-Frames.
// Alle IDs und Nutzdaten sind frei erfunden und keine Volvo-Zuordnung.
class DemoGenerator {
 public:
  void reset(uint64_t now_us) {
    for (size_t i = 0; i < kSignalCount; ++i) {
      signals_[i].counter = 0;
      signals_[i].next_us = now_us + static_cast<uint64_t>(i) * 2000ULL;
    }
  }

  size_t poll(uint64_t now_us, CanFrame* out, size_t max_frames, uint32_t& next_seq) {
    size_t produced = 0;
    for (size_t i = 0; i < kSignalCount && produced < max_frames; ++i) {
      Signal& signal = signals_[i];
      while (signal.next_us <= now_us && produced < max_frames) {
        CanFrame frame;
        frame.seq = ++next_seq;
        frame.timestamp_us = signal.next_us;
        frame.id = signal.id;
        frame.dlc = signal.dlc;
        frame.extended = false;
        frame.demo = true;
        buildPayload(signal, frame);
        out[produced++] = frame;
        ++signal.counter;
        signal.next_us += signal.period_us;
        if (signal.next_us + signal.period_us * 4ULL < now_us) {
          signal.next_us = now_us + signal.period_us;
        }
      }
    }
    return produced;
  }

 private:
  struct Signal {
    uint32_t id;
    uint32_t period_us;
    uint32_t counter;
    uint64_t next_us;
    uint8_t dlc;
  };

  static constexpr size_t kSignalCount = 7;
  Signal signals_[kSignalCount] = {
      {0x100, 20000, 0, 0, 8},   // Radgeschwindigkeiten (synthetisch)
      {0x120, 10000, 0, 0, 8},   // Motor/Getriebe (synthetisch)
      {0x1A0, 50000, 0, 0, 8},   // Statusbits inkl. Demo-Kamera-Bit
      {0x2C0, 20000, 0, 0, 8},   // Lenkung/Fahrwerk (synthetisch)
      {0x3E0, 100000, 0, 0, 8},  // Batterie (synthetisch)
      {0x4A0, 200000, 0, 0, 8},  // Temperaturen (synthetisch)
      {0x5B0, 500000, 0, 0, 8},  // Zaehler (synthetisch)
  };

  static void set16(uint8_t* data, size_t offset, uint16_t value) {
    data[offset] = static_cast<uint8_t>(value & 0xFF);
    data[offset + 1] = static_cast<uint8_t>((value >> 8) & 0xFF);
  }

  static void set32(uint8_t* data, size_t offset, uint32_t value) {
    data[offset] = static_cast<uint8_t>(value & 0xFF);
    data[offset + 1] = static_cast<uint8_t>((value >> 8) & 0xFF);
    data[offset + 2] = static_cast<uint8_t>((value >> 16) & 0xFF);
    data[offset + 3] = static_cast<uint8_t>((value >> 24) & 0xFF);
  }

  static void buildPayload(const Signal& signal, CanFrame& frame) {
    const uint32_t c = signal.counter;
    const uint64_t t = frame.timestamp_us;
    for (size_t i = 0; i < kMaxDataBytes; ++i) frame.data[i] = 0;
    switch (signal.id) {
      case 0x100:
        set16(frame.data, 0, static_cast<uint16_t>(1200 + (c % 80)));
        set16(frame.data, 2, static_cast<uint16_t>(1210 + (c % 70)));
        set16(frame.data, 4, static_cast<uint16_t>(1195 + (c % 60)));
        set16(frame.data, 6, static_cast<uint16_t>(1205 + (c % 65)));
        break;
      case 0x120:
        set16(frame.data, 0, static_cast<uint16_t>(900 + (c * 17U) % 3500U));
        frame.data[2] = static_cast<uint8_t>((c * 3U) % 100U);
        frame.data[3] = static_cast<uint8_t>((c / 50U) % 8U);
        frame.data[4] = static_cast<uint8_t>(70 + (c % 20));
        break;
      case 0x1A0: {
        const bool camera_on = ((t / 15000000ULL) % 2ULL) != 0ULL;
        const bool ambient_on = ((t / 8000000ULL) % 2ULL) != 0ULL;
        const bool parking_on = ((t / 12000000ULL) % 2ULL) != 0ULL;
        frame.data[0] = static_cast<uint8_t>((camera_on ? 0x01 : 0x00) |
                                             (ambient_on ? 0x02 : 0x00) |
                                             (parking_on ? 0x04 : 0x00));
        frame.data[1] = static_cast<uint8_t>(c & 0xFF);
        frame.data[2] = static_cast<uint8_t>((c >> 8) & 0xFF);
        frame.data[3] = 0x5A;
        break;
      }
      case 0x2C0: {
        int16_t angle = static_cast<int16_t>((static_cast<int32_t>(c % 200U) - 100) * 30);
        set16(frame.data, 0, static_cast<uint16_t>(angle));
        set16(frame.data, 2, static_cast<uint16_t>((c * 11U) % 500U));
        frame.data[4] = 0x01;
        break;
      }
      case 0x3E0:
        set16(frame.data, 0, static_cast<uint16_t>(13200 + (c % 120)));
        frame.data[2] = static_cast<uint8_t>(75 + (c % 20));
        frame.data[3] = static_cast<uint8_t>(20 + (c % 10));
        break;
      case 0x4A0:
        frame.data[0] = static_cast<uint8_t>(20 + (c % 15));
        frame.data[1] = static_cast<uint8_t>(30 + (c % 20));
        frame.data[2] = static_cast<uint8_t>(40 + (c % 10));
        frame.data[3] = static_cast<uint8_t>(50 + (c % 5));
        break;
      case 0x5B0:
        set32(frame.data, 0, c);
        break;
      default:
        break;
    }
  }
};

}  // namespace volvo

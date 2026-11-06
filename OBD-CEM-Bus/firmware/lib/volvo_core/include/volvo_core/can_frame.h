#pragma once

#include <cstddef>
#include <cstdint>

namespace volvo {

constexpr size_t kMaxDataBytes = 8;

// Ein empfangener CAN-Frame. demo=true kennzeichnet ausschliesslich
// synthetische Daten aus dem Simulationsmodus.
struct CanFrame {
  uint32_t seq = 0;
  uint64_t timestamp_us = 0;
  uint32_t id = 0;
  uint8_t dlc = 0;
  bool extended = false;
  bool demo = false;
  uint8_t data[kMaxDataBytes] = {0};
};

inline bool isValidCanId(uint32_t id, bool extended) {
  return extended ? (id <= 0x1FFFFFFFUL) : (id <= 0x7FFUL);
}

inline bool isValidDlc(uint8_t dlc) { return dlc <= kMaxDataBytes; }

}  // namespace volvo

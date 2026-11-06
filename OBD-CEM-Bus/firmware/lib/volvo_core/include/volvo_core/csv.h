#pragma once

#include <cstddef>
#include <cstdint>
#include <cstdio>

#include "volvo_core/can_frame.h"

namespace volvo {

inline size_t formatCsvHeader(char* out, size_t out_size) {
  return static_cast<size_t>(std::snprintf(
      out, out_size, "seq,timestamp_us,can_id,extended,dlc,data_hex,demo\n"));
}

inline size_t formatCsvFrame(const CanFrame& frame, char* out, size_t out_size) {
  char data_hex[17];
  for (size_t i = 0; i < kMaxDataBytes; ++i) {
    std::snprintf(&data_hex[i * 2], 3, "%02X", frame.data[i]);
  }
  data_hex[16] = '\0';
  return static_cast<size_t>(std::snprintf(
      out, out_size, "%u,%llu,0x%08X,%u,%u,%s,%u\n",
      static_cast<unsigned>(frame.seq),
      static_cast<unsigned long long>(frame.timestamp_us),
      static_cast<unsigned>(frame.id), frame.extended ? 1U : 0U,
      static_cast<unsigned>(frame.dlc), data_hex, frame.demo ? 1U : 0U));
}

}  // namespace volvo

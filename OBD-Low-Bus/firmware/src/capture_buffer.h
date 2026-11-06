#pragma once

#include <cstddef>
#include <cstdint>

#include "volvo_core/can_frame.h"

namespace volvo {

// Aufzeichnungspuffer; bevorzugt im PSRAM, mit kleinerem internen Fallback.
class CaptureBuffer {
 public:
  size_t begin(size_t preferred_capacity, size_t fallback_capacity);
  void end();

  void clear();
  bool push(const volvo::CanFrame& frame);
  size_t size() const { return count_; }
  size_t capacity() const { return capacity_; }
  uint32_t dropped() const { return dropped_; }
  bool enabled() const { return data_ != nullptr; }
  const volvo::CanFrame& at(size_t index) const { return data_[(start_ + index) % capacity_]; }
  size_t copyTo(volvo::CanFrame* destination, size_t max_count) const;

 private:
  volvo::CanFrame* data_ = nullptr;
  size_t capacity_ = 0;
  size_t start_ = 0;
  size_t count_ = 0;
  uint32_t dropped_ = 0;
  bool psram_ = false;
};

}  // namespace volvo

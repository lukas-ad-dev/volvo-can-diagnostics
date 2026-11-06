#include "capture_buffer.h"

#include <esp_heap_caps.h>

namespace volvo {

size_t CaptureBuffer::begin(size_t preferred_capacity, size_t fallback_capacity) {
  end();
  if (preferred_capacity == 0) return 0;

  data_ = static_cast<volvo::CanFrame*>(
      heap_caps_malloc(preferred_capacity * sizeof(volvo::CanFrame),
                       MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
  if (data_ != nullptr) {
    capacity_ = preferred_capacity;
    psram_ = true;
  } else if (fallback_capacity > 0) {
    data_ = static_cast<volvo::CanFrame*>(
        heap_caps_malloc(fallback_capacity * sizeof(volvo::CanFrame),
                         MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT));
    if (data_ != nullptr) {
      capacity_ = fallback_capacity;
      psram_ = false;
    }
  }
  start_ = 0;
  count_ = 0;
  dropped_ = 0;
  return capacity_;
}

void CaptureBuffer::end() {
  if (data_ != nullptr) {
    heap_caps_free(data_);
    data_ = nullptr;
  }
  capacity_ = 0;
  start_ = 0;
  count_ = 0;
  dropped_ = 0;
  psram_ = false;
}

void CaptureBuffer::clear() {
  start_ = 0;
  count_ = 0;
  dropped_ = 0;
}

bool CaptureBuffer::push(const volvo::CanFrame& frame) {
  if (data_ == nullptr || capacity_ == 0) return false;
  bool dropped = false;
  if (count_ == capacity_) {
    dropped = true;
    ++dropped_;
    start_ = (start_ + 1) % capacity_;
    --count_;
  }
  data_[(start_ + count_) % capacity_] = frame;
  ++count_;
  return !dropped;
}

size_t CaptureBuffer::copyTo(volvo::CanFrame* destination, size_t max_count) const {
  if (data_ == nullptr) return 0;
  size_t n = count_ < max_count ? count_ : max_count;
  for (size_t i = 0; i < n; ++i) destination[i] = at(i);
  return n;
}

}  // namespace volvo

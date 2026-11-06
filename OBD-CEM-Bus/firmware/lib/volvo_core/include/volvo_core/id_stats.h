#pragma once

#include <cstddef>
#include <cstdint>
#include <cstring>

#include "volvo_core/can_frame.h"

namespace volvo {

struct IdAggregate {
  uint32_t id = 0;
  uint32_t count = 0;
  uint32_t payload_changes = 0;
  uint64_t first_us = 0;
  uint64_t last_us = 0;
  uint8_t max_dlc = 0;
  bool extended = false;
  bool used = false;
  bool demo = false;
  uint8_t last_data[kMaxDataBytes] = {0};
  uint8_t or_data[kMaxDataBytes] = {0};
  uint8_t and_data[kMaxDataBytes] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
};

class IdStats {
 public:
  static constexpr size_t kMaxIds = 256;

  void clear() {
    count_ = 0;
    dropped_entries_ = 0;
  }

  size_t size() const { return count_; }
  uint32_t droppedEntries() const { return dropped_entries_; }
  const IdAggregate* entries() const { return entries_; }

  const IdAggregate* find(uint32_t id, bool extended) const {
    for (size_t i = 0; i < count_; ++i) {
      if (entries_[i].id == id && entries_[i].extended == extended) return &entries_[i];
    }
    return nullptr;
  }

  IdAggregate* findMutable(uint32_t id, bool extended) {
    for (size_t i = 0; i < count_; ++i) {
      if (entries_[i].id == id && entries_[i].extended == extended) return &entries_[i];
    }
    return nullptr;
  }

  bool add(const CanFrame& frame) {
    IdAggregate* entry = findMutable(frame.id, frame.extended);
    if (entry == nullptr) {
      if (count_ >= kMaxIds) {
        ++dropped_entries_;
        return false;
      }
      entry = &entries_[count_++];
      *entry = IdAggregate{};
      entry->id = frame.id;
      entry->extended = frame.extended;
      entry->used = true;
      entry->demo = frame.demo;
      entry->count = 1;
      entry->first_us = frame.timestamp_us;
      entry->last_us = frame.timestamp_us;
      entry->max_dlc = frame.dlc;
      for (size_t i = 0; i < frame.dlc; ++i) {
        entry->last_data[i] = frame.data[i];
        entry->or_data[i] = frame.data[i];
        entry->and_data[i] = frame.data[i];
      }
      return true;
    }

    if (frame.timestamp_us > entry->last_us) entry->last_us = frame.timestamp_us;
    entry->demo = entry->demo || frame.demo;
    ++entry->count;
    if (frame.dlc != entry->max_dlc) {
      ++entry->payload_changes;
    } else if (std::memcmp(entry->last_data, frame.data, frame.dlc) != 0) {
      ++entry->payload_changes;
    }
    if (frame.dlc > entry->max_dlc) entry->max_dlc = frame.dlc;
    for (size_t i = 0; i < frame.dlc; ++i) {
      entry->last_data[i] = frame.data[i];
      entry->or_data[i] |= frame.data[i];
      entry->and_data[i] &= frame.data[i];
    }
    return true;
  }

  static double frequencyHz(uint32_t count, uint64_t duration_us) {
    if (duration_us == 0) return 0.0;
    return static_cast<double>(count) * 1000000.0 / static_cast<double>(duration_us);
  }

  double frequencyHz(const IdAggregate& entry) const {
    if (entry.count == 0) return 0.0;
    uint64_t duration = 0;
    if (entry.last_us > entry.first_us) duration = entry.last_us - entry.first_us;
    if (duration < 1000000ULL) duration = 1000000ULL;
    return frequencyHz(entry.count, duration);
  }

 private:
  IdAggregate entries_[kMaxIds] = {};
  size_t count_ = 0;
  uint32_t dropped_entries_ = 0;
};

}  // namespace volvo

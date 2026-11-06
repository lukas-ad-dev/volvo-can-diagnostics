#pragma once

#include <cmath>
#include <cstddef>
#include <cstdint>

#include "volvo_core/can_frame.h"
#include "volvo_core/id_stats.h"

namespace volvo {

constexpr size_t kMaxCompareEntries = 256;

struct PhaseState {
  IdStats stats;
  bool active = false;
  bool valid = false;
  bool demo_seen = false;
  uint64_t start_us = 0;
  uint64_t stop_us = 0;
  uint32_t frames = 0;

  void reset() {
    stats.clear();
    active = false;
    valid = false;
    demo_seen = false;
    start_us = 0;
    stop_us = 0;
    frames = 0;
  }
};

struct CompareEntry {
  uint32_t id = 0;
  bool extended = false;
  bool in_a = false;
  bool in_b = false;
  bool demo = false;
  uint32_t count_a = 0;
  uint32_t count_b = 0;
  double freq_a = 0.0;
  double freq_b = 0.0;
  double freq_delta_pct = 0.0;
  uint8_t dlc_a = 0;
  uint8_t dlc_b = 0;
  uint8_t data_a[kMaxDataBytes] = {0};
  uint8_t data_b[kMaxDataBytes] = {0};
  uint8_t changed_mask = 0;
  uint8_t changed_bits[kMaxDataBytes] = {0};
  uint8_t variable_a[kMaxDataBytes] = {0};
  uint8_t variable_b[kMaxDataBytes] = {0};
  bool payload_changed = false;
  bool frequency_changed = false;
};

struct CompareResult {
  bool ok = false;
  bool demo = false;
  bool truncated = false;
  uint64_t duration_a_us = 0;
  uint64_t duration_b_us = 0;
  size_t entry_count = 0;
  CompareEntry entries[kMaxCompareEntries] = {};
};

class PhaseTracker {
 public:
  bool start(char phase, uint64_t now_us) {
    if (phase == 'A') {
      if (b_.active) return false;
      a_.reset();
      a_.active = true;
      a_.start_us = now_us;
      return true;
    }
    if (phase == 'B') {
      if (a_.active) return false;
      b_.reset();
      b_.active = true;
      b_.start_us = now_us;
      return true;
    }
    return false;
  }

  bool stop(char phase, uint64_t now_us) {
    if (phase == 'A') {
      if (!a_.active) return false;
      a_.stop_us = now_us;
      a_.active = false;
      a_.valid = true;
      return true;
    }
    if (phase == 'B') {
      if (!b_.active) return false;
      b_.stop_us = now_us;
      b_.active = false;
      b_.valid = true;
      return true;
    }
    return false;
  }

  void reset() {
    a_.reset();
    b_.reset();
  }

  void add(const CanFrame& frame) {
    if (a_.active) {
      a_.stats.add(frame);
      ++a_.frames;
      a_.demo_seen = a_.demo_seen || frame.demo;
    } else if (b_.active) {
      b_.stats.add(frame);
      ++b_.frames;
      b_.demo_seen = b_.demo_seen || frame.demo;
    }
  }

  bool active(char phase) const { return phase == 'A' ? a_.active : (phase == 'B' ? b_.active : false); }
  bool valid(char phase) const { return phase == 'A' ? a_.valid : (phase == 'B' ? b_.valid : false); }
  uint32_t frames(char phase) const { return phase == 'A' ? a_.frames : (phase == 'B' ? b_.frames : 0); }
  bool demoSeen(char phase) const { return phase == 'A' ? a_.demo_seen : (phase == 'B' ? b_.demo_seen : false); }

  uint64_t durationUs(char phase, uint64_t now_us) const {
    const PhaseState& state = phase == 'A' ? a_ : b_;
    if (!state.active && !state.valid) return 0;
    uint64_t end = state.active ? now_us : state.stop_us;
    return end > state.start_us ? (end - state.start_us) : 0;
  }

  void compare(CompareResult& result, uint64_t now_us) const {
    result = CompareResult{};
    bool a_ready = a_.valid || a_.active;
    bool b_ready = b_.valid || b_.active;
    if (!a_ready || !b_ready) {
      result.ok = false;
      return;
    }
    result.ok = true;
    result.demo = a_.demo_seen || b_.demo_seen;
    result.duration_a_us = durationUs('A', now_us);
    result.duration_b_us = durationUs('B', now_us);
    if (result.duration_a_us == 0) result.duration_a_us = 1;
    if (result.duration_b_us == 0) result.duration_b_us = 1;

    for (size_t i = 0; i < a_.stats.size(); ++i) {
      const IdAggregate& a = a_.stats.entries()[i];
      const IdAggregate* b = b_.stats.find(a.id, a.extended);
      if (result.entry_count >= kMaxCompareEntries) {
        result.truncated = true;
        return;
      }
      CompareEntry& out = result.entries[result.entry_count++];
      fillEntry(out, &a, b, result.duration_a_us, result.duration_b_us);
    }

    for (size_t i = 0; i < b_.stats.size(); ++i) {
      const IdAggregate& b = b_.stats.entries()[i];
      if (a_.stats.find(b.id, b.extended) != nullptr) continue;
      if (result.entry_count >= kMaxCompareEntries) {
        result.truncated = true;
        return;
      }
      CompareEntry& out = result.entries[result.entry_count++];
      fillEntry(out, nullptr, &b, result.duration_a_us, result.duration_b_us);
    }
  }

 private:
  static void fillEntry(CompareEntry& out, const IdAggregate* a, const IdAggregate* b,
                        uint64_t duration_a_us, uint64_t duration_b_us) {
    out.in_a = (a != nullptr);
    out.in_b = (b != nullptr);
    out.id = a != nullptr ? a->id : b->id;
    out.extended = a != nullptr ? a->extended : b->extended;
    out.demo = (a != nullptr && a->demo) || (b != nullptr && b->demo);

    if (a != nullptr) {
      out.count_a = a->count;
      out.dlc_a = a->max_dlc;
      for (size_t i = 0; i < kMaxDataBytes; ++i) {
        out.data_a[i] = a->last_data[i];
        out.variable_a[i] = i < a->max_dlc ? (a->or_data[i] ^ a->and_data[i]) : 0;
      }
      out.freq_a = IdStats::frequencyHz(a->count, duration_a_us);
    }
    if (b != nullptr) {
      out.count_b = b->count;
      out.dlc_b = b->max_dlc;
      for (size_t i = 0; i < kMaxDataBytes; ++i) {
        out.data_b[i] = b->last_data[i];
        out.variable_b[i] = i < b->max_dlc ? (b->or_data[i] ^ b->and_data[i]) : 0;
      }
      out.freq_b = IdStats::frequencyHz(b->count, duration_b_us);
    }

    if (a != nullptr && b != nullptr) {
      uint8_t max_dlc = out.dlc_a > out.dlc_b ? out.dlc_a : out.dlc_b;
      if (out.dlc_a != out.dlc_b) out.payload_changed = true;
      for (size_t i = 0; i < kMaxDataBytes; ++i) {
        out.changed_bits[i] = out.data_a[i] ^ out.data_b[i];
        if (i < max_dlc && out.changed_bits[i] != 0) {
          out.changed_mask |= static_cast<uint8_t>(1U << i);
          out.payload_changed = true;
        }
      }
      if (out.freq_a > 0.0) {
        out.freq_delta_pct = (out.freq_b - out.freq_a) * 100.0 / out.freq_a;
      }
      double diff = std::fabs(out.freq_b - out.freq_a);
      double rel = std::fabs(out.freq_delta_pct);
      out.frequency_changed = diff > 0.2 && (out.freq_a == 0.0 || rel > 20.0);
    }
  }

  PhaseState a_;
  PhaseState b_;
};

}  // namespace volvo

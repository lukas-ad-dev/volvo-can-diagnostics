#include <unity.h>

#include <cstring>

#include "volvo_core/can_frame.h"
#include "volvo_core/csv.h"
#include "volvo_core/demo_generator.h"
#include "volvo_core/hardware_pins.h"
#include "volvo_core/id_stats.h"
#include "volvo_core/ndjson.h"
#include "volvo_core/output_guard.h"
#include "volvo_core/phase_tracker.h"
#include "volvo_core/ring_buffer.h"

using namespace volvo;

static CompareResult g_compare;

static CanFrame makeFrame(uint32_t id, uint64_t timestamp_us, uint8_t value,
                          bool extended = false, bool demo = false) {
  CanFrame frame;
  frame.id = id;
  frame.timestamp_us = timestamp_us;
  frame.dlc = 8;
  frame.extended = extended;
  frame.demo = demo;
  std::memset(frame.data, 0, sizeof(frame.data));
  frame.data[0] = value;
  frame.data[1] = static_cast<uint8_t>(value + 1);
  return frame;
}

void test_ring_buffer_overwrites_and_counts(void) {
  RingBuffer<int, 2> ring;
  TEST_ASSERT_TRUE(ring.push(1));
  TEST_ASSERT_TRUE(ring.push(2));
  TEST_ASSERT_TRUE(ring.full());
  TEST_ASSERT_FALSE(ring.push(3));
  TEST_ASSERT_EQUAL_UINT32(1, ring.dropped());
  TEST_ASSERT_EQUAL_UINT32(2, ring.size());
  TEST_ASSERT_EQUAL_INT(2, ring.at(0));
  TEST_ASSERT_EQUAL_INT(3, ring.at(1));
  ring.clear();
  TEST_ASSERT_TRUE(ring.empty());
}

void test_id_stats_aggregation(void) {
  IdStats stats;
  stats.add(makeFrame(0x100, 0, 0x01));
  stats.add(makeFrame(0x100, 1000000, 0x03));
  TEST_ASSERT_EQUAL_UINT32(1, stats.size());
  const IdAggregate* entry = stats.find(0x100, false);
  TEST_ASSERT_NOT_NULL(entry);
  TEST_ASSERT_EQUAL_UINT32(2, entry->count);
  TEST_ASSERT_EQUAL_UINT32(1, entry->payload_changes);
  TEST_ASSERT_EQUAL_UINT32(0x03, entry->or_data[0]);
  TEST_ASSERT_EQUAL_UINT32(0x01, entry->and_data[0]);
  TEST_ASSERT_EQUAL_UINT32(0x02, static_cast<uint32_t>(entry->or_data[0] ^ entry->and_data[0]));
  TEST_ASSERT_DOUBLE_WITHIN(0.001, 2.0, stats.frequencyHz(*entry));
}

void test_phase_compare_new_and_changed(void) {
  PhaseTracker tracker;
  TEST_ASSERT_TRUE(tracker.start('A', 0));
  for (int i = 0; i < 10; ++i) {
    tracker.add(makeFrame(0x100, static_cast<uint64_t>(i) * 100000ULL, 0x01));
  }
  TEST_ASSERT_TRUE(tracker.stop('A', 1000000));

  TEST_ASSERT_TRUE(tracker.start('B', 2000000));
  for (int i = 0; i < 10; ++i) {
    tracker.add(makeFrame(0x100, 2000000ULL + static_cast<uint64_t>(i) * 100000ULL, 0x03));
  }
  tracker.add(makeFrame(0x200, 2500000ULL, 0x7F));
  TEST_ASSERT_TRUE(tracker.stop('B', 3000000));

  tracker.compare(g_compare, 4000000);
  TEST_ASSERT_TRUE(g_compare.ok);
  TEST_ASSERT_EQUAL_UINT32(2, g_compare.entry_count);
  bool found_100 = false;
  bool found_200 = false;
  for (size_t i = 0; i < g_compare.entry_count; ++i) {
    const CompareEntry& entry = g_compare.entries[i];
    if (entry.id == 0x100) {
      found_100 = true;
      TEST_ASSERT_TRUE(entry.in_a);
      TEST_ASSERT_TRUE(entry.in_b);
      TEST_ASSERT_TRUE(entry.payload_changed);
      TEST_ASSERT_EQUAL_UINT8(0x02, entry.changed_bits[0]);
      TEST_ASSERT_DOUBLE_WITHIN(0.01, 10.0, entry.freq_a);
      TEST_ASSERT_DOUBLE_WITHIN(0.01, 10.0, entry.freq_b);
    }
    if (entry.id == 0x200) {
      found_200 = true;
      TEST_ASSERT_FALSE(entry.in_a);
      TEST_ASSERT_TRUE(entry.in_b);
    }
  }
  TEST_ASSERT_TRUE(found_100);
  TEST_ASSERT_TRUE(found_200);
}

void test_phase_start_rejects_parallel_phase(void) {
  PhaseTracker tracker;
  TEST_ASSERT_TRUE(tracker.start('A', 0));
  TEST_ASSERT_FALSE(tracker.start('B', 1));
  TEST_ASSERT_TRUE(tracker.stop('A', 10));
  TEST_ASSERT_TRUE(tracker.start('B', 20));
}

void test_demo_generator_marks_frames(void) {
  DemoGenerator generator;
  generator.reset(0);
  uint32_t seq = 0;
  CanFrame frames[64];
  bool saw_demo = false;
  bool camera_off = false;
  bool camera_on = false;
  for (uint64_t t = 0; t <= 16100000ULL; t += 100000ULL) {
    size_t count = generator.poll(t, frames, 64, seq);
    for (size_t i = 0; i < count; ++i) {
      TEST_ASSERT_TRUE(frames[i].demo);
      TEST_ASSERT_TRUE(isValidCanId(frames[i].id, frames[i].extended));
      TEST_ASSERT_TRUE(frames[i].dlc <= kMaxDataBytes);
      saw_demo = true;
      if (frames[i].id == 0x1A0) {
        if ((frames[i].data[0] & 0x01) == 0) camera_off = true;
        else camera_on = true;
      }
    }
  }
  TEST_ASSERT_TRUE(saw_demo);
  TEST_ASSERT_TRUE(camera_off);
  TEST_ASSERT_TRUE(camera_on);
}

void test_hardware_pin_mapping(void) {
  TEST_ASSERT_EQUAL_UINT8(15, pins::kCanTx);
  TEST_ASSERT_EQUAL_UINT8(16, pins::kCanRx);
  TEST_ASSERT_EQUAL_UINT8(17, pins::kRs485Tx);
  TEST_ASSERT_EQUAL_UINT8(18, pins::kRs485Rx);
  TEST_ASSERT_NOT_EQUAL(pins::kCanTx, pins::kRs485Tx);
  TEST_ASSERT_NOT_EQUAL(pins::kCanTx, pins::kRs485Rx);
  TEST_ASSERT_NOT_EQUAL(pins::kCanRx, pins::kRs485Tx);
  TEST_ASSERT_NOT_EQUAL(pins::kCanRx, pins::kRs485Rx);
  TEST_ASSERT_EQUAL_UINT8(1, pins::kOutput1);
  TEST_ASSERT_EQUAL_UINT8(2, pins::kOutput2);
}

void test_usb_ndjson_format(void) {
  CanFrame frame = makeFrame(0x1A0, 1234567ULL, 0x11);
  frame.seq = 42;
  char line[256];
  size_t length = formatCanNdjson(frame, line, sizeof(line));
  TEST_ASSERT_TRUE(length > 0);
  TEST_ASSERT_NOT_NULL(strstr(line, "\"type\":\"can\""));
  TEST_ASSERT_NOT_NULL(strstr(line, "\"seq\":42"));
  TEST_ASSERT_NOT_NULL(strstr(line, "\"id_hex\":\"0x1A0\""));
  TEST_ASSERT_NOT_NULL(strstr(line, "\"data\":\"1112000000000000\""));
  TEST_ASSERT_NOT_NULL(strstr(line, "\"demo\":false"));
}

void test_output_guard_blocks_everything(void) {
  OutputGuard guard;
  TEST_ASSERT_FALSE(guard.requestOutput(1, true));
  TEST_ASSERT_FALSE(guard.requestOutput(2, true));
  TEST_ASSERT_FALSE(guard.requestOutput(1, false));
  TEST_ASSERT_FALSE(guard.outputsEnabled());
}

void test_csv_export(void) {
  CanFrame frame = makeFrame(0x1A0, 1234567ULL, 0x11);
  char header[128];
  char line[256];
  formatCsvHeader(header, sizeof(header));
  formatCsvFrame(frame, line, sizeof(line));
  TEST_ASSERT_NOT_NULL(strstr(header, "seq,timestamp_us,can_id"));
  TEST_ASSERT_NOT_NULL(strstr(line, "0x000001A0"));
  TEST_ASSERT_NOT_NULL(strstr(line, "1112000000000000"));
  TEST_ASSERT_NOT_NULL(strstr(line, ",0\n"));
}

void setUp(void) {}
void tearDown(void) {}

int main(int argc, char** argv) {
  (void)argc;
  (void)argv;
  UNITY_BEGIN();
  RUN_TEST(test_ring_buffer_overwrites_and_counts);
  RUN_TEST(test_id_stats_aggregation);
  RUN_TEST(test_phase_compare_new_and_changed);
  RUN_TEST(test_phase_start_rejects_parallel_phase);
  RUN_TEST(test_demo_generator_marks_frames);
  RUN_TEST(test_hardware_pin_mapping);
  RUN_TEST(test_usb_ndjson_format);
  RUN_TEST(test_output_guard_blocks_everything);
  RUN_TEST(test_csv_export);
  return UNITY_END();
}

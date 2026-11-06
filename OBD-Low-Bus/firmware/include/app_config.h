#pragma once

#include <cstddef>
#include <cstdint>

#include "secrets.h"
#include "volvo_core/hardware_pins.h"

namespace volvo {

// Einzige Quelle der Hardwarebelegung: volvo_core/hardware_pins.h.
// Dort verhindern static_asserts versehentliche Aenderungen der bestaetigten
// Waveshare-Belegung (CAN TX=GPIO15, RX=GPIO16; RS485 TX=GPIO17, RX=GPIO18).
constexpr uint8_t kPinCanTx = pins::kCanTx;
constexpr uint8_t kPinCanRx = pins::kCanRx;
constexpr uint8_t kPinRs485Tx = pins::kRs485Tx;
constexpr uint8_t kPinRs485Rx = pins::kRs485Rx;
constexpr uint8_t kPinRs485De = pins::kRs485De;

// Externe Klemmen GPIO1/GPIO2 des Waveshare-Boards (SH1.0).
// In V0.1 hochohmig und niemals aktiv getrieben.
constexpr uint8_t kPinOutput1 = pins::kOutput1;
constexpr uint8_t kPinOutput2 = pins::kOutput2;

constexpr uint32_t kDefaultBitrateKbps = 500;
constexpr uint32_t kSupportedBitrates[] = {125, 250, 500};
constexpr size_t kSupportedBitrateCount = sizeof(kSupportedBitrates) / sizeof(kSupportedBitrates[0]);

constexpr size_t kLiveRingCapacity = 1024;
constexpr size_t kCaptureCapacity = 16384;
constexpr size_t kCaptureFallbackCapacity = 2048;
constexpr size_t kMaxIds = 256;
constexpr size_t kMaxHttpMessages = 200;
constexpr size_t kMaxStreamClients = 2;
constexpr uint32_t kTwaiRxQueueLength = 1024;
constexpr int kCanReceiveBurst = 64;
constexpr size_t kUsbLoggerQueueLength = 2048;

constexpr uint16_t kHttpPort = 80;
constexpr uint16_t kStreamPort = 81;

constexpr char kApSsid[] = VOLVO_AP_SSID;
static_assert(sizeof(VOLVO_AP_PASSWORD) - 1 >= 12, "WLAN-Passwort muss mindestens 12 Zeichen lang sein");

constexpr uint32_t kCanTaskStack = 8192;
constexpr uint32_t kStreamTaskStack = 4096;
constexpr uint32_t kUsbLoggerTaskStack = 4096;
constexpr uint32_t kHttpTaskStack = 8192;

}  // namespace volvo

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

// TWAI-TX wird auf einen ungenutzten Dummy-Pin gelegt. Der echte
// Transceiver-TXD (GPIO15) bleibt dauerhaft INPUT_PULLUP und kann daher
// auch bei einem Treiber-/Init-Glitch nicht dominant werden.
constexpr uint8_t kPinCanTwaiTx = 48;
static_assert(kPinCanTwaiTx == 48, "Dummy-TWAI-TX muss GPIO48 sein");
static_assert(kPinCanTwaiTx != kPinCanTx && kPinCanTwaiTx != kPinCanRx,
              "Dummy-TWAI-TX darf nicht auf den CAN-Pins liegen");
static_assert(kPinCanTwaiTx != kPinRs485Tx && kPinCanTwaiTx != kPinRs485Rx &&
                  kPinCanTwaiTx != kPinRs485De,
              "Dummy-TWAI-TX darf nicht auf den RS485-Pins liegen");
static_assert(kPinCanTwaiTx != kPinOutput1 && kPinCanTwaiTx != kPinOutput2,
              "Dummy-TWAI-TX darf nicht auf den Ausgangs-Pins liegen");
static_assert(kPinCanTwaiTx != 0 && kPinCanTwaiTx != 3 && kPinCanTwaiTx != 45 &&
                  kPinCanTwaiTx != 46,
              "Dummy-TWAI-TX darf kein Bootstrap-Pin sein");

// Fester, passiver Testbetrieb auf Basis der ausgewerteten 500-kbit/s-Logs.
constexpr uint32_t kDefaultBitrateKbps = 500;
constexpr uint32_t kSupportedBitrates[] = {500};
constexpr size_t kSupportedBitrateCount = sizeof(kSupportedBitrates) / sizeof(kSupportedBitrates[0]);

// Freigabe fuer den heutigen read-only Live-Test. Kein Auto-Start:
// TWAI wird weiterhin nur durch explizites START installiert.
constexpr bool kAllowCanStart = true;

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

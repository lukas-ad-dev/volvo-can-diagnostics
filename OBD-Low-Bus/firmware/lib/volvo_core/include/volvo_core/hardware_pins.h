#pragma once

#include <cstdint>

// Zentrale Hardwarebelegung. Nur hier duerfen die Pins geaendert werden.
//
// Am 04.11.2026 erneut anhand der offiziellen Waveshare-Quellen verifiziert:
//   Schaltplan: https://files.waveshare.com/wiki/ESP32-S3-RS485-CAN/ESP32-S3-RS485-CAN-Schematic.pdf
//   Demo:      ESP32-S3-RS485-CAN-Demo.zip, WS_GPIO.h (TXD2=15, RXD2=16, TXD1=17, RXD1=18)
//   Doku:      https://docs.waveshare.com/ESP32-S3-RS485-CAN
//
// Bestaetigte Belegung:
//   CAN (TWAI):  TX = GPIO15, RX = GPIO16
//   RS485:       TX = GPIO17, RX = GPIO18
//   RS485 DE:    GPIO21
//
// Die fruehere 17/18-Zuordnung fuer CAN war falsch und ist hier bewusst
// korrigiert. Die static_asserts verhindern ein versehentliches Zurueckfallen.
namespace volvo {
namespace pins {

constexpr uint8_t kCanTx = 15;
constexpr uint8_t kCanRx = 16;
constexpr uint8_t kRs485Tx = 17;
constexpr uint8_t kRs485Rx = 18;
constexpr uint8_t kRs485De = 21;

constexpr uint8_t kOutput1 = 1;
constexpr uint8_t kOutput2 = 2;

static_assert(kCanTx == 15, "CAN TX muss GPIO15 sein (Waveshare WS_GPIO.h TXD2)");
static_assert(kCanRx == 16, "CAN RX muss GPIO16 sein (Waveshare WS_GPIO.h RXD2)");
static_assert(kRs485Tx == 17, "RS485 TX muss GPIO17 sein (Waveshare WS_GPIO.h TXD1)");
static_assert(kRs485Rx == 18, "RS485 RX muss GPIO18 sein (Waveshare WS_GPIO.h RXD1)");
static_assert(kCanTx != kRs485Tx && kCanTx != kRs485Rx && kCanRx != kRs485Tx && kCanRx != kRs485Rx,
              "CAN- und RS485-Pins duerfen sich nicht ueberschneiden");
static_assert(kCanTx != kOutput1 && kCanTx != kOutput2 && kCanRx != kOutput1 && kCanRx != kOutput2,
              "CAN-Pins duerfen nicht auf den Ausgangs-GPIOs liegen");
static_assert(kRs485Tx != kOutput1 && kRs485Tx != kOutput2 && kRs485Rx != kOutput1 && kRs485Rx != kOutput2,
              "RS485-Pins duerfen nicht auf den Ausgangs-GPIOs liegen");

}  // namespace pins
}  // namespace volvo

#pragma once

#include <cstdint>

namespace volvo {

// Harte Sicherheitssperre fuer die erste Version:
// Es gibt keine verifizierte Treiber-/Relais-Hardware, deshalb darf
// kein Ausgang jemals eingeschaltet werden. Auch ein versehentlicher
// Aufruf mit on=true bleibt wirkungslos. Die Firmware treibt die Pins
// nicht einmal auf LOW, weil LOW-aktive Relais dadurch einschalten
// koennten; sie bleiben hochohmig (INPUT).
class OutputGuard {
 public:
  static constexpr bool kHardwareVerified = false;

  bool requestOutput(uint8_t channel, bool on) {
    (void)channel;
    (void)on;
    return false;
  }

  bool outputsEnabled() const { return false; }
};

}  // namespace volvo

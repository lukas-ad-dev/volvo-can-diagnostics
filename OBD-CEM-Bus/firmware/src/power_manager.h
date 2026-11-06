#pragma once

#include <Arduino.h>
#include <WiFi.h>

#include "output_control.h"

namespace volvo {

enum class PowerState : uint8_t { Active, PreparingSleep, SleepPrepared };

// Architektur fuer spaetere Energiesparfunktionen.
// WICHTIG: Es wird in V0.1 kein Deep Sleep ausgeloest. Der ESP32 verliert
// dabei TWAI/WLAN; ein Aufwachen per CAN erfordert zusaetzliche Hardware
// oder ein verifiziertes Wake-Signal. CAN-Stille allein ist kein Beweis
// fuer Fahrzeug-Ruhe.
class PowerManager {
 public:
  void begin();
  PowerState state() const { return state_; }
  bool prepareSleep(OutputControl& outputs);
  void noteCanActivity(uint64_t now_us);
  bool vehicleSleepCandidate(uint64_t now_us) const;
  const char* stateName() const;

 private:
  PowerState state_ = PowerState::Active;
  uint64_t last_can_activity_us_ = 0;
};

}  // namespace volvo

#include "power_manager.h"

#include "usb_logger.h"

namespace volvo {

void PowerManager::begin() {
  state_ = PowerState::Active;
  last_can_activity_us_ = 0;
  usbLogger().diag("PWR", "Energiespararchitektur aktiv; kein automatischer Deep Sleep.");
}

bool PowerManager::prepareSleep(OutputControl& outputs) {
  state_ = PowerState::PreparingSleep;
  outputs.forceSafeState();
  WiFi.mode(WIFI_OFF);
  state_ = PowerState::SleepPrepared;
  usbLogger().diag("PWR", "Schlaf vorbereitet: WLAN aus, Ausgaenge sicher. Kein Deep Sleep gestartet.");
  return true;
}

void PowerManager::noteCanActivity(uint64_t now_us) {
  last_can_activity_us_ = now_us;
}

bool PowerManager::vehicleSleepCandidate(uint64_t now_us) const {
  // Absichtlich immer false: Eine CAN-Pause ist kein verifizierter
  // Fahrzeug-Ruhezustand. Erst nach experimentell bestaetigten Signalen
  // darf hier eine echte Logik entstehen.
  (void)now_us;
  return false;
}

const char* PowerManager::stateName() const {
  switch (state_) {
    case PowerState::PreparingSleep: return "PREPARING_SLEEP";
    case PowerState::SleepPrepared: return "SLEEP_PREPARED";
    default: return "ACTIVE";
  }
}

}  // namespace volvo

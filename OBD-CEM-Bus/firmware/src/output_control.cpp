#include "output_control.h"

#include "usb_logger.h"

namespace volvo {

void OutputControl::begin() {
  forceSafeState();
  usbLogger().diag("OUT", "GPIO1/GPIO2 hochohmig (INPUT), nicht angesteuert; Ausgaenge in V0.1 gesperrt.");
}

void OutputControl::forceSafeState() {
  // Bewusst kein digitalWrite: Ein LOW-Pegel wuerde ein LOW-aktives Relais
  // einschalten. Bis eine konkrete Treiberschaltung definiert ist, bleiben
  // beide Pins hochohmig. Die externe Beschaltung muss den inaktiven Zustand
  // festlegen (z. B. Pull-up fuer ein LOW-aktives Relais).
  pinMode(kPinOutput1, INPUT);
  pinMode(kPinOutput2, INPUT);
}

bool OutputControl::setOutput(uint8_t channel, bool on) {
  (void)channel;
  (void)on;
  forceSafeState();
  return false;
}

bool OutputControl::outputState(uint8_t channel) const {
  (void)channel;
  return false;
}

}  // namespace volvo

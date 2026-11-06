#pragma once

#include <Arduino.h>

#include "app_config.h"
#include "volvo_core/output_guard.h"

namespace volvo {

class OutputControl {
 public:
  void begin();
  void forceSafeState();
  bool setOutput(uint8_t channel, bool on);
  bool outputState(uint8_t channel) const;
  bool hardwareEnabled() const { return guard_.outputsEnabled(); }

 private:
  OutputGuard guard_;
};

}  // namespace volvo

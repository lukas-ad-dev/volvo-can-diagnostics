#pragma once

#include <Arduino.h>
#include <Preferences.h>

#include "app_config.h"

namespace volvo {

class Settings {
 public:
  void begin();
  uint32_t bitrateKbps() const { return bitrate_; }
  bool demoEnabled() const { return demo_; }
  bool setBitrate(uint32_t kbps);
  bool setDemo(bool enabled);
  static bool isSupportedBitrate(uint32_t kbps);

 private:
  Preferences prefs_;
  uint32_t bitrate_ = kDefaultBitrateKbps;
  bool demo_ = false;
};

}  // namespace volvo

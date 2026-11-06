#include "settings.h"

namespace volvo {

void Settings::begin() {
  prefs_.begin("volvocan", false);
  uint32_t stored_bitrate = prefs_.getUInt("bitrate", kDefaultBitrateKbps);
  if (!isSupportedBitrate(stored_bitrate)) stored_bitrate = kDefaultBitrateKbps;
  bitrate_ = stored_bitrate;
  demo_ = prefs_.getBool("demo", false);
}

bool Settings::isSupportedBitrate(uint32_t kbps) {
  for (size_t i = 0; i < kSupportedBitrateCount; ++i) {
    if (kSupportedBitrates[i] == kbps) return true;
  }
  return false;
}

bool Settings::setBitrate(uint32_t kbps) {
  if (!isSupportedBitrate(kbps)) return false;
  bitrate_ = kbps;
  prefs_.putUInt("bitrate", bitrate_);
  return true;
}

bool Settings::setDemo(bool enabled) {
  demo_ = enabled;
  prefs_.putBool("demo", demo_);
  return true;
}

}  // namespace volvo

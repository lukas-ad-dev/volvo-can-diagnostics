#include <Arduino.h>
#include <WiFi.h>
#include <esp_heap_caps.h>

#include "app_config.h"
#include "can_manager.h"
#include "output_control.h"
#include "power_manager.h"
#include "settings.h"
#include "stream_server.h"
#include "usb_logger.h"
#include "web_server.h"

using namespace volvo;

namespace {
Settings g_settings;
CanManager g_can;
StreamServer g_stream;
WebServerApp g_web;
OutputControl g_outputs;
PowerManager g_power;

bool startAccessPoint() {
  WiFi.persistent(false);
  WiFi.mode(WIFI_AP);
  delay(150);

  IPAddress ip(192, 168, 4, 1);
  IPAddress gateway(192, 168, 4, 1);
  IPAddress subnet(255, 255, 255, 0);
  WiFi.softAPConfig(ip, gateway, subnet);

  for (int attempt = 1; attempt <= 5; ++attempt) {
    if (WiFi.softAP(kApSsid, VOLVO_AP_PASSWORD, 6, false, 4)) {
      WiFi.setSleep(false);
      usbLogger().diag("WLAN", "AP '%s' gestartet, IP %s", kApSsid,
                       WiFi.softAPIP().toString().c_str());
      return true;
    }
    usbLogger().diag("WLAN", "AP-Start fehlgeschlagen (Versuch %d/5)", attempt);
    delay(700);
  }
  return false;
}
}  // namespace

void setup() {
  usbLogger().begin();
  delay(350);
  usbLogger().diag("BOOT", "Volvo CAN Control V0.1 - PASSIVE ANALYSE");
  usbLogger().diag("BOOT", "TWAI ausschliesslich LISTEN_ONLY, kein Senden.");
  usbLogger().diag("BOOT", "GPIO1/GPIO2 hochohmig (INPUT), nicht angesteuert.");

  g_settings.begin();
  g_outputs.begin();
  g_power.begin();

  if (!startAccessPoint()) {
    usbLogger().diag("WLAN", "Kein Access Point. Weboberflaeche bleibt ohne Netzwerk.");
  }

  g_can.begin(&g_settings);
  g_web.begin(&g_settings, &g_can, &g_outputs, &g_power);
  g_stream.begin(&g_can);

  usbLogger().diag("SYS", "Heap frei: %u Bytes, PSRAM frei: %u Bytes, PSRAM gesamt: %u Bytes, PSRAM erkannt: %s",
                   static_cast<unsigned>(ESP.getFreeHeap()),
                   static_cast<unsigned>(heap_caps_get_free_size(MALLOC_CAP_SPIRAM)),
                   static_cast<unsigned>(heap_caps_get_total_size(MALLOC_CAP_SPIRAM)),
                   psramFound() ? "ja" : "nein");
}

void loop() {
  g_web.loop();
  delay(2);
}

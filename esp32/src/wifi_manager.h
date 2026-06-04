#pragma once

#include <Arduino.h>
#include <WiFi.h>

#include "config.h"

class DashboardWiFi {
 public:
  void wifi_init() {
    WiFi.mode(WIFI_STA);
    WiFi.persistent(false);
    WiFi.setAutoReconnect(true);
    WiFi.begin(WIFI_SSID, WIFI_PASS);

    uint32_t started = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - started < 15000) {
      delay(250);
      Serial.print('.');
    }
    Serial.println();

    if (WiFi.status() == WL_CONNECTED) {
      retry_delay_ms_ = WIFI_RETRY_MIN_MS;
      next_retry_ms_ = 0;
      Serial.print("WiFi connected: ");
      Serial.println(WiFi.localIP());
    } else {
      next_retry_ms_ = millis() + retry_delay_ms_;
      Serial.println("WiFi initial connection failed");
    }
  }

  bool wifi_ensure() {
    if (WiFi.status() == WL_CONNECTED) {
      retry_delay_ms_ = WIFI_RETRY_MIN_MS;
      next_retry_ms_ = 0;
      return true;
    }

    uint32_t now = millis();
    if (next_retry_ms_ != 0 && static_cast<int32_t>(now - next_retry_ms_) < 0) {
      return false;
    }

    Serial.println("WiFi reconnecting");
    WiFi.disconnect(false, false);
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    next_retry_ms_ = now + retry_delay_ms_;
    retry_delay_ms_ = min<uint32_t>(retry_delay_ms_ * 2, WIFI_RETRY_MAX_MS);
    return false;
  }

 private:
  uint32_t retry_delay_ms_ = WIFI_RETRY_MIN_MS;
  uint32_t next_retry_ms_ = 0;
};

static DashboardWiFi wifi_manager;

inline void wifi_init() {
  wifi_manager.wifi_init();
}

inline bool wifi_ensure() {
  return wifi_manager.wifi_ensure();
}

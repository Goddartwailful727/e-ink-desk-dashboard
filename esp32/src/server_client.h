#pragma once

#include <Arduino.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClient.h>

#include "config.h"

extern String current_etag;

static String pending_etag;

class DashboardClient {
 public:
  bool client_check() {
    if (WiFi.status() != WL_CONNECTED) {
      return false;
    }

    HTTPClient http;
    http.setTimeout(10000);
    if (!http.begin(CHECK_URL)) {
      Serial.println("HTTP check begin failed");
      return false;
    }

    int code = http.GET();
    if (code != HTTP_CODE_OK) {
      Serial.printf("HTTP check failed: %d\n", code);
      http.end();
      return false;
    }

    String body = http.getString();
    http.end();

    String etag = parse_etag(body);
    if (etag.length() == 0) {
      Serial.println("HTTP check missing etag");
      return false;
    }

    if (etag == current_etag) {
      return false;
    }

    pending_etag = etag;
    Serial.print("New etag: ");
    Serial.println(pending_etag);
    return true;
  }

  bool client_download(uint8_t* black_buf, uint8_t* red_buf) {
    if (black_buf == nullptr || red_buf == nullptr || WiFi.status() != WL_CONNECTED) {
      return false;
    }

    HTTPClient http;
    http.setTimeout(20000);
    if (!http.begin(RAW_URL)) {
      Serial.println("HTTP raw begin failed");
      return false;
    }

    int code = http.GET();
    if (code != HTTP_CODE_OK) {
      Serial.printf("HTTP raw failed: %d\n", code);
      http.end();
      return false;
    }

    int len = http.getSize();
    const size_t expected = FRAME_BYTES * 2;
    if (len >= 0 && static_cast<size_t>(len) != expected) {
      Serial.printf("HTTP raw size mismatch: %d\n", len);
      http.end();
      return false;
    }

    WiFiClient* stream = http.getStreamPtr();
    bool ok = read_exact(*stream, black_buf, FRAME_BYTES) &&
              read_exact(*stream, red_buf, FRAME_BYTES);
    http.end();

    if (!ok) {
      Serial.println("HTTP raw stream incomplete");
      return false;
    }

    if (pending_etag.length() > 0) {
      current_etag = pending_etag;
      pending_etag = "";
    }
    return true;
  }

 private:
  String parse_etag(const String& body) {
    int key = body.indexOf("\"etag\"");
    if (key < 0) {
      key = body.indexOf("etag");
    }
    if (key < 0) {
      return "";
    }

    int colon = body.indexOf(':', key);
    if (colon < 0) {
      return "";
    }

    int first_quote = body.indexOf('"', colon + 1);
    if (first_quote < 0) {
      return "";
    }

    int second_quote = body.indexOf('"', first_quote + 1);
    if (second_quote < 0) {
      return "";
    }

    return body.substring(first_quote + 1, second_quote);
  }

  bool read_exact(WiFiClient& stream, uint8_t* dst, size_t bytes) {
    size_t offset = 0;
    uint32_t last_read = millis();

    while (offset < bytes) {
      int available = stream.available();
      if (available > 0) {
        size_t chunk = min(bytes - offset, static_cast<size_t>(available));
        int read_count = stream.read(dst + offset, chunk);
        if (read_count > 0) {
          offset += static_cast<size_t>(read_count);
          last_read = millis();
          continue;
        }
      }

      if (!stream.connected() && stream.available() == 0) {
        break;
      }

      if (millis() - last_read > 20000) {
        break;
      }

      delay(1);
    }

    return offset == bytes;
  }
};

static DashboardClient dashboard_client;

inline bool client_check() {
  return dashboard_client.client_check();
}

inline bool client_download(uint8_t* black_buf, uint8_t* red_buf) {
  return dashboard_client.client_download(black_buf, red_buf);
}

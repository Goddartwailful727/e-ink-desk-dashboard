#include <Arduino.h>
#include <esp_task_wdt.h>

#include "config.h"
#include "display_manager.h"
#include "server_client.h"
#include "wifi_manager.h"

uint8_t* black_layer = nullptr;
uint8_t* red_layer = nullptr;
String current_etag;
uint32_t last_poll = 0;

static bool button_was_down = false;

static void alloc_buffers() {
  // Prefer PSRAM, fall back to regular RAM
  if (psramFound()) {
    black_layer = static_cast<uint8_t*>(ps_malloc(FRAME_BYTES));
    red_layer = static_cast<uint8_t*>(ps_malloc(FRAME_BYTES));
  }
  if (black_layer == nullptr) {
    black_layer = static_cast<uint8_t*>(malloc(FRAME_BYTES));
  }
  if (red_layer == nullptr) {
    red_layer = static_cast<uint8_t*>(malloc(FRAME_BYTES));
  }
  if (black_layer == nullptr || red_layer == nullptr) {
    Serial.println("FATAL: Cannot allocate frame buffers");
    while (true) {
      delay(1000);
    }
  }
  memset(black_layer, 0xFF, FRAME_BYTES);
  memset(red_layer, 0xFF, FRAME_BYTES);
  Serial.println(psramFound() ? "[mem] Using PSRAM" : "[mem] Using regular RAM");
}

static void poll_dashboard(bool force) {
  if (!force && millis() - last_poll < POLL_INTERVAL_MS) {
    return;
  }
  last_poll = millis();
  if (!wifi_ensure()) {
    return;
  }
  if (client_check()) {
    Serial.println("Downloading dashboard frame");
    if (client_download(black_layer, red_layer)) {
      Serial.println("Displaying dashboard frame");
      display_frame(black_layer, red_layer);
    }
  }
}

void setup() {
  disableCore0WDT();
  Serial.begin(115200);
  delay(1000);

  alloc_buffers();

  pinMode(PIN_BUTTON, INPUT_PULLUP);

  display_init();
  display_connecting();

  wifi_init();
  if (wifi_ensure()) {
    poll_dashboard(true);
  }
}

void loop() {
  wifi_ensure();

  bool button_down = digitalRead(PIN_BUTTON) == LOW;
  bool button_pressed = button_down && !button_was_down;
  button_was_down = button_down;

  if (button_pressed) {
    poll_dashboard(true);
  } else {
    poll_dashboard(false);
  }

  delay(20);
}

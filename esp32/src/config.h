#pragma once

#include <Arduino.h>

static const char WIFI_SSID[] = "YOUR_WIFI_SSID";
static const char WIFI_PASS[] = "YOUR_WIFI_PASSWORD";

static const String SERVER_BASE = "http://YOUR_SERVER_IP:8646";
static const String CHECK_URL = SERVER_BASE + "/dashboard/check";
static const String RAW_URL = SERVER_BASE + "/dashboard/current.raw";

static constexpr int PIN_EPD_BUSY = 14;
static constexpr int PIN_EPD_CS = 5;
static constexpr int PIN_EPD_DC = 21;
static constexpr int PIN_EPD_RST = 13;
static constexpr int PIN_EPD_MOSI = 17;
static constexpr int PIN_EPD_SCLK = 18;
static constexpr int PIN_BUTTON = 0;

static constexpr uint16_t DISPLAY_WIDTH = 800;
static constexpr uint16_t DISPLAY_HEIGHT = 480;
static constexpr size_t FRAME_BYTES = 48000;

static constexpr uint32_t POLL_INTERVAL_MS = 10000;
static constexpr uint32_t WIFI_RETRY_MIN_MS = 1000;
static constexpr uint32_t WIFI_RETRY_MAX_MS = 30000;

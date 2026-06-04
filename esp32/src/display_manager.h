#pragma once

#include <Arduino.h>
#include <GxEPD2_3C.h>
#include <epd3c/GxEPD2_750c_Z08.h>
#include <SPI.h>

#include "config.h"

class DashboardDisplay {
 public:
  void display_init() {
    SPI.begin(PIN_EPD_SCLK, -1, PIN_EPD_MOSI, PIN_EPD_CS);
    display_.epd2.selectSPI(SPI, SPISettings(4000000, MSBFIRST, SPI_MODE0));
    display_.init(115200);
    display_.setRotation(0);
    display_.setFullWindow();
  }

  void display_connecting() {
    display_.setFullWindow();
    display_.firstPage();
    do {
      display_.fillScreen(GxEPD_WHITE);
      display_.setTextColor(GxEPD_BLACK);
      display_.setTextSize(3);
      display_.setCursor(260, 230);
      display_.print("Connecting...");
    } while (display_.nextPage());
  }

  void display_frame(const uint8_t* black, const uint8_t* red) {
    if (black == nullptr || red == nullptr) {
      return;
    }

    display_.setFullWindow();
    display_.firstPage();
    do {
      for (uint16_t y = 0; y < DISPLAY_HEIGHT; ++y) {
        for (uint16_t x = 0; x < DISPLAY_WIDTH; ++x) {
          size_t idx = (static_cast<size_t>(y) * DISPLAY_WIDTH + x) >> 3;
          uint8_t mask = 0x80 >> (x & 7);
          bool black_bit = (black[idx] & mask) != 0;
          bool red_bit = (red[idx] & mask) != 0;
          uint16_t color = GxEPD_WHITE;

          if (!black_bit && red_bit) {
            color = GxEPD_BLACK;
          } else if (black_bit && !red_bit) {
            color = GxEPD_RED;
          }

          display_.drawPixel(x, y, color);
        }
      }
    } while (display_.nextPage());
  }

  void display_clear() {
    display_.setFullWindow();
    display_.firstPage();
    do {
      display_.fillScreen(GxEPD_WHITE);
    } while (display_.nextPage());
  }

 private:
  GxEPD2_3C<GxEPD2_750c_Z08, 32> display_{
      GxEPD2_750c_Z08(PIN_EPD_CS, PIN_EPD_DC, PIN_EPD_RST, PIN_EPD_BUSY)};
};

static DashboardDisplay dashboard_display;

inline void display_init() {
  dashboard_display.display_init();
}

inline void display_connecting() {
  dashboard_display.display_connecting();
}

inline void display_frame(const uint8_t* black, const uint8_t* red) {
  dashboard_display.display_frame(black, red);
}

inline void display_clear() {
  dashboard_display.display_clear();
}

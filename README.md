# Kivy Selfie

Simple Kivy GUI for a photobooth that takes 3 pictures to print them with a thermal printer
and save the pictures with optionally an email address (to send them after the event).

The email addresses and pictures are simply appended to a CSV file.


## Hardware requirements

The hardware used:

- Pi & co
  * Raspberry Pi 2 model B
  * Camera Pi v2.1
  * 7'' Raspberry pi Touchscreen
  * Power supply of 5V/2.5A (official power supply for Raspberry Pi)
- Thermal printer
  * Tiny Thermal Receipt Printer by Adafruit
  * 5V/2A power supply recommanded by Adafruit
  * 2.1mm jack adapter to connect the power to the printer


## Thermal printer configuration

The printer configuration follows that tutorial:
https://learn.adafruit.com/instant-camera-using-raspberry-pi-and-thermal-printer?view=all#system-setup

In particular for my printer to be added to the cups server

```bash
sudo lpadmin -p ZJ-58 -E -v serial:/dev/ttyAMA0?baud=9600 -m zjiang/ZJ-58.ppd
sudo lpoptions -d ZJ-58
```

Remarks:
* The printer used for this project is the [Tiny Thermal Receipt Printer - TTL Serial / USB](https://www.adafruit.com/product/2751). The TTL serial connection was used as unwanted characters were send to the USB connection
between pictures.  
The TTL serial connection is done easily by connecting the RX port of the printer (the middle pin) to the
GPIO 14 on the raspberry pi and the Ground pin to one of the raspberry (see [here](https://learn.adafruit.com/mini-thermal-receipt-printer/circuitpython)).
* The `ZJ-58.ppd` file was modified to switch the default size to `X48MMY210MM` and the default feed distance
was set to `2feed9mm`


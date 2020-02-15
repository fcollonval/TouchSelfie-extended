# Kivy Selfie

Simple Kivy GUI for a photobooth that takes 3 pictures to print them with a thermal printer
and save the pictures with optionally an email address (to send them after the event).

The email addresses and pictures are simply appended to a CSV file.

## Execution

```
python3 main.py
```

To stop the application, enter *exit* as email address and press the print
button. You could also enter *halt* to stop the application and shutdown the
raspberry pi.

I experienced unstabilities due to graphic card errors (mostly due to lake of GPU memory).
So to be more robust to Kivy crashes, you can use the `runner.py` script. It will restart the application
if it crashes except if the magic word *exit* or *halt* were given as email
addresses.

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


> It is important to give quite some memory to the GPU for the application
to be stable. I recommend using 512Mo.

As light source, I bought a *beauty ring* light. They are cheap and good enough in this case. But be sure to have a dedicated power supply for it. I try powering it through USB. But this may the raspberry pi unstable.

## Software requirements

* Python packages

* Kivy >= 1.10 - https://kivy.org
* rpi_backlight >= 2 - https://github.com/linusg/rpi-backlight

```bash
sudo apt-get update
sudo apt-get install libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
   pkg-config libgl1-mesa-dev libgles2-mesa-dev \
   python3-setuptools libgstreamer1.0-dev git-core \
   gstreamer1.0-plugins-{bad,base,good,ugly} \
   gstreamer1.0-{omx,alsa} python3-dev libmtdev-dev \
   xclip xsel python3-picamera python3-pip
sudo pip3 install -U Cython==0.28.2
sudo pip3 install rpi_backlight
sudo pip3 install git+https://github.com/kivy/kivy.git@1.10.1
garden install iconfonts
```

* Printer driver

```bash    
sudo apt-get update
sudo apt-get install git cups wiringpi build-essential libcups2-dev libcupsimage2-dev
cd
git clone https://github.com/adafruit/zj-58
cd zj-58
make
sudo ./install
```

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


from copy import copy
from datetime import datetime
import os.path as osp
from threading import Thread
from time import sleep

import cups
import getpass

from kivy.app import App
from kivy.config import Config
from kivy.core.image import Image as CoreImage

from kivy.graphics.texture import Texture
from kivy.graphics.vertex_instructions import Rectangle

from kivy.uix.widget import Widget
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.properties import ObjectProperty, BooleanProperty, \
    NumericProperty, StringProperty, ListProperty
from kivy.clock import Clock
from kivy.garden import iconfonts

from PIL import Image

from constants import RESOLUTION
# from camera import camera

TMP_FOLDER = 'snapshots'
STORAGE_FOLDER = 'pictures'
COUNTDOWN = 2
PREVIEW_REFRESH = 1.
NPHOTOS = 3
PRINTER = 'ZJ-58'

iconfonts.register('default_font', 'fontawesome-webfont.ttf', 'font-awesome.fontd')


class SelfieScreen(Screen):
    snaps = ListProperty(None)
    text = ObjectProperty(None)
    camera = ObjectProperty(None)
    selfie_in_progress = BooleanProperty(False)
    countdown = NumericProperty(0)
    counter = NumericProperty(0)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.snaps = [
            Texture.create(size=RESOLUTION) for i in range(NPHOTOS)
        ]
        # self.camera = camera
        self.clock_event = None

    def decrement(self, dt):
        self.countdown -= 1
        if self.countdown == 0:
            self.take_picture()
        else:
            self.text.font_size = 100
            self.text.text = str(self.countdown)

    def take_picture(self):
        if self.clock_event is not None:
            self.clock_event.cancel()

        self.text.text = "Smile"
        filename = osp.join(TMP_FOLDER, "snap{}.png".format(self.counter))
        # self.camera.capture_image(filename)
        tw, th = self.camera.texture_size
        self.snaps[self.counter] = copy(self.camera.texture.get_region(0, 0, tw, th))
        self.counter += 1

        if self.counter == NPHOTOS:
            self.process_picture()
        else:
            self.countdown = COUNTDOWN
            self.text.text = "Get ready!"
            self.clock_event = Clock.schedule_interval(self.decrement, 1)
    
    def process_picture(self):
        self.parent.current = "print"
        self.selfie_in_progress = False
        self.text.text = "Press to start"

        return
        # collage of four shots
        # compute collage size
        w = RESOLUTION[0]
        h = RESOLUTION[1]
        w_ = w * 2
        h_ = h * 2
        # Assemble collage
        snapshot = Image.new('RGBA', (w_, h_))
        composition = [
            (  0,   0,  w, h),
            (w,   0, w_, h),
            (  0, h,  w, h_),
            (w, h, w_, h_)
        ]
        for i, position in enumerate(composition):
            snapshot.paste(
                Image.open(osp.join(TMP_FOLDER, "snap{}.jpg".format(i))),
                position
            )
        
        #paste the collage enveloppe
        front = Image.open('collage_four_square.png')
        front = front.resize((w_,h_))
        front = front.convert('RGBA')
        snapshot = snapshot.convert('RGBA')
        snapshot = Image.alpha_composite(snapshot, front)

        # Save the final composition
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = osp.join(STORAGE_FOLDER, "picture_{}.jpg".format(stamp))
        snapshot = snapshot.convert('RGB')
        snapshot.save(filename)
        self.parent.montage_filename = filename

        # Switch screen
        self.parent.current = "print"
        self.selfie_in_progress = False
        self.text.text = "Press to start"

    def on_touch_down(self, touch):
        if self.selfie_in_progress:
            return
        
        self.selfie_in_progress = True
        self.text.text = "Get ready!"
        self.countdown = COUNTDOWN
        self.counter = 0
        self.clock_event = Clock.schedule_interval(self.decrement, 1)


class PrintScreen(Screen):
    snaps = ListProperty(None) 

    def on_pre_enter(self, *args):
        previews = self.ids.preview
        previews.canvas.clear()
        with previews.canvas:
            for i in range(NPHOTOS):
                Rectangle(
                    size=(self.width/NPHOTOS, self.height - 60), 
                    pos=(i*self.width/NPHOTOS, 0), 
                    texture=self.snaps[i]
                )


class ScreenOrchestrator(ScreenManager):

    def send_email(self, email):
        # TODO
        print("Store email and print " + email)
        try:
            conn = cups.Connection()
            printers = conn.getPrinters()
            if PRINTER not in printers:
                raise ValueError("Printer {} not found.".format(PRINTER))
            cups.setUser(getpass.getuser())
            # Printer, filename, title, options
            conn.printFile(PRINTER, "dummy.png", 'dummy', {'fit-to-page': 'True'})
        except Exception as err:
            print("Print failed: {}".format(repr(err)))
        self.reset()

    def reset(self):
        self.current = "selfie" 

class SelfieApp(App):
    
    def build(self):
        Config.set("kivy", "keyboard_mode", "systemanddock")
        return ScreenOrchestrator(transition=FadeTransition())


if __name__ == "__main__":
    SelfieApp().run()

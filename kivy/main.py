from datetime import datetime
import os.path as osp

import cups
import getpass

from kivy.app import App
from kivy.config import Config
from kivy.core.image import Image as CoreImage

from kivy.graphics.texture import Texture
from kivy.graphics import Fbo, Rectangle

from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.properties import ObjectProperty, BooleanProperty, \
    NumericProperty, StringProperty, ListProperty
from kivy.clock import Clock
from kivy.garden import iconfonts

from PIL import Image


BACKGROUND = "photobooth_bg.png"
COUNTDOWN = 2
NPHOTOS = 3
# 5 * 15.2cm @200DPI
PAPER_SIZE = (402, 1197)
PRINTER = 'ZJ-58'
# Pi Camera v2 Hardware 3280 × 2464 pixels
RESOLUTION = (960, 960)
STORAGE_FOLDER = 'pictures'

iconfonts.register('default_font', 'fontawesome-webfont.ttf', 'font-awesome.fontd')


class SelfieScreen(Screen):
    camera = ObjectProperty(None)
    countdown = NumericProperty(0)
    counter = NumericProperty(0)
    selfie_in_progress = BooleanProperty(False)
    snaps = ListProperty(None)
    text = ObjectProperty(None)

    RESOLUTION = RESOLUTION
    
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
        self.text.text = "Smile"
        if self.clock_event is not None:
            self.clock_event.cancel()

        self.camera.play = False
        # Big thanks to https://gist.github.com/rooterkyberian/32d751bfaf7bc32433b3#file-dtryhard_kivy-py
        ct = self.camera.texture
        t = Texture.create(size=self.camera.texture_size, colorfmt=ct.colorfmt, bufferfmt=ct.bufferfmt)
        t.blit_buffer(ct.pixels, colorfmt=ct.colorfmt, bufferfmt=ct.bufferfmt)
        t.flip_vertical()
        self.snaps[self.counter] = t

        self.camera.play = True
        self.counter += 1

        if self.counter == NPHOTOS:
            self.process_picture()
        else:
            self.countdown = COUNTDOWN
            self.text.text = "Get ready!"
            self.clock_event = Clock.schedule_interval(self.decrement, 1)
    
    def process_picture(self):
        # Switch screen
        self.parent.current = "print"

    def on_pre_enter(self, *args):
        if self.camera is not None:
            self.text.text = "Press to start"
            self.selfie_in_progress = False
            self.camera.play = True

    def on_pre_leave(self, *args):
        if self.camera is not None:
            self.camera.play = False

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
    montage_file = StringProperty("")

    def on_pre_enter(self, *args):
        w = self.width/NPHOTOS
        h = self.height - 60.
        thumbnail_size = (int(w), int(w / RESOLUTION[0] * RESOLUTION[1]))

        previews = self.ids.preview
        previews.canvas.clear()
        with previews.canvas:
            for i in range(NPHOTOS):
                Rectangle(
                    size=thumbnail_size,
                    pos=(int(i*thumbnail_size[0]), int(0.5*(h - thumbnail_size[1]))),
                    texture=self.snaps[i]
                )

        # Generate the composed image
        background = CoreImage(BACKGROUND).texture
        fbo = Fbo(size=PAPER_SIZE)
        
        w, h = fbo.size
        length = int(0.8 * w)  # Picture will be square of 80% of paper width
        length = min(length, int(h * 0.85/ NPHOTOS))

        with fbo:
            Rectangle(size=fbo.size, pos=(0, 0), texture=background)
            for i in range(NPHOTOS):
                Rectangle(
                    size=(length, length),
                    pos=(
                        int(0.5 * (w - length)), 
                        int(h - (i + 1) * (0.45 * (w - length) + length))
                    ),
                    texture=self.snaps[i]
                )
        # Carry the actual draw
        fbo.draw()

        # Save the final composition
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.montage_file = osp.join(STORAGE_FOLDER, "picture_{}.jpg".format(stamp))
        fbo.bind()
        fbo.texture.save(self.montage_file, flipped=True)
        fbo.release()

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
        self.parent.current = "selfie" 


class ScreenOrchestrator(ScreenManager):
    pass


class SelfieApp(App):
    
    def build(self):
        Config.set("kivy", "keyboard_mode", "systemanddock")
        return ScreenOrchestrator(transition=FadeTransition())


if __name__ == "__main__":
    SelfieApp().run()

from datetime import datetime
import os.path as osp
import os
# import cups
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

from escpos import printer

from PIL import Image

IDVENDOR=0x0fe6
IDPRODUCT=0x811e
OUTPUT_ENDPOINT=0x02
BACKGROUND = "photobooth_bg.png"
COUNTDOWN = 2
NPHOTOS = 1 
# 5 * 15.2cm @200DPI
PAPER_SIZE = (402, 1197)
PRINTER = 'ZJ-58'
# Pi Camera v2 Hardware 3280 × 2464 pixels
RESOLUTION = (960, 960)
STORAGE_FOLDER = 'pictures'

iconfonts.register('default_font', 'fontawesome-webfont.ttf', 'font-awesome.fontd')
# cups.setUser(getpass.getuser())


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
        
    def __init__(self, *args, **kwargs):
        super(PrintScreen, self).__init__(*args, **kwargs)
        stamp = datetime.now().strftime("%Y%m%d")
        db_name = "database_" + stamp
        if osp.exists(db_name + ".csv"):
            i = 0
            while osp.exists(db_name + "_{}.csv".format(i)):
                i += 1
            db_name += "_{}".format(i)
        self.db = db_name + ".csv"
        with open(self.db, "w") as f:
            f.write("file,email\n")

        self.printer = printer.Usb(IDVENDOR, IDPRODUCT, out_ep=OUTPUT_ENDPOINT)

    def on_pre_enter(self, *args):
        if self.ids.input_email is not None:
            self.ids.input_email.text = ""
        
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
        length = int(0.9 * w)  # Picture will be square of 90% of paper width
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
        if len(self.montage_file):
            try:
#                self.printer.image(str(self.montage_file))
#                # Feed some paper to have a nice cut
#                self.printer._raw(b"\n\n\n")
                pass
            except Exception as err:
                print("Print failed: {}".format(repr(err)))
            
            if len(email):
                with open(self.db, "a") as f:
                    f.write("{},{}\n".format(self.montage_file, email))

            self.montage_file = ""
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

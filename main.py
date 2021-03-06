from datetime import datetime
import logging
from pathlib import Path
import os
import os.path as osp
import re
from subprocess import PIPE, Popen

from kivy.app import App
from kivy.clock import Clock
from kivy.config import Config
from kivy.core.image import Image as CoreImage
from kivy.graphics.texture import Texture
from kivy.graphics import Fbo, Rectangle
from kivy.lang import Builder
from kivy.properties import ObjectProperty, BooleanProperty, \
    NumericProperty, StringProperty, ListProperty
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.textinput import TextInput

from kivy.garden import iconfonts

from rpi_backlight import Backlight  # >=2.0.0

Builder.load_file("style.kv")


BACKGROUND = "photobooth_bg.png"
COUNTDOWN = 5 
NPHOTOS = 3 
# 5 * 15.2cm @200DPI
PAPER_SIZE = (402, 1197)
PRINTER = 'ZJ-58_2'
# Pi Camera v2 Hardware 3280 × 2464 pixels
RESOLUTION = (960, 960)
STORAGE_FOLDER = 'pictures'
# Backlight timeout for extinction in seconds
BACKLIGHT_TIMEOUT = 300
# File to indicate nice exit
EXIT_INDICATOR = Path(__file__).parent / "selfie.exit"
# Initial email addresses list
EMAILS_LIST = Path(__file__).parent / "emails.csv"

bl = Backlight()

curdir = osp.dirname(osp.realpath(__file__))
iconfonts.register(
    'default_font', 
    osp.join(curdir, 'data', 'fontawesome-webfont.ttf'), 
    osp.join(curdir, 'data', 'font-awesome.fontd')
)


def is_printer_printing():
    p = Popen(["lpstat", "-p"], stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    return re.search(r"ZJ-58.*printing", out.decode('utf-8')) is not None


class ComboEdit(TextInput):
    options = ListProperty((Button(text=''), ))

    def __init__(self, **kwargs):
        self.email_db = []
        if EMAILS_LIST.exists():
            with EMAILS_LIST.open() as femails:
                self.email_db = set(map(lambda e: e.strip(), femails.readlines()))

        self.drop_down = DropDown()
        self.drop_down.bind(on_select=self.on_select)
        super(ComboEdit, self).__init__(**kwargs)

    def _set_suggestions(self):
        self.options = (Button(text=''), )
        if len(self.text) >= 1:
            new_options = []
            for email in self.email_db:
                if email.startswith(self.text):
                    btn = Button(
                        text=email,
                        font_size="30sp",
                        size_hint_y=None,
                        height=40
                    )
                    new_options.append(btn)
                if len(new_options) == 3:  # Show maximum 3 suggestions
                    break
            self.options = new_options

    def add_text_to_db(self):
        self.email_db.add(str(self.text))

    def keyboard_on_key_up(self, *args):
        self._set_suggestions()
        return super(ComboEdit, self).keyboard_on_key_up(*args)

    def on_options(self, instance, value):
        self.drop_down.clear_widgets()
        for widget in value:
            widget.bind(on_release=lambda btn: self.drop_down.select(btn.text))
            self.drop_down.add_widget(widget)

    def on_select(self, *args):
        self.text = args[1]

    def on_touch_up(self, touch):
        if touch.grab_current == self:
            self.drop_down.open(self)
            self._set_suggestions()
        return super(ComboEdit, self).on_touch_up(touch)


class SelfieScreen(Screen):
    camera = ObjectProperty(None)
    countdown = NumericProperty(0)
    counter = NumericProperty(0)
    selfie_in_progress = BooleanProperty(False)
    snaps = ListProperty(None)
    text = ObjectProperty(None)
    montage_file = StringProperty("")

    RESOLUTION = RESOLUTION
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.snaps = [
            Texture.create(size=RESOLUTION) for i in range(NPHOTOS)
        ]
        # Initialize the camera at the first frame refresh to ensure it is active
        self.clock_event = Clock.schedule_once(self._init_camera) 
        self.backlight_event = None

        self.background = CoreImage(BACKGROUND).texture

    def _init_camera(self, dt):
        # Flip the camera horizontally so moving left, move you left
        #  Trick done in PiCamera obj as we known which camera we got
        self.camera._camera._camera.hflip = True


    def decrement(self, dt):
        self.countdown -= 1
        if self.countdown == 0:
            if self.clock_event is not None:
                self.clock_event.cancel()
            self.take_picture()
        else:
            self.text.font_size = 100
            self.text.text = str(self.countdown)

    def wait_for_printer(self, dt):
        # Get the printer status
        if is_printer_printing():
            self.text.text = "Impression..."
            self.selfie_in_progress = True
            self.clock_event = Clock.schedule_once(self.wait_for_printer, 1)
        else:
            self.text.text = "Appuyez"
            self.selfie_in_progress = False

    def sleep(self, dt):
        if bl.power:
            bl.power = False
            if self.camera is not None:
                self.camera.play = False

    def wake_up(self):
        if not bl.power:
            bl.power = True
            if self.camera is not None:
                self.camera.play = True

    def take_picture(self):
        self.text.text = "Souriez"
        # Get the reset of the action to be done after the next frame is 
        # rendered so that the text label get updated.
        Clock.schedule_once(self._take_snapshot, 0)

    def _take_snapshot(self, dt):
        self.camera.play = False
        # Big thanks to https://gist.github.com/rooterkyberian/32d751bfaf7bc32433b3#file-dtryhard_kivy-py
        ct = self.camera.texture
        t = Texture.create(size=self.camera.texture_size, colorfmt=ct.colorfmt, bufferfmt=ct.bufferfmt)
        t.blit_buffer(ct.pixels, colorfmt=ct.colorfmt, bufferfmt=ct.bufferfmt)
        t.flip_vertical()
        t.flip_horizontal()  # Reverse mirror effect on selfie screen
        self.snaps[self.counter] = t
        
        self.camera.play = True
        self.counter += 1

        if self.counter == NPHOTOS:
            self.process_picture()
        else:
            self.countdown = COUNTDOWN
            self.text.text = "Encore {}!".format(NPHOTOS - self.counter)
            self.clock_event = Clock.schedule_interval(self.decrement, 1)
    
    def process_picture(self):
        # Generate the composed image
        def save_montage(background):
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
                            int(h - (i + 1) * (0.25 * (w - length) + length))
                        ),
                        texture=self.snaps[i]
                    )
            # Carry the actual draw
            fbo.draw()

            # Save the final composition
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            montage_file = osp.join(curdir, STORAGE_FOLDER, "picture_{}.jpg".format(stamp))
            fbo.bind()
            fbo.texture.save(montage_file, flipped=True)
            fbo.release()
            del fbo

            return montage_file

        try:
            self.montage_file = save_montage(self.background)
        except Exception as e:
            logging.error(e)
            self.text.text = "Erreur..."
            self.clock_event = Clock.schedule_once(self.wait_for_printer)
            self.camera.play = True
        else:
            # Switch screen
            self.parent.current = "print"

    def on_pre_enter(self, *args):
        if self.camera is not None:
            self.text.text = "En préparation..."
            self.selfie_in_progress = True
            self.clock_event = Clock.schedule_once(self.wait_for_printer, 0.1)
            self.camera.play = True
        self.sleep_timeout = Clock.schedule_once(self.sleep, BACKLIGHT_TIMEOUT)

    def on_pre_leave(self, *args):
        if self.camera is not None:
            self.camera.play = False
        if self.sleep_timeout is not None:
            self.sleep_timeout.cancel()

    def on_touch_down(self, touch):
        if self.sleep_timeout is not None:
            # Reset backlight timeout
            self.sleep_timeout.cancel()
            if not self.selfie_in_progress:
                self.sleep_timeout = Clock.schedule_once(self.sleep, BACKLIGHT_TIMEOUT)

        if not bl.power:  # If the backlight was off just turn it off on touch
            self.wake_up()
            return

        if self.selfie_in_progress:
            return
        
        self.selfie_in_progress = True
        if self.sleep_timeout is not None:
            self.sleep_timeout.cancel()
        self.text.text = "C'est parti!"
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
        self.db = osp.join(curdir, db_name + ".csv")
        if not osp.exists(self.db):
            with open(self.db, "w") as f:
                f.write("file,email\n")

    def on_pre_enter(self, *args):
        if self.ids.input_email is not None:
            self.ids.input_email.text = ""
        
        h = self.height - 60.
        w = min(self.width/NPHOTOS, h)
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

    def send_email(self, email):
        # special terms
        if email.strip() in ('exit', 'halt'):
            EXIT_INDICATOR.touch()
            App.get_running_app().stop()
            if email == 'halt':
                os.system("sudo halt")
            return

        if len(self.montage_file):
            # Add email address to database
            self.ids.input_email.add_text_to_db()
            try:
                # Send the file to the printer
                os.system("lp {}".format(osp.join(curdir, self.montage_file)))
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
        Config.set("kivy", "keyboard_layout", "data/email_kb.json")
        return ScreenOrchestrator(transition=FadeTransition())

if __name__ == "__main__":
    if EXIT_INDICATOR.exists():
        EXIT_INDICATOR.unlink()
    app = SelfieApp()
    app.run()

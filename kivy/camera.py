from abc import ABC, abstractmethod
from enum import Enum
import io
from random import randint

from PIL import Image

from constants import RESOLUTION


class CameraBackend(Enum):
    DUMMY = 0
    GPHOTO2 = 1
    PICAMERA = 2


backend = CameraBackend.DUMMY


try:
    import gphoto2 as gp
    if len(gp.check_result(gp.gp_camera_autodetect())) == 0:
        raise ImportError()
    backend = CameraBackend.GPHOTO2
except ImportError:
    try:
        from picamera import PiCamera
        backend = CameraBackend.PICAMERA
    except ImportError:
        backend = CameraBackend.DUMMY


class AbstractCamera(ABC):

    def close(self):
        pass

    @abstractmethod
    def preview(self):
        raise NotImplementedError()
    
    @abstractmethod
    def capture_image(self, filename):
        raise NotImplementedError()


class DummyCamera(AbstractCamera):
    
    resolution = RESOLUTION

    def preview(self):
        fp = io.BytesIO()
        im = Image.new('RGB', (640, 424), tuple([randint(0, 255) for i in range(3)]))
        im.save(fp, format='JPEG')
        fp.seek(0)
        return fp

    def capture_image(self, filename):
        im = Image.new('RGB', self.resolution, tuple([randint(0, 255) for i in range(3)]))
        im.save(filename, format='JPEG')


class GPhoto2Camera(AbstractCamera):

    def __init__(self):
        self.context = gp.Context()
        self.camera = gp.Camera()
        self.camera.init(self.context)

        config = self.camera.get_config()
        OK, image_size = gp.gp_widget_get_child_by_name(config, 'imagesize')
        if OK >= gp.GP_OK:
            # set value
            value = gp.check_result(gp.gp_widget_get_choice(image_size, 2))
            gp.check_result(gp.gp_widget_set_value(image_size, value))
            
        OK, image_quality = gp.gp_widget_get_child_by_name(config, 'imagequality')
        if OK >= gp.GP_OK:
            # set value
            value = gp.check_result(gp.gp_widget_get_choice(image_quality, 0))
            gp.check_result(gp.gp_widget_set_value(image_quality, value))

        # set config
        self.camera.set_config(config)
        
        text = camera.get_summary(self.context)
        print('Summary')
        print('=======')
        print(str(text))

    def close(self):
        self.camera.exit(self.context)

    def preview(self):
        camera_file = self.camera.capture_preview()
        file_data = camera_file.get_data_and_size()
        return io.BytesIO(file_data)

    def capture_image(self, filename):
        file_path = self.camera.capture(gp.GP_CAPTURE_IMAGE)
        camera_file = self.camera.file_get(file_path.folder, file_path.name, 
            gp.GP_FILE_TYPE_NORMAL)
        camera_file.file_save(filename)


class ThePiCamera(AbstractCamera):

    resolution = RESOLUTION

    def __init__(self):
        self.camera = PiCamera(resolution=self.resolution)

    def preview(self):
        fp = io.BytesIO()
        self.camera.capture(fp, 'jpeg', resize=(640, 424))
        fp.seek(0)
        return fp

    def capture_image(self, filename):
        self.camera.capture(filename, 'jpeg')


chooser = {
    CameraBackend.DUMMY: DummyCamera,
    CameraBackend.GPHOTO2: GPhoto2Camera,
    CameraBackend.PICAMERA: ThePiCamera
}
print(backend)
camera = chooser[backend]()

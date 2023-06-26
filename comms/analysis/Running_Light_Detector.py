from STRIDR.comms.analysis.base import *
import numpy as np
import struct
from collections import OrderedDict

import sys
#sys.path.prepend( '/opt/opencv-3.4.5/lib/python3.5/dist-packages' )


class Running_Light_Detector(Detection):
    """A simple running light detector using image thresholding."""

    def __init__(self, paramf='', database=None):
        self.byteID = b'\x1b'
        self.params = {}
        self.params['iqr_threshold'] = 8
        super().__init__(database=database,
                         paramf=paramf,
                         byteID=self.byteID)

    def detect(self, start_time=None, end_time=None):
        im, image_times = self.database.get_data(
            "camera_ae", start_time=start_time, end_time=end_time)
        if isinstance(im, (list)):
            im = im[0]
            image_time = image_times[0]
        else:
            image_time = image_times
        heading, thistime = self.database.get_data(
            "imu_heading", start_time=start_time, end_time=end_time)
        cos_heading = np.cos(np.radians(heading))
        sin_heading = np.sin(np.radians(heading))
        heading = np.degrees(np.arctan2(
            sin_heading.mean(), cos_heading.mean()))
        if not isinstance(im, np.ndarray):
            print('Running_Light_Detector: no camera data between {} and {}'.format(
                start_time, end_time))
            return None
        if not heading:
            print('Running_Light_Detector: no imu_heading data between {} and {}'.format(
                start_time, end_time))
            return None

        # going to assume im is an iterable list of images, each item being one image...
        accumulated_detections = self._detect_running_lights(im, heading)
        if accumulated_detections:
            number_of_lights = len(accumulated_detections)
            all_detections = []
            # only report the first four for now
            for detection in accumulated_detections[:4]:
                all_detections.append(detection[0])
                all_detections.append(detection[1])

            components = struct.pack('=B{:d}B{:d}B'.format(
                number_of_lights, number_of_lights), number_of_lights, *all_detections)
            outsig = Signal(priority=1,
                            time=thistime[0],
                            algID=self.byteID,
                            components=accumulated_detections.tobytes())
            return outsig
        else:
            print(
                'Running_Light_Detector: No running lights detected at {}'.format(image_time))
            return None

    def _get_horizon_images(self, image_data):
        polar_image_data = cv2.warpPolar(image_data,
                                         (image_data.shape[1],
                                          image_data.shape[1]),
                                         (int(
                                             image_data.shape[1] / 2), int(image_data.shape[0] / 2)),
                                         580,
                                         cv2.INTER_LINEAR + cv2.WARP_POLAR_LINEAR)
        polar_image_data = np.transpose(polar_image_data, axes=[1, 0, 2])
        horizon_1_image_data = np.fliplr(polar_image_data[750:, 486:798])
        polar_image_data = np.roll(polar_image_data, int(
            polar_image_data.shape[1] / 2), axis=1)
        horizon_2_image_data = np.fliplr(polar_image_data[750:, 486:798])
        return horizon_1_image_data, horizon_2_image_data

    def _iqr_threshold_image(self, image_data, threshold):
        image_iqr = scipy.stats.iqr(image_data.flatten())
        image_data[image_data < threshold * 1.48 * image_iqr] = 0
        return image_data

    def _label_lights(self, horizon_image):
        """Simple threshold based running light detector for the STRIDR camera."""
        gray_image_data = cv2.cvtColor(horizon_image, cv2.COLOR_RGB2GRAY)
        gray_image_data = self._iqr_threshold_image(gray_image_data, self.params['iqr_threshold'])
        binary_image = gray_image_data.copy()
        binary_image[np.nonzero(binary_image)] = 1
        binary_image = scipy.ndimage.binary_closing(binary_image,
                                                    np.ones((3, 3)),
                                                    iterations=1)
        labeled_image, _ = scipy.ndimage.label(binary_image)
        return labeled_image

    def _scale_bearing(self, bearing):
        if bearing > 360:
            bearing -= 360
        return ((bearing / 360) * 255).astype('uint8')

    def _running_light_color_and_bearing(self, heading, horizon_image, running_lights, horizon_number):
        light_colors = {}
        heading = get_heading()
        # shift heading so it's 0-360
        heading
        for light_number in range(1, running_lights.max() + 1):
            light_indices = np.nonzero(running_lights == light_number)
            # STRIDR compass is aligned relative to the axis aligned with the switch and camera
            # The compass reads 0/N when the camera is oriented to the north of the on/off switch
            light_relative_bearing = (np.mean(
                light_indices[1]) - running_lights.shape[1] / 2) / running_lights.shape[1] * 92.3
            if horizon_number == 1:
                # horizon 1 is the camera side of the top board
                light_bearing = self._scale_bearing(
                    heading + light_relative_bearing)
            else:
                # horizon 2 is the on/off switch side of the top board
                light_bearing = self._scale_bearing(
                    heading + 180 + light_relative_bearing)
            light_image_channels = [
                horizon_image[..., cn][light_indices] for cn in range(3)]
            light_image_channel_maxes = [lic.max()
                                         for lic in light_image_channels]
            lic_max_index = np.argmax(light_image_channel_maxes)
            if lic_max_index == 0:
                # red
                light_colors[light_number] = (0, light_bearing)
            elif lic_max_index == 1:
                # green
                light_colors[light_number] = (128, light_bearing)
            else:
                # blue/white
                light_colors[light_number] = (255, light_bearing)
        return light_colors

    def _detect_running_lights(self, im, heading):
        im = im.astype('float')
        if (im[:, 335:965, :].astype('float').mean() < 60):
            horizon_1, horizon_2 = self._get_horizon_images(im)
            horizon_1_labeled = self._label_lights(horizon_1)
            horizon_2_labeled = self._label_lights(horizon_2)
            horizon_1_lights = self._running_light_color_and_bearing(
                heading, horizon_1, horizon_1_labeled, 1)
            horizon_2_lights = self._running_light_color_and_bearing(
                heading, horizon_2, horizon_2_labeled, 2)
            lights = [val for val in horizon_1_lights.values()] + \
                [val for val in horizon_2_lights.values()]
            return lights
        else:
            return None

    def model(self, signal):
        return {"": np.float(signal.components / 255)}

    def remove(self, signal, start_time=None, end_time=None):
        return None

    def components(self):
        comps = OrderedDict()
        comps['number_of_detections'] = 8
        # for each detection...
        comps['color'] = 8
        comps['bearing'] = 8
        return comps

    def struct_components(self):
        comps = OrderedDict()
        comps['number_of_detections'] = 'B'
        # for each detection...
        comps['color'] = 'B'
        comps['bearing'] = 'B'
        return comps

from STRIDR.comms.analysis.base import *
import numpy as np
import imageio
from collections import OrderedDict

import sys
#sys.path.prepend( '/opt/opencv-3.4.5/lib/python3.5/dist-packages' )


class Image_Clouds(Environment):
    def __init__(self, paramf='', database=None):
        self.byteID = b'\x16'
        self.params = {}
        self.params['cloud_threshold'] = 0.84
        super().__init__(database=database, paramf=paramf, byteID=self.byteID)

    def characterize(self, start_time=None, end_time=None):
        images, image_times = self.database.get_data("camera_hdr",
                                                     start_time=start_time,
                                                     end_time=end_time)
        percent_cloud = []
        for image in images:
            percent_cloud.append(self._sat_to_percent(image))
        percent_cloud = [x for x in percent_cloud if x]
        if percent_cloud:
            percent_cloud = (255 * np.mean(percent_cloud)).astype('uint8')
            mean_time = np.mean(image_times)
            outsig = Signal(priority=1,
                            time=mean_time,
                            algID=self.byteID,
                            components=percent_cloud.tobytes())
            return outsig
        else:
            return None

    def _sat_to_percent(self, im_sat):
        # assumes im_sat is a pre-processed image (i.e. HDR using cv2.createMergeMertens())
        # crop to the sky for this analysis
        im_sat = im_sat[:, 335:965, :].astype('float')
        if (im_sat.mean() > 60):
            clouds = (im_sat[..., 0] / (im_sat[..., -1] + 1)
                      ) > self.params['cloud_threshold']
            return (255 * np.sum(clouds) / np.size(clouds)).astype('uint8')
        else:
            return None

    def model(self, signal):
        return {"cam_cloud_cover": np.float(signal.components/255)}

    def remove(self, signal, start_time=None, end_time=None):
        return None

    def components(self):
        comps = OrderedDict()
        comps['Cloud_Cover'] = 8
        return comps

    def struct_components(self):
        comps = OrderedDict()
        comps['Cloud_Cover'] = 'B'
        return comps

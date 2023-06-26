from STRIDR.comms.analysis.base import *
import numpy as np
from collections import OrderedDict


class Read_Waves(Environment):
    def __init__(self, paramf='', database=None):
        self.byteID = b'\x19'
        super().__init__(database=database, paramf=paramf, byteID=self.byteID)

    def characterize(self, start_time=None, end_time=None):
        waves = []
        for k in ['imu_sig_wave_height', 'imu_peak_period']:
            wv, thistime = self.database.get_data(
                k, start_time=start_time, end_time=end_time)
            waves.append(wv)
        if not thistime:
            return None
        waves = np.array(waves, dtype=np.float16).tobytes()
        outsig = Signal(
            priority=1, time=thistime[0], algID=self.byteID, components=bytes(waves))
        return outsig

    def model(self, signal):
        return {"": np.float(signal.components/255)}

    def remove(self, signal, start_time=None, end_time=None):
        return None

    def components(self):
        comps = OrderedDict()
        comps['Significant_Wave_Height'] = 16
        comps['Peak_Wave_Period'] = 16
        return comps

    def struct_components(self):
        comps = OrderedDict()
        comps['Significant_Wave_Height'] = 'float16'
        comps['Peak_Wave_Period'] = 'float16'
        return comps

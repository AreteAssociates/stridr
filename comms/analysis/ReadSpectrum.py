# -*- coding: utf-8 -*-
from STRIDR.comms.analysis.base import *
import numpy as np
from collections import OrderedDict
import pandas


class Read_Spectrum(Environment):
    def __init__(self, paramf='', database=None):
        self.byteID = b'\x18'
        self.params = {}
        self.params['bin_edges'] = [
            0, 0.0278, .05, .0722, .0944, .1389, .1833, .2278, .2722, .3167, .3611, .4278, .5]
        super().__init__(database=database, paramf=paramf, byteID=self.byteID)

    def characterize(self, start_time=None, end_time=None):
        spc, thistime = self.database.get_data(
            'imu_spc', start_time=start_time, end_time=end_time)
        if thistime is None:
            return
        spc = spc[0]
        spc['bins'] = np.digitize(
            spc['wave_frequencies_hz'], self.params['bin_edges'], right=True)
        psds = []
        full_psds = np.array(spc['psd_m^2/hz'])
        for bin_number in set(spc['bins']):
            bin_indices = np.nonzero(spc['bins'] == bin_number)[0]
            psds.append(np.mean(full_psds[bin_indices]))
        psds = np.array(psds, dtype=np.float16).tobytes()
        outsig = Signal(
            priority=1, time=thistime[0], algID=self.byteID, components=psds)
        return outsig

    def model(self, signal):
        return {"": np.float(signal.components/255)}

    def remove(self, signal, start_time=None, end_time=None):
        return None

    def components(self):
        comps = OrderedDict()
        for component_number in range(len(self.params['bin_edges']) - 1):
            comps['PSD_bin_{}'.format(component_number)] = 16
        return comps

    def struct_components(self):
        comps = OrderedDict()
        for component_number in range(len(self.params['bin_edges']) - 1):
            comps['PSD_bin_{}'.format(component_number)] = 'float16'
        return comps

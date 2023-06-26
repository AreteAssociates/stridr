from STRIDR.comms.analysis.base import *
import numpy as np
from collections import OrderedDict


class Fourier_Interp(Environment):
    def __init__(self, paramf='', database=None):
        self.database = database
        self.byteID = b'\x1a'
        self.params = {}
        self.params['freq_step'] = 1
        self.params['fcount'] = 6
        super().__init__(database=database, paramf=paramf, byteID=self.byteID)

    def characterize(self, start_time=None, end_time=None):
        lat, thistime = self.database.get_data(
            DATA_KEY['latitude'], start_time=start_time, end_time=end_time)
        lon, _ = self.database.get_data(
            DATA_KEY['longitude'], start_time=start_time, end_time=end_time)
        l = len(lat)
        loline = lon[0]+(1/l)*np.arange(l)*(lon[-1]-lon[0])
        laline = lat[0]+(1/l)*np.arange(l)*(lat[-1]-lat[0])
        lat = lat-laline
        lon = lon-loline
        z = np.arange(l)/float(l)
        lat_parmas, _ = curve_fit(self._fourier, z, lat, [
                                  1.0] * self.params['fcount'])
        lon_parmas, _ = curve_fit(self._fourier, z, lon, [
                                  1.0] * self.params['fcount'])
        # taking the fit params, and packaging them for shipping
        fit_params = np.array(lat_parmas, dtype=np.float16).tobytes() + \
            np.array(lon_parmas, dtype=np.float16).tobytes()
        outsig = Signal(
            priority=1, time=thistime[0], algID=self.byteID, components=fit_params)
        return outsig

    def _fourier(self, x, *a):
        ret = a[0] * np.cos(np.pi / self.params['freq_step'] * x)
        for deg in range(1, len(a)):
            ret += a[deg] * np.cos((deg+1) * np.pi /
                                   self.params['freq_step'] * x)
        return ret

    def model(self, signal, len_model=1000):
        # can ignore, optional
        fitparams = np.frombuffer(signal.components, dtype=np.float16)
        latparams = fitparams[:self.params['fcount']]
        lonparams = fitparams[self.params['fcount']:]
        z = np.arange(len_model)/len_model
        lat = self._fourier(z, *latparams)
        lon = self._fourier(z, *lonparams)
        return [lat, lon]

    def remove(self, signal, start_time=None, end_time=None):
        # can ignore, optional
        lat, thistime = self.database.get_data(
            'latitude', start_time=start_time, end_time=end_time)
        lon, _ = self.database.get_data(
            'longitude', start_time=start_time, end_time=end_time)
        l = len(lat)
        loline = lon[0]+(1/l)*np.arange(l)*(lon[-1]-lon[0])
        laline = lat[0]+(1/l)*np.arange(l)*(lat[-1]-lat[0])
        lat = lat-laline
        lon = lon-loline
        mod_lat, mod_lon = self.model(signal, len_model=len(lat))
        return [lat-mod_lat, lon-mod_lon]

    def components(self):
        comps = OrderedDict()
        for q in range(self.params['fcount']):
            comps['lat'+str(q)] = 16
        for q in range(self.params['fcount']):
            comps['lon'+str(q)] = 16
        return comps

    def struct_components(self):
        comps = OrderedDict()
        for q in range(self.params['fcount']):
            comps['lat'+str(q)] = 'float16'
        for q in range(self.params['fcount']):
            comps['lon'+str(q)] = 'float16'
        return comps

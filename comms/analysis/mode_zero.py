from STRIDR.comms.analysis.base import *
from collections import OrderedDict


class Mean_Var(Environment):
    def __init__(self, paramf='', database=None):
        self.byteID = b'\x11'
        self.params = {}
        self.params['mean_sensors'] = ['charger_Iin', 'imu_ax', 'imu_ay',
                                       'imu_az', 'imu_gx', 'imu_gy', 'imu_gz', 'sst', 'conductivity']
        self.params['var_sensors'] = ['imu_ax', 'imu_ay', 'imu_az',
                                      'imu_gx', 'imu_gy', 'imu_gz', 'sst', 'conductivity']
        super().__init__(database=database, paramf=paramf, byteID=self.byteID)

    def characterize(self, start_time=None, end_time=None):
        means = []
        vars = []
        thattime = 0
        for sig in self.params['mean_sensors']:
            print(sig)
            this_dat, thistime = self.database.get_data(
                sig, start_time=start_time, end_time=end_time)
            if this_dat:
                mean_of_data = np.mean(this_dat)
                if sig == 'conductivity':
                    if mean_of_data < 550:
                        # if no conductivity sensor is attached, the open circuit generates a mean reading of 502-503
                        mean_of_data = 0
                thattime = thistime[0]
            else:
                mean_of_data = 0.0
            means.append(mean_of_data)
        for sig in self.params['var_sensors']:
            print(sig)
            this_dat, thistime = self.database.get_data(
                sig, start_time=start_time, end_time=end_time)
            if this_dat:
                data_var = np.var(this_dat)
                if sig == 'conductivity':
                    if np.mean(this_dat) < 550:
                        # if no conductivity sensor is attached, the open circuit generates a mean reading of 502-503, don't report variance for this condition either
                        data_var = 0
                thattime = thistime[0]
            else:
                data_var = 0.0
            vars.append(data_var)
        if sum(means) != 0:
            fit_params = np.array(means, dtype=np.float16).tobytes(
            ) + np.array(vars, dtype=np.float16).tobytes()
            outsig = Signal(priority=1, time=thattime,
                            algID=self.byteID, components=fit_params)
            return outsig
        else:
            return None

    def model(self, signal):
        return None

    def remove(self, signal, start_time=None, end_time=None):
        return None

    def components(self):
        comps = OrderedDict()
        for sig in self.params['mean_sensors']:
            comps[sig+'_mean'] = 16
        for sig in self.params['var_sensors']:
            comps[sig+'_var'] = 16
        return comps

    def struct_components(self):
        comps = OrderedDict()
        for sig in self.params['mean_sensors']:
            comps[sig+'_mean'] = 'float16'
        for sig in self.params['var_sensors']:
            comps[sig+'_var'] = 'float16'
        return comps


class Co_Var(Environment):
    def __init__(self, paramf='', database=None):
        self.byteID = b'\x1c'
        self.params = {}
        self.params['covar_sensors'] = [
            ('imu_gx', 'imu_ax'), ('imu_gy', 'imu_ay'), ('imu_gz', 'imu_az')]
        super().__init__(database=database, paramf=paramf, byteID=self.byteID)

    def characterize(self, start_time=None, end_time=None):
        covs = []
        thattime = 0
        for sig in self.params['covar_sensors']:
            this_dat1, thistime = self.database.get_data(
                sig[0], start_time=start_time, end_time=end_time)
            this_dat2, thistime = self.database.get_data(
                sig[1], start_time=start_time, end_time=end_time)
            if this_dat1 and this_dat2:
                c = (127*np.corrcoef(this_dat1, this_dat2)).astype(np.int8)
                covs.append(c[0, 1])
                thattime = thistime[0]
            else:
                covs.append(np.int8(-128))
        if sum(covs) != (-128 * len(self.params['covar_sensors'])):
            fit_params = np.array(covs, dtype=np.int8).tobytes()
            outsig = Signal(priority=1, time=thattime,
                            algID=self.byteID, components=fit_params)
            return outsig
        else:
            return None

    def model(self, signal):
        return None

    def remove(self, signal, start_time=None, end_time=None):
        return None

    def components(self):
        comps = OrderedDict()
        for sig in self.params['covar_sensors']:
            tag = sig[0]+'_'+sig[1]
            comps[tag+'_covariance'] = 8
        return comps

    def struct_components(self):
        comps = OrderedDict()
        for sig in self.params['covar_sensors']:
            tag = sig[0]+'_'+sig[1]
            comps[tag+'_covariance'] = 'b'
        return comps


class Polynomial_Fits(Environment):
    def __init__(self, paramf='', database=None):
        self.byteID = b'\x12'
        super().__init__(database=database, paramf=paramf, byteID=self.byteID)

    def characterize(self, start_time=None, end_time=None):
        polys = []
        for sig in self.params['sensors']:
            this_dat, thistime = self.database.get_data(
                sig, start_time=start_time, end_time=end_time)
            polys.append(np.polyfit(np.arange(len(this_dat)),
                                    this_dat, self.params['degree']))
        fit_params = np.array(polys, dtype=np.float16).tobytes()
        outsig = Signal(priority=1, time=thistime,
                        algID=self.byteID, components=fit_params)
        return outsig

    def model(self, signal):
        modeled = []
        for sig in self.params['sensors']:
            modeled.append()
        return None

    def remove(self, signal, start_time=None, end_time=None):
        return None

    def components(self):
        comps = OrderedDict()
        for sig in self.params['sensors']:
            for deg in range(self.params['degree']):
                comps[sig+'_poly'+str(deg)] = 16
        return comps

    def struct_components(self):
        comps = OrderedDict()
        for sig in self.params['sensors']:
            for deg in range(self.params['degree']):
                comps[sig+'_poly'+str(deg)] = 'float_16'
        return comps


class Zip_Compress(Compression):
    def __init__(self, paramf='', database=None):
        self.byteID = b'\x13'
        super().__init__(database=database, paramf=paramf, byteID=self.byteID)

    def compress(self, key, start_time=None, end_time=None):
        polys = []
        dats, thistime = self.database.get_data(
            key, start_time=start_time, end_time=end_time)
        zip_out = zlib.compress(dat.tobytes(), level=9)
        outsig = Signal(priority=1, time=thistime,
                        algID=self.byteID, components=zip_out)
        return outsig

    def model(self, signal):
        return np.frombytes(zlib.decompress(signal.components))

    def components(self):
        comps = {}
        return comps

    def struct_components(self):
        comps = {}
        return comps

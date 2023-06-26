#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar 27 08:15:18 2019

@author: csa0301
"""

from STRIDR.comms.analysis.base import *
import numpy as np
from collections import namedtuple, OrderedDict

parsedMicroEnvironments = namedtuple(
    'parsedMicroEnvironments', 'band_sigma band_level')
# TODO: GET BANDS DOWN TO 5 or less!!!
# from this, also update detections to an int8!


class microphoneEnvironment(Environment):
    def __init__(self, paramf='', database=None):
        self.byteID = b'\xa7'
        self.params = {}
        self.params['nfft'] = 1024
        self.params['Fs'] = 8000  # VERIFY###################
        self.params['num_bands'] = 10
        # number of one minute Hysteresis periods kept for the hydrophone environment
        self.num_hyst_periods = 4
        self.hyst_weights = [.125, .125, .25, .5]
        self.params['factor'] = 4
        for q in range(self.params['num_bands']):
            self.params['band_'+str(q)] = int(self.params['nfft']*((np.exp(q/self.params['factor'])) - 1) /
                                              (np.exp(self.params['num_bands']/self.params['factor']+1)))
        # first 463 bins are 890-22600Hz
        self.num_bins = int((self.params['nfft']/2)) + 1
        self.hysteresis_filled = False
        self.circ_buf_idx = 0
        self.key = 'audio'
        super().__init__(database=database, paramf=paramf, byteID=self.byteID)

        self.band_level_hyst = np.zeros(
            (self.params['num_bands'], self.num_hyst_periods))
        self.band_level = np.zeros(self.params['num_bands'])
        self.band_sigma_hyst = np.zeros(
            (self.params['num_bands'], self.num_hyst_periods))
        self.band_sigma = np.zeros(self.params['num_bands'])

    def characterize(self, start_time=None, end_time=None):
        retcode = self.calc_mean_std(
            start_time=start_time, end_time=end_time, circ_buf_idx=0)
        if not retcode:
            return None
        self.band_level = self.band_level_hyst[:, 0]
        self.band_sigma = self.band_sigma_hyst[:, 0]

        """
      self.hysteresis_filled = True
      start_time=0; 
      end_time=60*4
      if( not self.hysteresis_filled and end_time - start_time < self.num_hyst_periods * 60):
          print('Do not have enough input time to fill up the Hysteresis to correctly compute initial environment')
          return None;
      else:
          numIterations = int((end_time - start_time)/60); # compute environment in one minute chunks
          # compute the initial environment and fill up the Hysteresis buffer 
          for i in range(0, numIterations):
              # do not compute seastate and shipping density until hysteresis is full
              if(i < self.num_hyst_periods - 1 and ~self.hysteresis_filled):
                  self.calc_mean_std(start_time + (i* 60), start_time + ((i+ 1)* 60), self.circ_buf_idx)
              else:
                  self.hysteresis_filled = True
                  self.calc_mean_std(start_time + (i* 60), start_time + ((i+ 1)* 60), self.circ_buf_idx)
              self.circ_buf_idx = (self.circ_buf_idx +1) % self.num_hyst_periods
          
          self.band_level = np.zeros(self.params['num_bands']);
          self.band_sigma = np.zeros(self.params['num_bands']);
          
          for j in range(0, self.num_hyst_periods):
              self.band_sigma = np.add((np.array(self.band_sigma_hyst[:, (self.circ_buf_idx + j) % self.num_hyst_periods] *  self.hyst_weights[j])).tolist(), self.band_sigma)
              self.band_level = np.add((np.array(self.band_level_hyst[:, (self.circ_buf_idx + j) % self.num_hyst_periods] *  self.hyst_weights[j])).tolist(), self.band_level)
              
          self.time = end_time
      """

        # save the environment in the database

        band_sigma = np.float16(self.band_sigma)
        band_level = np.float16(self.band_level)
        env_data = np.array((band_level, band_sigma, self.time), dtype=[(
            'band_level', np.float64, self.params['num_bands']), ('band_sigma', np.float64, self.params['num_bands']), ('time', np.float64)])
        #self.database.store_data({'microphone_env': env_data, 'time':start_time})

        # create the output signal to send out
        envSig = np.array((band_sigma, band_level)).tobytes()
        outsig = Signal(priority=2, time=start_time,
                        algID=self.byteID, components=envSig)

        return outsig

        # component parses the concatenated Signal created in the environment and recreates the individual variables
    def components(self):
        comps = OrderedDict()
        for q in range(self.params['num_bands']):
            comps['band_level_'+str(q)] = 16
            comps['band_sigma_'+str(q)] = 16
        return comps

    def struct_components(self):
        comps = OrderedDict()
        for q in range(self.params['num_bands']):
            comps['band_level_'+str(q)] = 'float16'
            comps['band_sigma_'+str(q)] = 'float16'
        return comps

    def decode_components(self, Signal):
        envSig = Signal.components
        envSig = np.frombuffer(Signal.components, dtype=np.float32).reshape(
            (2, self.params['num_bands']))
        self.band_sigma = envSig[0, :]
        self.band_level = envSig[1, :]

        parsedEnv = parsedMicroEnvironments(self.band_sigma, self.band_level)

        return parsedEnv

    def parseSavedDBEvn(self, data_struct=None):

        if data_struct is not None:
            self.band_level = data_struct['band_level']
            self.band_sigma = data_struct['band_sigma']
            self.time = data_struct['time']
        else:
            print('cannot parse saved database environment')

        return None

    def calc_mean_std(self, start_time=None, end_time=None, circ_buf_idx=0):
        def ffthis(audio_signal, bin_size=1024):
            nspec = len(audio_signal)//bin_size
            ffout = np.zeros((nspec, bin_size), dtype=np.complex)
            for q in range(0, nspec):
                ffout[q, :] = np.fft.fft(
                    audio_signal[(q*bin_size):((q+1)*bin_size)])
            return ffout
        self.time = end_time
        data, _ = self.database.get_data(self.key, start_time, end_time)
        if not data:
            return None
        data = ffthis(data[0])

        #data,_ = self.database.get_data(self.key, start_time, end_time);
        # take magnitude of the fft data
        fdata = np.abs(data[:, 0:self.num_bins]/self.params['nfft'])

        num_mag_val = len(fdata)     # num rows in fileData   513

        #row_offsets = np.array(range(0,num_psd)) * self.params['nfft']
        #tv = (row_offsets+(self.params['nfft']/2))/self.params['Fs'];

        fv = np.asarray([i * (self.params['Fs'] / self.params['nfft'])
                         for i in range(0, self.params['nfft'] + 1)])
        # fv = np.array(range(0,num_bins) * (self.params['Fs'] / self.params['nfft'])

        bands = np.zeros((self.params['num_bands'], num_mag_val))

        for k in range(0, self.params['num_bands']):
            # find starting index
            low_f = self.params['band_'+str(k)]

            # find ending index
            high_f = self.params['band_'+str(k+1)] if k < (
                self.params['num_bands']-1) else int(self.params['nfft']/2)

            # loop over spectra and extract levels for each band
            for kt in range(0, num_mag_val):
                # integrate the power in all bins
                bands[k, kt] = np.sum(fdata[kt, low_f:high_f])

            # complete the computation of the environment parameters
            self.band_level_hyst[k, circ_buf_idx] = np.mean(bands[k])
            self.band_sigma_hyst[k, circ_buf_idx] = np.std(bands[k])

        return 1


class microphoneDetection(Detection):
    time = []
    band_idx = []
    B_lvl = []
    key = 'microphone'

    def __init__(self, database=None):
        # super.__init__(database)
        self.database = database
        self.byteID = b'\xa8'

    def detect(self, start_time=None, end_time=None, n_sigma=0):

        # recompute the microphone environment for the time period before tstart
        self.env = self.database.get_data('microphone_env', start_time)
        if(self.env == None):
            self.env = microphoneEnvironment(self.database)
            self.env.characterize(
                start_time - (self.env.num_hyst_periods * 60), start_time)

        # compute environment in one minute chunks
        numIterations = int((end_time - start_time)/60)
        self.detections = np.zeros((numIterations, self.env.num_bands))
        self.detectionsBin = np.int16(0)

        # calculate the frequency vector
        fv = np.asarray([i * (self.env.Fs / self.env.nfft)
                         for i in range(0, self.env.num_bins)])

        for ki in range(0, numIterations):

            # check to see if the environment is already computed for that time period
            env_data_struct = self.database.get_data('microphone_env', start_time + (
                ki * 60) - 60, start_time + (ki * 60))  # get Env from prev minute
            self.env.parseSavedDBEvn(env_data_struct)

            # do not let environment become more than 1 minute stale
            if start_time + (ki * 60) - self.env.time > 60:
                # get Env from prev minute
                self.env.characterize(
                    start_time + (ki * 60) - 60, start_time + (ki * 60))

            # update the 3 sigma threshold for each octave band with the new environment
            threshold = self.env.band_level + n_sigma * self.env.band_sigma

            data = self.database.get_data(
                self.key, start_time + (ki * 60), start_time + ((ki + 1) * 60))
            # take magnitude of the fft data
            fdata = np.abs(data[:, 0:self.env.num_bins] / self.env.nfft)

            num_mag_val = len(fdata)     # num rows in fileData   513

            bands = np.zeros(num_mag_val)

            for kb in range(0, self.env.num_bands):

                # find starting index
                low_f = (2 ** (kb/3)*1000) * (2**(-1/6))
                b_idx_start = np.abs(fv - low_f).argmin()

                # find ending index
                high_f = (2 ** (kb/3)*1000) * (2**(1/6))
                b_idx_end = np.abs(fv - high_f).argmin() - 1

                # create the indices array for 3rd octave bands
                if b_idx_start == None or b_idx_end == None:
                    b_idx = []
                else:
                    b_idx = np.array(range(b_idx_start, b_idx_end + 1))

                # loop over spectra and extract levels for each band
                for kt in range(0, num_mag_val):
                    # integrate the power in all bins
                    bands[kt] = np.sum(fdata[kt, b_idx])

                fdata_level = np.mean(bands)

                if fdata_level > threshold[kb]:
                    self.detections[ki, kb] = 1
                    self.detectionsBin = self.detectionsBin | (1 << kb)
                else:
                    self.detections[ki, kb] = 0

        detSig = self.detectionsBin
        detSig = np.int8(self.detectionsBin)
        detSig = detSig.tobytes()

        outsig = Signal(priority=3, time=start_time,
                        algID=self.byteID, components=detSig)

        return outsig

        # component parses the concatenated Signal created in the environment and recreates the individual variables
    def components(self):
        comps = OrderedDict()
        for q in range(self.env.num_bands):
            comps['band'+str(q)] = 16
        return comps

    def struct_components(self):
        comps = OrderedDict()
        for q in range(self.env.num_bands):
            comps['band'+str(q)] = 'h'
        return comps

    def decode_components(self, Signal):
        detSig = np.frombuffer(Signal.components, dtype=np.int16)
        self.detections = np.zeros(self.env.num_bands)

        for i in range(0, self.env.num_bands):
            mask = 0x1 << i
            self.detections[i] = (mask & detSig) >> i

        return self.detections


"""

wavDB = databaseWavFileReader()
#fileData = wavDB.get_data('hydrophone', 40 * 60, 50 * 60) # start time is 42 minutes and duration is 5 seconds, therefore end time is 42 minutes and 5 sec

microEnv = microphoneEnvironment(wavDB)
outsig = microEnv.characterize(40 * 60, 50 * 60)

tempLen = len(outsig)

print('microEnv.b_level')
print(microEnv.band_level)
print('microEnv.b_sigma')
print(microEnv.band_sigma)

parsedEnv = microEnv.components(outsig)

print('parsedEnv')
print(parsedEnv)

print('microEnv.b_level')
print(microEnv.band_level)
print('microEnv.b_sigma')
print(microEnv.band_sigma)





microDet = microphoneDetection(database = wavDB)
outsig = microDet.detect(3840 + (4 * 60), 4080 + (10 * 60), 3) # between 40 and 50 minutes of the file

tempLen = len(outsig)
#outsig = microDet.detect((5* 60), 0 + (12 * 60), 3) # between 40 and 50 minutes of the file
tempDetection = microDet.detections;
tempDetectionBin = bin(microDet.detectionsBin)
print(tempDetection)
print(tempDetectionBin)

parsedDets = microDet.components(outsig)

print('parsedDets')
print(parsedDets)

print('microDetect')
print(microDet.detections)

print('done')

"""

# -*- coding: utf-8 -*-

from data import buoy_database
import numpy as np
import wave

class databaseWavFileReader(buoy_database):
    
    envList = [];

    def get_data(self,key,start_time=None,end_time=None):
        
        if(key == 'hydrophone' or key == 'microphone'):
        
            #wr = wave.open('/Users/csa0301/Documents/Projects/OOT/Matlab/testSig.WAV','rb')
            #wr = wave.open('/Users/csa0301/Documents/Projects/OOT/HydrophoneData/rear_hydrophone_gain_4.WAV','rb')
            #wr = wave.open('/Users/csa0301/Documents/Projects/OOT/HydrophoneData/STRIDR_hydro1.WAV','rb')
            wr = wave.open('/Users/csa0301/Documents/Projects/OOT/MicrophoneData/exterior_microphone_gain_10.WAV', 'rb')
            
            Fs= wr.getframerate()
            print(['sample rate: ',Fs])
            width = wr.getsampwidth()
            print(['Sample Width: ',width])
            file_dur = wr.getnframes()/Fs
            print(['File Duration: ',file_dur,'sec'])
            
            if end_time > file_dur :
                end_time = file_dur
            
            if start_time > file_dur :
                print('Data not available in file\n')
            else :
                nfft = 1024
                position = int(start_time * Fs)
                print('Position',position)
                nframes = np.int((end_time-start_time)*Fs/nfft)
                wr.setpos(position)
                    
                fdata = np.zeros((nframes,nfft),dtype=complex) # first 96 bins are 0-4500Hz
                for iframe in np.arange(nframes):
                    data = wr.readframes(nfft)
                    
                    if len(data) % 3 != 0:
                        raise ValueError('Size of data must be a multiple of 3 bytes')
                    
                    fbuf = np.zeros(len(data) // 3, dtype='<i4')
                    fbuf.shape = -1, 1
                    temp = fbuf.view('B').reshape(-1, 4)
                    temp[:, 1:] = np.frombuffer(data, dtype='B').reshape(-1, 3)
                    #plt.plot(fbuf)
                    #plt.show()
                    # need to muliply by 256 to shift left by 8 bits so that the upper 24 of the 32 bits are data and the lower 8 are zeros. This allows the signed bit to be in the correct spot
                    fbuf = np.array(fbuf, dtype=int)
                    #plt.plot(fbuf)
                    #plt.show()
                    fbuf = np.squeeze(fbuf)
                    GZoom = 40
                    #for hydrophone only
                    #fdata[iframe,:] = np.fft.fft(fbuf, n = nfft) * 10 **(-GZoom/20)
                    # for microphone only
                    fdata[iframe,:] = np.fft.fft(fbuf, n = nfft)
    
                    #convert to PSD
                    #f = np.abs(f1)
                    #fdata[iframe,0:numBins]= np.square(f[0:numBins])
    
                
                
    
    #            fdata = np.zeros((nframes,86),dtype=float) # first 86 bins are 0-4000Hz
    #            for iframe in np.arange(nframes):
    #                bytes1 = wr.readframes(nfft)
    #                x=np.frombuffer(bytes1,dtype='int8',count=width*nfft)
    #                fbuf = 256*(x[1:(width*nfft-2):3]*256+x[2:(width*nfft-1):3])+x[3:width*nfft:3]
    #                f = np.abs(np.fft.fft(fbuf))
    #                fdata[iframe,0:86]=f[0:86]*f[0:86]
    #                print("hello")
                return fdata
        elif(key == 'hydrophone_env' or key == 'microphone_env'):
            #return the most recently added env
            siz = len(self.envList)
            return self.envList[-1]
                
    def store_data(self,key, data, start_time=None, end_time=None):
        self.envList.append(data);
        
        return None;
    

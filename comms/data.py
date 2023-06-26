
import h5py
import os
import datetime
from collections import defaultdict
import numpy as np
import glob
import STRIDR.comms.data_readers as data_readers# functions to read different sensor data
import STRIDR.comms.sql_try as sqldb
from STRIDR.comms.parameters import DB_LOCATION

def archive():
  nowtime = "%1.0f"%(datetime.datetime.now().timestamp())
  data_archive = '/data/data'+nowtime
  os.rename(DB_LOCATION,DB_LOCATION+"_"+nowtime)
  sensor_types = os.listdir('/data')
  os.mkdir(data_archive)
  for sensor in sensor_types:
    if os.path.isdir(sensor) and not sensor in ['lost+found','satcom']:
      datas = glob.glob('/data/'+sensor+'/*')
      os.mkdir(data_archive+'/'+sensor)
      for data in datas:
        os.rename(data,os.path.join(data_archive,sensor,data.split('/')[-1]))
  return
  

class buoy_database():
  #This database is used to access the data from only a single STRIDR buoy. 
  def __init__(self,context='buoy',source=None):
    #context can be buoy or server. When fully implemented on the buoys and the server
    # this parameter will be ignored. 
    # A buoy context will allow for access to raw data, historical communication and the
    #   reconstructions derived from those communications. 
    self.context = context
    self.data = defaultdict(list)
    self.keys = ['accel','compass','solar',
                 'sea_temp','air_temp','pressure','GPS',
                 'audio','fft_audio', 'camera']
    if source == None:
        print('No source selected. This database will generate a random stream of data.')
        self.source = None
        self.type = 'rand'
    elif type(source) == str:
        self.source = h5py.File(source)
        self.type = 'h5'
    elif type(source) == sqldb.database:
        self.source = source
        self.type = 'sql'
    else:
        self.type = None
        raise ValueError("Illegal source argument.")
    self._process_db()
    return None

  def _process_db(self):
    if self.type == 'rand':
        self.start_time = datetime.datetime.now()-datetime.timedelta(days=1)
        # shape is a tuple of (channels,sample_per_channel)
        self.k_shape = {'accel':(3,5*60*2),'compass':(1,5*60*2),
                        'solar':(1,1),'sea_temp':(1,1),'air_temp':(1,1),
                        'pressure':(1,1),'GPS':(1,1),'audio':(1,4096),
                        'fft_audio':(1,1024), 'camera':(480,640),
                        'conductivity':(1,1) }    
        delta_t=datetime.datetime.now()-self.start_time
        delta_t=delta_t.total_seconds()/(60*60*24*4)
        for key in self.keys:
            delta_s = np.int64(np.floor(delta_t*self.k_shape[key][0]))
            self.data[key] = np.random.randn(delta_s,*self.k_shape[key][1:])
    elif self.type == 'h5':
        self.file = h5py.File(self.source, 'r')
        # add keys to self.data with h5 indices (see store data for why)
        # assume times in order already 
        _ = [self.data[k].extend(np.arange(len(self.file[k]))) for k in self.file.keys()]
        # at least read in time info, assume recorded as string in following utc format
        self.data['time'] = [datetime.datetime.strptime(t, "%Y-%m-%dT%H%M%S.%f") for t in self.file['time'][:]]
        self.keys = self.data.keys()
        #self.sample_rate = [self.source['data'][k]['rate'] for k in self.keys]
        #raise NotImplementedError('patience is a virtue')
    elif self.type == 'sql':
        # source is already database class
        self.keys = self.source.columns
    else:
        raise ValueError('Error in data processing.') 
        
  def _sort_time(self):
    # make sure all sensor streams are the same length
    # probably need to add in stuff for get/store data to handle when there is a zero instead of pointer information
    _ = [self.data[k].extend( [0]*(len(self.data['time']) - len(self.data[k]))) for k in self.data.keys()]
    # sort
    tixs = np.argsort(self.data['time'])
    # ugh this is so bad
    for k,v in self.data.items():
      self.data[k] = [self.data[k][t] for t in tixs]
    return     
            
  def get_data(self,key,start_time=None,end_time=None):
    try:
        #if start_time is None, will start at first sample
        if key not in self.keys:
            print('Invalid key: ',key)
            
            return None, None
        t0, tf = self.timespan(key=key)
        if (start_time is None) & (end_time is None): # wake up index
            start_time, end_time = self.timespan(key=key, index=True)
            self.get_data_type = 'wake_up_index'
        elif ((start_time is not None) and (start_time < 10e3)) or ((end_time is not None) and (end_time < 10e3)): # wake up index
            t0, tf = self.timespan(key=key, index=True)
            start_time = t0 if (start_time is None) else start_time
            end_time = t0-15*60 if (end_time is None) else end_time
            self.get_data_type = 'wake_up_index'
        elif ((start_time is not None) and (start_time >= 10e3)) or ((end_time is not None) and (end_time >= 10e3)): # unix time
            t0, tf = self.timespan(key=key, index=False)
            start_time = t0 if (start_time is None) else start_time
            end_time = t0-15*60 if (end_time is None) else end_time
            self.get_data_type = 'time'
        if self.type == 'rand':
            delta_t=end_time-start_time
            delta_t=delta_t.total_seconds()/(60*60*24*4)
            delta_s = np.int64(np.floor(delta_t*self.k_shape[key][0]))
            d_start = start_time-self.start_time
            start = d_start.total_seconds()/(60*60*24*4)
            start = np.int64(np.floor(start))
            return self.data[key][start:delta_s,:,:]
        else:        
            if self.type == 'h5':
                raise NotImplementedError('No get_data functionality for h5s yet')
            else: # sql
                print( 'Retrieving {} data with start_time: {} and end_time: {}'.format( key, start_time, end_time ) )
                data = self.source.get_values(key, start_time, end_time, self.get_data_type)[0]
                if len(data) == 0:
                    return None, None
                val,times = data
                if (type(val[0]) == str) and (os.path.exists(val[0])):
                    print( 'data.get_data: Sensor data is a pointer, calling a read_data routine' )
                    # sensor consists of pointers
                    newv, newt = [],[]
                    for v in val:
                        thisd, thist = data_readers.read_data(v,key, pointer=False)
                        newv.append(thisd)
                        newt.append(thist)
                    val = newv
                    times = newt
                # API says numpy array but this is returning lists
                return val, times
    except Exception as e:
        print( 'In data.buoy_database error is {}'.format( e ) )
        return None, None
    
  def store_data(self, data_dict):
    try:
        if self.type == 'sql':
            # dictionary of values with key, and time index
            self.source.add_values(data_dict, '')
            # add column
        else:
            raise NotImplementedError('No store_data functionality for db source ',self.type)
    except Exception as e:
        print(e)
        return

  def timespan(self, key=None, index=True):
      if self.source:
        return self.source.timespan(key, index=index)
      else:
        return (None,None)
    
  def unix_to_wake_up_time(self, unix_times):
    if self.type == 'sql':
        if type(unix_times) in [list,tuple]:
            wake_up_ixs = []
            for time in unix_times:
                wake_up_ixs.append(self.source.execute('''SELECT wake_up_index from data_table
                                           WHERE time='''+str(time)).fetchone()[0])
            return wake_up_ixs
        else:
            return self.source.execute('''SELECT wake_up_index from data_table
                                           WHERE time='''+str(unix_times)).fetchone()[0]
    else:
        raise NotImplementedError('')
      
          
def get_first_file(*locs):
  files = glob.glob(os.path.join(*locs))
  if files:
    return files[0]
  else:
    return None

class single_frame_db():
  def __init__(self,base_folder=None):
    self.data = {}
    self.keys = []
    self.times = {}
    if not base_folder:
        base_folder = os.path.join("STRIDR","example_data1")
    self.sources = {'gps':get_first_file(base_folder,"gps","*.log"),
                    'imu':get_first_file(base_folder,"imu","sensor_timeseries*.csv"),
                    'waves':get_first_file(base_folder,"imu","wave_spectrum*.csv"),
                    'conductivity':get_first_file(base_folder,"conductivity","*.log"),
                    'sst':get_first_file(base_folder,"sst","*.log"),
                    'audio':get_first_file(base_folder,"audio","*.log"),
                    'fft_audio':get_first_file(base_folder,"audio_fft","*.npy"),
                    'camera':get_first_file(base_folder,"camera","*.jpg"),}
    for k,v in self.sources.items():
      if not v:
        print('Could not find a file for: '+str(k))
        continue
      dat = data_readers.read_data(v,k,0)
      if isinstance( dat, dict ):
        for kk in dat.keys():
          if kk == 'time':
            continue
          print(k+":"+kk)
          self.data[kk] = dat[kk]
          self.times[kk] = dat['time']
          self.keys.append(kk)
      else:
        self.data[k] = dat
  def get_data(self,tag,start_time=None,end_time=None):
      return self.data[tag], self.times[tag]
  def store_data(self,dict):
      return None
  def keys(self):
    return self.keys()
  def sources(self):
    return self.sources.keys()

class server_database():
  def __init__(self):
    self.data = {}
    self.times = []
    self.data = 0
  def empty_db(self,tag,start_time=None,end_time=None):
      return 0, 0

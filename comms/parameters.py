import os
import pickle
import glob
import datetime
import shutil
import sqlite3
import platform

def get_variable_from_db(c, key):
    c.execute('SELECT value FROM Variables WHERE key="{}"'.format(key))
    return c.fetchone()[0]

TIME_PATTERN = "%Y%m%dT%H%M%S.%f"
DB_MAX_SIZE = 25000000

#test to see if this is beaglebone or otherwise
IS_BB =  platform.architecture()[0] == '32bit'
# get magic from database
if IS_BB:
  CONFIG_DB = '/var/config.db'
  conn = sqlite3.connect(CONFIG_DB)
  c = conn.cursor()
  WRITABLE_DIRECTORY = r'/var'
  SYSTEM_MESSAGE_DIRECTORY = os.path.join(WRITABLE_DIRECTORY, 'system_messages')
  PARAM_FILE = os.path.join(SYSTEM_MESSAGE_DIRECTORY, 'params.pkl')
  DB_LOCATION = os.path.join(SYSTEM_MESSAGE_DIRECTORY, 'example.db')
  DB_ERROR_LOG = os.path.join(SYSTEM_MESSAGE_DIRECTORY, 'db_error_log.pkl')
  DEBUG = True;
  #DATA_DIRECTORY = r'\\arete\shared\arlington\Engineering\Projects\OoT\5 Other\end2end\stridr_c'
  DATA_DIRECTORY = get_variable_from_db(c, 'PATH_ROOT_SENSOR_DATA')
  DB_MANUAL_OFFSET = None
  ALGORITHM_ROTATION_FILE = os.path.join(os.path.dirname(DB_LOCATION),'alg_rot.txt')
  Q_LOCATION = os.path.join(SYSTEM_MESSAGE_DIRECTORY, r'signal_queue')
  if not os.path.exists(SYSTEM_MESSAGE_DIRECTORY):
      os.makedirs(SYSTEM_MESSAGE_DIRECTORY)
      shutil.copy(r'/home/oot/params.pkl', PARAM_FILE)
  if not os.path.exists(Q_LOCATION):
      os.makedirs(Q_LOCATION)

  COMPRESSED_EXPORT_PATH = os.path.join(SYSTEM_MESSAGE_DIRECTORY, 'zippedSig.pkl')
else:
  # These are set up for running STRIDR in a folder with a structure similar to what's on the drifter
  # i.e.
  # ./test_folder
  # ./test_folder/data/... all the data for testing as logged by sensors on a float
  # ./test_folder/var/
  # ./test_folder/var/system_messages
  # ./test_folder/var/system_messages/signal_queue
  # etc.
  #
  # Start the flask server from ./test_folder
  CONFIG_DB = os.path.join( os.getcwd(), 'var', 'config.db' )
  SYSTEM_MESSAGE_DIRECTORY = os.path.join( os.getcwd(), 'var', 'system_messages' )
  DB_LOCATION = os.path.join( SYSTEM_MESSAGE_DIRECTORY, 'example.db' )
  DB_ERROR_LOG = os.path.join( SYSTEM_MESSAGE_DIRECTORY, 'db_error_log.pkl')
  Q_LOCATION = os.path.join( SYSTEM_MESSAGE_DIRECTORY, 'signal_queue' )
  if not os.path.exists(Q_LOCATION):
    os.makedirs(Q_LOCATION)
  DEBUG = True
  DATA_DIRECTORY = os.path.join( os.getcwd(), 'data' )
  DB_MANUAL_OFFSET = 0#get_os_datetime_offset() #4*3600
  ALGORITHM_ROTATION_FILE = os.path.join( SYSTEM_MESSAGE_DIRECTORY, 'alg_rot.txt' )
  
  if not os.path.exists(SYSTEM_MESSAGE_DIRECTORY):
    os.makedirs(SYSTEM_MESSAGE_DIRECTORY)
  PARAM_FILE = r'params.pkl'
  if not os.path.isfile(PARAM_FILE):
    with open(PARAM_FILE,'wb') as f:
      pickle.dump({},f);

SYSTEM_STATUS_MSG = os.path.join( SYSTEM_MESSAGE_DIRECTORY, 'SystemStatus.bin' )
  
HIGHEST_MODE = 0;
HEADER_LL_FACT = 1.0/2.0

#core
NUM_Qs = 4;

MO_MAX_BYTES = 340;
MT_MAX_BYTES = 240;
LEN_TX_HEAD = 6;
LEN_RX_HEAD = 4;
MAX_ITER = 100;


#derived
HEADER_LL_LOC = os.path.join(Q_LOCATION,'last_reported_latlon.npy')
COMPRESSED_EXPORT_PATH = os.path.join(SYSTEM_MESSAGE_DIRECTORY, 'zippedSig.pkl')


#Data
wave_keys = {'height':'imu_height','peakperiod':'imu_peakperiod','meanheight':'imu_meanheight','var_height':'imu_var_height','ax_var':'imu_ax_var','ay_var':'imu_ay_var','az_var':'imu_az_var','imu_height':'imu_height','imu_peakperiod':'imu_peakperiod','imu_meanheight':'imu_meanheight','imu_var_height':'imu_var_height','imu_ax_var':'imu_ax_var','imu_ay_var':'imu_ay_var','imu_az_var':'imu_az_var'}
imu_keys = {'imu_spc':'imu_spc','altitude':'imu_lowpass_vert_accel','imu_altitude':'imu_lowpass_vert_accel', 'x_accel':'imu_ax', 'y_accel':'imu_ay', 'z_accel':'imu_az', 
        'imu_x_gyro':'imu_gx', 'imu_y_gyro':'imu_gy', 'imu_z_gyro':'imu_gz', 'x_gyro':'imu_gx', 'y_gyro':'imu_gy', 'z_gyro':'imu_gz', 
        'compass':'imu_compass', 'bprkpa':'imu_bprkpa', 'temp_c':'imu_temp_c', 'imu_x_accel':'imu_x_accel', 'imu_y_accel':'imu_y_accel', 'imu_z_accel':'imu_z_accel', 'imu_compass':'imu_compass', 'imu_bprkpa':'imu_bprkpa', 'imu_temp_c':'imu_temp_c'}
cam_keys = {'camera':'camera'}
gps_keys = {'latitude':'gps_latitude','longitude':'gps_longitude','gps_latitude':'gps_latitude','gps_longitude':'gps_longitude'}
phone_keys = {'audio':'audio','fft_microphone':'fft_microphone','fft_hydrophone':'fft_hydrophone','microphone':'microphone','hydrophone':'hydrophone'}
other_keys = {'conductivity':'conductivity','temperature':'temperature','solar_panels':'charger_Iin','pressure':'pressure','ss_temp':'sst','air_temp':'air_temp'}
DATA_KEY = {**wave_keys,**imu_keys,**cam_keys,**gps_keys,**phone_keys,**other_keys}

def get_os_datetime_offset():
    files = glob.glob(os.path.join(DATA_DIRECTORY, '*','*.*'))
    if len(files) == 0:
        return 0
    year = str(datetime.datetime.now().year)
    filetime = datetime.datetime.strptime(year+os.path.splitext(files[0].split(year)[-1])[0], TIME_PATTERN).timestamp() 
    ostime = os.path.getmtime(files[0])
    offset_hour = int((filetime-ostime)/3600.)
    return offset_hour*3600

import numpy as np
import os
import sys
sys.path.append(os.getcwd())
import glob
from STRIDR.comms.analysis.fourier_interp import Fourier_Interp
from STRIDR.comms import sql_try
import STRIDR.comms.data

class cuckoo_db(object):
    def __init__(self, mimic_db):
        self.mimic_db = mimic_db
        self.corrupt = False

    def get_data(self,tag,start_time=None,end_time=None):
      real_data = self.mimic_db.get_data(tag,start_time,end_time)
      real_data = np.array(real_data)
      if not self.corrupt:
        return real_data
      if np.random.randint(2):
        real_data = real_data[:np.random.randint(1,len(real_data))]
      if np.random.randint(2):
        real_data[np.random.randint(1,len(real_data))] = np.nan
      if np.random.randint(2):
        real_data[np.random.randint(1,len(real_data))] = 0
      if np.random.randint(2):
        real_data[np.random.randint(1,len(real_data))] = np.inf
      return real_data

    def set_corrupt(self, corrupt):
      self.corrupt = corrupt
      return

#Gather data
sqldb = STRIDR.comms.sql_try.database('bob.db')
db = STRIDR.comms.data.buoy_database(source=sqldb)
cuckoo = cuckoo_db(db)
# get saved param file
PARAM_FILE = r'params.pkl'
# Initialize environment class
FI = Fourier_Interp(database=cuckoo, paramf=PARAM_FILE) 
# let's update params to new values 
fakeparams = {'fcount':6,'freq_step':1}
FI.update_parameters(fakeparams)

# now, let's loop over a couple of times so see if the cuckoo messes up the processing
for q in range(10):
  try:
    #running the methods. 
    A = FI.characterize()
    la,lo = FI.model(A)
    removed = FI.remove(A,None)
  except Exception as ex:
    print('Threw exception:')
    exc_type, exc_obj, tb = sys.exc_info()
    print("    "+str(ex))
    lineno = tb.tb_lineno
    print("     on line number:"+str(lineno))
print('Passed')

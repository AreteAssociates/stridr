# -*- coding: utf-8 -*-
"""
Created on Sun Apr 21 07:56:45 2019

@author: kroman
"""
import os
import glob
import datetime
import pickle
import sqlite3
import STRIDR.comms.data_readers as dr

from STRIDR.comms.parameters import *

"""
def create_database(datadir, db_name):
    db = database(db_name)
    if db.conn == -1:
        print('Connection error')
        return None
    # Load sensor data
    sensors = glob.glob(os.path.join(datadir, '*'))
    for sensor_dir in sensors:
        sensor = os.path.split(sensor_dir)[1]
        if 'cam' in sensor:
            sensor = 'camera'
        sensor_data = glob.glob(os.path.join(sensor_dir, '*.*'))
        for sdf in sensor_data:
            # hydrophone and camera will be pointers
            data_dict = dr.read_data(sdf,sensor)
            if (data_dict is None) or (len(data_dict['time']) == 0):
                continue
            # store times as unix instead of datetime objects
            #data_dict['time'] = [datetime.datetime.timestamp(t) for t in data_dict['time']]
            # add values to db
            db.add_values(data_dict, sensor)
    return db
"""
def get_filetime_offset(manual=None):
    if manual is not None: #manually provide offset, e.g. for demo
        return DB_MANUAL_OFFSET
    offset_path = os.path.join(os.path.dirname(DB_LOCATION), 'blank.txt')
    with open(offset_path, 'w') as fout:
        fout.write(str(datetime.datetime.now().timestamp()))
    with open(offset_path, 'r') as fout:
        dt_time = fout.read()
    mod_time = os.path.getmtime(offset_path)
    offset_hour = int((float(dt_time)-mod_time)/3600.)
    return offset_hour*3600
    
class database(object):
    def __init__(self, db_name=DB_LOCATION, datadir=DATA_DIRECTORY, manual_file_offset=True):
        self.datadir = datadir
        self.db_name = db_name
        self.error_log_path = DB_ERROR_LOG
        if os.path.exists(self.error_log_path):
            with open(self.error_log_path, 'rb') as fin:
                try:
                    self.error_log = pickle.load(fin)
                except:
                    # unreadable or some other error, kill file and start over
                    os.remove(self.error_log_path)
                    self.error_log = []
        else:
            self.error_log = []
        # connect to db (either new or saved)
        self.connect()
        if self.conn == -1:
            print('Connection error')
            print(self.error_log)
        # create table if it doesn't exist already
        self.create_table('data_table')
        min_tix = (self.execute('SELECT MAX(time) FROM data_table WHERE time IS NOT NULL;')).fetchone()[0]
        min_ix = (self.execute('SELECT MAX(wake_up_index) FROM data_table WHERE wake_up_index IS NOT NULL;')).fetchone()[0]
        print('comms.sql_try.py: MAX(time) FROM data_table: {}, MAX(wake_up_index) FROM data_table: {}.'.format(min_tix, min_ix))
        self.last_wakeup_time =  -1 if min_tix is None else min_tix + 1e-6 #add arb. small value to ensure pull from later than last time
        self.last_wakeup_index = -1 if min_ix is None else min_ix
        print('comms.sql_try.py: last_wakeup_time: {}, last_wakeup_index: {}.'.format(self.last_wakeup_time, self.last_wakeup_index))
        self.mtime_offset = get_filetime_offset(manual=manual_file_offset) 
        self.this_wakeup_index = self.last_wakeup_index + 1
       
    
    def on_wakeup(self): # This is run at end, more appropriate name would be on_bedtime...
        """
        datadir
            - sensor 1
                - file 1
                - ...
                - file n
            - sensor 2
            - ...
            - sensor n
        
        """        
        sensors = glob.glob(os.path.join(self.datadir, '*'))
        print('adding')
        for s in sensors:
            print(s);
            if os.path.split(s)[-1] == 'satcom' or os.path.split(s)[-1][:4] == 'data':
                continue;
            files = sorted(glob.glob(os.path.join(s, '*')))
            times = [datetime.datetime.strptime(os.path.splitext(f)[0].split('_')[-1], TIME_PATTERN).timestamp() for f in files]
            zipped = sorted(zip(files,times), key=lambda x: x[1])
            # drop files unless they come from the last wakeup time AND are more than 10 minutes old, 
            # so we don't accidentally load data that's still collecting
            ten_minutes_ago = datetime.datetime.now() - datetime.timedelta(minutes=10)
            files = [f for f,t in zipped if ( (t >= self.last_wakeup_time) and (t <= ten_minutes_ago.timestamp() ) )]
            sensor_name = os.path.basename(s)
            print(sensor_name, len(files))
            for f in files:
                data_dict = dr.read_data(f,os.path.basename(sensor_name))
                if (data_dict is None) or (data_dict == {}):
                    continue
                data_dict['wake_up_index'] = [self.this_wakeup_index]*len(data_dict['time'])
                # add values to db
                self.add_values(data_dict, sensor_name)
        print('done adding')

    def get_values(self, k, start_time, end_time, index_type):
        # start time and end time are unix timestamps which is also how time is stored in sql db
        cols = [k, 'time']
        sql = "SELECT "+','.join(cols)+''' FROM data_table WHERE 
              ('''+index_type+''' BETWEEN '''+str(start_time)+''' AND '''+str(end_time) + ''' 
              AND '''+k+''' IS NOT NULL);'''
        cursor = self.execute(sql)
        if cursor is None:
            print('nocurs!')
            return cursor
        # return list of lists of values and column names
        # list[0] = col[0]
        return list(zip(*cursor.fetchall())), [d[0] for d in cursor.description]
    
    def add_values(self, data_dict, source):            
        # add columns if doesn't exist
        columns = self.columns
        keys, vals = [],[]
        for k,v in data_dict.items():
            if k in [source, 'time', 'wake_up_index']:
                colname = k
            else:
                colname = '_'.join([source,k]) if source != '' else k
            if colname in columns:
                pass
            else:
                print('adding column '+colname)
                WRITE_OUT = self.add_column(colname,v[0])
                if WRITE_OUT: #save pointers in db, write data out
                    this_time = data_dict['time'][0] if 'time' in data_dict.keys() else data_dict['wake_up_index'][0]
                    if not os.path.exists(os.path.join(self.datadir, colname)):
                        os.mkdir(os.path.join(self.datadir, colname))
                    this_time = datetime.datetime.fromtimestamp(this_time)
                    this_time = this_time.strftime("%Y-%m-%dT%H%M%S")
                    fname = os.path.join(self.datadir, colname,colname+'_'+this_time+'.pkl')
                    with open(fname, 'wb') as fout:
                        pickle.dump(v, fout)
                    v = [fname]*len(v)
                columns.append(colname)
            keys.append(colname)
            vals.append(v)
        vals = list(zip(*vals))
        sql = "INSERT INTO data_table ('"+ "','".join(keys)+ "') VALUES ("+"?,"*(len(keys)-1)+"?)"
        self.execute(sql, other=vals)
        
    def update_values(self, k, vals, start_time, end_time):
        # either time, or wake_up_index
        if start_time < 10e3:
            timecol = 'wake_up_index'
        else:
            timecol = 'time'
        # get all possible entries
        sql = "SELECT primary_id from data_table WHERE "+timecol+" BETWEEN "+start_time+" AND "+end_time
        cursor = self.execute(sql)
        if cursor is None:
            return
        results = cursor.fetchall()
        if len(results) < len(vals):
            print('Error, no existing entries to update for specified time')
        else:
            ids = [r[0] for r in results[:len(vals)]]
            for n,v in enumerate(vals):
                sql = "UPDATE data_table SET "+k+"="+v+" WHERE primary_id="+str(ids[n])
                self.execute(sql)
        
    def close_db(self):
        self.on_wakeup() # This should be run here
        self.conn.commit()
        self.conn.close()
        with open(self.error_log_path, 'wb') as fin:
            pickle.dump(self.error_log, fin)
    
    def connect(self):
        try:
            conn = sqlite3.connect(self.db_name,check_same_thread=False)
            self.conn = conn
        except Exception as e:
            self.conn = -1
            print(e)
            self.error_log.append(('sqlite3.connect',self.db_name,e)) 
        
    def execute(self, sql, other=None):
        cursor = self.conn.cursor()
        try:
            if other is not None:
                #print(sql, other)
                cursor.executemany(sql, other)
            else:
                cursor.execute(sql)
            return cursor
        except Exception as e:
            print(e)
            self.error_log.append((sql,other,e))
            
    def create_table(self, name):
        create_table_sql = '''CREATE TABLE IF NOT EXISTS '''+name+''' (
                                primary_id INTEGER PRIMARY KEY,
                                wake_up_index INTEGER,
                                time INTEGER);'''
        self.execute(create_table_sql)

        # see if index exists already
        num_index_wakeup = self.execute('''SELECT COUNT(name) FROM sqlite_master WHERE type='index' AND name='idx_wake_up_index'; ''').fetchone()[0]
        if num_index_wakeup == 1: return
        else:
            # create wakeup index because it doesn't exist yet
            self.execute('CREATE INDEX idx_wake_up_index ON data_table(wake_up_index);')
        return
        
    def add_column(self, colname, val):
        WRITE_OUT_FLAG = False
        if type(val) == int:
            dtype = 'INTEGER'
        elif type(val) == float:
            dtype = 'REAL'
        elif type(val) == str:
            dtype = 'TEXT'
        else:
            dtype = 'TEXT' #pointer
            WRITE_OUT_FLAG = True
        sql = "ALTER TABLE data_table ADD COLUMN "+ colname +" "+dtype
        self.execute(sql)
        return WRITE_OUT_FLAG
    
    def timespan(self, k=None, index=True):
        # default to last wake up time
        timecol = 'wake_up_index' if index else 'time'
        t0, tf = -1, -1
        try:
            if k is not None:
                t0 = (self.execute('SELECT MIN('+timecol+') FROM data_table WHERE '+k+' IS NOT NULL AND wake_up_index='+str(self.last_wakeup_index)+';')).fetchone()[0]
                tf = (self.execute('SELECT MAX('+timecol+') FROM data_table WHERE '+k+' IS NOT NULL AND wake_up_index='+str(self.last_wakeup_index)+';')).fetchone()[0]
            else: 
                t0 = self.last_wakeup_index if index else (self.execute('SELECT MIN('+timecol+') FROM data_table WHERE wake_up_index='+str(self.last_wakeup_index)+';')).fetchone()[0]
                tf = self.last_wakeup_index if index else (self.execute('SELECT MAX('+timecol+') FROM data_table WHERE wake_up_index='+str(self.last_wakeup_index)+';')).fetchone()[0]
        except AttributeError:
            pass
        return t0 if t0 is not None else -1, tf if tf is not None else -1
    
    @property 
    def columns(self):
        curs= self.execute('PRAGMA table_info(data_table)')
        if curs is None:
            return []
        return [i[1] for i in curs]
  

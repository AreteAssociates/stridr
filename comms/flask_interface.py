#!/usr/bin/env python3

import os
import sys
import glob
import socket
import json
import datetime
import time
import subprocess
import pickle
import numpy as np
import struct
sys.path.append(os.getcwd())

from flask import Flask, jsonify, abort, make_response, request, render_template

from STRIDR.comms.comms_main import read_packet, jsonify_packet
from STRIDR.comms.analysis.base import xy_to_lat_lon, decode_dist
from STRIDR.services.mt_processor import create_msg
from STRIDR.comms.Packet_Tools import load_packet

packet = b'';
unpacket = {};

LL_PKL = 'll_by_imei.pkl'

ENGINEERING_KEY = b'\x01'
MSG_VERSION = b'\x01'
HEADER = ENGINEERING_KEY + MSG_VERSION

app = Flask(__name__,template_folder= r"/home/oot/STRIDR/comms")
# The template is used for buoy testing.

#Used for on buoy testing
##############################################################################
@app.route('/')
def index():
  packets = glob.glob('/home/oot/data/satcom/mo/*.msg');
  packets.sort(key=lambda f: int(f[(f.rfind('.')-3):f.rfind('.')]))
  if packets:
    packet = packets[-1];
    pack = load_packet(packet);
    dpack = read_packet(pack);
    response_json = json.dumps(jsonify_packet(dpack),sort_keys = True, indent = 4, separators = (',', ': '))
  else:
    response_json = ''; 
  return render_template(
    r'template.html',
    response=response_json.replace('\\n','<br>').replace('\\"','"'),
    date=datetime.datetime.now()
)

@app.route('/ping', methods=['GET'])
def ping():
  return 'ack', 201

def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

@app.route('/shutdown', methods=['POST'])
def shutdown():
    shutdown_server()
    return 'Server shutting down...'

@app.route("/run_test")
def run_test():
    subprocess.Popen('stdbuf -oL python quick_test/quick_test.py > quick_test_out.txt',shell=True);
    return '<pre>Running Tests, redicrecting shortly...</pre><meta http-equiv="refresh" content="2; url=/test">'


@app.route("/test")
def display_test():
    result = 'Test results, updated real-time if still running: \n'
    if os.path.exists('quick_test_out.txt'):
        with open('quick_test_out.txt', 'r') as f:
            result += f.read();
    else:
        result += 'NoFile';
    return '<pre>'+result+'</pre><meta http-equiv="refresh" content="5">'
#End code for on buoy testing
##############################################################################
  
@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)
@app.errorhandler(500)
def intern_err(error):
    return make_response(jsonify({'error': 'Internal Server Error'}), 500)

    
#Server-side encoding 
##############################################################################
@app.route('/arete/get_geofence', methods=['GET'])
def get_geofence():
    return create_msg.format_msg([b'\xB2'])

@app.route('/arete/set_geofence', methods=['POST'])
def set_geofence():
    packet = request.get_json()
    if ( ('keepin' in packet.keys()) and ('keepout' in packet.keys()) ):        # have correct keys, create packet
        keepin = int(packet['keepin'])
        keepout = int(packet['keepout'])
        command = struct.pack('=c2H', b'\xC2', keepin, keepout)
        return create_msg.format_msg([command])
    else:
        return None

@app.route('/arete/binary', methods=['POST'])
def get_binary():
    return create_msg.format_msg(request.get_data().encode('latin1'))

@app.route('/arete/shutdown', methods=['GET'])
def get_shutdown():
    return b'\xff\xff\xff\xff\xff\r\x01\x1e\xc0\xff\xee\x8a\xfe'

@app.route('/arete/patch_mt_eng_message', methods=['GET'])
def patch_mt_eng_message():
    try:
        packet = b'\x39\xdbsudo mount -o remount,rw / && sed -i "s/simple_send_engineering_message(msg).*$/simple_send_engineering_message(msg, send_immediate=True)/" /home/oot/STRIDR/services/mt_processor/commands.py ; sudo mount -o remount,ro /'
        return create_msg.format_msg(packet)
    except Exception as current_exception:
        print(current_exception)
        return make_response('', 500)

@app.route('/arete/set_comms', methods=['POST'])
def set_communications():
    packet = request.get_json()

    #defaults
    interval_minutes = 0

    if ( 'interval_minutes' in packet.keys()): interval_minutes = packet['interval_minutes']

    command_key = b'\xe1'
    command_msg = struct.pack('cB', command_key, interval_minutes)
    return create_msg.format_msg([command_msg])

@app.route('/arete/set_processing', methods=['POST'])
def set_processing():
    # i am in hate with this command format
    packet = request.get_json()
    print(packet)
    if packet is None: packet = {}
    for i, k in enumerate(packet):
        try:
            # format for each command is "key,variable_name,type,value"
            cmd = packet[k]
            cmd = cmd.split(',')

            # key should be string, either 0x3F or 3F, not b'\x3F'... convert to that
            key = cmd[0].strip()
            if key[:2] == '0x': key = key[2:]
            key = bytes.fromhex(key)

            # if variable_name has spaces, strip 'em
            variable_name = cmd[1].strip()

            value_type = cmd[2]
            if value_type == 'bool': value = bool(cmd[3])
            if value_type == 'float': value = float(cmd[3])
            if value_type == 'int': value = int(cmd[3])
            if value_type == 'str': value = str(cmd[3])

        except: 
            return make_response(jsonify({'error': 'Failed to parse command {}.'.format(i)}), 500)

    cmd_str = request.get_data()
    return create_msg.format_msg([ b'\x37' + len(cmd_str).to_bytes(1, 'big') + cmd_str ])

@app.route('/arete/ping', methods=['GET'])
def mt_ping():
    command = b'\x6A'
    return create_msg.format_msg([command])

@app.route('/arete/set_rf', methods=['POST'])
def configure_rf():
    command = b'\xA7'

    # defaults
    xband_threshold = 16
    xband_hysteresis = 1
    ais_threshold = 22
    ais_hysteresis = 1

    # set values if configured
    packet = request.get_json()
    print(packet)
    if 'xband_threshold' in packet.keys(): xband_threshold = packet['xband_threshold']
    if 'xband_hysteresis' in packet.keys(): xband_hysteresis = packet['xband_hysteresis']
    if 'ais_threshold' in packet.keys(): ais_threshold = packet['ais_threshold']
    if 'ais_hysteresis' in packet.keys(): ais_hysteresis = packet['ais_hysteresis']
    
    print(xband_threshold, xband_hysteresis, ais_threshold, ais_hysteresis)
    command_msg = struct.pack('cBBBB', command, xband_threshold, xband_hysteresis, ais_threshold, ais_hysteresis)
    return create_msg.format_msg([command_msg])

    
#Server-side decoding 
##############################################################################
@app.route('/arete/packet', methods=['POST'])
def parse_packet():
  unpacket = json.dumps({});
  if not request.json:
    packet = request.get_data();
    if len(packet) > 340:
      print('packet too big!')
      abort(500)
    try:
      unpacket = read_packet(packet);
      unpacket = jsonify_packet(unpacket);
    except Exception as e:
      print(e)
      abort(500);
  elif request.json and 'data' in request.json and 'IMEI' in request.json:
    unpacket = request.json;
    parsed_data = read_packet(request.json['data'].encode('latin1'));
    unpacket['unpacked_data'] = parsed_data;
    try:
      if not os.path.exists(LL_PKL): #initializing if needed
        with open(LL_PKL,'wb') as f:
          pickle.dump({'test':'test'},f);
      with open(LL_PKL,'rb') as f:
        ll_by_imei = pickle.load(f);
      if unpacket['IMEI'] in ll_by_imei.keys() and not 'Full_ll' in unpacket['unpacked_data'].keys() and 'dlat_meters' in unpacket['unpacked_data'].keys():
        old_ll = ll_by_imei[unpacket['IMEI']]; 
        delta_lls = np.array([unpacket['unpacked_data']['dlat_meters'],
                              unpacket['unpacked_data']['dlon_meters']]);
        new_ll = old_ll+xy_to_lat_lon(delta_lls,old_ll);
        ll_by_imei[unpacket['IMEI']] = list(new_ll);
        unpacket['unpacked_data']['Full_ll'] = new_ll;
      else:
        if not 'dlat_meters' in unpacket['unpacked_data'].keys():
          print('No position information in the packet!' );
          unpacket['unpacked_data']['Full_ll'] = [-9999.99,-9999.99];
        elif not 'Full_ll' in unpacket['unpacked_data'].keys():
          print('Out of order packets!!!! Need first packet first');
        else:
          ll_by_imei[unpacket['IMEI']] = unpacket['unpacked_data']['Full_ll'];
      with open(LL_PKL,'wb') as f:
        pickle.dump(ll_by_imei,f);
    except Exception as e:
      print(e)
      print('Error in LL handling!!')
      unpacket['unpacked_data']['Full_ll'] = [-9999.99,-9999.99]
    #now, finally packaging it up
    unpacket['unpacked_data'] = jsonify_packet(unpacket['unpacked_data']);
    unpacket = jsonify_packet(unpacket)
  return unpacket,  201

    
if __name__ == '__main__':
  app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
  app.run(host='0.0.0.0', port=5000)


# TODO: Merge Packet_Tools prioritize and save, to stress SD card less.

from STRIDR.comms import Packet_Tools, sql_try, analysis
from STRIDR.comms.analysis import Running_Light_Detector
from STRIDR.comms.analysis import microphoneAnalysis
from STRIDR.comms.analysis import fourier_interp
from STRIDR.comms.analysis import ReadSpectrum
from STRIDR.comms.analysis import ReadWaves
from STRIDR.comms.analysis import Image_Clouds
from STRIDR.comms.analysis import mode_zero
from STRIDR.comms.engineering import eng_coms, parse_engineering
from STRIDR.comms.parameters import *
from STRIDR.comms.data_readers import read_data
from STRIDR.comms.data import buoy_database, server_database, single_frame_db, archive
from STRIDR.comms import analysis
import os
import numpy as np
import logging
import time
import argparse
from copy import deepcopy
import sys
import json

sys.path.append(os.getcwd())


rotation = [ReadWaves.Read_Waves, ReadSpectrum.Read_Spectrum, None, None]


def rotate_algorithms():
    # once every hour (or 1 in 4)
    if os.path.exists(ALGORITHM_ROTATION_FILE):
        try:
            with open(ALGORITHM_ROTATION_FILE, 'rb') as fin:
                where = np.frombuffer(fin.read(), dtype=np.uint8)[0]
        except:
            where = 0
    else:
        where = 0
    with open(ALGORITHM_ROTATION_FILE, 'wb') as fin:
        fin.write(np.array((where+1) %
                           len(rotation), dtype=np.uint8).tobytes())
    return rotation[where]


def load_algorithms(mode=HIGHEST_MODE):
    # Load algorithms. There's probably a better way to do this
    environs = []
    detects = []
    compres = []

    if mode == 0:
        rotated_alg = rotate_algorithms()
        if rotated_alg is not None:
            environs += [rotated_alg]
        environs += [Image_Clouds.Image_Clouds,
                     mode_zero.Mean_Var,
                     mode_zero.Co_Var,
                     fourier_interp.Fourier_Interp,
                     microphoneAnalysis.microphoneEnvironment]
        detects += [Running_Light_Detector.Running_Light_Detector]
    if mode == 1:
        environs += []
        detects += []
        compres += []
    if mode == 2:
        environs += []
        detects += []
        compres += []
    if mode == 3:
        environs += []
        detects += []
        compres += []
    return environs, detects, compres


def load_db(demo=False, archive=False):
    print('loading database')
    if os.path.exists(DB_LOCATION):
        if archive:
            db_size = os.stat(DB_LOCATION).st_size
            if db_size > DB_MAX_SIZE:
                print('Database got too big! It is {} bytes, greater than the limit of {} bytes!'.format(
                    db_size, DB_MAX_SIZE))
                archive()

    sqldb = sql_try.database(
        db_name=DB_LOCATION, datadir=DATA_DIRECTORY, manual_file_offset=DB_MANUAL_OFFSET)
    # make db wrapper
    db = buoy_database(source=sqldb)
    if demo:
        # clearing the signal queue:
        print('Clearing the signal queue')
        for q in range(NUM_Qs):
            qname = os.path.join(Q_LOCATION, 'q'+str(q)+'.pkl')
            if os.path.exists(qname):
                os.remove(qname)
    return db


def run_algorithms(db=None, mode=HIGHEST_MODE, logger=None, coms_exception=False):
    # load the algorithms
    environs, detects, compres = load_algorithms(mode=mode)

    if not db:
        db = load_db()

    # Load signal queue
    sig_q = Packet_Tools.init_queue()
    if logger:
        logger.info("Signal Queue loaded")

    # Loop through algorithms, accumulating signals
    # The first algorithm is the header
    for f in environs:
        try:
            if logger:
                logger.info('Running '+f.__name__)
            print('Running '+f.__name__)
            # Are algorithms initialized here?
            alg = f(database=db, paramf=PARAM_FILE)
            # since SB times are weird and different per sensor
            signal = alg.characterize(start_time=None)
            print('  Returned Signal:')
            print('  '+str(signal))
            if signal:
                Packet_Tools.prioritize(signal, sig_q)
                Packet_Tools.sort_signals(sig_q)
                Packet_Tools.save_queue(sig_q)
        except Exception as e:
            if logger:
                logger.info(e)
            print(e)
            coms_exception = True

    for f in detects:
        try:
            if logger:
                logger.info('Running '+f.__name__)
            print('Running '+f.__name__)
            alg = f(database=db, paramf=PARAM_FILE)
            signal = alg.detect(start_time=None)
            print('  Returned Signal:')
            print('  '+str(signal))
            if signal:
                Packet_Tools.prioritize(signal, sig_q)
                Packet_Tools.sort_signals(sig_q)
                Packet_Tools.save_queue(sig_q)
        except Exception as e:
            if logger:
                logger.info(e)
            coms_exception = True
    for f in compres:
        if not os.path.isfile(COMPRESSED_EXPORT_PATH):
            try:
                alg = f(database=db, paramf=PARAM_FILE)  # db = sql database
                sig = alg.characterize(compression_func=compress_func)
                if sig:
                    print('not implemented: saving signal to:' + COMPRESSED_EXPORT_PATH)

            except Exception as e:
                print('Compression failed!')
                print(e)

    return coms_exception


def make_packet(db, mode=HIGHEST_MODE, logger=None, send=False, coms_exception=False):  # Startup
    # Load signal queue
    sig_q = Packet_Tools.init_queue()
    if logger:
        logger.info("Signal Queue loaded")

    # Send queue to packet creater to create packet
    # but first, add the header
    packet = analysis.make_header(db, coms_exception=coms_exception)
    packet += eng_coms()
    if logger:
        logger.info("Packet header assembled")
    packet, signals_incl = Packet_Tools.pack(sig_q, packet)
    if logger:
        logger.info("Signals packed in packet")
    print("""Made a packet with the following signals:
- Header
- Engineering
- Signals {}""".format([x.algID.hex() for x in signals_incl]))
    print('made packet from signals, with length '+str(len(packet)))
    # Okay, when you are ready to send a packet, and want to fill remaining bytes
    n_remain_bytes = MO_MAX_BYTES - len(packet)  # for example
    if n_remain_bytes and logger:
        logger.info("Filling the remaining "+str(n_remain_bytes)+" bytes.")
    # out_bytes will either be exactly as many as you want, or 1 less (will not split up a value)
    # out_bytes will start with algID (0x28)

    # Send Packet.
    # If sending fails, return the signals to the queue.
    # If it succeeds, update the last reported position
    print(packet)
    if send and not Packet_Tools.send(packet):
        if logger:
            logger.info("Packet failed to send!")
        print('sending failed!')
        for sig in signals_incl:
            Packet_Tools.prioritize(sig, sig_q)
    else:
        print('sent!')
        if logger:
            logger.info("Packet sent!")

    # Cleanup
    Packet_Tools.save_queue(sig_q)
    return packet


def export_algorithm_components():
    # load the algorithms, and the database
    environs, detects, compres = load_algorithms(mode=HIGHEST_MODE)
    # load_algorithms is geared towards packet creation, so it doesn't load every possiblity in the rotated_algorithms list
    # add all of those here
    for rotated_alg in rotation:
        if rotated_alg not in environs and rotated_alg:
            environs.append(rotated_alg)
    # similarly, load_algorithms doesn't handle things in mode_zero like polynomial fits
    # add those to compres
    # compres.append( mode_zero.Zip_Compress )
    # compres.append( mode_zero.Polynomial_Fits )

    # collect the
    alg_ID_components = {}
    for f in environs:
        alg = f(database=None, paramf=PARAM_FILE)
        alg_ID_components[alg.byteID.hex()] = {'name': alg.__class__.__name__,
                                               'components': deepcopy(alg.struct_components())}
    for f in detects:
        alg = f(database=None, paramf=PARAM_FILE)
        alg_ID_components[alg.byteID.hex()] = {'name': alg.__class__.__name__,
                                               'components': deepcopy(alg.struct_components())}
    for f in compres:
        alg = f(database=None, paramf=PARAM_FILE)
        alg_ID_components[alg.byteID.hex()] = {'name': alg.__class__.__name__,
                                               'components': -1}
    return alg_ID_components


def read_packet(packet, mode=HIGHEST_MODE):
    # load the algorithms, and the database
    environs, detects, compres = load_algorithms(mode=mode)
    # load_algorithms is geared towards packet creation, so it doesn't load every possiblity in the rotated_algorithms list
    # add all of those here
    for rotated_alg in rotation:
        if rotated_alg not in environs and rotated_alg:
            environs.append(rotated_alg)
    # similarly, load_algorithms doesn't handle things in mode_zero like polynomial fits
    # add those to compres
    # compres.append( mode_zero.Zip_Compress )
    # compres.append( mode_zero.Polynomial_Fits )
    sdb = server_database()

    # collect the
    alg_ID_components = {}
    for f in environs:
        alg = f(database=sdb, paramf=PARAM_FILE)
        alg_ID_components[alg.byteID] = deepcopy(alg.components())
    for f in detects:
        alg = f(database=sdb, paramf=PARAM_FILE)
        alg_ID_components[alg.byteID] = deepcopy(alg.components())
    for f in compres:
        alg = f(database=sdb, paramf=PARAM_FILE)
        alg_ID_components[alg.byteID] = -1
    # Now, actually parse the packet
    packet, header = Packet_Tools.RX_header_handler(packet)

    if ('Full_ll' in header.keys() and
        'BatteryLevel' in header.keys() and
        'software_revision' in header.keys() and
            'subcomponent' in header.keys()):
         # it's an engineering message
        packet, eng = parse_engineering(packet)
        try:
            unpacked = {**header, **eng}
        except:
            unpacked = {**header}
    else:
        packet, signals = Packet_Tools.unpack(packet, alg_ID_components)
        try:
            unpacked = {**header, **signals}
        except:
            unpacked = {**header}
    return unpacked


def jsonify_packet(unpacket):
    def make_jsonable(val):
        if type(val) == np.float32 or type(val) == np.float16 or type(val) == np.float64:
            return float(val)
        elif type(val) == np.int8 or type(val) == np.uint8 or \
                type(val) == np.int16 or type(val) == np.uint16 or \
                type(val) == np.int32 or type(val) == np.uint32:
            return int(val)
        elif type(val) == type(b''):
            return val.decode('latin1')
        elif isinstance(val, (dict, )):
            jsonable_val = {}
            for key, dict_val in val.items():
                jsonable_val[key] = make_jsonable(dict_val)
            return jsonable_val
        else:  # give up, call it a string
            return str(val)
    jpack = {}
    for k, v in unpacket.items():
        if type(v) == np.ndarray:
            if len(v) == 1:
                jpack[k] = make_jsonable(v[0])
            else:
                jpack[k] = [make_jsonable(val) for val in v]
        else:
            jpack[k] = make_jsonable(v)
    with open('AretePacket.json', 'w') as f:
        json.dump(jpack, f)
    return json.dumps(jpack)


if __name__ == '__main__':
    def existing_dir(string):
        if os.path.isfile(string):
            return string
        else:
            raise ValueError(
                "Path to file must exist, and must point to the binary packet")
    # Some basic argument parsing
    parser = argparse.ArgumentParser(
        description='Arete Ocean of Things Communications Interface')
    parser.add_argument('--demo', action='store_true',
                        help='Run the demo on the data in the Demo folder.')
    parser.add_argument('--path', type=existing_dir,
                        help='Path to an existing packet. If given, the script just unpacks this packet.')
    args = parser.parse_args()
    send_packet = not args.demo

    if args.path:
        packet = Packet_Tools.load_packet(args.path)
        unpacket = read_packet(packet)
        json_packet = jsonify_packet(packet)
        print(json_packet)
        sys.exit()

    # Start logger
    # logger = logging.getLogger('Coms');
    # logger.setLevel(logging.DEBUG);
    # fh = logging.FileHandler("coms"+str(int(time.time()))+'.log')
    # fh.setLevel(logging.DEBUG);
    logger = None
    coms_exception = False
    # if DEBUG:
    #  ch = logging.StreamHandler()
    #  ch.setLevel(logging.ERROR)

    # Load data interface
    db = load_db(args.demo)
    # load database class or create if doesn't exist
    if logger:
        logger.info("DB loaded")
    # try:
    run_algorithms(db, logger=logger)
    packet = make_packet(db, logger=logger, send=send_packet)
    Packet_Tools.save_packet(
        packet, 'areteMO'+str(db.source.this_wakeup_index)+'.packet')
    # except:
    #  print('This round failed')
    # close database (save out error log, etc.)
    db.source.close_db()

    if args.demo:
        unpacket = read_packet(packet)
        json_packet = jsonify_packet(unpacket)
        import shutil
        shutil.move('AretePacket.json', 'AretePacket' +
                    str(db.source.this_wakeup_index)+'.json')
        print(json_packet)

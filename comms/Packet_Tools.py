# TODO: Robustify! Make sure things don't break easy.
#

import os
from copy import deepcopy
import pickle
import numpy as np
import struct

from STRIDR.comms.parameters import *
from STRIDR.comms.analysis.base import decode_dist

ENGINEERING_KEY = b'\x01'
MSG_VERSION_1 = b'\x01'
ENGINEERING_HEADER = ENGINEERING_KEY + MSG_VERSION_1


def pack(sig_q, packet):
    # accumulates signals in order, until the packet is full or the queue is empty
    def byte_len(x): return len(x.components)+len(x.algID)
    signals_incl = []
    iterstop = 0
    # to handle the fact that some items may be priority, but are too big for the packet
    top_mainind = NUM_Qs
    while len(packet) < MO_MAX_BYTES and iterstop < MAX_ITER:
        iterstop += 1
        max_siglen = MO_MAX_BYTES-len(packet)
        # gets a list of main queue indices with items
        main_ind_list = [i for i, q in enumerate(
            sig_q[:top_mainind]) if len(q)]
        if not main_ind_list:  # queue is empty!
            print('Queue is empty!')
            return packet, signals_incl
        main_ind = max(main_ind_list)
        # now, for the main index we found above, see if any items there fit
        sub_ind_list = [i for i, q in enumerate(
            sig_q[main_ind]) if byte_len(q) < max_siglen]
        if not sub_ind_list:  # no items fit from main_ind.
            top_mainind = main_ind-1
            if top_mainind == 0:  # queue doesn't have any signals small enough for packet remainder
                return packet, signals_incl
        else:
            sub_ind = max(sub_ind_list)
            packet += sig_q[main_ind][sub_ind].algID + \
                sig_q[main_ind][sub_ind].components
            signals_incl.append(sig_q[main_ind].pop(sub_ind))
        if not iterstop < MAX_ITER:
            print('something went wrong, reached maxiter in packet_tools.pack')
            break
    return packet, signals_incl


def unpack(packet, alg_ID_components):
    # Parse the rest of the packet
    returndict = {}
    iterstop = 0
    while len(packet) and iterstop < MAX_ITER:
        iterstop += 1
        if not iterstop < MAX_ITER:
            print('something went wrong, reached maxiter in packet_tools.unpack')
            break
        while not packet[0:1] in alg_ID_components.keys():
            iterstop += 1
            if not iterstop < MAX_ITER:
                print('something went wrong, reached maxiter in packet_tools.unpack')
                break
            # so,if we are in here, we assume something has gone wrong. For now,
            # we can hope that incrementing by one will help.
            # print('Could not find ID '+str(packet[0:1]))
            if not 'not_decoded' in returndict.keys():
                returndict['not_decoded'] = b''
            returndict['not_decoded'] += packet[0:1]  # .decode('latin1')
            packet = packet[1:]
        # print(alg_ID_components[packet[0:1]]);
        if len(packet) and packet[0:1] in alg_ID_components.keys():
            print('Found byteID {} in the packet'.format(packet[0:1]))
            sigdict, packet = general_handler(
                packet, alg_ID_components[packet[0:1]])
            try:
                returndict = {**sigdict, **returndict}
            except:
                # safe to pass here since returndict doesn't need to be updated
                pass
        else:
            break
    return packet, returndict


def handle_engineering_messages_version1(packet):
    header = {}
    # strip engineering header off
    packet = packet[len(ENGINEERING_HEADER):]
    print('Processing version 1 engineering message.')

    # boot test message also contains location but who cares
    if packet[:36] == b'Unit initial boot testing completed.':
        header['Text_Status'] = packet
        return b'', header

    # Ping handler
    msg_matcher = b'Ping'
    if packet[:len(msg_matcher)] == msg_matcher:
        parts = packet.split(',')
        header['Ping'] = 'OK'
        header['Timestamp'] = parts[1]
        header['Full_ll'] = [parts[2], parts[3]]
        return b'', header

    # Error message handler
    msg_matcher = 'Error.'
    if packet[:len(msg_matcher)] == msg_matcher:
        header['Text_Status'] = packet
        return b'', header

    # Geofence setting
    msg_matcher = 'keepin='
    if packet[:len(msg_matcher)] == msg_matcher:
        header['Text_Status'] = packet
        return b'', header


def RX_header_handler(packet):
    header = {}
    if packet[0] and ENGINEERING_KEY == True:
        if packet[1] == MSG_VERSION_1:
            return b'', handle_engineering_messages_version1(packet)
    elif (packet[:3] == b'\xff\xff\xff' and
          (packet[13] == int.from_bytes(b'\x01', 'little') or
            packet[13] == b'\x01')):
        # it's an engineering message
        BATTHI = 14.2
        BATTLO = 12.5
        _, _, _, battery_status, subcomponent, latitude, longitude, _ = struct.unpack(
            '=cccccffc', packet[:14])
        header['Full_ll'] = np.array([latitude, longitude])
        header['BatteryLevel'] = int.from_bytes(
            battery_status, byteorder='little') / 16 * (BATTHI - BATTLO) + BATTLO
        code_version = int.from_bytes(subcomponent, byteorder='little') >> 4
        header['software_revision'] = 'ABCDEFGHIJKLMN_'[code_version - 1]
        header['subcomponent'] = subcomponent
        packet = packet[14:]
        return packet, header
    else:
        # Handle data messages
        header_bytes = packet[:16]
        packet = packet[16:]
        # decode system status
        header['System_Status'] = {'coms_exception': True if header_bytes[0] & 64 == 64 else False,
                                   'sys_exception': True if header_bytes[0] & 128 == 128 else False,
                                   'wakeup_index': packet[0] & 63}
        # decode position, including DOPs, latitude, longitude, and check for current GPS position reported
        dops = np.frombuffer(
            header_bytes[1:4], dtype='uint8').astype('float') / 10
        header['position'] = {'pdop': dops[0],
                              'hdop': dops[1],
                              'vdop': dops[2],
                              'number_of_satellites': header_bytes[4],
                              'latitude': np.frombuffer(header_bytes[8:12], dtype=np.float32)[0],
                              'longitude': np.frombuffer(header_bytes[12:], dtype=np.float32)[0]}
        if header['position']['latitude'] > 90:
            print('Packet_Tools.RX_header_handler: This packet contains a current GPS position indicated an issue with the GPS during the sample period.')
            header['position']['latitude'] -= 500
            header['position']['status'] = 'Current GPS position reported'
        else:
            header['position']['status'] = 'Sample period GPS position reported'

        # handle charge rate and battery
        charge_rate = (header_bytes[5] >> 4) / 16
        CHRGHI = .5
        header['ChargeRate'] = charge_rate * CHRGHI
        # decode battery, move this to a separate encode/decode function in the future
        BATTHI = 15.0
        BATTLOW = 12.5
        battery_level = ((header_bytes[5] & 240) >> 4) / 16
        header['BatteryLevel'] = battery_level * (BATTHI - BATTLOW) + BATTLOW

        # figure out the code version
        code_version = np.uint8(header_bytes[6]) >> 4
        header['software_revision'] = 'ABCDEFGHIJKLMN_'[code_version - 1]

        return packet, header


def null_handler(packet):
    # return an empty dictionary, and the packet minus the headder.
    return {}, packet[2:]


def general_handler(packet, components):
    # removing the algorithm marker
    byteID = packet[0].to_bytes(1, 'big')
    packet = packet[1:]
    datas = {}
    if components == -1:
        datas['Compressed_Data'] = packet
        return datas, b''
    try:
        for component, length in components.items():
            if length == 8:
                datas[component] = np.frombuffer(packet[:1], dtype=np.uint8)
                packet = packet[1:]
            elif length == 16:
                datas[component] = np.frombuffer(packet[:2], dtype=np.float16)
                packet = packet[2:]
            elif length == 32:
                datas[component] = np.frombuffer(packet[:4], dtype=np.float32)
                packet = packet[4:]
            elif length == 64:
                datas[component] = np.frombuffer(packet[:8], dtype=np.float64)
                packet = packet[8:]
        return datas, packet
    except:
        print('Failed to decode a {} packet, removing the byteID and returning the remaining packet for processing'.format(byteID))
        return None, packet


def sort_signals(sig_q):
    def priority_order(x): return x.priority
    for q in sig_q:
        q.sort(key=priority_order, reverse=True)
    return


def init_queue():
    sig_q = []
    for q in range(NUM_Qs):
        qname = os.path.join(Q_LOCATION, 'q'+str(q)+'.pkl')
        # if there is no q file, or if it's blank
        if ((not os.path.isfile(qname)) or (os.path.getsize(qname) == 0)):
            # make one
            with open(qname, 'wb') as f:
                pickle.dump([], f)
                sig_q.append([])
        else:
            with open(qname, 'rb') as f:
                sig_q.append(pickle.load(f))
    return sig_q


def save_queue(sig_q):
    for n, q in enumerate(sig_q):
        qname = os.path.join(Q_LOCATION, 'q'+str(n)+'.pkl')
        with open(qname, 'wb') as f:
            pickle.dump(q, f)
    return


def age_queue(sig_q):
    # mean_var, fourier_interp
    replace_algIDs = {b'\x11': False, b'\x27': False}
    new_sig_q = [[]*NUM_Qs]
    for n, q in enumerate(sig_q):  # only replace within a priority level
        q_algids = [sig.algID for sig in q]
        this_q = []
        for sig in q:
            if sig.algID in replace_algIDs.keys():
                if replace_algIDs[sig.algID]:
                    continue  # already added latest, no need to add previous
                else:
                    where = np.where(np.array(q_algids) == sig.algID)[0]
                    if len(where) > 1:
                        # multiple occurrences, add latest one.
                        this_q.append(q[where[-1]])
                        # will ignore/drop the other occurences
                        replace_algIDs[sig.algID] = True
            else:
                this_q.append(sig)
        new_sig_q[n] = this_q
    sig_q = new_sig_q
    return sig_q


def prioritize(signal, sig_q):
    # simple now, lots of potential improvement
    priority_level = int(signal.priority)
    sig_q[priority_level].append(signal)
    return None


def send(packet):
    # This would return the result of the packet send command
    # Ideally it returns true, indicating successful transmit
    # Returns false on failed transmit
    # Since we're presently /not/ transmitting, we're going to
    #   return True, indicating successful transmit, because
    #   failure to try isn't failure to send. Right? Right.
    #
    # The commented-out command below is a stub that used to 
    # transmit the binary packet
    #return satcom_send_and_receive(packet)
    return True


def save_packet(packet, filename):
    with open(filename, 'wb') as f:
        f.write(packet)


def load_packet(filename):
    with open(filename, 'rb') as f:
        packet = f.read()
    return packet

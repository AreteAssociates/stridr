import numpy as np
import struct

def eng_coms():
    return b''


def parse_engineering(packet):
    # boot test message also contains location but who cares
    if packet[:36] == b'Unit initial boot testing completed.':
        print(packet.decode('Latin-1'))
        return None, {'message': packet.decode('Latin-1')}

    else:
       return None, None


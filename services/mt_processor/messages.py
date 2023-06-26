#!/usr/bin/env python3

# format = { cmd: ['Text Name', 
#                  function_name, 
#                  [param1_num_bytes, param2_num_bytes, etc.] ]
#          }

#from STRIDR.services.mt_processor.commands import *
from STRIDR.services.mt_processor import commands

offset_length = 5
offset_ncmds  = 6
offset_crc    = -2

cmds = { 0xE1: ['COMMS: Set Rate', commands.comms_set_rate, [1] ],
         #0x99: ['COMMS: Configure Communications',
         #       commands.comms_configure, [1, 1, 1] ],
         #0x78: ['COMMS: Set Quiet Period', 
         #       commands.comms_set_quiet_period, [1] ],
         #0xD2: ['DEVICE: Disable device', commands.device_disable, [1] ],
         #0x33: ['DEVICE: Enable device', commands.device_enable, [1] ],
         #0x4B: ['DEVICE: Configure device',
         #       commands.device_configure, [1, 1, 1, 1] ],
        #0x66: ['SYSTEM: Enable wifi', commands.system_enable_wifi, [1] ],
         0x1E: ['SYSTEM: Shutdown', commands.system_shutdown, [3] ],
         0xA7: ['DEVICE: Configure RF sensor', commands.configure_rf_settings, [1, 1, 1, 1] ],
         0x37: ['DEVICE: Configure processing variables', commands.configure_processing_variables, ['L'] ],
         0x6A: ['SYSTEM: Ping', commands.ping, [0] ],
         0xF7: ['SYSTEM: Update database parameter', commands.update_db, [1, 1, 4] ],
         0x39: ['SYSTEM: Shell command', commands.shell, ['L'] ],
       }


SHUTDOWN_SECRET = b'\xC0\xFF\xEE'

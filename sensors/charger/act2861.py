import smbus
import time
import atexit

bus = 1
addr = 0x24

b = smbus.SMBus(bus)


class act2861(object):

        bus = 0
        addr = 0
        b = None

        reg_MAIN_CONTROL1 = 0x00
        reg_MAIN_CONTROL2 = 0x01
        reg_STATUS_GEN    = 0x02
        reg_STATUS_CHG    = 0x03
        reg_STATUS_TEMP   = 0x04
        reg_FAULTS1       = 0x05
        reg_FAULTS2       = 0x06
        reg_ADC_OUT1      = 0x07
        reg_ADC_OUT2      = 0x08 # not used on its own
        reg_ADC_CONFIG1   = 0x09
        reg_ADC_CONFIG2   = 0x0a
        reg_CHG_CONTROL1 = 0x0b
        reg_CHG_CONTROL2 = 0x0c
        reg_CHG_CONTROL3 = 0x0d
        reg_OTG_MODE1 = 0x0e
        reg_OTG_MODE2 = 0x0f
        reg_OTG_MODE3 = 0x10
        reg_BATT_VOLT1 = 0x11
        reg_BATT_VOLT2 = 0x12
        reg_OTG_VOLT1 = 0x13
        reg_OTG_VOLT2 = 0x14
        reg_IN_I_LIM = 0x15
        reg_IN_V_LIM = 0x16
        reg_OTG_I_LIM = 0x17
        reg_FAST_CHG_I = 0x18
        reg_PRECHG_TERM_I = 0x19
        reg_BATT_LOW_V = 0x1a
        reg_SAFETY_TIMER = 0x1b
        reg_JEITA = 0x1c
        reg_TEMP_SET = 0x1d
        reg_IRQ_CONTROL1 = 0x1e
        reg_IRQ_CONTROL2 = 0x1f
        reg_OTG_STATUS = 0x20

        adc_VIN  = 0x09
        adc_VOUT = 0x12
        adc_IIN  = 0x00
        adc_IOUT = 0x1b
        adc_TEMP = 0x2d

        MAIN_CONTROL1 = { 'HIZ' : 0x80,
                          'OVERRIDE_EN_CHG' : 0x40,
                          'SHIPM_ENTER' : 0x20,
                          'GPIO_OUT' : 0x10,
                          'DIS_NCHG_CHG' : 0x08,
                          'WATCHDOG_RESET' : 0x04,
                          'AUDIO_FREQUENCY_LIMIT' : 0x02,
                          'REGISTER_RESET' : 0x01 }
                          
        MAIN_CONTROL2 = { 'DIS_TH' : 0x80,
                          'DIS_OCP_SHUTDOWN' : 0x40,
                          'DIS_VBAT_OVP' : 0x20,
                          'FET_ILIMIT' : 0x10,
                          'VIN_OV_RESTART_DELAY' : 0x08,
                          'VREG_EN' : 0x04,
                          'WATCHDOG1' : 0x02,
                          'WATCHDOG2' : 0x01 }


        def __init__(self, bus=1, addr=0x24):
            self.bus = bus
            self.addr = addr
            self.b = smbus.SMBus(bus)
            atexit.register(self.close)
            return

        def close(self):
            b.close()
            return

        def get_register(self, reg):
            return self.b.read_i2c_block_data(self.addr, reg, 1)[0]

        def set_register(self, reg, value):
            return self.b.write_byte_data(self.addr, reg, value)

        def get_register_bit(self, reg, bit):
            register_value = self.get_register(reg)
            register_bit = register_value & (1<<bit)
            return register_bit >> bit

        def set_register_bit(self, reg, bit):
            v = self.get_register(reg)
            new_v = v | (1<<bit) # sets bit
            self.b.write_byte_data(self.addr, reg, new_v)
            v = self.get_register_bit(reg, bit)
            if v == 1: return True
            return False

        def clear_register_bit(self, reg, bit):
            v = self.get_register(reg)
            new_v = v & ~(1<<bit) # clears bit
            self.b.write_byte_data(self.addr, reg, new_v)
            v = self.get_register_bit(reg, bit)
            if v == 0: return True
            return False

        def latch_adc_inputs(self):
            self.b.write_byte_data(self.addr, self.reg_ADC_CONFIG1, 0xc7) # one shot
            return

        def is_adc_ready(self, timeout=1):
            t_start = time.time()
            while self.b.read_i2c_block_data(self.addr, self.reg_ADC_CONFIG2, 1)[0] & 0x80 != 0x80:
                # not ready
                if time.time() > t_start + timeout:
                    return False
            # broke out of wait loop; ADC_DATA_READY == 1, adc is ready
            return True

        def get_adc_channel(self, channel):
            self.b.write_byte_data(self.addr, self.reg_ADC_CONFIG2, channel)
            if self.is_adc_ready():
                v = self.b.read_i2c_block_data(self.addr, self.reg_ADC_OUT1, 2)
                return int(format(v[0], '08b')+format(v[1], '08b')[2:6], 2) - 2048
            else:
                return 0

        def get_adc_vin(self):
            self.latch_adc_inputs()
            return 0.02035 * self.get_adc_channel(self.adc_VIN)

        def get_adc_vout(self):
            self.latch_adc_inputs()
            return 0.01527 * self.get_adc_channel(self.adc_VOUT)

        def get_adc_iin(self):
            self.latch_adc_inputs()
            return 0.7633 / 33000 / 0.01 * self.get_adc_channel(self.adc_IIN)

        def get_adc_iout(self):
            self.latch_adc_inputs()
            return 1 * 0.7633 / 33000 / 0.01 * self.get_adc_channel(self.adc_IOUT)

        def get_adc_temp(self):
            self.latch_adc_inputs()
            return 0.2707 * self.get_adc_channel(self.adc_TEMP) - 809.49

        def byte_to_bool(self, byte, bit):
            return format(byte, '08b')[::-1][bit] == '1'

        def disable_safety_timer(self):
            return self.set_register_bit(self.reg_SAFETY_TIMER, 6)

        def enable_safety_timer(self):
            return self.clear_register_bit(self.reg_SAFETY_TIMER, 6)

        def disable_th(self):
            return self.set_register_bit(self.reg_MAIN_CONTROL2, 7)
        
        def enable_th(self):
            return self.clear_register_bit(self.reg_MAIN_CONTROL2, 7)

        def set_input_current_limit(self, value):
            enable_current_limit = 0x80
            if not ( (value > 0.1) & (value < 1.27) ):
                return False
            voltage = int(value * 10)
            set_val = enable_voltage_limit | voltage
            return self.set_register(self.reg_IN_I_LIM, set_val)

        def set_input_voltage_limit(self, value):
            enable_voltage_limit = 0x80 # we can never set this bit in the range limit, so it will always stay enabled
            offset = 4.0
            if not ( (value > 0.1) & (value < 12.7) ):
                return False
            voltage = int((value - offset) * 10)
            return self.set_register(self.reg_IN_V_LIM, voltage)

        def set_batt_set_voltage(self, value):
            offset = 5
            setpoint = int( 100*(value-offset) )
            high_byte = (setpoint & 0xff00) >> 8
            low_byte = (setpoint & 0xff)
            high_register = self.get_register(self.reg_BATT_VOLT1)
            mask = high_register & 0x07
            new_high_register = mask | high_register
            new_low_register = low_byte
            self.b.write_i2c_block_data(self.addr, self.reg_BATT_VOLT1, [new_high_register, new_low_register])
            return True

        def get_batt_set_voltage(self):
            offset = 5 #V from datasheet p81
            registers = self.b.read_i2c_block_data(self.addr, self.reg_BATT_VOLT1, 2)
            registers[0] = registers[0] & 0x07 # mask off LDO bytes
            return int.from_bytes(registers, byteorder='big')/100 + offset  #convert from cV to V and add offset

        def set_batt_recharge_voltage(self, v_recharge):
            settings = [ 200, 300, 400, 450, 500, 600, 750, 800 ] # mV setpoints
            if v_recharge not in settings:
                print('V_recharge setpoints are: {} mV.'.format(settings))
                return False
            index = settings.index(v_recharge)
            reg_val = self.get_register(self.reg_CHG_CONTROL3)
            mask = reg_val & 0x1f # clear the top three bits
            new_reg_val = mask | (index << 5) # shift index to start at bit 5
            return self.set_register(self.reg_CHG_CONTROL3, new_reg_val)

        def set_vin_limit(self, value):
            offset = 4
            if value > 16.7: return False
            setpoint = int((value - offset) * 10)
            return self.set_register(self.reg_IN_V_LIM, setpoint)

        def get_vin_limit(self):
            offset = 4
            return self.get_register(self.reg_IN_V_LIM) / 10 + offset

        def enable_vin_limit(self):
            return self.clear_register_bit(self.reg_IN_V_LIM, 7)

        def disable_vin_limit(self):
            return self.set_register_bit(self.reg_IN_V_LIM, 7)

        def set_iin_limit(self, value):
            if value > 16.7: return False
            setpoint = int(value)
            return self.set_register(self.reg_IN_I_LIM, setpoint)

        def get_iin_limit(self):
            return self.get_register(self.reg_IN_I_LIM)

        def enable_iin_limit(self):
            return self.clear_register_bit(self.reg_IN_I_LIM, 7)

        def disable_iin_limit(self):
            return self.set_register_bit(self.reg_IN_I_LIM, 7)

        def get_faults(self):
            v = self.b.read_i2c_block_data(self.addr, self.reg_FAULTS1, 2) # 2 registers long
            if v == [0, 0]: no_faults = True
            else: no_faults = False
            return { 'NO_FAULTS'        : no_faults,
                     'nIRQ_clear'       : self.byte_to_bool(v[0], 7),
                     'CHG_Time_Expired' : self.byte_to_bool(v[0], 6), 
                     'CHG_VBAT_OV'      : self.byte_to_bool(v[0], 5), 
                     'VREG_OC_UVLO'     : self.byte_to_bool(v[0], 4), 
                     'TSD'              : self.byte_to_bool(v[0], 3), 
                     'FET_OC'           : self.byte_to_bool(v[0], 2), 
                     'CHG_MODE_INPUT_OV': self.byte_to_bool(v[0], 1), 
                     'CHG_MODE_INPUT_UV': self.byte_to_bool(v[0], 0), 
                     'WATCHDOG_FAULT'   : self.byte_to_bool(v[1], 7),
                     'OTG_VOUT_FAULT'   : self.byte_to_bool(v[1], 6), 
                     'OTG_VBAT_CUT_FLT' : self.byte_to_bool(v[1], 5), 
                     'OTG_VOUT_OV'      : self.byte_to_bool(v[1], 4), 
                     'OTG_LIGHT_LOAD'   : self.byte_to_bool(v[1], 3), 
                     'OTG_VBAT_OV'      : self.byte_to_bool(v[1], 2), 
                     'I2C FAULT'        : self.byte_to_bool(v[1], 1), 
                     'DEADBATTERY'      : self.byte_to_bool(v[1], 0) }

        def get_temperature_status(self):
            v = self.b.read_i2c_block_data(self.addr, self.reg_STATUS_TEMP, 1)[0]
            return { 'POK_VOUT'         : self.byte_to_bool(v, 7),
                     'TH_BAT_DETECT'    : self.byte_to_bool(v, 6),
                     'OTG_COLD_DIS'     : self.byte_to_bool(v, 5),
                     'OTG_HOT_DIS'      : self.byte_to_bool(v, 4),
                     'CHRG_COLD'        : self.byte_to_bool(v, 3),
                     'CHRG_COOL'        : self.byte_to_bool(v, 2),
                     'CHRG_WARM'        : self.byte_to_bool(v, 1),
                     'CHRG_HOT'         : self.byte_to_bool(v, 0) }

        def get_charger_status(self):
            v = self.b.read_i2c_block_data(self.addr, self.reg_STATUS_CHG, 1)[0]
            chg_status = { '0000' : 'RESET',
                           '0001' : 'SCOND',
                           '0010' : 'SCSUSPEND',
                           '0011' : 'PCOND',
                           '0100' : 'PCSUSPEND',
                           '0101' : 'FASTCHG',
                           '0110' : 'FCSUSPEND',
                           '0111' : 'CHGFULL',
                           '1000' : 'CFSUSPEND',
                           '1001' : 'CHGTERM',
                           '1010' : 'CTSUSPEND',
                           '1011' : 'FAULT' }

            return { 'EN_CHG_PIN_STATUS': self.byte_to_bool(v, 7),
                     'THERMAL_ACTIVE'   : self.byte_to_bool(v, 6),
                     'INPUT_IINLIM_STATUS': self.byte_to_bool(v, 5),
                     'INPUT_VINLIM_STATUS': self.byte_to_bool(v, 4),
                     'CHARGE_STATUS'    : chg_status[ format(v, '08b')[4:] ] }

        def get_general_status(self):
            v = self.b.read_i2c_block_data(self.addr, self.reg_STATUS_GEN, 1)[0]
            op_mode = { '00' : 'HiZ Mode',
                        '01' : 'Charger Mode',
                        '10' : 'OTG Mode',
                        '11' : 'INVALID MODE!!!' }
            return { 'nVBAT_Good'        : self.byte_to_bool(v, 7),
                     'nIRQ_PIN_STATUS'   : self.byte_to_bool(v, 6),
                     'nOTG_PIN_STATUS'   : self.byte_to_bool(v, 5),
                     'INPUT_UVLO_CHG'    : self.byte_to_bool(v, 4),
                     'INPUT_OV_CHG'      : self.byte_to_bool(v, 3),
                     'GPIO_IN'           : self.byte_to_bool(v, 2),
                     'MODE'              : op_mode[ format(v, '08b')[6:] ] }




if __name__ == '__main__':
    bus = 1
    charger = act2861(bus)
    charger.get_adc_vout() #etc
    charger.b.write_byte_data(0x24, 0x0a, 0x09)
    charger.b.read_i2c_block_data(0x24, 0x07, 2)


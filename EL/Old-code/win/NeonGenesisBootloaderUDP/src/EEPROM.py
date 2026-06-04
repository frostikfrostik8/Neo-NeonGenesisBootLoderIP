import re
import configparser
from output import logger
from crc16 import crc16

class EEPROM:
    def __init__(self, file, log = logger):
        self.file = file
        self.log = log
        self.config = configparser.ConfigParser()
        self.template = configparser.ConfigParser()
        self.crc = crc16()

        self.config_struct_0 = { 'PwM_FillMode': {'val': 0xFF}, 
                    'PwM_Groups': {'gr0': 0xFFFF, 
                                   'gr1': 0xFFFF, 
                                   'gr2': 0xFFFF},
                    'KM_decNum': {'val': 0xFF},
                    'KMx_State': {'val0': 0xFF,
                                  'val1': 0xFF,
                                  'val2': 0xFF,
                                  'val3': 0xFF,
                                  'val4': 0xFF,
                                  'val5': 0xFF,
                                  'val6': 0xFF,
                                  'val7': 0xFF},
                    'Controller_Type': {'val': 0xFF},
                    'Shunt_Code': {'val': 0xFF},
                    'EVSE_Type': {'val': 0xFF},
                    'Version_Board': {'val': 0xFF},
                    'StationPower': {'val': 0xFFFF},
                    'StationMaxCurrent': {'val': 0xFFFF},
                    'Flags1': {'val': 0xFF},
                    'Flags2': {'val': 0xFF},
                    'nLeds_1': {'val': 0xFF},
                    'LedOffset_1': {'val': 0xFF},
                    'nLeds_2': {'val': 0xFF},
                    'LedOffset_2': {'val': 0xFF},
                    'Relay': {'val4': 0xFF, 
                              'val5': 0xFF, 
                              'val6': 0xFF, 
                              'val7': 0xFF, 
                              'val8': 0xFF}}

        self.config_struct_1 = { 'PwM_FillMode': {'val': 0xFF}, 
                    'PwM_Section': {'val': 0xFFFFFFFFFFFF},
                    'KM_decNum': {'val': 0xFF},
                    'KMx_State': {'val0': 0xFF},
                    'KMx_State': {'val1': 0xFF},
                    'KMx_State': {'val2': 0xFF},
                    'KMx_State': {'val3': 0xFF},
                    'KMx_State': {'val4': 0xFF},
                    'KMx_State': {'val5': 0xFF},
                    'KMx_State': {'val6': 0xFF},
                    'KMx_State': {'val7': 0xFF},
                    'Controller_Type': {'val': 0xFF},
                    'Shunt_Code': {'val': 0xFF},
                    'EVSE_Type': {'val': 0xFF},
                    'Version_Board': {'val': 0xFF},
                    'StationPower': {'val': 0xFFFF},
                    'StationMaxCurrent': {'val': 0xFFFF},
                    'Flags1': {'val': 0xFF},
                    'Flags2': {'val': 0xFF},
                    'nLeds_1': {'val': 0xFF},
                    'LedOffset_1': {'val': 0xFF},
                    'nLeds_2': {'val': 0xFF},
                    'LedOffset_2': {'val': 0xFF},
                    'Relay': {'val4': 0xFF, 
                              'val5': 0xFF, 
                              'val6': 0xFF, 
                              'val7': 0xFF, 
                              'val8': 0xFF}}

        try:
            self.config.read(self.file)
        except configparser.Error as e:
            log.log(f"Error reading INI file: {e}")
            exit()

        try:
            self.template.read("Config_Template.ini")
        except configparser.Error as e:
            self.log.log(f"Error reading Template file: {e}")
            exit()

    def __del__(self):
        pass

    def findPair(self, collection, key1, key2):
        retval = 0
        for i in collection:
            if i == key1:
                retval += 1
                for j in collection[i]:
                    if j == key2: retval += 1

        return retval

    def getArrayEEPROM(self):
        config_array = bytearray()

        self.log.logfile("\n************ EEPROM Structure ***********")

        for i in self.template.sections(): 
            try:
                for j in self.template[i].keys():
                    value = self.template.getint(i, j)
                    size = 0
                    while value != 0:
                        value = value >> 8
                        size += 1

                    if(self.findPair(self.config, i, j) == 2):
                        for t in range(0, size): config_array.append((self.config.getint(i, j) >> (8 * (size - t - 1))) & 0xFF)
                        self.log.logfile("* {:<20}\\{:<5}:{:>10} *".format(i, j, hex(self.config.getint(i, j))))
                    else:
                        for t in range(0, size): config_array.append(0x00)
                        self.log.logfile("* {:<20}\\{:<5}:{:>10} *".format(i, j, hex(0)))
            except configparser.Error as e:
                self.log.log(f"\nError reading .ini file: {e}")

        self.log.logfile("************ EEPROM Structure ***********")

        crc = self.crc.findCRC(config_array, len(config_array))
        config_array.append((crc & 0xFF))
        config_array.append((crc >> 8) & 0xFF)
        self.log.log("\nEEPROM buffer include {} bytes: ".format(len(config_array)) + "{}".format(config_array.hex()))

        return config_array



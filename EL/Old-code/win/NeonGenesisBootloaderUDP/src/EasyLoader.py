#import socket
import keyboard
import time
import math
from sys import argv, platform, exit
# import re

if platform.startswith("linux"):
    import virtualserialports

#For ESP32
import esptool
import threading
# import stopit

#User Libriaries
from output import logger
from serialport import serialport
from udp import udpport
from crc16 import crc16
from EEPROM import EEPROM
from esplogger import CustomLogger

#Create obj
log = logger()
crc = crc16()

#Type update
update_type = 0

# params = [10]
# params = argv
# print(params)

# (script, id, Port, file, ip) = params

#Application arguments
if len(argv) == 4: 
    script, id, Port, file = argv
    update_type = 0
elif len(argv) == 5: 
    script, id, Port, file, ip = argv
    update_type = 1
else:
    log.printBanner()
    exit()

if(update_type == 0): ser = serialport(Port, 115200, log)
elif(update_type == 1): udp = udpport(ip, Port, log)

if len(id) <= 3:
    id_arr = list(id)
    if len(id) == 1:
        ID = int(id[0], base = 16)
        ID_PERIPH = 0
    if len(id) == 2:
        ID = int(id[1], base = 16)
        ID_PERIPH = int(id[0], base = 16)
        if ID_PERIPH > 0x09: 
            ID = (ID_PERIPH << 4) + ID
            ID_PERIPH = 0
    if len(id) == 3:
        ID = int(id[2], base = 16)
        ID_PERIPH = (int(id[0], base = 16) << 4) + int(id[1], base = 16)

log.log("\n----------- Update parameters -----------\n")
log.printDevice(ID, ID_PERIPH)
log.printDate()
if update_type == 0: log.printConnectionParameters(115200, Port, ID, file)
elif update_type == 1: log.printConnectionParametersIP(ip, Port, file)

#Version
Version = ""

#Logic counters
State = 0
Stop = 0

#Block size 1024
size_block = 512

#Reset
reset_type2 = bytearray(b'\x01\x06\x01\x04\x00\x01\x08\x37')#\x00\x00
goto_type2 = bytearray(b'\x01\x06\x01\x04\x00\x04\xc8\x34')
reset_type1 = bytearray(b'\x04\x06\x01\x04\x00\x01\x08\x62')
reset_LCSC = bytearray(b'\xF0\x06\x01\x04\x00\x01\x00\x00') #\x88\x9E
reset_Chademo = bytearray(b'\x02\x06\x01\x04\x00\x01\x08\x04')
reset_CCS = bytearray(b'\x03\x06\x01\x04\x00\x01\x09\xd5')
reset_GBT = bytearray(b'\x05\x06\x01\x04\x00\x01\x09\xb3')
reset_GBT_2 = bytearray(b'\x08\x06\x01\x04\x00\x01\x08\xae')
reset_2CAN = bytearray(b'\x07\x06\x01\x04\x00\x01\x08\x51')

#Sync for ESP32
sync_arr = bytearray(b'\xc0\x00\x08\x24\x00\x00\x00\x00\x00\x07\x07\x12\x20\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\xc0')
sync_resp = bytearray(b'\xc0\x01\x08\x04\x00\x07\x07\x12\x20\x00\x00\x00\x00\xc0')
default_arr = bytearray(b'\xc0\xc0')

#Name of virtual ports for ESP32
name_port1 = "COM22"
name_port2 = "COM23"

#Address application or transceiver
address_transceiver = 0x2000
address_application = 0x4000
address_application_slow = 0x20000

if ID_PERIPH == 0x01: address = address_transceiver
else: address = address_application

#Timeout for Type 1
timeout = 0

#Counters pages
current_page = 0
received_page = 0
write_flag = 0
time_to_repeat = 0

if file != "Reset":
    if ID_PERIPH == 0x02:
        #Read .ini file
        eeprom = EEPROM(file, log)
        buffer_config = eeprom.getArrayEEPROM()
        #EEPROM BUFFER
        eeprom_size = len(buffer_config)
        eeprom_buffer = bytearray(size_block - eeprom_size)
        eeprom_buffer += buffer_config
    else:
        #Read file
        f = open(file, 'rb')
        program = f.read()
        f.close()

        #Main text length
        size_programm = len(program)

        #Flash frame
        size_buffer = math.ceil(size_programm/size_block)
        buffer = []

        #For CRC 
        total_programm = bytearray(size_block * size_buffer)
        crc_program = 0

        log.printSize(size_programm, size_buffer, size_block)

        for i in range(0, size_buffer):
            piece = bytearray(size_block)
            for j in range(0, size_block):
                if ((i * size_block) + j) > (size_programm - 1):
                    piece[j] = 0xFF
                else:
                    piece[j] = program[(i * size_block) + j]
                total_programm[(i * size_block) + j] = piece[j]
            buffer.append(piece)

        #Find crc all program
        crc_program = crc.findCRC(total_programm, len(total_programm))

def buildFrame(command, data, size):
    frame = bytearray(len(data) + 6)
    frame[0] = ID
    frame[1] = command
    frame[2] = (size >> 8) & 0x00FF
    frame[3] = size & 0x00FF
    for i in range(0, len(data)):
        frame[i + 4] = data[i]

    frame = crc.addCRC(frame, len(frame))

    return frame

def buildReset(device = 0, command = 0):
    frame = bytearray(device.to_bytes(1, 'big') + b'\x06\x01\x04' + command.to_bytes(2, 'big') + b'\x00\x00')#, byteorder='big'bytearray(b'\x00\x06\x01\x04\x00\x01\x00\x00')
    frame = crc.addResetCRC(frame, len(frame))
    return frame

def buildMyReset(device = 0, command = 0):
    frame = bytearray(device.to_bytes(1, 'big') + b'\x06\x01\x04' + command.to_bytes(2, 'big') + b'\x00\x00')#, byteorder='big'bytearray(b'\x00\x06\x01\x04\x00\x01\x00\x00')
    frame = crc.addCRC(frame, len(frame))
    return frame


#ProgressBar counter
pb = 0

def logic(message: bytearray):
    global State, current_page, received_page, size_buffer, Stop, write_flag, pb, time_to_repeat, Version
    ref = 0
    if len(message) == 8:
        if(crc.checkCRC(message)):
            if message[0] == ID:
                ref = 1
                if message[1] == 0x00:
                    log.printDefault()
                    if received_page < size_buffer:
                        if (State != 0) & (State != 5): Stop = 1
                        else: 
                            State = 1
                            write_flag = 0
                    else:
                        State = 0
                        Stop = 1

                elif (message[1] == 0x01) & (State == 1):
                    if message[5] == 0x01:
                        log.printErased(0)
                        State = 2
                        write_flag = 0
                        #time.sleep(0.5)
                    elif message[5] == 0x02:
                        log.printErased(1)
                        State = 0
                        Stop = 1

                elif ((message[1] == 0x02) | (message[1] == 0x06)) & (State == 2) & (write_flag <= 1):
                    received_page = (message[4] << 8) | message[5]
                    if received_page != 0xFFFF:
                        if (received_page/size_buffer) < 1: log.printWritten(0, received_page, 0)
                        else: log.printWritten(0, received_page, 1)
                        if (received_page - 1) == current_page:
                            if received_page != size_buffer:
                                current_page += 1
                                write_flag = 0
                        elif received_page == current_page: write_flag = 0#time_to_repeat += 1

                        if received_page == size_buffer:
                            State = 3
                            write_flag = 0

                        log.progressBar(received_page/size_buffer)
                        if (received_page/size_buffer) < 1: pb = 1

                    else:
                        log.printWritten(1, received_page, 1)
                        log.printMeme()
                        State = 0
                        Stop = 1

                elif (message[1] == 0x03) & (State == 3):
                    if message[5] == 0x01:
                        log.printChecked(0)
                        State = 0
                        write_flag = 0
                    elif message[5] == 0x02:
                        log.printChecked(1)
                        State = 0
                        Stop = 1
                elif (message[1] == 0x05):
                    if chr(message[5]) != '\n':
                        Version += chr(message[5])
                        log.printVersion(0, Version)
                        State = 4
                    else: 
                        log.printVersion(1, Version)
                        State = 0
                    write_flag = 0
                elif (message[1] == 0x08):
                    if message[5] == 0x01:
                        log.printEEPROM(0)
                    elif message[5] == 0x02:
                        log.printEEPROM(1)
    return ref

def chooseFrame():
    global State, buffer
    frame = bytearray()
    payload = bytearray(b'\x00\x01')

    if State == 0:
        frame = buildFrame(0x00, payload, len(payload))
    elif State == 1:
        payload[0] = (address & 0xFF00) >> 8
        payload[1] = address & 0x00FF
        frame = buildFrame(0x01, payload, len(payload))
    elif State == 2:
        if(address == address_application): frame = buildFrame(0x02, buffer[current_page], len(buffer[current_page]))
        elif(address == address_transceiver): frame = buildFrame(0x06, buffer[current_page], len(buffer[current_page]))
    elif State == 3:
        payload[0] = (crc_program & 0xFF00) >> 8
        payload[1] = crc_program & 0x00FF
        frame = buildFrame(0x03, payload, len(payload))
    elif State == 4:
        payload[0] = 0
        payload[0] = 0
        frame = buildFrame(0x05, payload, len(payload))
    return frame

escape = False

def getPayload(frame):
    retval = bytearray()
    if len(frame) > 6:
        size = (frame[2] << 8) + frame[3]
        for i in range(4, size + 4): retval.append(frame[i])
    return retval

def virtualPort():
    global name_port1, name_port2
    print("---------> start virtual-com-thread")
    with virtualserialports.VirtualSerialPorts(2, loopback=False, debug=False) as ports:   
        name_port1 = ports[0]#"/dev/pts/1"#
        name_port2 = ports[1]#"/dev/pts/2"#
        log.log(f"Create virtual port: {name_port1}")
        log.log(f"Create virtual port: {name_port2}")

    # virtualserialports.run(2, loopback=False, debug=False)
        while escape != True:
            time.sleep(1)
    print("---------> stop virtual-com-thread")
    return

def espUpdate(esp_port, sync):
    global escape
    try:
        print("---------> start espUpdate-thread")

        #Retarget log to custom logget
        esptool.log.set_logger(CustomLogger())

        with esptool.ESP32ROM(esp_port, 460800, False) as esp: #, 115200, 'no-reset-no-sync', True, 5
            if sync: esp.connect()#'no-reset-no-sync'
            else: esp.connect('no-reset-no-sync')#'no-reset-no-sync'

            esp.ESP_RAM_BLOCK = 0x400
            esp.FLASH_WRITE_SIZE = 0x400

            log.log(f"[Log from ESP32]: Detected ESP on port {esp_port}: {esp.get_chip_description()}")
            log.log("[Log from ESP32]: Features: " + ", ".join(esp.get_chip_features()))

            # esptool.chip_id(esp)
            esptool.read_mac(esp)
            esptool.flash_id(esp)

            esp = esptool.run_stub(esp)

            esp.FLASH_WRITE_SIZE = 0x400
            # esptool.attach_flash(esp)

            esptool.erase_flash(esp)
            esptool.write_flash(esp, [(0, file)])#, 'force', 'force', 'no_compress'
            esp.run(True)
            
            escape = True
            print("---------> stop espUpdate-thread")
            return
            
    except esptool.FatalError as e:
        escape = True
        print("---------> stop espUpdate-thread cause: {}".format(e))
        return

def espEmulator(esp_port = serialport):
    print("---------> start espEmulator-thread")
    global escape
    payload = bytearray()
    udp.setTimeout(10)
    while escape != True:
        payload.extend(esp_port.receiveFrame(Stop, 0))

        if len(payload) != 0:
            if (len(payload) > 4) & (payload[len(payload) - 1] == 0xC0):
            
                udp.transmittFrame(buildFrame(0x09, payload, len(payload)), -1)

                esp_port.transmittFrame(getPayload(udp.receiveFrame(Stop, 0)), -1)
                payload.clear()
    print("---------> stop espEmulator-thread")
    return

def esp_logic():
    global default_arr, sync_arr, Stop #global name_port1, name_port2,

    virtual_port1 = serialport(name_port1, 460800, log)
    virtual_port1.setTimeout(0.001)
    
    udp.setTimeout(2)
    udp.transmittFrame(buildFrame(0x09, default_arr, len(default_arr)), 1)
    log.log(getPayload(udp.receiveFrame(Stop, 1)).decode('utf-8'))

    for i in range(0, 128):
        udp.transmittFrame(buildFrame(0x09, sync_arr, len(sync_arr)), 1)
        if (getPayload(udp.receiveFrame(Stop, 1)) == sync_resp): break
    udp.receiveFrame(Stop, 1)

    thread1 = threading.Thread(target = espEmulator, args = (virtual_port1,))
    thread2 = threading.Thread(target = espUpdate, args = (name_port2, False,))
    thread2.start()
    thread1.start()

#---------------------Connect at 19200---------------------
#ser.connect_reset()

#Reset send
log.log("\n---------- Try to reset device ----------")
log.printResetDevice(ID, 0)

if update_type == 0:
    if (ID != 0x07) & ((ID & 0xF0) != 0xF0):#(ID == 0x01) | (ID == 0x03) | (ID == 0x04) | (ID == 0x05) | (ID == 0x06) | (ID == 0x08):
        ser.setSpeed(19200)
        ser.setTimeout(3)

        ser.transmittFrame(buildReset(ID, 0x01), 1)

    elif (ID == 0x07) | ((ID & 0xF0) == 0xF0):
        ser.setSpeed(115200)
        ser.setTimeout(2)

        if ID == 0x07: ser.transmittFrame(buildReset(ID, 0x01), 1)
        if (ID & 0xF0) == 0xF0: ser.transmittFrame(buildMyReset(ID, 0x01), 1)

    ser.receiveFrame(Stop, 8)
    time.sleep(3)

    #---------------------Connect at 115200--------------------
    ser.setSpeed(115200)
    ser.setTimeout(0.02)
    ser.receiveFrame(Stop, 8)

    if (ID_PERIPH != 0) & (ID_PERIPH != 0x01) & (ID_PERIPH != 0x02) & (ID_PERIPH != 0x03):
        log.log("\nGo to transmitter")
        ser.transmittFrame(buildFrame(0x07, bytearray(2), 2), 1) #Go to transceiver
        log.printResetDevice(ID, ID_PERIPH)
        ID = ID_PERIPH #Fix ID for periph device
        time.sleep(2)
        ser.transmittFrame(buildFrame(0x06, bytearray(2), 2), 1) #First message for config + reset periph
        time.sleep(2)
        ser.setTimeout(0.01)

    elif ID_PERIPH == 0x02:
        log.log("\n--------- Try to update EEPROM ----------\n")
        ser.setTimeout(3)
        ser.transmittFrame(buildFrame(0x08, eeprom_buffer, eeprom_size), 1)
        EEPROM_ASK = ser.receiveFrame(Stop, 8)

        EEPROM_ASK_SHORT = bytearray()
        if len(EEPROM_ASK) == 0: exit()
        for i in range(0, 8): EEPROM_ASK_SHORT.append(EEPROM_ASK[i])

        logic(EEPROM_ASK_SHORT)
        Stop = 1

    elif ID_PERIPH == 0x03:
        ser.disconnect()
        espUpdate(Port, True)

elif update_type == 1:
    udp.connect()
    
    if (ID != 0x07) & ((ID & 0xF0) != 0xF0):
        udp.transmittFrame(buildReset(ID, 0x01), 1)

    elif (ID == 0x07) | ((ID & 0xF0) == 0xF0):
        if ID == 0x07: udp.transmittFrame(buildReset(ID, 0x01), 1)
        if (ID & 0xF0) == 0xF0: udp.transmittFrame(buildMyReset(ID, 0x01), 1)

    udp.receiveFrame(Stop, 8)
    time.sleep(5)

    if (ID_PERIPH != 0) & (ID_PERIPH != 0x01) & (ID_PERIPH != 0x02) & (ID_PERIPH != 0x03):
        log.log("\nGo to transmitter")
        udp.transmittFrame(buildFrame(0x07, bytearray(2), 2), 1) #Go to transceiver
        log.printResetDevice(ID, ID_PERIPH)
        ID = ID_PERIPH #Fix ID for periph device
        time.sleep(2)
        udp.transmittFrame(buildFrame(0x06, bytearray(2), 2), 1) #First message for config + reset periph
        time.sleep(2)

    elif ID_PERIPH == 0x02:
        log.log("\n--------- Try to update EEPROM ----------\n")
        udp.transmittFrame(buildFrame(0x08, eeprom_buffer, eeprom_size), 1)
        EEPROM_ASK = udp.receiveFrame(Stop, 8)

        EEPROM_ASK_SHORT = bytearray()
        if len(EEPROM_ASK) == 0: exit()
        for i in range(0, 8): EEPROM_ASK_SHORT.append(EEPROM_ASK[i])

        logic(EEPROM_ASK_SHORT)
        Stop = 1

    elif ID_PERIPH == 0x03:
        log.log("\n---------- Try to update ESP ------------\n")

        if platform.startswith("linux"):
            thread0 = threading.Thread(target = virtualPort)
            thread0.start()

        else:
            log.log(f"Open virtual port: {name_port1}")
            log.log(f"Open virtual port: {name_port2}")

        time.sleep(2)
        esp_logic()

        if platform.startswith("linux"): exit(0)
        else: exit()

if file == "Reset": exit()

if Stop == 0: log.log("\n--------- Try to update device ----------\n")
my_time = time.perf_counter()

#Read version of bootloader
State = 4

# count = 0
message = bytearray()

try:
    while (Stop == 0):
        #Transmitted message
        frame = chooseFrame()

        if update_type == 0:
            if ((write_flag == 0)): 
                if (State == 4) & (Version != ""): print("\r\b\r\b\r\b\r\b\r\b")
                if (State == 4): ser.transmittFrame(frame, 0)
                elif (State == 2) & (received_page < (size_buffer - 1)): ser.transmittFrame(frame, 0)
                else: ser.transmittFrame(frame, 1)
                write_flag = 1

        elif update_type == 1:
            if ((write_flag == 0)):
                if (State == 4) & (Version != ""): print("\r\b\r\b\r\b\r\b\r\b")
                if (State == 4): udp.transmittFrame(frame, 0)
                elif (State == 2) & (received_page < (size_buffer - 1)): udp.transmittFrame(frame, 0)
                else: udp.transmittFrame(frame, 1)
                write_flag = 1

        if update_type == 0: message += bytearray(ser.receiveFrame(Stop, 0))
        elif update_type == 1: message = bytearray(udp.receiveFrame(Stop, 0))

        if (Stop == 0) & (len(message) >= 8): 
            for i in range(0, len(message) - 8 + 1):
                ptr = bytearray(8)
                for j in range(0, 8):
                    ptr[j] = message[i + j]
                # print(": 0x{}".format(ptr.hex()))
                if logic(bytearray(ptr)): 
                    message.clear()
                    my_time = time.perf_counter()
                    break
                # print(": 0x{}".format(ptr.hex()))

        if pb != 0:
            pb = 0
            log.clearProgress()

        if (time.perf_counter() - my_time) > 10:
            log.log("Timeout exeption")
            break

except KeyboardInterrupt:
    log.log("Exeption detected. Stop application")
    
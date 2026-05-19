import serial
import serial.tools.list_ports

from output import logger

class virtualserialport:
    def __init__(self, port, speed, out = logger):
        self.Port = port
        self.Speed = speed
        self.log = out
        self.Serial = serial.serial_for_url(self.Port, baudrate = self.Speed, timeout = 0.02)

    def __del__(self):
        pass

    def disconnect(self):
        self.Serial.close()

    def connect(self):
        self.Serial = serial.Serial(self.Port, baudrate = self.Speed, timeout = 0.02)

    def connect_reset(self):
        self.Serial = serial.Serial(self.Port, baudrate = 19200, timeout = 0.02)

    def setTimeout(self, timeout):
        self.Serial.timeout = timeout

    def setSpeed(self, speed):
        self.Serial.baudrate = speed

    def transmittFrame(self, frame, log_flag):
        # Sending a reply to client
        if(log_flag != 0):
            if (len(frame) < 20): self.log.log("\nTransmitted" + ": 0x{}".format(frame.hex())) # | (frame[1] == 0x08)
            else: self.log.log("\nTransmitted 0x...")
        else:
            if (len(frame) < 20): print("\nTransmitted" + ": 0x{}".format(frame.hex())) # | (frame[1] == 0x08)
            else: print("\nTransmitted 0x...")

        if self.Serial != 0:
            self.Serial.write(frame)

    def receiveFrame(self, stop, num):
        frame = bytearray()

        try:
            if self.Serial:
                # while len(frame) < 8:
                # frame += self.Serial.read(num)
                frame += self.Serial.readline()
            if (len(frame) >= num) & (num != 0):
                clientMsg = "Received" + ": 0x{}".format(frame.hex())
                self.log.log(clientMsg)
            # else: frame += bytearray(8)

        except TimeoutError:
            self.log.log("\nTimeout\n")
            stop = 1

        return frame
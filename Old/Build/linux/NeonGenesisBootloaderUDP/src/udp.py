import socket
from output import logger

bufferSize  = 2000

class udpport:

    def __init__(self, ip, port, out = logger):
        localHOST = socket.gethostname()
        localIP = socket.gethostbyname(localHOST)
        self.Port = int(port)
        self.selfIP = '255.255.255.255'#localIP
        self.destIP = ip
        self.log = out
        self.UDP = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)#, proto=socket.IPPROTO_UDP)
        self.UDP.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        print("Host:\t{}".format(localHOST))
        print("IP:\t{}".format(self.selfIP))
        print("Port:\t{}".format(self.Port))
        

    def __del__(self):
        pass

    def connect(self):
        self.UDP.bind(("", self.Port))#self.selfIP
        self.setTimeout(2)

    def setTimeout(self, timeout):
        self.UDP.settimeout(timeout)

    def transmittFrame(self, frame, log_flag):
        # Sending a reply to client
        if(log_flag == 1):
            if (len(frame) < 20): self.log.log("\nTransmitted by UDP: " + "0x{}".format(frame.hex())) # | (frame[1] == 0x08)
            else: self.log.log("\nTransmitted by UDP: 0x...")
        elif(log_flag == 0):
            if (len(frame) < 20): print("\nTransmitted by UDP: " + "0x{}".format(frame.hex())) # | (frame[1] == 0x08)
            else: print("\nTransmitted by UDP: 0x...")

        if self.UDP != 0:
            self.UDP.sendto(frame, (self.destIP, self.Port))

    def receiveFrame(self, stop, num):
        frame = bytearray()

        try:
            if self.UDP:
                bytesAddressPair = self.UDP.recvfrom(bufferSize)
                frame = bytesAddressPair[0]
            if (len(frame) >= num) & (num != 0):
                clientMsg = "Received by UDP" + ": 0x{}".format(frame.hex())
                self.log.log(clientMsg)

        except socket.timeout:
            self.log.log("\nTimeout\n")
            stop = 1

        return frame
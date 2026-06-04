class crc16:
    def crc(self):
        pass

    def findCRC(self, data, size):
        crc = 0xFFFF
        size_ptr = size - 1
        while size > 0:
            size -= 1
            crc ^= data[size_ptr - size]
            for i in range(0, 8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc = crc >> 1
        return crc

    def addCRC(self, data, size):
        crc = self.findCRC(data, size)
        
        data[size - 2] = crc & 0x00FF
        data[size - 1] = (crc >> 8) & 0x00FF

        return data
    
    def addResetCRC(self, data, size):
        crc = self.findCRC(data, size - 2)
        
        data[size - 2] = crc & 0x00FF
        data[size - 1] = (crc >> 8) & 0x00FF

        return data
    
    def clearCRC(self, data, size):
        data[size - 2] = 0
        data[size - 1] = 0

        return data
    
    def checkCRC(self, data):
        ptr = bytearray(data).copy()
        self.clearCRC(ptr, len(ptr))
        self.addCRC(ptr, len(ptr))
        if bytearray(data) == ptr: return 1
        else: return 0
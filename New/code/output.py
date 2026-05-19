#Date
import datetime

#For colored text
from termcolor import colored

class logger:
    
    def __init__(self):
        #LogUpdate
        self.LogUpdate = open("LogUpdate.txt", 'a')
        #For Progress Bar
        self.Width = 40

    def __del__(self):
        pass

    #For write to console and to Log file
    def log(self, s):
        print(s)
        print(s, file = self.LogUpdate)

    def logfile(self, s):
        print(s, file = self.LogUpdate)

    def printBanner(self):
        print("\nPlease call application with correct arguments!")
        print(colored("Serial port version:", 'grey'))
        print("Structure:\t" + colored("EasyLoader", 'green') + colored(" [ID]", 'yellow') + colored(" [PORT]", 'blue') + colored(" [FILE]", 'red'))
        print("Example:\t" + colored("EasyLoader", 'green') + colored(" 503", 'yellow') + colored(" /dev/ttyS0", 'blue') + colored(" ChS-RA-Tata.bin", 'red'))
        print(colored("or UDP version:", 'grey'))
        print("Structure:\t" + colored("EasyLoader", 'green') + colored(" [ID]", 'yellow') + colored(" [PORT]", 'blue') + colored(" [FILE]", 'red') + colored(" [IP]", 'light_cyan'))
        print("Example:\t" + colored("EasyLoader", 'green') + colored(" 3", 'yellow') + colored(" 8007", 'blue') + colored(" ChS-RA-Tata_final.bin", 'red') + colored(" 192.168.1.20\n", 'light_cyan'))

    def printDate(self):
        current_date = datetime.datetime.utcnow()
        formate_date = current_date.strftime('%Y-%m-%d %H:%M:%S')
        date = "Update date:\t" + formate_date + "\n"
        self.log(date)

    def printConnectionParameters(self, speed, port, id, file):
        self.log("Speed\t\t= {}".format(speed))
        self.log("Port\t\t= {}".format(port))
        self.log("File name\t= {}".format(file))

    def printConnectionParametersIP(self, ip, port, file):
        self.log("IP\t\t= {}".format(ip))
        self.log("Port\t\t= {}".format(port))
        self.log("File name\t= {}".format(file))

    def printDevice(self, id, id_periph):
        main_device = ""
        periph_device = ""

        if(id == 0x1): main_device = "Type2"
        if(id == 0x2): main_device = "Chademo"
        if(id == 0x3): main_device = "CCS"
        if(id == 0x4): main_device = "Type1"
        if(id == 0x5): main_device = "GBT"
        if(id == 0x6): main_device = "CCS-2"
        if(id == 0x7): main_device = "2CAN"
        if(id == 0x8): main_device = "GBT-2"
        if(id == 0x9): main_device = "CCS-3"
        if(id == 0xB): main_device = "GBT-3"
        if(id == 0xF): main_device = "LAN-RA"

        if((id & 0xF0) == 0xF0): main_device = "LCSC"

        if(id_periph == 0x01): periph_device = "Transceiver"
        if(id_periph == 0x02): periph_device = "EEPROM"
        if(id_periph == 0x03): periph_device = "ESP32"

        if((id_periph & 0xF0) == 0x50): periph_device = "DIDO-{}".format(id_periph & 0x0F)
        if((id_periph & 0xF0) == 0x60): periph_device = "MIRA-{}".format(id_periph & 0x0F)
        if((id_periph & 0xF0) == 0x70): periph_device = "2CAN-{}".format(id_periph & 0x0F)
        if((id_periph & 0xF0) == 0x90): periph_device = "BLCC-{}".format(id_periph & 0x0F)
        if((id_periph & 0xF0) == 0x80): periph_device = "LCSC-{}".format(id_periph & 0x0F)

        if(id_periph > 0):
            print("Update device:\t" + periph_device + " by " + main_device)
            print("Update device:\t" + periph_device + " by " + main_device, file=self.LogUpdate)
        else:
            print("Update device:\t" + main_device)
            print("Update device:\t" + main_device, file=self.LogUpdate)

    def printSize(self, size_programm, size_buffer, size_block):
        #File size in size_block bytes
        self.log("\nFile size {} Bytes".format(size_programm))
        self.log("File size {} blocks".format(size_buffer) + " (block = {} kBytes)".format(size_block / 1024))

    def clearProgress(self):
        print("\r\b\r\b\r\b\r\b\r\b\r\b\r\b\r\b\r\b")

    def progressBar(self, completion):
        top = "__" #"▁▁"
        bottom = '¯¯' #"▔▔"
        progressBar = "█"
        progressBarTxt = "|"

        for i in range(0, int(completion * self.Width)):
            progressBar += '▒' #'█' #'▓' #'♿ #'🐧'
            progressBarTxt += '|'
            top += '_' #'▁'
            bottom += '¯' #'▔'
        
        for i in range(int(completion * self.Width), self.Width):
            progressBar += ' '
            progressBarTxt += ' '
            top += '_' #'▁'
            bottom += '¯' #'▔'

        progressBar += '█'
        progressBarTxt += ' '

        if completion < 1: print("Progress: {}% ".format(int(completion*100)))
        else: self.log("Progress: {}% ".format(int(completion*100)))
        print(top)
        print(progressBar[0:1] + colored(progressBar[1:(self.Width + 1)], 'green') + progressBar[(self.Width + 1):(self.Width + 2)])
        print(bottom)

    def clearProgress(self):
        print("\r\b\r\b\r\b\r\b\r\b\r\b\r\b\r\b")
    
    def printDefault(self):
        print("State [Deafault]" + colored(" ✅", 'green'))
        print("State [Deafault]", file=self.LogUpdate)

    def printErased(self, state):
        if state == 0:
            print("State [Erased successfully]" + colored(" ✅", 'green'))
            print("State [Erased successfully]", file=self.LogUpdate)
        else:
            print("State [Erased failed]" + colored(" ❎", 'red'))
            print("State [Erased failed]", file=self.LogUpdate)

    def printWritten(self, state, number, log_flag):

        if state == 0:
            print("State [Written block {}]".format(number))
            if log_flag != 0: print("State [Written block {}]".format(number), file=self.LogUpdate)
        else:
            print("State [Written failed]" + colored(" ❎", 'red'))
            print("State [Written failed]", file=self.LogUpdate)

    def printEEPROM(self, state):

        if state == 0:
            print("State [Written EEPROM successfully]" + colored(" ✅", 'green'))
            print("State [Written EEPROM successfully]", file=self.LogUpdate)
        else:
            print("State [Written EEPROM failed]" + colored(" ❎", 'red'))
            print("State [Written EEPROM failed]", file=self.LogUpdate)

    def printChecked(self, state):

        if state == 0:
            print("State [Checked successfully]" + colored(" ✅", 'green'))
            print("State [Checked successfully]", file=self.LogUpdate)
        else:
            print("State [Checked failed]" + colored(" ❎", 'red'))
            print("State [Checked failed]", file=self.LogUpdate)

    def printVersion(self, state, text):

        if state == 0:
            print("State [Receive version]")
            print(text)
        else:
            print("State [Received version]" + colored(" ✅", 'green'))
            print("State [Received version]", file=self.LogUpdate)
            print(text)
            print(text, file=self.LogUpdate)

    def printResetDevice(self, id, id_periph):
        main_device = ""
        periph_device = ""

        if(id == 0x1): main_device = "Type2"
        if(id == 0x2): main_device = "Chademo"
        if(id == 0x3): main_device = "CCS"
        if(id == 0x4): main_device = "Type1"
        if(id == 0x5): main_device = "GBT"
        if(id == 0x6): main_device = "CCS-2"
        if(id == 0x7): main_device = "2CAN"
        if(id == 0x8): main_device = "GBT-2"
        if(id == 0x9): main_device = "CCS-3"
        if(id == 0xB): main_device = "GBT-3"
        if(id == 0xF): main_device = "LAN-RA"

        if((id & 0xF0) == 0xF0): main_device = "LCSC"

        if(id_periph == 0x01): periph_device = "Transceiver"
        if(id_periph == 0x02): periph_device = "EEPROM"
        if(id_periph == 0x03): periph_device = "ESP32"

        if((id_periph & 0xF0) == 0x50): periph_device = "DIDO-{}".format(id_periph & 0x0F)
        if((id_periph & 0xF0) == 0x60): periph_device = "MIRA-{}".format(id_periph & 0x0F)
        if((id_periph & 0xF0) == 0x70): periph_device = "2CAN-{}".format(id_periph & 0x0F)
        if((id_periph & 0xF0) == 0x90): periph_device = "BLCC-{}".format(id_periph & 0x0F)
        if((id_periph & 0xF0) == 0x80): periph_device = "LCSC-{}".format(id_periph & 0x0F)

        if(id_periph > 0):
            print("\nReset " + periph_device + " by " + main_device)
            print("\nReset " + periph_device + " by " + main_device, file=self.LogUpdate)
        else:
            print("\nReset " + main_device)
            print("\nReset " + main_device, file=self.LogUpdate)


    def printMeme(self):
        print("⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄")
        print("⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⣀⣀⣀⠄⠄⠄⠄⡀⠄⠄⡀⠠⣤⣄⠄⠄⠄⠄⠄")
        print("⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠈⠉⢉⡏⠄⠄⠄⢸⡇⠄⣼⠇⠄⢀⡏⠄⠄⠄⠄⠄")
        print("⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⣸⣧⡤⣤⡀⠈⠓⠚⣿⠄⠄⣸⠳⠶⢶⡀⠄⠄")
        print("⠄⠄⠄⠄⣀⡀⠄⠄⠄⠄⠄⠄⣿⠁⠄⣸⡇⣀⣠⡴⠟⠄⠄⣿⣀⣀⣼⠇⠄⠄")
        print("⠄⣠⣶⣿⣿⣿⣿⠆⠄⠄⠄⠄⠻⠦⠶⠋⠄⠉⠄⠄⠄⠄⠄⠉⠉⠉⠁⠄⠄⠄")
        print("⢰⣿⣿⡿⠛⠉⠉⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄")
        print("⢸⣿⣿⡇⠄⠄⠄⠄⠄⠄⠄⠄⠄⢀⣀⣠⣤⣀⣀⠄⠄⠄⠄⢀⣀⣀⣀⡀⠄⠄")
        print("⠄⢿⣿⣧⠄⠄⠄⠄⠄⠄⢀⣴⣿⣿⣿⣿⣿⣿⣿⣷⣄⠄⣼⣿⣿⣿⣿⣿⣦⠄")
        print("⠄⠘⣿⣿⣧⡀⠄⠄⠄⢠⣾⣿⣿⣿⣿⣿⣿⣿⢿⣿⣿⡀⠹⠿⠛⠉⢹⣿⣿⡄")
        print("⠄⠄⠈⢿⣿⣿⣄⠄⢠⣿⣿⣿⣇⣍⢹⣿⣯⣰⣼⣿⡿⠁⠄⠄⠄⢀⣾⣿⣿⠃")
        print("⠄⠄⠄⠈⢿⣿⣿⣶⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠿⠁⠄⠄⢀⣴⣾⣿⡿⠃⠄")
        print("⠄⠄⠄⠄⠈⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣦⣤⣶⣿⣿⣿⠟⠋⠄⠄⠄")
        print("⠄⠄⠄⠄⠄⠈⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠟⠉⠄⠄⠄⠄⠄⠄")
        print("⠄⠄⠄⠄⠄⠄⢻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠁⠄⠄⠄⠄⠄⠄⠄⠄")
        print("⠄⠄⠄⠄⠄⠄⢸⣿⣿⣿⣿⠋⠉⠉⠉⠘⣿⣿⣿⣿⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄")
        print("⠄⠄⠄⠄⠄⠄⢸⣿⣿⣿⡏⠄⠄⠄⠄⠄⢹⣿⣿⣿⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄")
        print("⠄⠄⠄⠄⠄⠄⢸⣿⣿⣿⡇⠄⠄⠄⠄⠄⠸⣿⣿⣿⡄⠄⠄⠄⠄⠄⠄⠄⠄⠄")
        print("⠄⠄⠄⠄⠄⠄⣿⣿⣿⣿⠄⠄⠄⠄⠄⠄⠄⣿⣿⣿⣷⠄⠄⠄⠄⠄⠄⠄⠄⠄")
        print("⠄⠄⠄⠄⠄⠄⣿⣿⣿⡇⠄⠄⠄⠄⠄⠄⠄⢸⣿⣿⣿⡆⠄⠄⠄⠄⠄⠄⠄⠄")
        print("⠄⠄⠄⠄⠄⢰⣿⣿⣿⣄⠄⠄⠄⠄⠄⠄⠄⠈⣿⣿⣿⣿⣶⡄⠄⠄⠄⠄⠄⠄")
        print("⠄⠄⠄⠄⠄⠈⠻⣿⣿⡟⠄⠄⠄⠄⠄⠄⠄⠄⢿⣿⣿⣿⠿⠃⠄⠄⠄⠄⠄⠄")
        print("⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄⠄")
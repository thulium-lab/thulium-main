from serial import Serial, SerialException
import time
def write_read_com(port,command):
    port.write(command)
    return port.readline().decode()
#
class ArduinoShutters():
    def __init__(self,port=None,device=None):
        if device != None:
            self.device = device
        elif port != None:
            # rewrite it based on library which I wrote on com port connection
            try:
                self.device = Serial(port,baudrate=57600,timeout=1)
            except SerialException:
                print('Nooo')
                # actually do smth
        print('Arduino is opened and ready')

    def setWMShutters(self,data):
        """ data is array of (channel(int), state(int)) format
            to send it to arduino it should be transferted to string 'WMShutters chan1 state1 chan2 state 2 ....' """
        print('arduino-setWMShutters')
        message = b'WMShutters'
        for chan, state in data:
            message += b' %i %i'%(chan,state)
        message += b'!'
        print(message)
        self.device.write(message)
        print('written')
        print(self.device.readline()) # here one should add check of correct writing
        # add check of success
        return 1
        # print(self.device)
        # self.device.write(b'*IDN?')
        # print(self.device.readline())
        # print('middle')
        # resp = write_read_com(self.device,b'*IDN?')
    #     # print(resp)
    # def writeMsg(self,message):
    #     self.device.write(message)
    #     print('written')
    #     print(self.device.readline())



# if __name__ == '__main__':
#     # a = ArduinoShutters(port = 'COM27')
#     arduino = Serial('COM27', baudrate=57600, timeout=1)
#     time.sleep(1)
#     print(arduino.write(b'*IDN?'))
#     time.sleep(1)
#     print(arduino.readline())
# import serial
# import time
# arduino = serial.Serial('COM27',baudrate=57600,timeout=1)
# print(arduino.is_open)
# #for i in range(10000):
# #    b = 1
# #arduino.write(b'*IDN?')
# #print(arduino.readline())
# for i in range(10):
#     time.sleep(2)
#     arr = [i%2]*3
#     arduino.write(b'WMShutters 1 %i 2 %i 3 %i'% (arr[0],arr[1],arr[2]))
#     print(i,' respons',arduino.readline())
# arduino.write(b'*IDN?')
# print(arduino.readline())
# arduino.close()


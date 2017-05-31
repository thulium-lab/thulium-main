import serial
import time
arduino = serial.Serial('COM27',baudrate=57600,timeout=1)
print(arduino.is_open)
#for i in range(10000):
#    b = 1    
#arduino.write(b'*IDN?')
#print(arduino.readline())
for i in range(10):
    time.sleep(2)
    arr = [i%2]*3
    arduino.write(b'WMShutters 1 %i 2 %i 3 %i'% (arr[0],arr[1],arr[2]))
    print(i,' respons',arduino.readline())
arduino.close()
#print(arduino.is_open)
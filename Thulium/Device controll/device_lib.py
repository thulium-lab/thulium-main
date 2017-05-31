from serial import Serial
from serial.tools import list_ports
from time import sleep
from serial.serialutil import SerialException
from numpy import sign

for port in [port.device for port in list(list_ports.comports())]:
    print(port)

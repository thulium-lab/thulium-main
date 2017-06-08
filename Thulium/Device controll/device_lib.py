# from serial import Serial
# from serial.tools import list_ports
# from time import sleep
# from serial.serialutil import SerialException
# from numpy import sign
#
# for port in [port.device for port in list(list_ports.comports())]:
#     print(port)
from serial import Serial
from serial import SerialException
import serial.tools.list_ports

def connectArduino(response=''):
    from PyQt5.QtWidgets import QErrorMessage
    from serial import Serial
    from serial import SerialException
    import serial.tools.list_ports
    # ports = list(serial.tools.list_ports.comports())
    for port in serial.tools.list_ports.comports():
        if port.description.startswith("USB-SERIAL CH340"):
            try:
                arduino = Serial(port.device, baudrate=57600, timeout=1)
            except SerialException as e:
                error = QErrorMessage()
                error.showMessage("Can't open port %s !" % port.device + e.__str__())
                error.exec_()
                return -1
            # here one can add checking response on command arduino.write(b'*IDN?'), know is somewhy doesn't work
            return arduino
    error = QErrorMessage()
    error.showMessage("Arduino is not connected!")
    error.exec_()
    return -1

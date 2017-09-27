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
from PyQt5.QtWidgets import QWidget, QPushButton, QVBoxLayout,QComboBox
from serial.tools import list_ports
def connectArduino(response=''):
    from PyQt5.QtWidgets import QErrorMessage
    from serial import Serial
    from serial import SerialException
    import serial.tools.list_ports
    # ports = list(serial.tools.list_ports.comports())
    for port in serial.tools.list_ports.comports():
        if port.description.startswith("USB-SERIAL CH340"):
            try:
                arduino = Serial(port.device, baudrate=57600, timeout=.01)
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

class COMPortDevice:
    """General class for com ports. """
    connected = False
    port = ''
    baudrate = 9600
    timeout = 1
    identification_names = [] # first few words that should be in the output to *IDN? command splited bu ',' to check

    # function to check based on port info if the port is correct, if port is transfered then checks if
    # port pass check. In the last version only with port it is used
    def preCheck(self,port=None):
        return True

    def close(self): # closes port
        self.stream.close()
        self.connected = False

    def connect(self,idn_message=b'*IDN?\r'):
        """tries to connect port.
        idn_message - message to be sent to devise to identify it
        If connected returns 0, if not - value < 0 """
        try:
            p = Serial(self.port, self.baudrate, timeout=self.timeout)
            p.write(idn_message)
            s = p.readline()
            s = s.decode().split(',')
            print('Port answer ', s)
            # below is check for IDN command respons
            if len(s) < len(self.identification_names): # if length of identification names is smaller than expected
                p.close()
                self.stream = None
                return -1
            else:
                status = True
                for i in range(len(self.identification_names)): # checks every name
                    if s[i] != self.identification_names[i]:
                        status = False
                        break
                if status: # if there no mistakes while name comparison
                    print('\n' + 'Divese ' + str(self.identification_names) + ' connected on port ' + self.port + '\n')
                    self.connected = True
                    self.stream = p
                    return 0
                else: # if any mistake while name comparison
                    p.close()
                    return -1
        except SerialException as e:
            print(e)
            self.stream = None
            return -2

    def write_read_com(self, command):
        """tries to write command to devise and read it's response"""
        status = True
        readout = ''
        if not self.connected:
            return (False,'')
        try:
            self.stream.write(command)
            readout = self.stream.readline().decode()
        except SerialException as e:
            status = False
            print(e)
        return (status,readout) # return statuus of reading and readout

    class BasicWidget(QWidget):
        def __init__(self,data=None, parent=None,connect=True):
            self.data=data
            self.parent = parent
            super().__init__()

            layout = QVBoxLayout()
            self.port_menu = QComboBox()
            self.port_menu.currentTextChanged[str].connect(self.portChanged)
            layout.addWidget(self.port_menu)

            info_btn = QPushButton('Update')
            info_btn.clicked.connect(self.updateBtnPressed)
            layout.addWidget(info_btn)

            self.connect_btn = QPushButton('Connect')
            self.connect_btn.clicked.connect(self.connectBtnPressed)
            layout.addWidget(self.connect_btn)

            self.setLayout(layout)
            self.updateBtnPressed() #to update com ports

            if connect:
                self.connectBtnPressed()

        def portChanged(self,name):
            self.data.port = name.strip('+')

        def updateBtnPressed(self):
            """updates com ports list and runs preCheck to choose suitable ports"""
            available_com_ports = [port.device for port in list(list_ports.comports())]
            last_port=''
            for i,port in enumerate(list(list_ports.comports())):
                if self.data.preCheck(port):
                    available_com_ports[i] +='+'
                    last_port = port.device # the last preChecked port will be set to default
            self.port_menu.clear()
            print(last_port)
            self.port_menu.addItems(available_com_ports)
            print(last_port)
            if last_port:
                self.port_menu.setCurrentText(last_port+'+')# show default port
                self.data.port = last_port

        def connectBtnPressed(self):
            if not self.data.connected: # if not yet connected - connect
                res = self.data.connect()
                if res < 0:
                    print("Can't connect ",self.data.port)
                    self.connect_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')
                    return
                self.connect_btn.setStyleSheet("QWidget { background-color: %s }" % 'green')
                self.connect_btn.setText('Disconnect')
            else:   # else disconnect
                self.data.close()  # disconnect them
                self.connect_btn.setText('Connect')
                self.connect_btn.setStyleSheet("QWidget { background-color: %s }" % 'yellow')
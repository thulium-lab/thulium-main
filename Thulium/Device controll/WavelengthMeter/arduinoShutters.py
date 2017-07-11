from serial import Serial, SerialException
# import time
import sys
sys.path.append(r'D:\Dropbox\Python\Thulium\Device controll')
from device_lib import COMPortDevice
from serial.tools import list_ports
from PyQt5.QtCore import (QTimer)
from PyQt5.QtGui import (QTextCursor)
from PyQt5.QtWidgets import (QWidget, QComboBox,QRadioButton, QSpinBox, QCheckBox, QTabWidget, QFileDialog,QMessageBox, QDoubleSpinBox,QTextEdit)
from PyQt5.QtWidgets import (QApplication, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton)


class Arduino(COMPortDevice):
    """This class is based on COMPortDevice from device_lib
        Comment: arduino not always sends unswer, so checking its answer isn't the best way"""
    baudrate = 9600
    identification_names = []#['ArduinoUnoShutters']
    timeout = 0.01
    n_lines = 50    # number of lines (readings from arduino) to display in QTextEdit window
    readings = []   # array of string where to contain readings
    available_com_ports = []
    n_chars_in_string = 400

    def __init__(self):
        pass
        # self.updateCOMPortsInfo()   #not neccesery here

    def preCheck(self):
        """Override method of parent class"""
        for port in list(list_ports.comports()):
            if port.manufacturer == 'wch.cn':
                self.port = port.device

    def setWMShutters(self, data):
        """ function which is called to set Wavelength Meter shutters
            data is array of (channel(int), state(int)) format
            to send it to arduino it should be transferted to string 'WMShutters chan1 state1 chan2 state 2 ....' """
        print('arduino-setWMShutters')
        message = b'WMShutters'
        for chan, state in data:
            message += b' %i %i' % (chan, state)
        message += b'!'
        print(message)
        status, readout = self.stream.write_read_com(message)
        if not status:
            return False
        print('written')
        # print(self.device.readline()) # here one should add check of correct writing
        # add check of success
        return True

    def read_serial(self):
        """function to read all data avaylable in serial stream from arduino"""
        if self.connected:
            for i in range(20):
                try:
                    s = self.stream.readline().decode()
                    if s=='':
                        break
                    self.append_readings(s)
                    # print("arduino >>   ",s,end='')
                except SerialException as e:
                    print('There are problems with arduino. Connection will be terminated')
                    print(e)
                    self.close()

    def append_readings(self,s):
        """append last readings from arduino to the list"""
        # print("arduino >>   ", s, end='')

        # if there no \n on the end (string s is small) - just add it to the last string
        if (not s.endswith('\n')) and len(self.readings) and len(self.readings[-1] + s)<self.n_chars_in_string:
            self.readings[-1] += s
        else:
            if len(self.readings) < self.n_lines: # if it's less the n_lines in readings
                self.readings.append(s)
            else:
                self.readings[:-1] = self.readings[1:]
                self.readings[-1] = s

    def updateCOMPortsInfo(self):
        """updates all serial ports info - here is needed for construction of available_com_ports list"""
        self.available_com_ports = [port.device for port in list(list_ports.comports())]

    class Widget(QWidget):
        """GUI for arduino"""
        def __init__(self,parent=None,data=None):
            self.data = data
            self.parent = parent
            super().__init__()
            self.initUI()
            # self.setWindowTitle('Arduino') # Doesn't work
            self.updateBtnPressed() # to get preChecked port from start
            self.timer = QTimer() # timer is needed for readings from serial port
            self.timer.setInterval(500)
            self.timer.timeout.connect(self.updateReadings)
            self.timer.start()

        def initUI(self):
            main_layout = QVBoxLayout()

            port_layout = QHBoxLayout()
            port_layout.addWidget(QLabel('Port'))

            self.port_menu = QComboBox()
            self.port_menu.currentTextChanged[str].connect(self.portChanged)
            port_layout.addWidget(self.port_menu)

            info_btn = QPushButton('Update')
            info_btn.clicked.connect(self.updateBtnPressed)
            port_layout.addWidget(info_btn)

            self.description = QLabel()
            port_layout.addWidget(self.description)

            # port_layout.addStretch(1)

            self.connect_btn = QPushButton('Connect')
            self.connect_btn.clicked.connect(self.connectBtnPressed)
            port_layout.addWidget(self.connect_btn)

            main_layout.addLayout(port_layout)

            write_layout = QHBoxLayout()

            self.line_to_send = QLineEdit()
            write_layout.addWidget(self.line_to_send)

            send_btn = QPushButton('Send')
            send_btn.clicked.connect(self.sendBtnPressed)
            write_layout.addWidget(send_btn)

            self.do_update = QCheckBox('Update readings')
            self.do_update.setChecked(True)
            write_layout.addWidget(self.do_update)

            main_layout.addLayout(write_layout)

            self.readings_text = QTextEdit()
            main_layout.addWidget(self.readings_text)

            self.setLayout(main_layout)

        def portChanged(self,name):
            self.data.port = name
            for port in list_ports.comports():
                if port.__dict__['device'] == self.data.port:
                    self.description.setText(port.__dict__['description'])
                    # self.description.repaint()
                    break

        def updateBtnPressed(self):
            """updates info about com ports"""
            self.data.updateCOMPortsInfo()
            self.port_menu.clear()
            self.port_menu.addItems(['-'] + self.data.available_com_ports)
            self.data.preCheck()
            self.port_menu.setCurrentText(self.data.port)
            for port in list_ports.comports():
                if port.__dict__['device'] == self.data.port:
                    self.description.setText(port.__dict__['description'])
                    # self.description.repaint()
                    break

        def disconnectPorts(self):
            print('disconnectPorts')
            try:
                self.data.close()
            except:
                print("Can't close ports")

        def connectBtnPressed(self):
            if not self.data.connected: # if not yet connected - connect
                res = self.data.connect()
                if res < 0:
                    print("Can't connect arduino")
                    self.connect_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')
                    return
                self.connect_btn.setStyleSheet("QWidget { background-color: %s }" % 'green')
                self.connect_btn.setText('Disconnect')
            else:   # else disconnect
                self.disconnectPorts()  # disconnect them
                self.connect_btn.setText('Connect')
                self.connect_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')

        def sendBtnPressed(self):
            """In order to send some command to arduino. For example
            BeamShutters 0_4_1_ 721_4_0_!
            WMShutters 1 1 2 0
            """
            msg = self.line_to_send.text() + "!"
            self.line_to_send.setText('')
            print(msg)
            status, res = self.data.write_read_com(msg.encode('ascii'))
            if not status:
                print('problems with sending msg: ', msg)
            else:
                self.data.append_readings(res)
                self.readings_text.setText('\n'.join(self.data.readings))
                print(self.data.readings)

        def updateReadings(self):
            """updates reading from arduino"""
            self.data.read_serial()
            if self.do_update.isChecked():
                self.readings_text.setText(''.join(self.data.readings))
                self.readings_text.moveCursor(QTextCursor.End)

if __name__ == '__main__':
    # import sys

    app = QApplication(sys.argv)
    arduino = Arduino()
    mainWindow = arduino.Widget(data=arduino)
    mainWindow.show()
    sys.exit(app.exec_())

    # OLD

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


# def write_read_com(port,command):
#     port.write(command)
#     return port.readline().decode()
# #
# class ArduinoShutters():
#     def __init__(self,port=None,device=None):
#         if device != None:
#             self.device = device
#         elif port != None:
#             # rewrite it based on library which I wrote on com port connection
#             try:
#                 self.device = Serial(port,baudrate=57600,timeout=.05)
#             except SerialException:
#                 print('Nooo')
#                 # actually do smth
#         print('Arduino is opened and ready')
#
#     def setWMShutters(self,data):
#         """ data is array of (channel(int), state(int)) format
#             to send it to arduino it should be transferted to string 'WMShutters chan1 state1 chan2 state 2 ....' """
#         print('arduino-setWMShutters')
#         message = b'WMShutters'
#         for chan, state in data:
#             message += b' %i %i'%(chan,state)
#         message += b'!'
#         print(message)
#         self.device.write(message)
#         print('written')
#         # print(self.device.readline()) # here one should add check of correct writing
#         # add check of success
#         return 1
#         # print(self.device)
#         # self.device.write(b'*IDN?')
#         # print(self.device.readline())
#         # print('middle')
#         # resp = write_read_com(self.device,b'*IDN?')
#     #     # print(resp)
#     # def writeMsg(self,message):
#     #     self.device.write(message)
#     #     print('written')
#     #     print(self.device.readline())

from serial import Serial#
import socket
from serial import SerialException
from PyQt5.QtWidgets import (QWidget, QPushButton, QVBoxLayout,QComboBox, QHBoxLayout,QLineEdit, QLabel,QTextEdit)
from serial.tools import list_ports
from PyQt5.QtCore import (QLineF, QPointF, QRectF, Qt, QTimer)
from PyQt5.QtGui import (QBrush, QColor, QPainter,QIcon, QDoubleValidator,QTextCursor)
from Lib import *
import json


class COMPortDeviceServer:
    """Class to run on server, connect and transfer data to COM port
    All settings are in corresponding class in main program - this is basically mirror"""
    def __init__(self):
        print("Init COMPortDeviceServer")

    def close(self): # closes port
        self.stream.close()
        self.connected = False
        return True, "Ok"

    def connect(self):
        """tries to connect port.
        idn_message - message to be sent to devise to identify it
        If connected returns 0, if not - value < 0 """
        try:
            p = Serial(self.port, self.baudrate, timeout=self.timeout)
            p.write(self.idn_messege)
            s = p.readline().decode()
            if '*IDN?' in s:
                p.write(b'system:echo off\r')
                p.readline().decode()
                p.write(self.idn_messege)
                s = p.readline().decode()
            s = s.split(',')
            print('Port answer ', s)
            # below is check for IDN command respons  --- old part, mostly not used now
            if len(s) < len(self.identification_names): # if length of identification names is smaller than expected
                p.close()
                self.stream = None
                return "Identification names length problem. Port answer "+str(s)
            else:
                status = True
                for i in range(len(self.identification_names)): # checks every name
                    if s[i] != self.identification_names[i]:
                        status = False
                        print(s[i], self.identification_names[i])
                        break
                if status: # if there no mistakes while name comparison
                    print('\n' + 'Device ' + str(self.identification_names) + ' connected on port ' + self.port + '\n')
                    self.connected = True
                    self.stream = p
                    return "Ok"
                else: # if any mistake while name comparison
                    p.close()
                    return "Identification names problem. Port answer "+str(s)
        except SerialException as e:
            print(e)
            self.stream = None
            return "Serial exception occured"

    def write_com(self,command):
        status = True
        readout = ''
        if not self.connected:
            return (False, 'Not connected')
        try:
            self.stream.write(command)
            readout='Ok'
        except SerialException as e:
            status = False
            readout='bad'
            print("EXCEPTION")
            print(e)
        return (status, readout)  # return statuus of reading and readout

    def write_read_com(self, command):
        """tries to write command to devise and read it's response"""
        status = True
        readout = ''
        if not self.connected:
            return (False,'Not connected')
        try:
            self.stream.write(command.encode('ascii'))
            readout = self.stream.readline().decode()
        except SerialException as e:
            status = False
            print("EXCEPTION")
            print(e)
        return (status,readout) # return statuus of reading and readout

    def read_serial(self):
        """function to read all data available in serial stream from arduino"""
        data_read = ''
        if self.connected:
            try:
                res = ''
                for i in range(20):
                    s = self.stream.readline().decode()
                    if s =='':
                        break
                    else:
                        res += s
                # print('>>ARDUINO',repr(s))
                return True, res
                # print("arduino >>   ",s,end='')
            except SerialException as e:
                print('There are problems with arduino.')
                print(e)
                return False, "SerialException"
                # self.close()
            except Exception as e:
                print("EXCEPTION")
                print(e)
                return False, "Exception"
        else:
            return False,"Not connected"

class COMPortWidgetOLD(QWidget):
    port = ''
    baudrate = 9600
    timeout = .01
    readings = []
    n_lines = 50
    debug_mode = True
    identification_names = []  # first few words that should be in the output to *IDN? command splited bu ',' to check
    check_parameter = 'manufacturer'  # parameter on which preCheck is check
    check_answer = 'wch.cn'  # check answer (for arduino), must be specified in child
    def __init__(self, data=None, parent=None, host_port=None,connect=True):
        self.data = data
        self.data["host_port"]=host_port
        self.connected = False
        self.parent = parent
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(self.data["timeout"])
        super().__init__()
        self.update_timer = QTimer()  # timer is needed for readings from serial port
        self.update_timer.setInterval(1000)
        self.update_timer.timeout.connect(self.updateReadings)

        self.delayed_read_timer = QTimer()
        self.delayed_read_timer.setInterval(200)
        self.delayed_read_timer.timeout.connect(self.readDelayed)
        self.initUI()


    def initUI(self):
        layout = QVBoxLayout()
        connect_layout = QHBoxLayout()
        self.port_menu = QComboBox()
        self.port_menu.currentTextChanged[str].connect(self.portChanged)
        connect_layout.addWidget(self.port_menu)

        info_btn = QPushButton('Update')
        info_btn.clicked.connect(self.updateBtnPressed)
        connect_layout.addWidget(info_btn)

        self.connect_btn = QPushButton('Connect')
        self.connect_btn.clicked.connect(self.connectBtnPressed)
        connect_layout.addWidget(self.connect_btn)

        layout.addLayout(connect_layout)

        write_layout = QHBoxLayout()

        self.line_to_send = QLineEdit()
        write_layout.addWidget(self.line_to_send)

        send_btn = QPushButton('Send')
        send_btn.clicked.connect(self.sendBtnPressed)
        write_layout.addWidget(send_btn)

        layout.addLayout(write_layout)

        self.readings_text = QTextEdit()
        layout.addWidget(self.readings_text)
        # self.showEvent.connect(self.onShow)

        layout.addStretch(1)
        self.main_layout = layout
        self.setLayout(layout)
        self.updateBtnPressed()  # to update com ports

    def readDelayed(self):
        self.delayed_read_timer.stop()
        try:
            answer = str(self.sock.recv(1024), "utf-8")
            print("Arduino answer", answer)
        except:
            print("nothing to read")
            answer = ''
        if answer == "Connected":
            self.connected = True
            self.update_timer.start()
            self.connect_btn.setStyleSheet("QWidget { background-color: %s }" % 'green')
            self.connect_btn.setText('Disconnect')
            return 0
        elif answer == "Disconnected":
            self.connected = False
            self.connect_btn.setText('Connect')
            self.connect_btn.setStyleSheet("QWidget { background-color: %s }" % 'yellow')
        elif answer.startswith("AvailableCOMs"):
            available_com_ports = json.loads(answer.split(" ",1)[1])

            old_port = self.data["port"]  # this should be done to not loose port name while updating port_menu
            self.port_menu.clear()
            self.port_menu.addItems(available_com_ports)
            self.data["port"] = old_port

            if self.data["port"] in available_com_ports:
                self.port_menu.setCurrentText(self.data["port"])
        elif answer:
            self.readings.append(answer)
            self.readings_text.setText(''.join(self.readings[-20:]))
            self.readings_text.moveCursor(QTextCursor.End)

    def connect(self):
        msg = 'Connect ' + json.dumps(self.data)
        self.sock.sendto(bytes(msg, "utf-8"), self.data["host_port"])
        self.delayed_read_timer.start()
        # for i in range(3):
        #     try:
        #         res = str(self.sock.recv(1024), "utf-8")
        #         print("connected, attempt", i)
        #         break
        #     except:
        #         print('not connected, attempt',i)
        #
        # print('res',res)
        # if res =="Ok":
        #     self.connected = True
        #     self.update_timer.start()
        #     return 0
        # else:
        #     self.connected = False
        #     return -1

    def close(self):
        msg = 'Close '+ json.dumps(self.data)
        self.sock.sendto(bytes(msg, "utf-8"), self.data["host_port"])
        self.delayed_read_timer.start()
        # for i in range(3):
        #     try:
        #         res = str(self.sock.recv(1024), "utf-8")
        #         print("disconnected, attempt", i)
        #         break
        #     except:
        #         print('not disconnected, attempt',i)
        # print('res', res)
        # if res =="Ok":
        #     self.connected = False
        #     self.update_timer.stop()
        #     return 0
        # else:
        #     self.connected = False
        #     return -1

    def portChanged(self, name):  # sets chosen com port for furhter connection
        self.data["port"] = name.strip('+')

    def updateBtnPressed(self):
        """updates com ports list and runs preCheck to choose suitable ports"""
        # print('HOST,PORT',self.data["host_port"])
        self.sock.sendto(bytes("UpdateCOM " + json.dumps({}), "utf-8"), self.data["host_port"])
        self.delayed_read_timer.start()
        # answer="{}"
        # for i in range(3):
        #     try:
        #         answer =  str(self.sock.recv(1024), "utf-8")
        #         print("read, attempt", i)
        #         break
        #     except:
        #         print('not read, attempt', i)
        #         res = ''
        #
        # print("SERVER answer",answer)
        # if "AvailableCOMs" in answer:
        #     answer = answer.split(" ",maxsplit=1)[1]
        # available_com_ports = json.loads(answer)
        #
        # old_port = self.data["port"]  # this should be done to not loose port name while updating port_menu
        # self.port_menu.clear()
        # self.port_menu.addItems(available_com_ports)
        # self.data["port"] = old_port
        #
        # if self.data["port"] in available_com_ports:
        #     self.port_menu.setCurrentText(self.data["port"])

    def updateComPorts(self,ports_str):
        print("in updateComPorts")
        try:
            available_com_ports = json.loads(ports_str)
        except json.JSONDecodeError as e:
            print("Can not decode comports", ports_str)
            print(e)
            return
        old_port = self.data["port"]  # this should be done to not loose port name while updating port_menu
        self.port_menu.clear()
        self.port_menu.addItems(available_com_ports)
        self.data["port"] = old_port

        if self.data["port"] in available_com_ports:
            self.port_menu.setCurrentText(self.data["port"])

    def connectBtnPressed(self):
        if not self.connected:  # if not yet connected - connect
            res = self.connect()
            # if res < 0:
            #     print("Can't connect ", self.data["port"])
            #     self.connect_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')
            #     return
            # self.connect_btn.setStyleSheet("QWidget { background-color: %s }" % 'green')
            # self.connect_btn.setText('Disconnect')
            # if self.parent and 'save' in dir(self.parent):  # save connected port to reconnect to it after relaunch
            #     print('send save command to parent', self.parent)
            #     self.parent.save({'port': self.data.port})
        else:  # else disconnect
            self.update_timer.stop()
            res = self.close()  # disconnect them
            # if res <0 :
            #     print("Can not disconnect port", self.data["port"])
            #     self.connect_btn.setText('Connect')
            #     self.connect_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')
            # else:
            #     self.connect_btn.setText('Connect')
            #     self.connect_btn.setStyleSheet("QWidget { background-color: %s }" % 'yellow')

    def sendBtnPressed(self):
        """Sends message to device. Can be reimplemented (as in ArduinoShutters"""
        msg = json.dumps({"name":self.data["name"],"msg":self.line_to_send.text()})
        self.line_to_send.setText('')
        self.send(msg)

    def updateReadingsNew(self,new_readings):
        """new_readings is dictionary of {"status":"Not connected","last_msg":"","last_readings":[]}"""
        def join_values(value):
            if type(value) == str:
                return value
            elif type(value) == list:
                return "\n" + "\n".join(value)
            else:
                return ""
        text = '\n'.join([key + ": " + join_values(new_readings[key]) for key in new_readings])
        # text = '\n'.join([key + ": " + str(new_readings[key]) for key in new_readings])
        self.readings_text.setText(text)

    def updateReadings(self): # old version
        """updates reading from arduino"""
        # print('reading')
        msg = 'Read ' + json.dumps({key:self.data[key] for key in self.data if key in ["name","device"]})
        self.sock.sendto(bytes(msg, "utf-8"), self.data["host_port"])
        self.delayed_read_timer.start()
        # for i in range(3):
        #     try:
        #         res = str(self.sock.recv(1024), "utf-8")
        #         # print("read, attempt", i)
        #         break
        #     except:
        #         # print('not read, attempt', i)
        #         res = ''
        # # print('res', res)
        # if res:
        #     self.readings.append(res)
        #     self.readings_text.setText(''.join(self.readings[-20:]))
        #     self.readings_text.moveCursor(QTextCursor.End)

    def send(self,msg):
        full_msg = "Send " + msg
        self.sock.sendto(bytes(full_msg, "utf-8"), self.data["host_port"])
        try:
            text = json.loads(msg)["msg"]
        except:
            text = msg
        # self.parent.newCommandSent(text)
        self.delayed_read_timer.start()
        # for i in range(3):
        #     try:
        #         res = str(self.sock.recv(1024), "utf-8")
        #         print("sent, attempt", i)
        #         break
        #     except:
        #         print('not sent, attempt', i)
        #         res = ''
        # print('Send res', res)

class COMPortWidget(QWidget):
    port = ''
    baudrate = 9600
    timeout = .01
    readings = []
    n_lines = 50
    debug_mode = True
    identification_names = []  # first few words that should be in the output to *IDN? command splited bu ',' to check
    check_parameter = 'manufacturer'  # parameter on which preCheck is check
    check_answer = 'wch.cn'  # check answer (for arduino), must be specified in child
    def __init__(self, data=None, parent=None, host_port=None,connect=True):
        self.data = data
        self.data["host_port"]=host_port
        self.connected = False
        self.parent = parent
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(self.data["timeout"])
        super().__init__()
        # self.update_timer = QTimer()  # timer is needed for readings from serial port
        # self.update_timer.setInterval(1000)
        # self.update_timer.timeout.connect(self.updateReadings)

        # self.delayed_read_timer = QTimer()
        # self.delayed_read_timer.setInterval(200)
        # self.delayed_read_timer.timeout.connect(self.readDelayed)
        self.initUI()


    def initUI(self):
        layout = QVBoxLayout()
        connect_layout = QHBoxLayout()
        self.port_menu = QComboBox()
        self.port_menu.currentTextChanged[str].connect(self.portChanged)
        connect_layout.addWidget(self.port_menu)

        info_btn = QPushButton('Update')
        info_btn.clicked.connect(self.updateBtnPressed)
        connect_layout.addWidget(info_btn)

        self.connect_btn = QPushButton('Connect')
        self.connect_btn.clicked.connect(self.connectBtnPressed)
        connect_layout.addWidget(self.connect_btn)

        layout.addLayout(connect_layout)

        write_layout = QHBoxLayout()

        self.line_to_send = QLineEdit()
        write_layout.addWidget(self.line_to_send)

        send_btn = QPushButton('Send')
        send_btn.clicked.connect(self.sendBtnPressed)
        write_layout.addWidget(send_btn)

        layout.addLayout(write_layout)

        self.readings_text = QTextEdit()
        self.readings_text.setMaximumHeight(800)
        layout.addWidget(self.readings_text)
        # self.showEvent.connect(self.onShow)

        layout.addStretch(1)
        self.main_layout = layout
        self.setLayout(layout)
        self.updateBtnPressed()  # to update com ports

    # def readDelayed(self):
    #     self.delayed_read_timer.stop()
    #     try:
    #         answer = str(self.sock.recv(1024), "utf-8")
    #         print("Arduino answer", answer)
    #     except:
    #         print("nothing to read")
    #         answer = ''
    #     if answer == "Connected":
    #         self.connected = True
    #         self.update_timer.start()
    #         self.connect_btn.setStyleSheet("QWidget { background-color: %s }" % 'green')
    #         self.connect_btn.setText('Disconnect')
    #         return 0
    #     elif answer == "Disconnected":
    #         self.connected = False
    #         self.connect_btn.setText('Connect')
    #         self.connect_btn.setStyleSheet("QWidget { background-color: %s }" % 'yellow')
    #     elif answer.startswith("AvailableCOMs"):
    #         available_com_ports = json.loads(answer.split(" ",1)[1])
    #
    #         old_port = self.data["port"]  # this should be done to not loose port name while updating port_menu
    #         self.port_menu.clear()
    #         self.port_menu.addItems(available_com_ports)
    #         self.data["port"] = old_port
    #
    #         if self.data["port"] in available_com_ports:
    #             self.port_menu.setCurrentText(self.data["port"])
    #     elif answer:
    #         self.readings.append(answer)
    #         self.readings_text.setText(''.join(self.readings[-20:]))
    #         self.readings_text.moveCursor(QTextCursor.End)

    def connect(self):
        msg = 'Connect ' + json.dumps(self.data)
        self.sock.sendto(bytes(msg, "utf-8"), self.data["host_port"])
        # self.delayed_read_timer.start()
        # for i in range(3):
        #     try:
        #         res = str(self.sock.recv(1024), "utf-8")
        #         print("connected, attempt", i)
        #         break
        #     except:
        #         print('not connected, attempt',i)
        #
        # print('res',res)
        # if res =="Ok":
        #     self.connected = True
        #     self.update_timer.start()
        #     return 0
        # else:
        #     self.connected = False
        #     return -1

    def close(self):
        msg = 'Close '+ json.dumps(self.data)
        self.sock.sendto(bytes(msg, "utf-8"), self.data["host_port"])
        # self.delayed_read_timer.start()
        # for i in range(3):
        #     try:
        #         res = str(self.sock.recv(1024), "utf-8")
        #         print("disconnected, attempt", i)
        #         break
        #     except:
        #         print('not disconnected, attempt',i)
        # print('res', res)
        # if res =="Ok":
        #     self.connected = False
        #     self.update_timer.stop()
        #     return 0
        # else:
        #     self.connected = False
        #     return -1

    def portChanged(self, name):  # sets chosen com port for furhter connection
        self.data["port"] = name.strip('+')

    def updateBtnPressed(self):
        """updates com ports list and runs preCheck to choose suitable ports"""
        print('HOST,PORT',self.data["host_port"])
        self.sock.sendto(bytes("UpdateCOM " + json.dumps({}), "utf-8"), self.data["host_port"])
        # self.delayed_read_timer.start()
        # answer="{}"
        # for i in range(3):
        #     try:
        #         answer =  str(self.sock.recv(1024), "utf-8")
        #         print("read, attempt", i)
        #         break
        #     except:
        #         print('not read, attempt', i)
        #         res = ''
        #
        # print("SERVER answer",answer)
        # available_com_ports = json.loads(answer)
        #
        # old_port = self.data["port"]  # this should be done to not loose port name while updating port_menu
        # self.port_menu.clear()
        # self.port_menu.addItems(available_com_ports)
        # self.data["port"] = old_port
        #
        # if self.data["port"] in available_com_ports:
        #     self.port_menu.setCurrentText(self.data["port"])

    def updateComPorts(self,ports_str):
        print("in updateComPorts")
        try:
            available_com_ports = json.loads(ports_str)
        except json.JSONDecodeError as e:
            print("Can not decode comports", ports_str)
            print(e)
            return
        old_port = self.data["port"]  # this should be done to not loose port name while updating port_menu
        self.port_menu.clear()
        self.port_menu.addItems(available_com_ports)
        self.data["port"] = old_port

        if self.data["port"] in available_com_ports:
            self.port_menu.setCurrentText(self.data["port"])

    def connectBtnPressed(self):
        if not self.connected:  # if not yet connected - connect
            res = self.connect()
            # if res < 0:
            #     print("Can't connect ", self.data["port"])
            #     self.connect_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')
            #     return
            # self.connect_btn.setStyleSheet("QWidget { background-color: %s }" % 'green')
            # self.connect_btn.setText('Disconnect')
            # if self.parent and 'save' in dir(self.parent):  # save connected port to reconnect to it after relaunch
            #     print('send save command to parent', self.parent)
            #     self.parent.save({'port': self.data.port})
        else:  # else disconnect
            # self.update_timer.stop()
            res = self.close()  # disconnect them
            # if res <0 :
            #     print("Can not disconnect port", self.data["port"])
            #     self.connect_btn.setText('Connect')
            #     self.connect_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')
            # else:
            #     self.connect_btn.setText('Connect')
            #     self.connect_btn.setStyleSheet("QWidget { background-color: %s }" % 'yellow')

    def sendBtnPressed(self):
        """Sends message to device. Can be reimplemented (as in ArduinoShutters"""
        msg = json.dumps({"name":self.data["name"],"msg":self.line_to_send.text()})
        self.line_to_send.setText('')
        self.send(msg)

    def updateReadingsNew(self,new_readings):
        """new_readings is dictionary of {"status":"Not connected","last_msg":"","last_readings":[]}"""
        def join_values(value):
            if type(value) == str:
                return value
            elif type(value) == list:
                return "\n" + "\n".join(value)
            else:
                return ""
        text = '\n'.join([key + ": " + join_values(new_readings[key]) for key in new_readings])
        # text = '\n'.join([key + ": " + str(new_readings[key]) for key in new_readings])
        self.readings_text.setText(text)

    # def updateReadings(self): # old version
    #     """updates reading from arduino"""
    #     # print('reading')
    #     msg = 'Read ' + json.dumps({key:self.data[key] for key in self.data if key in ["name","device"]})
    #     self.sock.sendto(bytes(msg, "utf-8"), self.data["host_port"])
    #     self.delayed_read_timer.start()
    #     # for i in range(3):
    #     #     try:
    #     #         res = str(self.sock.recv(1024), "utf-8")
    #     #         # print("read, attempt", i)
    #     #         break
    #     #     except:
    #     #         # print('not read, attempt', i)
    #     #         res = ''
    #     # # print('res', res)
    #     # if res:
    #     #     self.readings.append(res)
    #     #     self.readings_text.setText(''.join(self.readings[-20:]))
    #     #     self.readings_text.moveCursor(QTextCursor.End)

    def send(self,msg):
        full_msg = "Send " + msg
        self.sock.sendto(bytes(full_msg, "utf-8"), self.data["host_port"])
        try:
            text = json.loads(msg)["msg"]
        except:
            text = msg
        self.parent.newCommandSent(text)
        # self.delayed_read_timer.start()
        # for i in range(3):
        #     try:
        #         res = str(self.sock.recv(1024), "utf-8")
        #         print("sent, attempt", i)
        #         break
        #     except:
        #         print('not sent, attempt', i)
        #         res = ''
        # print('Send res', res)


class COMPortDevice:
    """General class for com ports. """
    connected = False
    port = ''
    baudrate = 9600
    timeout = 1
    readings = []
    n_lines = 50
    identification_names = [] # first few words that should be in the output to *IDN? command splited bu ',' to check
    check_parameter = 'manufacturer' # parameter on which preCheck is check
    check_answer = 'wch.cn' # check answer (for arduino), must be specified in child

    def __init__(self,default_port=None):
        if default_port:
            self.port = default_port
    # function to check based on port info if the port is correct, if port is transfered then checks if
    # port pass check.
    def preCheck(self,port=None):
        if port:
            return (getattr(port,self.check_parameter,None) == self.check_answer)
        else:
            if (self.port != '' and self.port in [port.device for port in list_ports.comports()] and
                getattr([port for port in list_ports.comports() if port.device == self.port][0],self.check_parameter)==self.check_answer):
                return
            for port in list(list_ports.comports()):
                if getattr(port,self.check_parameter)== self.check_answer:
                    self.port = port.device
                    return

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
            s = p.readline().decode()
            if '*IDN?' in s:
                p.write(b'system:echo off\r')
                p.readline().decode()
                p.write(idn_message)
                s = p.readline().decode()
            s = s.split(',')
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
                        print(s[i], self.identification_names[i])
                        break
                if status: # if there no mistakes while name comparison
                    print('\n' + 'Device ' + str(self.identification_names) + ' connected on port ' + self.port + '\n')
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

    def write_com(self,command):
        status = True
        readout = ''
        if not self.connected:
            return (False, '')
        try:
            self.stream.write(command)
            readout='Ok'
        except SerialException as e:
            status = False
            readout='bad'
            print(e)
        return (status, readout)  # return statuus of reading and readout

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

    def read_serial(self):
        """function to read all data available in serial stream from arduino"""
        data_read = ''
        if self.connected:
            for i in range(20):
                try:
                    s = self.stream.readline().decode()
                    # print('>>ARDUINO',repr(s))
                    if s == '':
                        break
                    self.append_readings(s)
                    # print("arduino >>   ",s,end='')
                except SerialException as e:
                    print('There are problems with arduino. Connection will be terminated')
                    print(e)
                    self.close()
                except e:
                    print(e)
        # print('reading finised')

    def append_readings(self,s):
        """append last readings from arduino to the list"""
        # print("arduino >>   ", s, end='')
        # print('appedn readings',s)
        # if there no \n on the end (string s is small) - just add it to the last string
        if (not s.endswith('\n')) and len(self.readings) and len(self.readings[-1] + s)<self.n_chars_in_string:
            self.readings[-1] += s
        else:
            if len(self.readings) < self.n_lines: # if it's less the n_lines in readings
                self.readings.append(s)
            else:
                self.readings[:-1] = self.readings[1:]
                self.readings[-1] = s

    class BasicWidget(QWidget):
        """Basic widget for comport. Contains ports list. update and connect button, and possibility to send connands
        to the device"""
        def __init__(self,data=None, parent=None,connect=True):
            self.data=data
            self.parent = parent
            super().__init__()

            layout = QVBoxLayout()
            connect_layout = QHBoxLayout()
            self.port_menu = QComboBox()
            self.port_menu.currentTextChanged[str].connect(self.portChanged)
            connect_layout.addWidget(self.port_menu)

            info_btn = QPushButton('Update')
            info_btn.clicked.connect(self.updateBtnPressed)
            connect_layout.addWidget(info_btn)

            self.connect_btn = QPushButton('Connect')
            self.connect_btn.clicked.connect(self.connectBtnPressed)
            connect_layout.addWidget(self.connect_btn)

            layout.addLayout(connect_layout)

            write_layout = QHBoxLayout()

            self.line_to_send = QLineEdit()
            write_layout.addWidget(self.line_to_send)

            send_btn = QPushButton('Send')
            send_btn.clicked.connect(self.sendBtnPressed)
            write_layout.addWidget(send_btn)

            layout.addLayout(write_layout)
            layout.addStretch(1)
            self.main_layout = layout
            self.setLayout(layout)
            self.updateBtnPressed() #to update com ports

            if connect:
                self.connectBtnPressed()

        def portChanged(self,name): # sets chosen com port for furhter connection
            self.data.port = name.strip('+')

        def updateBtnPressed(self):
            """updates com ports list and runs preCheck to choose suitable ports"""
            available_com_ports = [port.device for port in list(list_ports.comports())]
            good_ports = [] # ports which pass preCheck
            for i,port in enumerate(list(list_ports.comports())):
                if self.data.preCheck(port):
                    available_com_ports[i] +='+'
                    good_ports.append(port.device)

            print("PreChecked ports,", good_ports)

            old_port = self.data.port # this should be done to not loose port name while updating port_menu
            self.port_menu.clear()
            self.port_menu.addItems(available_com_ports)
            self.data.port = old_port

            if self.data.port in good_ports: # if defalt port is good - do nothing
                self.port_menu.setCurrentText(self.data.port + '+')
            elif len(good_ports): # else choose last good port
                last_port = good_ports[-1]
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
                if self.parent and 'save' in dir(self.parent): # save connected port to reconnect to it after relaunch
                    print('send save command to parent',self.parent)
                    self.parent.save({'port':self.data.port})
            else:   # else disconnect
                self.data.close()  # disconnect them
                self.connect_btn.setText('Connect')
                self.connect_btn.setStyleSheet("QWidget { background-color: %s }" % 'yellow')

        def sendBtnPressed(self):
            """Sends message to device. Can be reimplemented (as in ArduinoShutters"""
            msg = self.line_to_send.text()+'\r'
            self.line_to_send.setText('')
            # print('message = ', msg)
            status, res = self.data.write_com(msg.encode('ascii'))
            # print('res', res)
            # status, res = self.data.write_read_com(msg.encode('ascii'))
            #
            # if not status:
            #     print('problems with sending msg: ', msg)
            # else:
            #     print(res)

    class ExtendedWidget(BasicWidget):
        def __init__(self,data=None, parent=None,connect=True):
            super().__init__(data=data, parent=parent,connect=connect)
            self.readings_text = QTextEdit()
            self.main_layout.addWidget(self.readings_text)
            # self.showEvent.connect(self.onShow)
            self.timer = QTimer()  # timer is needed for readings from serial port
            self.timer.setInterval(500)
            self.timer.timeout.connect(self.updateReadings)
            # self.timer.start()
            # self.close()

        def updateReadings(self):
            """updates reading from arduino"""
            # print('reading')
            self.data.read_serial()
            # print('NEW DATA',self.data.readings)
            self.readings_text.setText(''.join(self.data.readings))
            self.readings_text.moveCursor(QTextCursor.End)

        def showEvent(self,e):
            # print('heww')
            QWidget().showEvent(e)
            self.timer.start()

        def closeEvent(self,e):
            QWidget().closeEvent(e)
            self.timer.stop()


class LANDevice:
    """General class for com ports. """
    connected = False
    ip = ''
    port = 8080
    timeout = 1000 # ms
    buffer_size=1024
    identification_names = ['Stanford Research Systems', 'SG382','s/n002098'] # first few words that should be in the output to *IDN? command splited bu ',' to check
    check_parameter = 'manufacturer' # parameter on which preCheck is check
    check_answer = 'wch.cn' # check answer (for arduino), must be specified in child

    def __init__(self,ip = None, port=None):
        if port:
            self.port = port
        if ip:
            self.ip = ip
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def close(self): # closes port
        self.socket.close()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False

    def connect(self,idn_message=b'*IDN?\r'):
        """tries to connect port.
        idn_message - message to be sent to devise to identify it
        If connected returns 0, if not - value < 0 """
        try:
            self.socket.connect((self.ip,self.port))
            self.socket.send(idn_message)
            s = self.socket.recv(self.buffer_size)
            s = s.decode().split(',')
            print('Port answer ', s)
            if len(s) < len(self.identification_names): # if length of identification names is smaller than expected
                print('Wrong devise msg1')
                return -1
            else:
                status = True
                for i in range(len(self.identification_names)): # checks every name
                    if s[i] != self.identification_names[i]:
                        status = False
                        print(s[i], self.identification_names[i])
                        break
                if status: # if there no mistakes while name comparison
                    print('\nDevise ' + str(self.identification_names) + ' connected on ip' +self.ip +' port ' + str(self.port) + '\n')
                    self.connected = True
                    return 0
                else: # if any mistake while name comparison
                    print('Wrong devise msg2')
                    self.socket.close()
                    return -1
        except TimeoutError:
            self.connected = False
            print('Most probably wrong IP')
            return -2
        except ConnectionRefusedError:
            self.connected = False
            print('Wrogn IP or port')
            return -2
        return 0

    def write(self,command):
        status = True
        if not self.connected:
            return (False, 'not connected')
        try:
            self.socket.send(command)
            readout='Ok'
        except Exception as e:
            status = False
            readout='send error'
            print('Esception while sending')
            print(e)
        return (status, readout)  # return statuus of reading and readout

    def write_read(self, command):
        """tries to write command to devise and read it's response"""
        status = True
        readout = ''
        if not self.connected:
            return (False,'')
        try:
            self.socket.send(command)
            readout = self.socket.recv(self.buffer_size).decode()

        except Exception as e:
            status = False
            print('Esception while sending or reading')
            print(e)
        return (status,readout) # return statuus of reading and readout

    class BasicWidget(QWidget):
        """Basic widget for comport. Contains ports list. update and connect button, and possibility to send connands
        to the device"""
        def __init__(self,data=None, parent=None,connect=True):
            self.data=data
            self.parent = parent
            super().__init__()

            layout = QVBoxLayout()
            connect_layout = QHBoxLayout()

            connect_layout.addWidget(QLabel('IP'))
            self.ip_line = QLineEdit()
            self.ip_line.setText(self.data.ip)
            connect_layout.addWidget(self.ip_line)

            connect_layout.addWidget(QLabel('port'))
            self.port_line = QLineEdit()
            self.port_line.setText(str(self.data.port))
            connect_layout.addWidget(self.port_line)

            self.connect_btn = QPushButton('Connect')
            self.connect_btn.clicked.connect(self.connectBtnPressed)
            connect_layout.addWidget(self.connect_btn)

            layout.addLayout(connect_layout)

            write_layout = QHBoxLayout()

            self.line_to_send = QLineEdit()
            write_layout.addWidget(self.line_to_send)

            send_btn = QPushButton('Send')
            send_btn.clicked.connect(self.sendBtnPressed)
            write_layout.addWidget(send_btn)

            layout.addLayout(write_layout)
            self.setLayout(layout)

            if connect:
                self.connectBtnPressed()

        # def portChanged(self,name): # sets chosen com port for furhter connection
        #     self.data.port = name.strip('+')

        def connectBtnPressed(self):
            if not self.data.connected: # if not yet connected - connect
                self.data.ip = self.ip_line.text()
                try:
                    self.data.port = int(self.port_line.text())
                except ValueError:
                    print('Port should be an integer')
                    self.connect_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')
                    return
                res = self.data.connect()
                if res < 0:
                    print("Can't connect ",self.data.ip, self.data.port)
                    self.connect_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')
                    return
                self.connect_btn.setStyleSheet("QWidget { background-color: %s }" % 'green')
                self.connect_btn.setText('Disconnect')
                if self.parent and 'save' in dir(self.parent): # save connected port to reconnect to it after relaunch
                    print('send save command to parent',self.parent)
                    self.parent.save({'port':self.data.port})
            else:   # else disconnect
                self.data.close()
                self.connect_btn.setText('Connect')
                self.connect_btn.setStyleSheet("QWidget { background-color: %s }" % 'yellow')

        def sendBtnPressed(self):
            """Sends message to device. Can be reimplemented (as in ArduinoShutters"""
            msg = self.line_to_send.text()+'\r'
            self.line_to_send.setText('')
            print('message = ', msg)
            status, res = self.data.write_read(msg.encode('ascii'))

            if not status:
                print('problems with sending msg: ', msg)
            else:
                print(res)

if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    # device = COMPortDevice(default_port='COM15')
    # print(device.port)
    # mainWindow = device.BasicWidget(data=device,connect=False)
    device = LANDevice(ip='192.168.1.244',port='5025')
    mainWindow = device.BasicWidget(data=device,connect=False)
    mainWindow.show()
    sys.exit(app.exec_())

class MyBox(QLineEdit):
    def __init__(self, *args,valid = (10,999,6),value=0, **kwargs):
        self.valid = valid
        super(MyBox, self).__init__(*args, **kwargs)
        self.setValidator(QDoubleValidator(*valid))
        self.setText(str(value))

    def setValue(self,new_val):
        self.setText(str(new_val))
    def keyPressEvent(self, QKeyEvent):
        print(self.hasAcceptableInput())
        if not self.hasAcceptableInput():
            print('Out of range se')
            return
        p = 0
        if QKeyEvent.key() == Qt.Key_Up:
            p = 1
        if QKeyEvent.key() == Qt.Key_Down:
            p = -1
        if p == 0:
            return super(MyBox, self).keyPressEvent(QKeyEvent)
        number = [x for x in self.text()]
        val = float(self.text())
        position = self.cursorPosition()
        decimal_position = self.text().find('.') if self.text().find('.') != -1 else len(self.text())
        # print(position,decimal_position)
        if position <= decimal_position:
            factor = decimal_position - position
        else:
            factor = decimal_position -position + 1
        # print('factor',factor)
        new_val = val + p*10**factor
        if new_val >= self.valid[0] and new_val<= self.valid[1]:
            self.setText('%.5f'%(new_val))
        # pos = position - 1
        # while p and pos >= 0:
        #     if ('0' < number[pos] < '9') or (number[pos] == '9' and p < 0) or (number[pos] == '0' and p > 0):
        #         number[pos] = chr(ord(number[pos]) + p)
        #         p = 0
        #     elif number[pos] == '9':
        #         number[pos] = '0'
        #     elif number[pos] == '0':
        #         number[pos] = '9'
        #     pos -= 1
        # if p == 1:
        #     number = '1' + ''.join(number)
        #     position += 1
        # self.setText(''.join(number))
        self.setCursorPosition(position)

    def value(self):
        return float(self.text())

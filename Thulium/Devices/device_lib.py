
from serial import Serial#
import socket
from serial import SerialException
from PyQt5.QtWidgets import (QWidget, QPushButton, QVBoxLayout,QComboBox, QHBoxLayout,QLineEdit, QLabel)
from serial.tools import list_ports
from PyQt5.QtCore import (QLineF, QPointF, QRectF, Qt, QTimer)
from PyQt5.QtGui import (QBrush, QColor, QPainter,QIcon, QDoubleValidator)

class COMPortDevice:
    """General class for com ports. """
    connected = False
    port = ''
    baudrate = 9600
    timeout = 1
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
                        print(s[i], self.identification_names[i])
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

            print(good_ports)

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
            print('message = ', msg)
            status, res = self.data.write_read_com(msg.encode('ascii'))

            if not status:
                print('problems with sending msg: ', msg)
            else:
                print(res)

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
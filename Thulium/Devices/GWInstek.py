try:
    from .device_lib import COMPortDevice
except:
    from device_lib import COMPortDevice

from serial.tools import list_ports
from PyQt5.QtCore import (Qt)
from PyQt5.QtGui import (QDoubleValidator)
from PyQt5.QtWidgets import (QWidget)

from PyQt5.QtWidgets import (QApplication, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton)

scan_params_str = 'scan_params'
name_in_scan_params = 'GPD 3303'

class GPD(COMPortDevice):
    identification_names = ['GW INSTEK', 'GPD-3303D', 'SN:EO894799']
    timeout = 2.5
    port = 'COM6'
    check_answer = 'FTDI'
    def connect(self,idn_message=b'*IDN?\r'):
        return super().connect(b'REMOTE\n*IDN?\n')
    
    # def preCheck(self,port=None):
    #     if port:
    #         return (port.manufacturer == 'FTDI' and port.serial_number == 'AH02602GA')
    #     else:
    #         for port in list(list_ports.comports()):
    #             if port.manufacturer == 'FTDI' and port.serial_number == 'AH02602GA':
    #                 self.port = port.device

    def setV1(self, V1):
        s = 'VSET1:%s\n' %(V1)
        status,readout = self.write_com(s.encode())
        print(status, readout)

    def setV2(self, V2):
        s = 'VSET2:%s\n' %(V2)
        status,readout = self.write_com(s.encode())
        print(status, readout)

    def setI1(self, I1):
        s = 'ISET1:%s\n' % (I1)
        status,readout = self.write_com(s.encode())
        print(status, readout)

    def setI2(self, I2):
        s = 'ISET2:%s\n' %(I2)
        status,readout = self.write_com(s.encode())
        print(status, readout)

    def getV1(self):
        status,readout = self.write_read_com(b'VSET1?\n')
        readout = readout[:-2]
        print(status, readout)
        return readout

    def getV2(self):
        status,readout = self.write_read_com(b'VSET2?\n')
        readout = readout[:-2]
        print(status, readout)
        return readout

    def getI1(self):
        status,readout = self.write_read_com(b'ISET1?\n')
        readout = readout[:-2]
        print(status, readout)
        return readout

    def getI2(self):
        status,readout = self.write_read_com(b'ISET2?\n')
        readout = readout[:-2]
        print(status, readout)
        return readout

    def switch(self, on):
        if on:
            on = 1
        else:
            on = 0
        status, readout = self.write_com(b'OUT%d\n' %(on))
        print(status, readout)

class MyBox(QLineEdit):
    def __init__(self, valid = (0,32,2), *args, **kwargs):
        self.valid = valid
        super(MyBox, self).__init__(*args, **kwargs)
        self.setValidator(QDoubleValidator(*valid))

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
        print(position,decimal_position)
        if position <= decimal_position:
            factor = decimal_position - position
        else:
            factor = decimal_position -position + 1
        print('factor',factor)
        new_val = val + p*10**factor
        if new_val >= self.valid[0] and new_val<= self.valid[1]:
            self.setText('%.2f'%(new_val))
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



class GPDwidget(QWidget):
    def __init__(self,parent=None,globals=None):
        self.globals = globals
        self.gpd = GPD()
        self.parent = parent
        super().__init__()
        self.setWindowTitle('GPD 3303')
        self.on_btn = QPushButton('off')
        self.initUI()
        self.setMaximumWidth(500)
        self.sendScanParams()

    def initUI(self):
        layout = QHBoxLayout()

        l1= QVBoxLayout()
        l2 = QVBoxLayout()

        restor_btn = QPushButton('Restore')
        restor_btn.clicked.connect(self.restore)
        l2.addWidget(restor_btn)

        l2.addWidget(QLabel('V1, V'))
        self.V1line = MyBox(valid=(0, 32, 2))
        self.V1line.setText('0')
        self.V1line.textChanged.connect(self.changeV1)
        l2.addWidget(self.V1line)

        l2.addWidget(QLabel('I1, A'))
        self.I1line = MyBox(valid=(0, 3.2, 2))
        self.I1line.setText('0')
        self.I1line.textChanged.connect(self.changeI1)
        l2.addWidget(self.I1line)

        self.on_btn.clicked.connect(self.switch)
        l1.addWidget(self.on_btn)

        l1.addWidget(QLabel('V2, V'))
        self.V2line = MyBox(valid=(0, 32, 2))
        self.V2line.setText('0')
        self.V2line.textChanged.connect(self.changeV2)
        l1.addWidget(self.V2line)

        l1.addWidget(QLabel('I2, A'))
        self.I2line = MyBox(valid=(0, 3.2, 2))
        self.I2line.setText('0')
        self.I2line.textChanged.connect(self.changeI2)
        l1.addWidget(self.I2line)

        layout.addLayout(l1)
        layout.addLayout(l2)

        layout.addWidget(self.gpd.BasicWidget(data=self.gpd, parent=self,connect=False))

        self.setLayout(layout)

    def changeV1(self):
        print('V1')
        try:
            self.gpd.setV1(self.V1line.text())
        except ValueError:
            print('V1 input is not a float')

    def changeV2(self):
        print('V2')
        try:
            self.gpd.setV2(self.V2line.text())
        except ValueError:
            print('V2 input is not a float')

    def changeI1(self):
        print('I1')
        try:
            self.gpd.setI1(self.I1line.text())
        except ValueError:
            print('I1 input is not a float')

    def changeI2(self):
        print('I2')
        try:
            self.gpd.setI2(self.I2line.text())
        except ValueError:
            print('I2 input is not a float')

    def switch(self):
        if self.on_btn.text() == 'off':
            self.gpd.switch(1)
            self.on_btn.setText('on')
            self.on_btn.setStyleSheet("QWidget { background-color: %s }" % 'blue')
        else:
            self.gpd.switch(0)
            self.on_btn.setText('off')
            self.on_btn.setStyleSheet("QWidget { background-color: %s }" % 'None')

    def restore(self):
        self.I2line.textChanged.disconnect(self.changeI2)
        self.I1line.textChanged.disconnect(self.changeI1)
        self.V2line.textChanged.disconnect(self.changeV2)
        self.V1line.textChanged.disconnect(self.changeV1)
        I1 = self.gpd.getI1()
        self.I1line.setText(I1)

        I2 = self.gpd.getI2()
        self.I2line.setText(I2)

        V1 = self.gpd.getV1()
        self.V1line.setText(V1)

        V2 = self.gpd.getV2()
        self.V2line.setText(V2)

        self.I2line.textChanged.connect(self.changeI2)
        self.I1line.textChanged.connect(self.changeI1)
        self.V2line.textChanged.connect(self.changeV2)
        self.V1line.textChanged.connect(self.changeV1)


    def sendScanParams(self):
        params = ['V1','V2','I1', 'I2']
        if self.globals != None:
            if scan_params_str not in self.globals:
                self.globals[scan_params_str] = {}
            self.globals[scan_params_str][name_in_scan_params] = params
        return

    def getUpdateMethod(self):
        return self.updateFromScanner

    def updateFromScanner(self, param_dict=None):
        # self.scanner = True
        print('Here')
        try:
            for param, val in param_dict.items():
                param = param[0]
                print(param,val)
                if param == 'V1':
                    self.V1line.setText(str(val))
                    self.changeV1()
                elif param == 'V2':
                    self.V2line.setText(str(val))
                    self.changeV2()
                elif param == 'I1':
                    self.I1line.setText(str(val))
                    self.changeI1()
                elif param == 'I2':
                    self.I2line.setText(str(val))
                    self.changeI2()
        except Exception as e:
            print("can't change from scanner: ", e)
            return -1
        return 0

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    mainWindow = GPDwidget()
    mainWindow.show()
    sys.exit(app.exec_())
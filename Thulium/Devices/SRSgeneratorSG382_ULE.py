try:
    from .device_lib import COMPortDevice, LANDevice
except:
    from device_lib import COMPortDevice, LANDevice
from serial import Serial
from serial.tools import list_ports
from time import sleep
from serial.serialutil import SerialException
# matplotlib.use('Qt5Agg')
from PyQt5.QtCore import (QLineF, QPointF, QRectF, Qt, QTimer)
from PyQt5.QtGui import (QBrush, QColor, QPainter,QIcon, QDoubleValidator)
from PyQt5.QtWidgets import (QApplication, QGraphicsView, QGraphicsScene, QGraphicsItem, QMenu, QAction, QScrollArea,QFrame,
                             QGridLayout, QVBoxLayout, QHBoxLayout, QSizePolicy,QMainWindow, QDialog,QTextEdit,
                             QLabel, QLineEdit, QPushButton, QWidget, QComboBox,QRadioButton, QSpinBox, QCheckBox, QTabWidget, QFileDialog,QMessageBox, QDoubleSpinBox)
import matplotlib.pyplot as plt
from numpy import arange, sin, pi
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (QApplication, QGraphicsView, QGraphicsScene, QGraphicsItem,
                             QGridLayout, QVBoxLayout, QHBoxLayout, QSizePolicy,
                             QLabel, QLineEdit, QPushButton)
from datetime import datetime
import json
if __name__ == '__main__':
    configFile = 'SRSgeneratorSG382_ULE-config.json'
else:
    configFile = 'Devices/SRSgeneratorSG382_ULE-config.json'

class SRS_COM(COMPortDevice):
    identification_names = ['Stanford Research Systems', 'SG382','s/n002098']
    timeout = 10
    port = 'COM9'
    # baudrate = 19200
    check_answer = 'Prolific'
    # def preCheck(self,port=None):
    #     if port:
    #         return (port.manufacturer == 'Prolific')
    #     else:
    #         if self.port != '' and self.port in [port.device for port in list_ports.comports()]:
    #             return
    #         for port in list(list_ports.comports()):
    #             if port.manufacturer == 'Prolific':
    #                 self.port = port.device
    #                 return

    def setFreq(self,freq):
        print('In setFreq')
        # status,readout = self.write_read_com(b'FREQ %.3f Hz\r' %(freq))
        status, readout = self.write_com(b'FREQ %.3f Hz\r' % (freq))
        print(status, readout)
        return status,readout

    def setAmpl(self,ampl):
        status,readout = self.write_read_com(b'AMPR %f\r' %(ampl))
        print(status, readout)

    def getFreq(self):
        return self.write_read_com(b'FREQ? MHz\r')

    def getAmpl(self):
        return self.write_read_com(b'AMPR?\r')

class SRS_LAN(LANDevice):
    identification_names = ['Stanford Research Systems', 'SG382','s/n002098']
    timeout = 1
    ip = '192.168.1.244'
    port = 5025

    def setFreq(self,freq):
        print('In setFreq')
        # status,readout = self.write_read_com(b'FREQ %.3f Hz\r' %(freq))
        status, readout = self.write(b'FREQ %.3f Hz\r' % (freq))
        print(status, readout)
        return status,readout

    def setAmpl(self,ampl):
        status,readout = self.write_read(b'AMPR %f\r' %(ampl))
        print(status, readout)

    def getFreq(self):
        return self.write_read(b'FREQ? MHz\r')

    def getAmpl(self):
        return self.write_read(b'AMPR?\r')

class MyBox(QLineEdit):
    def __init__(self, *args,valid = (10,999,6), **kwargs):
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
            self.setText('%.3f'%(new_val))
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



class SRSGenerator(QWidget):
    def __init__(self,parent=None,globals=None):
        self.globals = globals
        # self.load()
        self.config = {}
        self.srs = SRS_LAN() #SRS_COM()
        self.f0 = 29000000.000
        self.df = 28.8
        self.t0 = datetime(2018,1,1,0,0,0)
        self.fnow = 29000000.000
        self.t = datetime.now()
        self.correctionOn = False
        # self.freq_offset = '0.0'
        self.ampl = '0.0'
        self.parent = parent
        super().__init__()
        self.setWindowTitle('SRS SG382 ULE')
        self.initUI()
        self.timer = QTimer()
        self.timer.setInterval(10000)
        self.timer.timeout.connect(self.routine)
        # self.sendScanParams()
        print(self)

    def load(self):

        with open(configFile,'r') as f:
            self.config = json.load(f)

    def save(self,dict_to_save):
        print("reee")
        self.config.update(dict_to_save)
        print('new_config', self.config)
        with open(configFile,'w') as f:
             json.dump(self.config,f)

    def initUI(self):
        layout = QHBoxLayout()

        l1= QVBoxLayout()

        # restor_btn = QPushButton('Restore')
        # restor_btn.clicked.connect(self.restore)
        # l1.addWidget(restor_btn)
        l11 = QHBoxLayout()
        l11.addWidget(QLabel('f0, Hz'))
        l11.addStretch(1)
        self.f0_label = QLabel('%.3f'%self.f0)
        l11.addWidget(self.f0_label)
        l1.addLayout(l11)

        l12 = QHBoxLayout()
        l12.addWidget(QLabel('df/dt, mHz/sec'))
        l12.addStretch(1)
        self.df_label = QLabel('%.2f'%self.df)
        l12.addWidget(self.df_label)
        l1.addLayout(l12)

        l13 = QHBoxLayout()
        l13.addWidget(QLabel('f now, Hz'))
        l13.addStretch(1)
        self.fnow_label = QLabel('%.3f'%self.fnow)
        l13.addWidget(self.fnow_label)
        l1.addLayout(l13)

        # l1.addWidget(QLabel('df/dt, mHz/sec'))
        # self.df = MyBox(valid=(-500,500,6))
        # self.df.setText(self.df)
        # self.df.textChanged.connect(self.changeFrequency)
        # # f_c_line.textEdited.connect(self.textEdited)
        # l1.addWidget(self.df)

        # l1.addWidget(QLabel('Amp, dBm'))
        # self.amp_line = MyBox(valid=(-40,7,6))
        # self.amp_line.setText(self.ampl)
        # self.amp_line.textChanged.connect(self.changeAmplitude)
        # # f_c_line.textEdited.connect(self.textEdited)
        # l1.addWidget(self.amp_line)

        self.start_btn = QPushButton('Start correction')
        self.start_btn.clicked.connect(self.startBtnPressed)
        l1.addWidget(self.start_btn)
        layout.addLayout(l1)

        layout.addWidget(self.srs.BasicWidget(data=self.srs, parent=self,connect=True))

        self.setLayout(layout)

    def startBtnPressed(self):
        if self.correctionOn:
            reply = QMessageBox.question(self, 'Message',
                                         'Stop ULE drif correction?', QMessageBox.Yes, QMessageBox.No)

            if reply == QMessageBox.Yes:
                self.correctionOn = False
                self.start_btn.setStyleSheet("QWidget { background-color: %s }" % 'yellow')
                self.start_btn.setText('Start correction')
                self.timer.stop()
                self.fnow = self.f0
                self.fnow_label.setText('%.3f' % self.fnow)
                print('Correction stoped')
                return
        else:
            self.correctionOn = True
            self.start_btn.setStyleSheet("QWidget { background-color: %s }" % 'green')
            self.start_btn.setText('Stop correction')
            self.timer.start()
            print('Correction started')
            return

    def routine(self):
        print('routine_start')
        if not self.correctionOn:
            self.timer.stop()
            self.start_btn.setStyleSheet("QWidget { background-color: %s }" % 'blue')
            return
        self.t = datetime.now()
        self.fnow = self.f0 + (self.t.timestamp() - self.t0.timestamp()) * self.df * 1e-3
        self.fnow_label.setText('%.3f'%self.fnow)
        print(self.fnow)
        status,readout = self.srs.setFreq(self.fnow)
        print('after')
        if not status:
            self.correctionOn = False
            self.start_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')
            self.start_btn.setText('Start correction')
            self.timer.stop()
            self.fnow = self.f0
            self.fnow_label.setText('%.3f' % self.fnow)
            print('Correction failed')
            return
    # def changeFrequency(self):
    #     print('changeFrequency')
    #     try:
    #         freq = (float(self.f_o_line.text()) + float(self.f_c_line.text()))/1e3
    #         print(freq)
    #         if 1<freq<500:
    #             self.srs.setFreq(freq)
    #     except ValueError:
    #         print('Frequency input is not a float')

    # def changeAmplitude(self):
    #     print('changeAmplitude')
    #     try:
    #         ampl = float(self.amp_line.text())
    #         self.amp_line.setText(str(ampl))
    #         print(ampl)
    #         self.srs.setAmpl(ampl)
    #     except ValueError:
    #         print('Amplitude input is not a float')

    # def restore(self):
    #     status, freq = self.srs.getFreq()
    #     freq = round((float(freq.strip().strip('0'))*1e3),3)
    #     self.f_c_line.setText(str(freq))
    #     self.f_o_line.setText('0.0')
    #     status, ampl = self.srs.getAmpl()
    #     self.amp_line.setText(ampl.strip())
    #
    # def sendScanParams(self):
    #     params = ['freq_center','freq_offset','ampl']
    #     if self.globals != None:
    #         if scan_params_str not in self.globals:
    #             self.globals[scan_params_str] = {}
    #         self.globals[scan_params_str][name_in_scan_params] = params
    #     return

    # def getUpdateMethod(self):
    #     return self.updateFromScanner

    # def updateFromScanner(self, param_dict=None):
    #     # self.scanner = True
    #     print('Here')
    #     try:
    #         for param, val in param_dict.items():
    #             param = param[0]
    #             print(param,val)
    #             if param == 'freq_center':
    #                 self.f_c_line.setText(str(val))
    #                 self.changeFrequency()
    #             elif param == 'freq_offset':
    #                 self.f_o_line.setText(str(val))
    #                 self.changeFrequency()
    #             elif param == 'ampl':
    #                 self.amp_line.setText(str(val))
    #                 self.changeAmplitude()
    #     except Exception as e:
    #         print("can't change from scanner: ", e)
    #         return -1
    #     return 0

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    mainWindow = SRSGenerator()
    mainWindow.show()
    sys.exit(app.exec_())
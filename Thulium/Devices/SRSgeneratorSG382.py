try:
    from .device_lib import COMPortDevice
except:
    from device_lib import COMPortDevice
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

scan_params_str = 'scan_params'
name_in_scan_params = 'ClockGenerator'

class SRS(COMPortDevice):
    identification_names = ['Stanford Research Systems', 'SG382','s/n001915']
    timeout = 0.1
    def preCheck(self,port=None):
        if port:
            return (port.manufacturer == 'Prolific')
        else:
            for port in list(list_ports.comports()):
                if port.manufacturer == 'Prolific':
                    self.port = port.device

    def setFreq(self,freq):
        status,readout = self.write_read_com(b'FREQ %f MHz\r' %(freq))
        print(status, readout)

    def setAmpl(self,ampl):
        status,readout = self.write_read_com(b'AMPR %f\r' %(ampl))
        print(status, readout)

    def getFreq(self):
        return self.write_read_com(b'FREQ? MHz\r')

    def getAmpl(self):
        return self.write_read_com(b'AMPR?\r')

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
        self.srs = SRS()
        self.freq_center = '417.2'
        self.freq_offset = '0.0'
        self.ampl = '0.0'
        self.parent = parent
        super().__init__()
        self.setWindowTitle('SRS SG382')
        self.initUI()
        self.sendScanParams()

    def initUI(self):
        layout = QHBoxLayout()

        l1= QVBoxLayout()

        restor_btn = QPushButton('Restore')
        restor_btn.clicked.connect(self.restore)
        l1.addWidget(restor_btn)

        l1.addWidget(QLabel('Center freq, kHz'))
        self.f_c_line = MyBox(valid=(0,500000,8))
        self.f_c_line.setText(self.freq_center)
        self.f_c_line.textChanged.connect(self.changeFrequency)
        # f_c_line.textEdited.connect(self.textEdited)
        l1.addWidget(self.f_c_line)

        l1.addWidget(QLabel('Offset freq, kHz'))
        self.f_o_line = MyBox(valid=(-500,500,6))
        self.f_o_line.setText(self.freq_offset)
        self.f_o_line.textChanged.connect(self.changeFrequency)
        # f_c_line.textEdited.connect(self.textEdited)
        l1.addWidget(self.f_o_line)

        l1.addWidget(QLabel('Amp, dBm'))
        self.amp_line = MyBox(valid=(-40,7,6))
        self.amp_line.setText(self.ampl)
        self.amp_line.textChanged.connect(self.changeAmplitude)
        # f_c_line.textEdited.connect(self.textEdited)
        l1.addWidget(self.amp_line)
        layout.addLayout(l1)

        layout.addWidget(self.srs.BasicWidget(data=self.srs, parent=self))

        self.setLayout(layout)

    def changeFrequency(self):
        print('changeFrequency')
        try:
            freq = (float(self.f_o_line.text()) + float(self.f_c_line.text()))/1e3
            print(freq)
            self.srs.setFreq(freq)
        except ValueError:
            print('Frequency input is not a float')

    def changeAmplitude(self):
        print('changeAmplitude')
        try:
            ampl = float(self.amp_line.text())
            self.amp_line.setText(str(ampl))
            print(ampl)
            self.srs.setAmpl(ampl)
        except ValueError:
            print('Amplitude input is not a float')

    def restore(self):
        status, freq = self.srs.getFreq()
        freq = round((float(freq.strip().strip('0'))*1e3),3)
        self.f_c_line.setText(str(freq))
        self.f_o_line.setText('0.0')
        status, ampl = self.srs.getAmpl()
        self.amp_line.setText(ampl.strip())

    def sendScanParams(self):
        params = ['freq_center','freq_offset','ampl']
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
                if param == 'freq_center':
                    self.f_c_line.setText(str(val))
                    self.changeFrequency()
                elif param == 'freq_offset':
                    self.f_o_line.setText(str(val))
                    self.changeFrequency()
                elif param == 'ampl':
                    self.amp_line.setText(str(val))
                    self.changeAmplitude()
        except Exception as e:
            print("can't change from scanner: ", e)
            return -1
        return 0

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    mainWindow = SRSGenerator()
    mainWindow.show()
    sys.exit(app.exec_())
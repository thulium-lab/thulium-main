import os, json, ctypes, sys, inspect
import pyqtgraph as pg
import numpy as np
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(os.path.dirname(currentdir))
sys.path.insert(0,parentdir)

try:
    from .device_lib import COMPortDevice
except:
    from device_lib import COMPortDevice

from PyQt5.QtCore import (QTimer, pyqtSignal, Qt,)
from PyQt5.QtGui import (QColor, QFont, QIcon,QDoubleValidator)
from PyQt5.QtWidgets import (QApplication, QMenu, QColorDialog, QGridLayout, QVBoxLayout, QHBoxLayout, QDialog, QLabel,
                             QLineEdit, QPushButton, QWidget, QRadioButton, QSpinBox, QCheckBox, QButtonGroup,
                             QErrorMessage,QDoubleSpinBox)
import datetime
import socket
HOST, PORT = "192.168.1.59", 9999
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(0.01)

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


class OutputPlotWindow(pg.GraphicsWindow):
    """Widget for displaying srs output and sacher piezo voltage"""
    def __init__(self):
        super().__init__()
        self.error_plot = self.addPlot()
        self.error_plot.showGrid(x=True,y=True,alpha=0.5)
        self.error_curve = self.error_plot.plot()
        self.error_lower_threshold = self.error_plot.addLine(y=-1)
        self.error_upper_threshold = self.error_plot.addLine(y=1)
        self.nextRow()
        self.voltage_plot = self.addPlot()
        self.voltage_plot.showGrid(x=True, y=True, alpha=0.5)
        self.voltage_curve = self.voltage_plot.plot()

class Lock402(QWidget):
    config_file = 'lock402.json'
    channel = '402nm'
    frequency = 745061690.0 # MHz
    threshold = 3 # MHz
    gain = 1.0  # mV/MHz
    output_voltage = 2.5 # V
    initial_voltage = 2.5 # V
    correction_limit = 2.5 # V
    max_dead_time = 5 # seconds, dunlocks if readings from WM are old
    timer_interval = 100 # ms
    K_neg = 1#PID
    K_p = 0#PID
    K_i = 0#PID
    K_d = 0#PID
    P = 0 #PID
    I = 0 #PID
    D = 0 #PID
    error2 = 0#PID
    config = {}

    def __init__(self):
        super().__init__()
        self.load()
        self.arduino = COMPortDevice(default_port='COM4')
        self.setWindowTitle('402 nm Laser Lock')
        # self.setWindowIcon(QIcon('maxresdefault.jpg'))  # circle_blue.ico
        self.initUI()
        self.arduino.write_com(('V %.2f!' % (self.initial_voltage)).encode())
        self.lock = False

        self.timer = QTimer()
        self.timer.setInterval(self.timer_interval)
        self.timer.timeout.connect(self.routine)

    def load(self):
        try:
            with open(self.config_file,'r') as f:
                self.config = json.load(f)
        except json.decoder.JSONDecodeError:
            print('ERROR in reading ', self.config_file)
        self.__dict__.update(self.config)

    def save(self,dict_to_save):
        print("Save")
        self.config.update(dict_to_save)
        print('new_config', self.config)
        with open(self.config_file,'w') as f:
             json.dump(self.config,f)

    def initUI(self):
        main_layout = QHBoxLayout()
        self.output_plots = OutputPlotWindow()
        self.output_plots.error_lower_threshold.setValue(-self.threshold)
        self.output_plots.error_upper_threshold.setValue(self.threshold)
        main_layout.addWidget(self.output_plots)



        lock_menu = QVBoxLayout()

        lock_menu.addWidget(QLabel('Timer interval, ms'))
        self.timer_line = QSpinBox()
        self.timer_line.setRange(10,9999)
        self.timer_line.setSingleStep(100)
        self.timer_line.setValue(self.timer_interval)
        self.timer_line.valueChanged[int].connect(self.timerChanged)
        lock_menu.addWidget(self.timer_line)

        lock_menu.addWidget(QLabel('Channel'))
        self.channel_line = QLineEdit()
        self.channel_line.setText(self.channel)
        self.channel_line.textEdited[str].connect(self.channelChanged)
        lock_menu.addWidget(self.channel_line)

        lock_menu.addWidget(QLabel('Frequency, MHz'))
        self.frequency_line = QDoubleSpinBox()
        self.frequency_line.setDecimals(1)
        self.frequency_line.setRange(0,999999999)
        self.frequency_line.setSingleStep(1)
        self.frequency_line.setValue(self.frequency)
        self.frequency_line.valueChanged[float].connect(self.frequencyChanged)
        lock_menu.addWidget(self.frequency_line)

        lock_menu.addWidget(QLabel('Threshold, MHz'))
        self.threshold_line = QDoubleSpinBox()
        self.threshold_line.setDecimals(1)
        self.threshold_line.setRange(0,999)
        self.threshold_line.setSingleStep(1)
        self.threshold_line.setValue(self.threshold)
        self.threshold_line.valueChanged[float].connect(self.thresholdChanged)
        lock_menu.addWidget(self.threshold_line)

        lock_menu.addWidget(QLabel('Gain, mV/MHz'))
        self.gain_line = QDoubleSpinBox()
        self.gain_line.setDecimals(2)
        self.gain_line.setRange(-999, 999)
        self.gain_line.setSingleStep(1)
        self.gain_line.setValue(self.gain)
        self.gain_line.valueChanged[float].connect(self.gainChanged)
        lock_menu.addWidget(self.gain_line)

        lock_menu.addWidget(QLabel('K_p'))
        self.K_p_line = QDoubleSpinBox()
        self.K_p_line.setDecimals(3)
        self.K_p_line.setRange(-99999, 99999)
        self.K_p_line.setSingleStep(0.01)
        self.K_p_line.setValue(self.K_p)
        self.K_p_line.valueChanged[float].connect(self.K_pChanged)
        lock_menu.addWidget(self.K_p_line)

        lock_menu.addWidget(QLabel('K_i'))
        self.K_i_line = QDoubleSpinBox()
        self.K_i_line.setDecimals(3)
        self.K_i_line.setRange(-99999, 99999)
        self.K_i_line.setSingleStep(0.01)
        self.K_i_line.setValue(self.K_i)
        self.K_i_line.valueChanged[float].connect(self.K_iChanged)
        lock_menu.addWidget(self.K_i_line)

        lock_menu.addWidget(QLabel('K_d'))
        self.K_d_line = QDoubleSpinBox()
        self.K_d_line.setDecimals(3)
        self.K_d_line.setRange(-99999, 99999)
        self.K_d_line.setSingleStep(0.01)
        self.K_d_line.setValue(self.K_d)
        self.K_d_line.valueChanged[float].connect(self.K_dChanged)
        lock_menu.addWidget(self.K_d_line)

        lock_menu.addWidget(QLabel('K_neg'))
        self.K_neg_line = QDoubleSpinBox()
        self.K_neg_line.setDecimals(2)
        self.K_neg_line.setRange(-99999, 99999)
        self.K_neg_line.setSingleStep(1)
        self.K_neg_line.setValue(self.K_neg)
        self.K_neg_line.valueChanged[float].connect(self.K_negChanged)
        lock_menu.addWidget(self.K_neg_line)

        lock_menu.addWidget(QLabel('Initial voltage, V'))
        self.initial_voltage_line = QDoubleSpinBox()
        self.initial_voltage_line.setDecimals(3)
        self.initial_voltage_line.setRange(0, 5)
        self.initial_voltage_line.setSingleStep(.01)
        self.initial_voltage_line.setValue(self.initial_voltage)
        self.initial_voltage_line.valueChanged[float].connect(self.initialVoltageChanged)
        lock_menu.addWidget(self.initial_voltage_line)

        lock_menu.addWidget(QLabel('Correction limit, V'))
        self.correction_limit_line = QDoubleSpinBox()
        self.correction_limit_line.setDecimals(3)
        self.correction_limit_line.setRange(0, 5)
        self.correction_limit_line.setSingleStep(.01)
        self.correction_limit_line.setValue(self.correction_limit)
        self.correction_limit_line.valueChanged[float].connect(self.correctionLimitChanged)
        lock_menu.addWidget(self.correction_limit_line)

        lock_menu.addWidget(QLabel('Current change'))
        self.current_change_lbl = QLabel()
        lock_menu.addWidget(self.current_change_lbl)

        self.lock_btn = QPushButton('Lock')
        self.lock_btn.pressed.connect(self.lockBtnPressed)
        lock_menu.addWidget(self.lock_btn)

        lock_menu.addStretch(1)

        main_layout.addLayout(lock_menu)

        main_layout.addWidget(self.arduino.BasicWidget(data=self.arduino))
        self.setLayout(main_layout)

    def timerChanged(self,new_val):
        print('timerIntervalChanged')
        self.timer_interval = new_val
        self.timer.setInterval(self.timer_interval)
        self.save({'timer_interval': new_val})

    def channelChanged(self,channel):
        print('ChannelChanged')
        self.channel = channel
        self.save({'channel':channel})

    def frequencyChanged(self,new_val):
        print('frequencyChanged')
        self.frequency = new_val
        self.save({'frequency':new_val})

    def thresholdChanged(self,new_val):
        print('thresholdChanged')
        self.threshold = new_val
        self.output_plots.error_lower_threshold.setValue(-self.threshold)
        self.output_plots.error_upper_threshold.setValue(self.threshold)
        self.save({'threshold': new_val})

    def gainChanged(self,new_val):
        print('gainChanged')
        self.gain = new_val
        self.save({'gain': new_val})

    def K_pChanged(self,new_val):
        print('K_pChanged')
        self.K_p = new_val
        self.save({'K_p': new_val})

    def K_iChanged(self,new_val):
        print('K_iChanged')
        self.K_i = new_val
        self.save({'K_i': new_val})

    def K_dChanged(self,new_val):
        print('K_dChanged')
        self.K_d = new_val
        self.save({'K_d': new_val})

    def K_negChanged(self,new_val):
        print('K_negChanged')
        self.K_neg = new_val
        self.save({'K_neg': new_val})

    def initialVoltageChanged(self,new_val):
        print('initialVoltageChanged')
        self.initial_voltage = new_val
        self.save({'initial_voltage': new_val})

    def correctionLimitChanged(self, new_val):
        print('correctionLimitChanged')
        self.correction_limit = new_val
        self.save({'correction_limit': new_val})

    def lockBtnPressed(self):
        print('connectBtnPressed')
        #  Starting parametres for PID
        #print('p =', self.P, 'i =', self.I, 'd =', self.D)
        self.P = 0
        self.I = 0
        self.D = 0
        #print('p =', self.P, 'i =', self.I, 'd =', self.D)
        if self.lock:
            self.lock = False
            self.timer.stop()
            self.current_change_lbl.setText('')
            self.lock_btn.setStyleSheet("QWidget { background-color: %s }" % 'grey')
        else:
            self.lock_btn.setStyleSheet("QWidget { background-color: %s }" % 'green')
            self.last_time = datetime.datetime.now().timestamp()
            self.output_voltage = self.initial_voltage
            self.error_log = []
            self.voltage_log = []
            self.lock=True
            self.timer.start()

    def unlock(self,msg):
        self.lock = False
        self.timer.stop()
        self.current_change_lbl.setText(msg)
        self.lock_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')
        self.arduino.write_com(('V %.2f!' % (self.initial_voltage)).encode())


    def routine(self):
        msg = 'LOCK_BY_WM %s\n'%(self.channel)
        sock.sendto(bytes(msg, "utf-8"), (HOST, PORT))
        try:
            received = str(sock.recv(1024), "utf-8")
        except Exception as e:
            print(e)
            return
        # print("Received: {}".format(received))
        received = received.strip().split()
        if len(received) != 2:
            self.unlock('No channel')
            return
        meas_time = float(received[0])
        frequency = float(received[1])*1e6
        #print ('402:',frequency)
        # msg = 'LOCK_BY_WM Green\n'
        # sock.sendto(bytes(msg, "utf-8"), (HOST, PORT))
        # received_green = str(sock.recv(1024), "utf-8")
        # received_green = received_green.strip().split()
        # frequency_green = float(received_green[1]) * 1e6
        # #print("Green: ", frequency_green )
        # msg = 'LOCK_BY_WM GreenX2\n'
        # sock.sendto(bytes(msg, "utf-8"), (HOST, PORT))
        # received_greenX2 = str(sock.recv(1024), "utf-8")
        # received_greenX2 = received_greenX2.strip().split()
        # frequency_greenX2 = float(received_greenX2[1]) * 1e6
        # #print("GreenX2: ", frequency_greenX2)
        # msg = 'LOCK_BY_WM Clock\n'
        # sock.sendto(bytes(msg, "utf-8"), (HOST, PORT))
        # received_clock = str(sock.recv(1024), "utf-8")
        # received_clock = received_clock.strip().split()
        # frequency_clock = float(received_clock[1]) * 1e6
        #print("clock: ", frequency_clock)

        #print(datetime.datetime.now().timestamp(),meas_time,frequency)
        if datetime.datetime.now().timestamp() - meas_time > self.max_dead_time or frequency < 0:
            self.unlock('Bad meas')
            return
        # if frequency_green > 0 and frequency_greenX2 > 0 and frequency_clock > 0:
        #     error = self.frequency - (frequency - (2 * frequency_green - frequency_greenX2)) * (262954938.0 + 2 * 426.7607) / (frequency_clock - (2 * frequency_green - frequency_greenX2) )
        # else:
        #     error = self.frequency - (frequency - (2 * 282365275.4 - 564730545.3000001)) * (262954938.0 + 2 * 426.7607) / (262955790.20000002 - (2 * 282365275.4 - 564730545.3000001) )
        #print ('error =', error)
        error = self.frequency - frequency
        #print('error',error)
        self.error_log.append(error)
        self.output_plots.error_curve.setData(self.error_log)
        if error > self.threshold and abs(error - self.error2) < 100000:
            self.P = self.gain*error*1e-3
            self.I += self.K_i * self.gain*error*1e-3
            self.D = self.gain * (error - self.error2) / 1000
            self.error2 = error

            #print ("P = ", self.P, "I = ", self.I, "D = ", self.D)
            self.output_voltage = self.initial_voltage + self.K_p * self.P + self.I + self.K_d * self.D #self.gain*error*1e-3
            if abs(self.output_voltage - self.initial_voltage) > 0.5*self.correction_limit:
                self.lock_btn.setStyleSheet("QWidget { background-color: %s }" % 'yellow')
            if abs(self.output_voltage - self.initial_voltage) > 1*self.correction_limit:
                self.unlock('Limit reached')
                return
            #print(self.output_voltage)
            if not self.arduino.connected:
                self.unlock('Bad arduino')
                return
            self.arduino.write_com(('V %.2f!'%(self.output_voltage)).encode())
            # print('Here')
            self.current_change_lbl.setText('%.3f'%(self.output_voltage))
        if error < - self.threshold and abs(error - self.error2) < 100000:
            self.P = self.gain*error*1e-3
            self.I +=  self.K_i *self.gain*error*1e-3
            self.D = self.gain * (error - self.error2) / 1000
            self.error2 = error

            #print ("P = ", self.P, "I = ", self.I, "D = ", self.D)
            self.output_voltage = self.initial_voltage + self.I + self.K_neg*(self.K_p * self.P  + self.K_d * self.D) #self.gain*error*1e-3
            if abs(self.output_voltage - self.initial_voltage) > 0.5*self.correction_limit:
                self.lock_btn.setStyleSheet("QWidget { background-color: %s }" % 'yellow')
            if abs(self.output_voltage - self.initial_voltage) > 1*self.correction_limit:
                self.unlock('Limit reached')
                return
            #print(self.output_voltage)
            if not self.arduino.connected:
                self.unlock('Bad arduino')
                return
            self.arduino.write_com(('V %.2f!'%(self.output_voltage)).encode())
            # print('Here')
            self.current_change_lbl.setText('%.3f'%(self.output_voltage))


        # self.current_change_lbl.setText('%.3f' % (self.output_voltage))
        #end of try

        self.voltage_log.append(self.output_voltage)
        self.output_plots.voltage_curve.setData(self.voltage_log)
        # print('finished')


        # print(self.error_log,self.voltage_log)



if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    mainWindow = Lock402()
    mainWindow.show()
    sys.exit(app.exec_())
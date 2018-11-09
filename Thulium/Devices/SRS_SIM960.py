try:
    from .device_lib import COMPortDevice, MyBox
except:
    from device_lib import COMPortDevice, MyBox
import matplotlib, time
import numpy as np
import json
# Make sure that we are using QT5
matplotlib.use('Qt5Agg')
from PyQt5.QtCore import ( QTimer)
from PyQt5.QtGui import (QIcon)
from PyQt5.QtWidgets import (QWidget,QMessageBox, QDoubleSpinBox)
from PyQt5.QtWidgets import (QApplication, QVBoxLayout, QHBoxLayout,QLabel, QLineEdit, QPushButton,QGridLayout, QCheckBox)

from numpy import sign

import pyqtgraph as pg

import datetime
from pymongo import MongoClient

import ctypes
myappid = u'LPI.BlueZalseLock' # arbitrary string
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)



class SRS(COMPortDevice):
    identification_names = ['Stanford_Research_Systems', 'SIM960','s/n016480']
    check_answer = 'Prolific'

    # def preCheck(self):
    #     for port in list(list_ports.comports()):
    #         if port.manufacturer == 'Prolific':
    #             self.port = port.device

    def readOutput(self):
        """Reads SRS output voltage in mVolts"""
        status, readout = self.write_read_com(b'OMON?\r')
        if not status:
            return False,0
        try:
            output = float(readout)
        except ValueError as e:
            print("Can't convert %s in readOutput to float" %readout)
            return False,0
        return True,output

    def isLockOn(self):
        """Checks if SRS is locked"""
        status, readout = self.write_read_com(b'AMAN?\r')
        if not status:
            return False, 0
        try: # somewhy here were errors - now do it with try
            output = int(readout)
        except ValueError as e:
            print("Can't convert %s in isLockOn to int" %readout)
            return False,0
        return True,output

    def turnLockOff(self):
        """Turns SRS lock off"""
        return self.write_read_com(b'AMAN 0\r')

    def turnLockOn(self):
        """Turns SRS lock on"""
        return self.write_read_com(b'AMAN 1\r')

    def readINSR(self):
        """Read SRS  Instrument Status (INSR) register"""
        status, readout = self.write_read_com(b'INSR?\r')
        if not status:
            return False, 0
        try:
            output = int(readout)
        except ValueError as e:
            print("Can't convert %s in readINSR to int" %readout)
            return False,0
        return True,output

    def clearINSR(self):
        """Clears SRS  Instrument Status (INSR) register (usually needed befor new lock"""
        for i in range(3):
            # print(self.write_read_com(b'INSR? %i\r' % (i)))
            self.write_read_com(b'INSR? %i\r' % (i))



class SRS_SIM960(QWidget):
    config_file = 'SRS_SIM960_config.json'
    def __init__(self):
        super().__init__()
        self.srs = SRS(default_port='COM9')
        self.p_current = 0.3
        self.p_half = 0.2
        self.i_current = 1.6e5
        self.i_half = 1.6e5
        self.d_current = 1.6e-4
        self.d_half = 1.6e-4
        self.sp = 0.5
        self.sp_start = 0.2
        self.spr_on = False
        self.spr = 1
        self.lock_on = False
        self.srs_insr_error_counter=0
        self.srs_insr_error_counter_threshold = 10
        self.attemps_to_relock = 0
        self.attemps_to_relock_threshold = 10
        self.config={}
        self.load()
        self.initUI()

        self.timer = QTimer()
        self.timer.setInterval(30)
        self.timer.timeout.connect(self.routine)
        self.timer.start()

        self.timerToStartRelocking = QTimer()
        self.timerToStartRelocking.setInterval(2000)
        self.timerToStartRelocking.timeout.connect(self.startMainTimer)

    def initUI(self):
        main_layout = QVBoxLayout()

        self.srsBaiscWidget = self.srs.BasicWidget(data=self.srs, parent=self, connect=True)
        main_layout.addWidget(self.srsBaiscWidget)

        layout1 = QHBoxLayout()
        self.restore_btn = QPushButton('Restore')
        self.restore_btn.pressed.connect(self.restoreBtnPressed)
        layout1.addWidget(self.restore_btn)
        self.load_to_btn = QPushButton('load to 1/2')
        self.load_to_btn.pressed.connect(self.loadToBtnPressed)
        layout1.addWidget(self.load_to_btn)
        self.load_to_srs_btn = QPushButton('load 1/2 to SRS')
        self.load_to_srs_btn.pressed.connect(self.loadToSRSPressed)
        layout1.addWidget(self.load_to_srs_btn)
        main_layout.addLayout(layout1)

        self.grid_layout = QGridLayout()
        self.grid_layout.addWidget(QLabel('Current'),0,1)
        self.grid_layout.addWidget(QLabel('at 1/2'),0,2)
        self.grid_layout.addWidget(QLabel('at start'), 0, 5)


        self.grid_layout.addWidget(QLabel('P'),1,0)
        self.p_current_line = MyBox(valid = (-1e3,1e3,7),value=self.p_current)
        self.p_current_line.textChanged.connect(self.pChanged)
        self.grid_layout.addWidget(self.p_current_line,1,1)
        self.p_half_line = MyBox(valid=(-1e3, 1e3, 7), value=self.p_half)
        self.p_half_line.textChanged.connect(self.pHalfChanged)#lambda text: self.__dict__.update({'p_half': float(text)}))
        self.grid_layout.addWidget(self.p_half_line, 1, 2)

        self.grid_layout.addWidget(QLabel('I'), 2, 0)
        self.i_current_line = MyBox(valid=(1e-2, 5e5, 7), value=self.i_current)
        self.i_current_line.textChanged.connect(self.iChanged)
        self.grid_layout.addWidget(self.i_current_line, 2, 1)
        self.i_half_line = MyBox(valid=(1e-2, 5e5, 7), value=self.i_half)
        self.i_half_line.textChanged.connect(self.iHalfChanged)#lambda text: self.__dict__.update({'i_half': float(text)}))
        self.grid_layout.addWidget(self.i_half_line, 2, 2)


        self.grid_layout.addWidget(QLabel('D'), 3, 0)
        self.d_current_line = MyBox(valid=(1e-6, 1e1, 7), value=self.d_current)
        self.d_current_line.textChanged.connect(self.dChanged)
        self.grid_layout.addWidget(self.d_current_line, 3, 1)
        self.d_half_line = MyBox(valid=(1e-6, 1e1, 7), value=self.d_half)
        self.d_half_line.textChanged.connect(self.dHalfChanged)#lambda text: self.__dict__.update({'d_half': float(text)}))
        self.grid_layout.addWidget(self.d_half_line, 3, 2)

        self.grid_layout.addWidget(QLabel('SP'), 1, 3)
        self.sp_line = MyBox(valid=(0, 1e1, 7), value=self.sp)
        self.sp_line.textChanged.connect(self.spChanged)
        self.grid_layout.addWidget(self.sp_line, 1, 4)

        self.grid_layout.addWidget(QLabel('SPR ON'), 2, 3)
        self.spr_on_box = QCheckBox()
        self.spr_on_box.setCheckState(self.spr_on)
        self.spr_on_box.stateChanged.connect(self.sprOnChanged)
        self.grid_layout.addWidget(self.spr_on_box, 2, 4)

        self.grid_layout.addWidget(QLabel('SPR'), 3, 3)
        self.spr_line = MyBox(valid=(1e-3, 1e4, 7), value=self.spr)
        self.spr_line.textChanged.connect(self.sprChanged)
        self.grid_layout.addWidget(self.spr_line, 3, 4)

        self.sp_start_line = MyBox(valid=(0, 1e1, 7), value=self.sp_start)
        self.sp_start_line.textChanged.connect(self.spStartChanged)#lambda text: self.__dict__.update({'sp_start': float(text)}))
        self.grid_layout.addWidget(self.sp_start_line, 1, 5)

        self.lock_btn = QPushButton('Lock')
        self.lock_btn.pressed.connect(self.lockPressed)
        self.grid_layout.addWidget(self.lock_btn, 3,5)

        self.insr_lbl = QLabel('000')
        self.grid_layout.addWidget(self.insr_lbl,1,6)

        main_layout.addLayout(self.grid_layout)
        self.setLayout(main_layout)

    def load(self):
        try:
            with open(self.config_file,'r') as f:
                self.config = json.load(f)
        except json.decoder.JSONDecodeError:
            print('ERROR in reading ', self.blue_lock_config_file)
            return
        except FileNotFoundError:
            return
        self.__dict__.update(self.config)

    def save_config(self):
        print('save_config')
        try:
            with open(self.config_file, 'r') as f:
                old_config = json.load(f)
        except (json.decoder.JSONDecodeError,FileNotFoundError):
            old_config = {}
        with open(self.config_file, 'w') as f:
            try:
                json.dump(self.config,f)
            except: # find what error does it raise when cannot dump
                json.dump(old_config, f)
                QMessageBox.warning(None, 'Message', "can not dump config to json, old version will be saved",
                                    QMessageBox.Ok)

    def startMainTimer(self):
        self.timerToStartRelocking.stop()
        self.timer.start()

    def loadToBtnPressed(self):
        self.p_half = self.p_current
        self.p_half_line.setValue(self.p_half)
        self.i_half = self.i_current
        self.i_half_line.setValue(self.i_half)
        self.d_half = self.d_current
        self.d_half_line.setValue(self.d_half)

    def restoreBtnPressed(self):
        print("Restor values from srs")
        try:
            s,v = self.srs.write_read_com(b'GAIN? \r')
            self.p_current = float(v)
            self.p_current_line.setValue(self.p_current)
            s, v = self.srs.write_read_com(b'INTG? \r')
            self.i_current = float(v)
            self.i_current_line.setValue(self.i_current)
            s, v = self.srs.write_read_com(b'DERV? \r')
            self.d_current = float(v)
            self.d_current_line.setValue(self.d_current)
            s, v = self.srs.write_read_com(b'RAMP? \r')
            self.spr_on = int(v)*2
            self.spr_on_box.setCheckState(self.spr_on)
            s, v = self.srs.write_read_com(b'SETP? \r')
            self.sp = float(v)
            self.sp_line.setCheckState(self.sp)
            s, v = self.srs.write_read_com(b'RATE? \r')
            self.spr = float(v)
            self.spr_line.setCheckState(self.spr)
            s, v = self.srs.write_read_com(b'AMAN? \r')
            self.lock_on = bool(int(v))
            if self.lock_on:
                self.lock_btn.setStyleSheet("QWidget { background-color: %s }" % 'green')
            else:
                self.lock_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')
        except Exception as e:
            print('AHTING')
            print(e)

    def loadToSRSPressed(self):
        print('Load 1/2 parameters to SRS without changing current values')
        self.srs.write_com(b'GAIM ' + ('%.1e' % self.p_half).encode() + b'\r')
        self.srs.write_com(b'INTG ' + ('%.1e' % self.i_half).encode() + b'\r')
        self.srs.write_com(b'DERV ' + ('%.1e' % self.d_half).encode() + b'\r')
        self.srs.write_com(b'SETP ' + ('%.3e' % self.sp).encode() + b'\r')
        self.srs.write_com(b'RATE ' + ('%.1e' % self.spr).encode() + b'\r')
        self.srs.write_com(b'RAMP ' + ('%i' % int(self.spr_on /2)).encode() + b'\r')

    def pChanged(self,new_text):
        value = float(new_text)
        if  value == 0:
            print('P can not be 0')
            self.p_current_line.setValue(self.p_current)
            return
        if value*self.p_current < 0:
            self.srs.write_com(b'APOL ' + (b'1' if value>0 else b'0') + b'\r')
        self.srs.write_com(b'GAIN ' + ('%.1e'%value).encode() + b'\r')
        self.p_current = value
        # print(new_text)

    def pHalfChanged(self, new_text):
        value = float(new_text)
        if value == 0:
            print('P can not be 0')
            self.p_half_line.setValue(self.p_half)
            return
        self.p_half = value
        self.config['p_half'] = value
        self.save_config()

    def iChanged(self,new_text):
        value = float(new_text)
        self.srs.write_com(b'INTG ' + ('%.1e' % value).encode() + b'\r')
        self.i_current = value

    def iHalfChanged(self,new_text):
        value = float(new_text)
        self.i_half = value
        self.config['i_half'] = value
        self.save_config()

    def dChanged(self,new_text):
        value = float(new_text)
        self.srs.write_com(b'DERV ' + ('%.1e' % value).encode() + b'\r')
        self.d_current = value

    def dHalfChanged(self,new_text):
        value = float(new_text)
        self.d_half = value
        self.config['d_half'] = value
        self.save_config()

    def spChanged(self,new_text):
        value = float(new_text)
        self.srs.write_com(b'SETP ' + ('%.3e' % value).encode() + b'\r')
        self.sp = value
        self.config['sp'] = value
        self.save_config()

    def spStartChanged(self,new_text):
        value = float(new_text)
        self.sp_start = value
        self.config['sp_start'] = value
        self.save_config()

    def sprChanged(self,new_text):
        value = float(new_text)
        self.srs.write_com(b'RATE ' + ('%.1e' % value).encode() + b'\r')
        self.spr = value
        self.config['spr'] = value
        self.save_config()

    def sprOnChanged(self,state):
        self.srs.write_com(b'RAMP ' + ('%i' % int(state/2)).encode() + b'\r')
        self.spr_on = int(state)
        self.config['spr_on'] = self.spr_on
        self.save_config()

    def lockPressed(self):
        print('lock Pressed')
        if self.lock_on:
            self.srs.write_read_com(b'AMAN 0\r')
            self.lock_on = False
            self.lock_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')
            self.insr_lbl.setText('000')
        else:
            self.attemps_to_relock = 0
            self.turnLockOn()


    def turnLockOn(self):
        self.timer.stop()
        # set parameters to start lock
        x_half = np.sqrt(np.log(1/0.5))
        time.sleep(0.01)
        for v in set(np.r_[np.arange(self.sp_start,self.sp,0.2),self.sp]):
            time.sleep(0.05)
            print(v)
            x = np.sqrt(np.log(1 / v))
            p = (x_half * np.exp(-x_half ** 2)) / (x * np.exp(-x ** 2)) * self.p_half
            i = (x_half * np.exp(-x_half ** 2)) / (x * np.exp(-x ** 2)) * self.i_half
            d = (x_half * np.exp(-x_half ** 2)) / (x * np.exp(-x ** 2)) * self.d_half
            if abs(p) < 0.1:
                p = sign(p) * 0.1
            self.srs.write_com(b'GAIN ' + ('%.1e' % p).encode() + b'\r')
            # self.srs.write_com(b'INTG ' + ('%.1e' % i).encode() + b'\r')
            # self.srs.write_com(b'DERV ' + ('%.1e' % d).encode() + b'\r')
            self.srs.write_com(b'SETP ' + ('%.3e' % v).encode() + b'\r')
            self.srs.write_com(b'AMAN 1\r')
        # self.srs.write_com(b'STRT 1\r')

        self.lock_on = True
        self.lock_btn.setStyleSheet("QWidget { background-color: %s }" % 'green')
        # time.sleep(100)
        self.timerToStartRelocking.start()

    def routine(self):
        if self.lock_on:
            status, readout = self.srs.write_read_com(b'INSR?\r')
            insr = int(readout)
            self.insr_lbl.setText("%i%i%i" % ((insr >> 0) % 2, (insr >> 1) % 2, (insr >> 2) % 2))
            status, readout = self.srs.write_read_com(b'OMON?\r')
            v_out = float(readout)
            if insr or v_out < 0.1 or v_out>9.9:# % 8 != 0:
                print('INSR',insr)
                self.insr_lbl.setStyleSheet("QWidget { background-color: %s }" % 'yellow')
                self.srs_insr_error_counter+=1
                if self.srs_insr_error_counter > self.srs_insr_error_counter_threshold:
                    self.attemps_to_relock +=1
                    if self.attemps_to_relock > self.attemps_to_relock_threshold:
                        self.insr_lbl.setStyleSheet("QWidget { background-color: %s }" % 'red')
                        self.insr_lbl.setText('000')
                        return
                    print('Relock attemp #',self.attemps_to_relock)
                    self.srs.write_read_com(b'AMAN 0\r')
                    self.insr_lbl.setStyleSheet("QWidget { background-color: %s }" % 'green')
                    self.insr_lbl.setText('000')
                    self.srs_insr_error_counter = 0
                    self.lock_on = False
                    self.turnLockOn()
            else:
                if self.attemps_to_relock > 0:
                    self.attemps_to_relock -= 1
                self.insr_lbl.setStyleSheet("QWidget { background-color: %s }" % 'green')
                self.insr_lbl.setText('000')

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    mainWindow = SRS_SIM960()
    # mainWindow = inst.Widget(data=inst)
    mainWindow.show()
    sys.exit(app.exec_())
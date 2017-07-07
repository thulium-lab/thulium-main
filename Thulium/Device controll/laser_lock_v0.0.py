import sys
import os
import random
import matplotlib
import numpy as np
import json
# Make sure that we are using QT5
matplotlib.use('Qt5Agg')
from PyQt5.QtCore import (QLineF, QPointF, QRectF, Qt, QTimer)
from PyQt5.QtGui import (QBrush, QColor, QPainter,QIcon)
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
from serial import Serial
from serial.tools import list_ports
from time import sleep
from serial.serialutil import SerialException
from numpy import sign
# from device_lib import COMPortDevice

import pyqtgraph as pg

import pymongo, datetime
from pymongo import MongoClient

import ctypes
myappid = u'LPI.BlueZalseLock' # arbitrary string
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

class BlueLock():
    available_com_ports = []
    com_ports_info= ''
    correction_limit = 0.1
    threshold_srs_error = 0.003
    maximum_srs_error = 0.03 # reaching this value srs will unlock
    # Flags
    srs_lock = False
    piezo_lock = False
    # output arrays
    srs_output  = None
    piezo_voltage = None
    blue_lock_config_file = 'blue_lock_config.json'
    config = {}
    # INSR error counter
    srs_insr_error_counter=0
    srs_insr_error_counter_threshold = 10

    def __init__(self):
        self.db = MongoClient('mongodb://192.168.1.15:27017/').measData.sacher_log
        self.load()
        self.updateCOMPortsInfo()
        self.srs = SRS()
        self.sacher = Sacher()

    def load(self):
        try:
            with open(self.blue_lock_config_file,'r') as f:
                self.config = json.load(f)
        except json.decoder.JSONDecodeError:
            print('ERROR in reading ', self.blue_lock_config_file)
        for key in self.config:
            self.__dict__[key] = self.config[key]

    def save_config(self):
        try:
            with open(self.blue_lock_config_file, 'r') as f:
                old_config = json.load(f)
        except json.decoder.JSONDecodeError:
            old_config = {}
        with open(self.blue_lock_config_file, 'w') as f:
            try:
                json.dump(self.config,f)
            except: # find what error does it raise when cannot dump
                json.dump(old_config, f)
                QMessageBox.warning(None, 'Message', "can not dump config to json, old version will be saved",
                                    QMessageBox.Ok)

    def updateCOMPortsInfo(self):
        self.available_com_ports = [port.device for port in list(list_ports.comports())]
        self.com_ports_info = '\n\n'.join(
            ['\n'.join([key + ':' + str(val) for key, val in p.__dict__.items()]) for p in list(list_ports.comports())])

    def readData(self, new=False):
        status, v1 = self.srs.readOutput()  # read output voltage of srs
        if not status:  # if there is a problem with reading return status false
            return False
        status, q1 = self.sacher.readPiezoVoltage()  # read piezo voltage of sacher
        if not status:  # if there is a problem with reading return status false
            return False
        if new:  # if lock is just turned on
            # create new data arrays
            self.srs_output = np.array([v1])
            self.piezo_voltage = np.array([q1])
        else:  # if not - update arrays
            self.srs_output = np.append(self.srs_output, v1)
            self.piezo_voltage = np.append(self.piezo_voltage, q1)
        return True  # return that readings are successfull

    def getDataToDB(self):
        return {'date': datetime.datetime.now(),
                'threshold_srs_error': self.threshold_srs_error,
                'correction_limit': self.correction_limit,
                'srs_output': list(self.srs_output),
                'piezo_voltage': list(self.piezo_voltage)
                }


    class Widget(QWidget):

        def __init__(self,parent=None,data=None):
            super().__init__()
            self.setWindowTitle('Blue Laser Lock')
            self.setWindowIcon(QIcon('maxresdefault.jpg')) #circle_blue.ico
            self.data = data
            self.parent = parent
            self.timer = QTimer()
            self.timer.setInterval(500)
            self.timer.timeout.connect(self.routine)
            self.initUI()

        def initUI(self):
            main_layout = QVBoxLayout()

            initialization_layout = QHBoxLayout()
            self.ports_info = QTextEdit()
            initialization_layout.addWidget(self.ports_info)

            info_layout = QVBoxLayout()
            info_btn = QPushButton('Update')
            info_btn.clicked.connect(self.updateBtnPressed)
            info_layout.addWidget(info_btn)

            info_layout.addWidget(QLabel('SRS'))
            self.srs_port_menu = QComboBox()
            self.srs_port_menu.currentTextChanged[str].connect(self.srsPortChanged)
            info_layout.addWidget(self.srs_port_menu)

            info_layout.addWidget(QLabel('Sacher'))
            self.sacher_port_menu = QComboBox()
            self.sacher_port_menu.currentTextChanged[str].connect(self.sacherPortChanged)
            info_layout.addWidget(self.sacher_port_menu)

            info_layout.addStretch(1)
            initialization_layout.addLayout(info_layout)

            connect_layout = QVBoxLayout()
            self.connect_btn = QPushButton('Connect')
            self.connect_btn.clicked.connect(self.connectBtnPressed)
            connect_layout.addWidget(self.connect_btn)
            connect_layout.addWidget(QLabel('SRS'))
            self.srs_connected_lbl = QLabel('Off')
            self.srs_connected_lbl.setStyleSheet("QWidget { background-color: %s }"% 'red')
            self.srs_connected_lbl.setMaximumWidth(20)
            connect_layout.addWidget(self.srs_connected_lbl)
            connect_layout.addWidget(QLabel('Sacher'))
            self.sacher_connected_lbl = QLabel('Off')
            self.sacher_connected_lbl.setStyleSheet("QWidget { background-color: %s }" % 'red')
            self.sacher_connected_lbl.setMaximumWidth(20)
            connect_layout.addWidget(self.sacher_connected_lbl)
            connect_layout.addStretch(1)

            initialization_layout.addLayout(connect_layout)

            main_layout.addLayout(initialization_layout)

            # add layout with readings of ULE transmission photodiode

            # layout with plots and lock controlls
            lock_layout = QHBoxLayout()

            self.output_plots = OutputPlotWindow()
            lock_layout.addWidget(self.output_plots)

            lock_menu = QVBoxLayout()
            self.lock_srs_btn = QPushButton('Lock SRS')
            self.lock_srs_btn.pressed.connect(self.lockSrsBtnPressed)
            lock_menu.addWidget(self.lock_srs_btn)

            lock_menu.addWidget(QLabel('Threshold SRS error'))
            self.threshold_srs_error = QDoubleSpinBox()
            self.threshold_srs_error.setDecimals(3)
            self.threshold_srs_error.setRange(0,0.999)
            self.threshold_srs_error.setSingleStep(0.001)
            self.threshold_srs_error.setValue(self.data.threshold_srs_error)
            self.threshold_srs_error.valueChanged[float].connect(self.thresholdErrorChanged)
            lock_menu.addWidget(self.threshold_srs_error)

            lock_menu.addWidget(QLabel('INSR'))
            self.insr_lbl = QLabel('___')
            lock_menu.addWidget(self.insr_lbl)

            self.lock_piezo_btn = QPushButton('Lock piezo')
            self.lock_piezo_btn.pressed.connect(self.lockPiezoBtnPressed)
            lock_menu.addWidget(self.lock_piezo_btn)

            lock_menu.addWidget(QLabel('Correction limit'))
            self.correction_limit = QDoubleSpinBox()
            self.correction_limit.setDecimals(3)
            self.correction_limit.setRange(0,9.999)
            self.correction_limit.setSingleStep(0.001)
            self.correction_limit.setValue(self.data.correction_limit)
            self.correction_limit.valueChanged[float].connect(self.correctionLimitChanged)
            lock_menu.addWidget(self.correction_limit)

            lock_menu.addWidget(QLabel('Piezo voltage'))
            self.piezo_voltage = QDoubleSpinBox()
            self.piezo_voltage.setDecimals(3)
            self.piezo_voltage.setRange(-9.999,9.999)
            self.piezo_voltage.setSingleStep(0.001)
            self.piezo_voltage.setValue(1.353)
            lock_menu.addWidget(self.piezo_voltage)

            lock_menu.addWidget(QLabel('Voltage change'))
            self.voltage_change_lbl = QLabel()
            lock_menu.addWidget(self.voltage_change_lbl)

            lock_menu.addStretch(1)

            lock_layout.addLayout(lock_menu)

            main_layout.addLayout(lock_layout)

            self.setLayout(main_layout)
            self.updateBtnPressed()

        def lockSrsBtnPressed(self):
            print('lockSrsBtnPressed')
            status, res = self.data.srs.isLockOn()
            if not status:
                print('Error while reading if SRS is locked')
                self.lock_srs_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')
                return
            if res: # srs is locked
                # confirm that you want to unlock it
                reply = QMessageBox.question(self, 'Message',
                                                   'Unlock SRS?', QMessageBox.Yes, QMessageBox.No)

                if reply == QMessageBox.Yes:
                    status, readout = self.data.srs.turnLockOff()
                    if status:
                        self.lock_srs_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')
                        print('SRS unlocked')
                    else:
                        print('Problems with unlocking SRS')
            else: # srs is not locked
                # lock it
                status, readout = self.data.srs.turnLockOn()
                if status:
                    self.lock_srs_btn.setStyleSheet("QWidget { background-color: %s }" % 'green')
                    print('SRS locked')
                else:
                    print('Problems with locking SRS')

        def lockPiezoBtnPressed(self):
            print('lockPiezoBtnPressed')
            if not self.data.srs.connected or not self.data.sacher.connected:
                #if ither of com ports is disconnectid
                print('No connection')
                return
            status,self.data.srs_lock = self.data.srs.isLockOn() # check if srs is locked
            if not status: #if error in readings simply do nothing
                return
            if not self.data.srs_lock: # if srs isn't locked
                print("SRS is not locked")
                self.lock_srs_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')
                return

            # if srs is locked
            self.lock_srs_btn.setStyleSheet("QWidget { background-color: %s }" % 'green')
            if not self.data.piezo_lock: # if piezo is not locked yet
                self.data.srs.clearINSR() # clean register INSR from srs - about it's overload or reaching limit
                self.lock_piezo_btn.setStyleSheet("QWidget { background-color: %s }" % 'green')
                status = self.data.readData(new=True) # try read data from srs and sacher
                if not status: # if there error while reading (most likely due to breaking com-port connections)
                    # don't lock and indicate it via red piezo_lock btn
                    self.lock_piezo_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')
                    self.timer.stop()
                    return
                self.output_plots.srs_plot.setYRange(-5*self.data.threshold_srs_error,5*self.data.threshold_srs_error)
                self.output_plots.srs_output_curve.setData(self.data.srs_output)
                self.output_plots.srs_lower_threshold.setValue(-self.data.threshold_srs_error)
                self.output_plots.srs_upper_threshold.setValue(self.data.threshold_srs_error)

                self.output_plots.sacher_piezo_curve.setData(self.data.piezo_voltage)
                self.piezo_voltage.setValue(self.data.piezo_voltage[-1])
                #create new entry in database
                self.data.current_db_id = self.data.db.insert_one(self.data.getDataToDB()).inserted_id
                print('Current entry mongodb id ',self.data.current_db_id)
                #start locking
                self.data.piezo_lock = True
                self.data.srs_insr_error_counter = 0 # dump this counter
                self.timer.start()
                return
            elif self.data.piezo_lock: # if already locked
                # unlock sacher (simply stop corrections)
                self.stopLock(piezo_lock_btn_color='grey', msg_to_db='Stoped by user')
                # self.data.piezo_lock = False
                # self.lock_piezo_btn.setStyleSheet("QWidget { background-color: %s }" % 'grey')
                # self.timer.stop()

        def routine(self): # programm that run on timer
            # print('routine')
            status, res = self.data.srs.isLockOn()
            if not status:
                print('Error while reading if SRS is locked')
                self.lock_srs_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')
                self.data.srs_lock = False
                self.lock_srs_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')
                return
            if not res:
                print('Srs was unclocked')
                self.stopLock(msg_to_db='SRS was unlocked')
                return
            status=self.data.readData() # try to read srs and sacher data
            if not status: # if readings unsuccessfull
                # stop lock (stop timer) and color piezo_lock button
                self.stopLock(msg_to_db='Error in reading data from srs or sacher')
                return
            # if readings are good
            self.data.db.update_one({'_id':self.data.current_db_id},{'$set':self.data.getDataToDB()}) #updata database
            status, insr = self.data.srs.readINSR() # check status redister of SRS
            if not status: # if readings unsuccessfull
                # stop lock (stop timer) and color piezo_lock button
                self.stopLock(msg_to_db='Error in reading data from srs or sacher')
                return
            # show INSR register in GUI first bit is lowerst
            self.insr_lbl.setText("%i%i%i"%((insr >> 0) % 2,(insr >> 1) % 2,(insr >> 2) % 2))
            if insr % 8 != 0: # if overload (0-bit) upperlimit(1-bit) or lowerlimit(2-bit) has happened
                print('Smth wrong with status register of SRS:%i%i%i'%((insr >> 0) % 2,(insr >> 1) % 2,(insr >> 2) % 2))
                bd_data = self.data.db.find_one({'_id':self.data.current_db_id})
                if 'insr' not in bd_data:
                    bd_data['insr']=[]
                bd_data['insr'].append((len(self.data.srs_output),insr))
                self.data.db.update_one({'_id': self.data.current_db_id}, {'$set': {'insr':bd_data['insr']}})
                self.data.srs.clearINSR()
                self.data.srs_insr_error_counter += 1
                print('srs_insr_error_counter ', self.data.srs_insr_error_counter)
                if self.data.srs_insr_error_counter > self.data.srs_insr_error_counter_threshold:
                    print('SRS INSR error reached threshold')
                    print('System is switched to Manual mode')
                    self.data.srs.turnLockOff() # turn off srs lock
                    self.data.srs_lock = False
                    self.lock_srs_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')
                    self.stopLock(msg_to_db='SRS status register exception')# :%i%i%i'%((insr >> 0) % 2,(insr >> 1) % 2,(insr >> 2) % 2))
                    return
            else:
                self.data.srs_insr_error_counter = 0 # dump counter if INSR is ok
            self.output_plots.srs_output_curve.setData(self.data.srs_output)
            self.output_plots.sacher_piezo_curve.setData(self.data.piezo_voltage)

            if abs(self.data.srs_output[-1]) > self.data.maximum_srs_error:
                print('SRS error is too large: %.3f'%self.data.srs_output[-1])
                print('System is switched to Manual mode')
                self.data.srs.turnLockOff()  # turn off srs lock
                self.data.srs_lock = False
                self.lock_srs_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')
                self.stopLock(msg_to_db='SRS error is too large: %.3f'%self.data.srs_output[-1])
                return
            if abs(self.data.srs_output[-1]) > self.data.threshold_srs_error: # if srs_output reached threshold
                # set color of the piezo_lock btn depending on how large is cuurrent correction
                if abs(self.data.piezo_voltage[-1] - self.data.piezo_voltage[0]) < self.data.correction_limit/2:
                    self.lock_piezo_btn.setStyleSheet("QWidget { background-color: %s }" % 'green')
                elif 0.9*self.data.correction_limit > abs(self.data.piezo_voltage[-1] - self.data.piezo_voltage[0]) >= self.data.correction_limit/2:
                    self.lock_piezo_btn.setStyleSheet("QWidget { background-color: %s }" % 'yellow')
                elif 1 * self.data.correction_limit > abs(
                    self.data.piezo_voltage[-1] - self.data.piezo_voltage[0]) >= 0.9*self.data.correction_limit :
                    self.lock_piezo_btn.setStyleSheet("QWidget { background-color: %s }" % 'orange')
                # if correction limit  is reached
                elif abs(self.data.piezo_voltage[-1] - self.data.piezo_voltage[0]) >= self.data.correction_limit:
                    print('Correction limit of piezo is reached. System is switched to Manual mode')
                    self.data.srs.turnLockOff() # turn off srs lock
                    self.data.srs_lock = False
                    self.lock_srs_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')
                    self.stopLock(msg_to_db='Correction limit %i was reached' % (self.data.piezo_voltage[-1] - self.data.piezo_voltage[0]))
                    return
                # if correction limit  WASN'T reached
                # correct sacher piezo voltage by 1mV
                status = self.data.sacher.writePiezoVoltage(self.data.piezo_voltage[-1] + sign(self.data.srs_output[-1]) * 1e-3)
                if not status:
                    self.stopLock(msg_to_db='Error in reading data from srs or sacher')
                    return
                # update labels
                self.piezo_voltage.setValue(self.data.piezo_voltage[-1] + sign(self.data.srs_output[-1]) * 1e-3)
                self.voltage_change_lbl.setText("%.3f"%(self.data.piezo_voltage[-1] + sign(self.data.srs_output[-1]) * 1e-3 - self.data.piezo_voltage[0]))

        def correctionLimitChanged(self,new_val): # correction limit of sacher piezo voltage
            print('correctionLimitChanged to ',new_val)
            self.data.correction_limit = new_val
            self.data.config['correction_limit'] = self.data.correction_limit
            self.data.save_config()

        def thresholdErrorChanged(self,new_val): # threshold for srs output voltage to do corrections
            print('thresholdErrorChanged to ',new_val)
            self.data.threshold_srs_error = new_val
            self.data.config['threshold_srs_error'] = self.data.threshold_srs_error
            self.data.save_config()
            self.output_plots.srs_lower_threshold.setValue(-self.data.threshold_srs_error)
            self.output_plots.srs_upper_threshold.setValue(self.data.threshold_srs_error)

        def srsPortChanged(self,name):
            self.data.srs.port = name

        def sacherPortChanged(self, name):
            self.data.sacher.port = name

        def connectBtnPressed(self):
            print('connectBtnPressed')
            if not self.data.srs.connected and not self.data.sacher.connected: # if SRS and Sacher are not connected yet
                # try to connect SRS
                res = self.data.srs.connect()
                if res < 0:
                    print("Can't connect SRS")
                    return
                # try to connect Sacher
                res = self.data.sacher.connect()
                if res < 0:
                    self.data.srs.stream.close()
                    print("Can't connect Sacher")
                    return

                print('SRS and Sacher connected!')
                self.srs_connected_lbl.setStyleSheet("QWidget { background-color: %s }" % 'green')
                self.srs_connected_lbl.setText('On')
                self.sacher_connected_lbl.setStyleSheet("QWidget { background-color: %s }" % 'green')
                self.sacher_connected_lbl.setText('On')
                self.connect_btn.setText('Disconnect')
            else: # if SRS and Sacher are already connected
                self.disconnectPorts() # disconnect them
                self.connect_btn.setText('Connect')
                self.srs_connected_lbl.setText('Off')
                self.srs_connected_lbl.setStyleSheet("QWidget { background-color: %s }" % 'red')
                self.sacher_connected_lbl.setText('Off')
                self.sacher_connected_lbl.setStyleSheet("QWidget { background-color: %s }" % 'red')

        def disconnectPorts(self):
            print('disconnectPorts')
            try:
                self.data.srs.close()
                self.data.sacher.close()
            except:
                print("Can't close ports")

        def updateBtnPressed(self): # updates ports info and tries to find srs and sacher ports
            print('updateBtnPressed')
            self.data.updateCOMPortsInfo()
            self.ports_info.setText(str(self.data.available_com_ports) +'\n\n'+ self.data.com_ports_info)
            self.srs_port_menu.clear()
            self.srs_port_menu.addItems(['-'] + self.data.available_com_ports)
            self.data.srs.preCheck()
            self.srs_port_menu.setCurrentText(self.data.srs.port)
            self.sacher_port_menu.clear()
            self.sacher_port_menu.addItems(['-'] + self.data.available_com_ports)
            self.data.sacher.preCheck()
            self.sacher_port_menu.setCurrentText(self.data.sacher.port)

        def stopLock(self,piezo_lock_btn_color='red',msg_to_db='No message'):
            self.lock_piezo_btn.setStyleSheet("QWidget { background-color: %s }" % piezo_lock_btn_color)
            self.timer.stop()
            self.data.piezo_lock = False
            self.data.db.update_one({'_id': self.data.current_db_id},
                                    {'$set': {'stop_message':msg_to_db}})  # updata database

class OutputPlotWindow(pg.GraphicsWindow):
    """Widget for displaying srs output and sacher piezo voltage"""
    def __init__(self):
        super().__init__()
        self.srs_plot = self.addPlot()
        self.srs_plot.showGrid(x=True,y=True,alpha=0.5)
        self.srs_output_curve = self.srs_plot.plot()
        self.srs_lower_threshold = self.srs_plot.addLine(y=0)
        self.srs_upper_threshold = self.srs_plot.addLine(y=0)
        self.nextRow()
        self.piezo_plot = self.addPlot()
        self.piezo_plot.showGrid(x=True, y=True, alpha=0.5)
        self.sacher_piezo_curve = self.piezo_plot.plot()

class COMPortDevice:
    """General class for com ports. """
    connected = False
    port = ''
    baudrate = 9600
    timeout = 1
    identification_names = [] # first few words that should be in the output to *IDN? command splited bu ',' to check

    # function to check based on port info if the port is correct
    def preCheck(self):
        return True

    def close(self): # closes port
        self.stream.close()
        self.connected = False

    def write_read_com(self, command):
        """tries to write command to devise and read it's response"""
        status = True
        readout = ''
        try:
            self.stream.write(command)
            readout = self.stream.readline().decode()
        except SerialException as e:
            status = False
            print(e)
        return (status,readout) # return statuus of reading and readout

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
            return -2

class Sacher(COMPortDevice):
    baudrate = 57600
    identification_names = ['Sacher Lasertechnik', ' PilotPC 500', ' SN14098015']

    def preCheck(self):
        for port in list(list_ports.comports()):
            if port.manufacturer == 'FTDI':
                self.port = port.device

    def readPiezoVoltage(self):
        """Reads voltage of piezo in Volts"""
        status,readout = self.write_read_com(b'P:OFFS?\r')
        if not status:
            return False,0
        piezo_offset, suffix = readout.split('\r')
        return (True,float(piezo_offset))

    def writePiezoVoltage(self,new_voltage):
        """writes new_voltage to piezo voltage"""
        return self.write_read_com(b'P:OFFS %.3fV\r' % new_voltage)

class SRS(COMPortDevice):
    identification_names = ['Stanford_Research_Systems', 'SIM960']

    def preCheck(self):
        for port in list(list_ports.comports()):
            if port.manufacturer == 'Prolific':
                self.port = port.device

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
if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    inst = BlueLock()
    mainWindow = inst.Widget(data=inst)
    mainWindow.show()
    sys.exit(app.exec_())
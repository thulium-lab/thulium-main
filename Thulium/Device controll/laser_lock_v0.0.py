import sys
import os
import random
import matplotlib
import numpy as np
import json
# Make sure that we are using QT5
matplotlib.use('Qt5Agg')
from PyQt5.QtCore import (QLineF, QPointF, QRectF, Qt, QTimer)
from PyQt5.QtGui import (QBrush, QColor, QPainter)
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

import pyqtgraph as pg

import pymongo, datetime
from pymongo import MongoClient
#
# class plotWidget(FigureCanvasi):
#     def __init__(self, parent=None, width=4, height=3, dpi=100):
#         fig, self.axes = plt.subplots()
#         # fig = Figure(figsize=(width, height), dpi=dpi)
#         # self.axes = fig.add_subplot(111)
#         # self.axes2 = fig.add_subplot(111)
#         # self.axes.hold(False)
#         # self.axes2.hold(False)
#         super(plotWidget, self).__init__(fig)
#         self.setParent(parent)
# class ApplicationWindow(QtWidgets.QMainWindow):
#     def __init__(self):
#         QtWidgets.QMainWindow.__init__(self)
#         self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
#         self.setWindowTitle("Blue laser lock")
#         self.main_widget = QtWidgets.QWidget(self)
#         layout1 = QtWidgets.QHBoxLayout(self.main_widget)
#         layout1l = plotWidget(self.main_widget)
#         layout1r = QtWidgets.QVBoxLayout(self.main_widget)
#         connect_btn = QPushButton('Connect',self)
class BlueLock():
    available_com_ports = []
    com_ports_info= ''
    correction_limit = 0.1
    threshold_srs_error = 0.003
    srs_lock = False
    piezo_lock = False
    srs_output  = None
    piezo_voltage = None
    blue_lock_config_file = 'blue_lock_config.json'
    config = {}
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

    class Widget(QWidget):
        def __init__(self,parent=None,data=None):
            super().__init__()
            self.data = data
            self.parent = parent
            self.timer = QTimer()
            self.timer.setInterval(1000)
            self.timer.timeout.connect(self.routine)
            self.initUI()

        def initUI(self):
            main_layout = QVBoxLayout()

            initialization_layout = QHBoxLayout()
            self.ports_info = QTextEdit()
            # self.ports_info.setText(str(self.data.available_com_ports) +'\n\n'+ self.data.com_ports_info)
            initialization_layout.addWidget(self.ports_info)

            info_layout = QVBoxLayout()
            info_btn = QPushButton('Update')
            info_btn.clicked.connect(self.updateBtnPressed)
            info_layout.addWidget(info_btn)

            info_layout.addWidget(QLabel('SRS'))
            self.srs_port_menu = QComboBox()
            self.srs_port_menu.currentTextChanged[str].connect(self.srsPortChanged)
            # self.srs_port_menu.addItems(['-']+self.data.available_com_ports)
            # self.data.srs.preCheck()
            # self.srs_port_menu.setCurrentText(self.data.srs.port)
            info_layout.addWidget(self.srs_port_menu)

            info_layout.addWidget(QLabel('Sacher'))
            self.sacher_port_menu = QComboBox()
            self.sacher_port_menu.currentTextChanged[str].connect(self.sacherPortChanged)

            # self.sacher_port_menu.addItems(['-']+self.data.available_com_ports)
            # self.data.sacher.preCheck()
            # self.sacher_port_menu.setCurrentText(self.data.sacher.port)
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

            lock_layout = QHBoxLayout()
            self.output_plots = OutputPlotWindow()
            lock_layout.addWidget(self.output_plots)

            lock_menu = QVBoxLayout()
            self.lock_srs_btn = QPushButton('Lock SRS')
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

        def getDataToDB(self):
            return {'date':datetime.datetime.now(),
                              'threshold_srs_error' : self.data.threshold_srs_error,
                              'correction_limit': self.data.correction_limit,
                               'srs_output':list(self.data.srs_output),
                               'piezo_voltage':list(self.data.piezo_voltage)
                              }
        def lockPiezoBtnPressed(self):
            print('lockPiezoBtnPressed')
            if not self.data.srs.connected or not self.data.sacher.connected:
                print('No connection')
                return
            status,self.data.srs_lock = self.data.srs.isLockOn()
            if not status:
                return
            if not self.data.srs_lock:
                print("SRS is not locked")
                self.lock_srs_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')
                return
            self.lock_srs_btn.setStyleSheet("QWidget { background-color: %s }" % 'green')

            if not self.data.piezo_lock:
                self.data.srs.clearINSR()
                self.lock_piezo_btn.setStyleSheet("QWidget { background-color: %s }" % 'green')
                status = self.readData(new=True)
                if not status:
                    self.lock_piezo_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')
                    self.timer.stop()
                    return
                self.output_plots.srs_plot.setYRange(-5*self.data.threshold_srs_error,5*self.data.threshold_srs_error)
                self.output_plots.srs_output_curve.setData(self.data.srs_output)
                self.output_plots.srs_lower_threshold.setValue(-self.data.threshold_srs_error)
                self.output_plots.srs_upper_threshold.setValue(self.data.threshold_srs_error)
                # self.output_plots.piezo_plot.setYRange(self.data.piezo_voltage[0]-)
                self.output_plots.sacher_piezo_curve.setData(self.data.piezo_voltage)
                self.piezo_voltage.setValue(self.data.piezo_voltage[-1])
                self.data.current_db_id = self.data.db.insert_one(self.getDataToDB()).inserted_id
                print('Current entry mongodb id ',self.data.current_db_id)
                self.data.piezo_lock = True
                self.timer.start()
                return
            elif self.data.piezo_lock:
                self.data.piezo_lock = False
                self.lock_piezo_btn.setStyleSheet("QWidget { background-color: %s }" % 'grey')
                self.timer.stop()

        def readData(self,new=False):
            status,v1 = self.data.srs.readOutput()
            if not status:
                # self.problemHandler()
                return False
            status,q1 = self.data.sacher.readPiezoVoltage()
            if not status:
                # self.problemHandler()
                return False
            if new:
                self.data.srs_output = np.array([v1])
                self.data.piezo_voltage = np.array([q1])
            else:
                self.data.srs_output = np.append(self.data.srs_output,v1)
                self.data.piezo_voltage = np.append(self.data.piezo_voltage,q1)
            return True

        def routine(self):
            # print('routine')
            status=self.readData()
            if not status:
                self.lock_piezo_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')
                self.timer.stop()
                self.data.piezo_lock = False
                return

            self.data.db.update_one({'_id':self.data.current_db_id},{'$set':self.getDataToDB()})
            status, insr = self.data.srs.readINSR()
            if not status:
                self.lock_piezo_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')
                self.timer.stop()
                self.data.piezo_lock = False
                return
            self.insr_lbl.setText("%i%i%i"%((insr >> 2) % 2,(insr >> 1) % 2,(insr >> 0) % 2))
            self.output_plots.srs_output_curve.setData(self.data.srs_output)
            self.output_plots.sacher_piezo_curve.setData(self.data.piezo_voltage)
            if abs(self.data.srs_output[-1]) > self.data.threshold_srs_error:
                if abs(self.data.piezo_voltage[-1] - self.data.piezo_voltage[0]) < self.data.correction_limit/2:
                    self.lock_piezo_btn.setStyleSheet("QWidget { background-color: %s }" % 'green')
                elif 0.9*self.data.correction_limit > abs(self.data.piezo_voltage[-1] - self.data.piezo_voltage[0]) >= self.data.correction_limit/2:
                    self.lock_piezo_btn.setStyleSheet("QWidget { background-color: %s }" % 'yellow')
                elif 1 * self.data.correction_limit > abs(
                    self.data.piezo_voltage[-1] - self.data.piezo_voltage[0]) >= 0.9*self.data.correction_limit :
                    self.lock_piezo_btn.setStyleSheet("QWidget { background-color: %s }" % 'orange')
                elif abs(self.data.piezo_voltage[-1] - self.data.piezo_voltage[0]) >= self.data.correction_limit:
                    print('Correction limit of piezo is reached. System will switched to Manual mode')
                    self.data.srs.turnLockOff()
                    self.data.piezo_lock = False
                    self.lock_piezo_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')
                    self.timer.stop()
                    self.data.piezo_lock = False
                    return
                status = self.data.sacher.writePiezoVoltage(self.data.piezo_voltage[-1] + sign(self.data.srs_output[-1]) * 1e-3)
                if not status:
                    self.lock_piezo_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')
                    self.timer.stop()
                    self.data.piezo_lock = False
                    return
                self.piezo_voltage.setValue(self.data.piezo_voltage[-1] + sign(self.data.srs_output[-1]) * 1e-3)
                self.voltage_change_lbl.setText("%.3f"%(self.data.piezo_voltage[-1] + sign(self.data.srs_output[-1]) * 1e-3 - self.data.piezo_voltage[0]))
                # sacher_offset = get_sacher_offset(sacher)
                # print("CORRECTION; total %.3f mV" % (abs(sacher_offset - sacher_offset0)))
            # print('SRS output = %.3f mV ; Sacher offset = %.3f V ; overload = %i' % (
            # 1e3 * error, get_sacher_offset(sacher), ovld))

        def correctionLimitChanged(self,new_val):
            print('correctionLimitChanged to ',new_val)
            self.data.correction_limit = new_val
            self.data.config['correction_limit'] = self.data.correction_limit
            self.data.save_config()

        def thresholdErrorChanged(self,new_val):
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
            if not self.data.srs.connected and not self.data.sacher.connected:
                res = self.data.srs.connect()
                if res < 0:
                    print("Can't connect SRS")
                    return
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
            else:
                self.disconnectPorts()
                self.connect_btn.setText('Connect')
                self.srs_connected_lbl.setText('Off')
                self.srs_connected_lbl.setStyleSheet("QWidget { background-color: %s }" % 'red')
                # self.srs_connected_lbl.show()
                self.sacher_connected_lbl.setText('Off')
                self.sacher_connected_lbl.setStyleSheet("QWidget { background-color: %s }" % 'red')
                self.repaint()

        def disconnectPorts(self):
            print('disconnectPorts')
            try:
                self.data.sacher.close()
                self.data.srs.close()
            except:
                print("Can't close ports")

            # print('Finished')

        def updateBtnPressed(self):
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

class OutputPlotWindow(pg.GraphicsWindow):
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
    connected = False
    port = ''
    baudrate = 9600
    timeout = 1
    identification_names = [] # first few words that should be in the output to *IDN? command splited bu ',' to check

    # function to check based on port info if the port is correct
    def preCheck(self):
        return True

    def close(self):
        self.stream.close()
        self.connected = False

    def write_read_com(self, command):
        status = True
        readout = ''
        try:
            self.stream.write(command)
            readout = self.stream.readline().decode()
        except SerialException as e:
            status = False
            print(e)
        return (status,readout)

    def connect(self,idn_message=b'*IDN?\r'):
        try:
            p = Serial(self.port, self.baudrate, timeout=self.timeout)
            p.write(idn_message)
            s = p.readline()
            s = s.decode().split(',')
            print('Port answer ', s)
            if len(s) < len(self.identification_names):
                p.close()
                self.stream = None
                return -1
            else:
                status = True
                for i in range(len(self.identification_names)):
                    if s[i] != self.identification_names[i]:
                        status = False
                        break
                if status:
                    print('\n' + 'Divese ' + str(self.identification_names) + ' connected on port ' + self.port + '\n')
                    self.connected = True
                    self.stream = p
                    return 0
                else:
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
        status,readout = self.write_read_com(b'P:OFFS?\r')
        if not status:
            return False,0
        piezo_offset, suffix = readout.split('\r')
        return (True,float(piezo_offset))

    def writePiezoVoltage(self,new_voltage):
        return self.write_read_com(b'P:OFFS %.3fV\r' % new_voltage)

class SRS(COMPortDevice):
    identification_names = ['Stanford_Research_Systems', 'SIM960']

    def preCheck(self):
        for port in list(list_ports.comports()):
            if port.manufacturer == 'Prolific':
                self.port = port.device

    def readOutput(self):
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
        status, readout = self.write_read_com(b'AMAN?\r')
        if not status:
            return False, 0
        # return float(readout)
        # is_lock_on = int(self.write_read_com(b'AMAN?\r'))
        try:
            output = int(readout)
        except ValueError as e:
            print("Can't convert %s in isLockOn to int" %readout)
            return False,0
        return True,output

    def turnLockOff(self):
        return self.write_read_com(b'AMAN 0\r')

    def readINSR(self):
        # ovld = int(write_read_com(srs, b'INSR? 0\r'))
        status, readout = self.write_read_com(b'INSR?\r')
        if not status:
            return False, 0
        # return float(readout)
        # is_lock_on = int(self.write_read_com(b'AMAN?\r'))
        try:
            output = int(readout)
        except ValueError as e:
            print("Can't convert %s in readINSR to int" %readout)
            return False,0
        return True,output

    def clearINSR(self):
        for i in range(3):
            print(self.write_read_com(b'INSR? %i\r' % (i)))

if __name__ == '__main__':
    # config = {}
    # config['day_folder'] = '2016_10_10'
    # config['all_meas_type'] = ['CL', 'LT', 'FB', 'T']
    # config['current_meas_type'] = 'CL'
    # config['add_points_flag']=  False
    # config['notes'] = 'some note'
    # config['number_of_shots'] = 10
    # with open(scanner_config_file,'w') as f:
    #     json.dump(config,f)
    import sys
    app = QApplication(sys.argv)
    inst = BlueLock()
    mainWindow = inst.Widget(data=inst)
    mainWindow.show()
    sys.exit(app.exec_())
try:
    from .device_lib import COMPortDevice
except:
    from device_lib import COMPortDevice
import matplotlib
import numpy as np
import json
# Make sure that we are using QT5
matplotlib.use('Qt5Agg')
from PyQt5.QtCore import ( QTimer)
from PyQt5.QtGui import (QIcon)
from PyQt5.QtWidgets import (QWidget,QMessageBox, QDoubleSpinBox)
from PyQt5.QtWidgets import (QApplication, QVBoxLayout, QHBoxLayout,QLabel, QLineEdit, QPushButton)

from numpy import sign

import pyqtgraph as pg

import datetime
from pymongo import MongoClient

import ctypes
myappid = u'LPI.BlueZalseLock' # arbitrary string
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

class BlueLock():
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
        self.db = MongoClient('mongodb://192.168.1.59:27017/').measData.sacher_log
        self.load()
        # self.updateCOMPortsInfo()
        self.srs = SRS(default_port=self.config.get('srs_port',''))
        self.sacher = Sacher(default_port=self.config.get('sacher_port',''))

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

    def readData(self, new=False):
        status, res = self.srs.isLockOn()
        if not status:
            return -1
        if not res:
            self.srs_lock = False
            return 0
        self.srs_lock = True
        status, v1 = self.srs.readOutput()  # read output voltage of srs
        if not status:  # if there is a problem with reading return status false
            return -1
        status, q1 = self.sacher.readPiezoVoltage()  # read piezo voltage of sacher
        if not status:  # if there is a problem with reading return status false
            return -2
        if new:  # if lock is just turned on
            # create new data arrays
            self.srs_output = np.array([v1])
            self.piezo_voltage = np.array([q1])
        else:  # if not - update arrays
            self.srs_output = np.append(self.srs_output, v1)
            self.piezo_voltage = np.append(self.piezo_voltage, q1)
        return 1  # return that readings are successfull

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
            self.timer.start()

        def initUI(self):
            main_layout = QVBoxLayout()

            initialization_layout = QHBoxLayout()
            initialization_layout.addWidget(QLabel('SRS'))
            self.srsWidget = self.data.srs.BasicWidget(data=self.data.srs, parent=self, connect=True)
            initialization_layout.addWidget(self.srsWidget)
            initialization_layout.addWidget(QLabel('Sacher'))
            self.sacherWidget = self.data.sacher.BasicWidget(data=self.data.sacher, parent=self, connect=True)
            initialization_layout.addWidget(self.sacherWidget)

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
            # self.updateBtnPressed()

        def save(self,dict_to_save):
            if dict_to_save['port'] == self.data.srs.port:
                new_dict_to_save = {'srs_port':dict_to_save['port']}
            else:
                new_dict_to_save = {'sacher_port': dict_to_save['port']}
            print("reee")
            self.data.config.update(new_dict_to_save)
            print('new_config', self.data.config)
            self.data.save_config()

        def lockSrsBtnPressed(self):
            # now this button used only as indicator
            print('lockSrsBtnPressed')

        def lockPiezoBtnPressed(self):
            # now this button used only as indicator
            print('lockPiezoBtnPressed')

        def handle_SRS_error(self):
            if self.data.piezo_lock:
                self.data.piezo_lock = False
                self.lock_piezo_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')
            self.data.srs_lock = False
            self.lock_srs_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')
            self.data.srs.connect = False
            self.srsWidget.connect_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')

        def handle_Sacher_error(self):
            self.data.piezo_lock = False
            self.lock_piezo_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')
            self.data.sacher.connect = False
            self.sacherWidget.connect_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')

        def routine(self): # programm that run on timer
            # print('routine')
            if not self.data.srs.connected or not self.data.sacher.connected:
                return
            srs_was_locked = self.data.srs_lock
            piezo_was_locked = self.data.piezo_lock
            status = self.data.readData(new = (not self.data.piezo_lock))  # try to read srs and sacher data
            if status < 0: # error in readings
                if status == -1:
                    self.handle_SRS_error()
                elif status == -2:
                    self.handle_Sacher_error()
                if  piezo_was_locked:
                    self.stopLock(msg_to_db='Error in reading data from srs or sacher')
                return
            elif status == 0: # srs is not locked
                self.data.srs_lock = False
                self.lock_srs_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')
                self.data.piezo_lock = False
                self.lock_piezo_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')
                if  piezo_was_locked:
                    self.stopLock(msg_to_db='Srs unlocked')
                return
            if self.data.srs_lock:
                self.lock_srs_btn.setStyleSheet("QWidget { background-color: %s }" % 'green')
            # if readings are good
            if not piezo_was_locked:
                self.data.srs.clearINSR()
                self.data.piezo_lock = True
                self.lock_piezo_btn.setStyleSheet("QWidget { background-color: %s }" % 'green')
                self.output_plots.srs_plot.setYRange(-5 * self.data.threshold_srs_error,
                                                     5 * self.data.threshold_srs_error)
                self.output_plots.srs_lower_threshold.setValue(-self.data.threshold_srs_error)
                self.output_plots.srs_upper_threshold.setValue(self.data.threshold_srs_error)
                self.data.srs_insr_error_counter = 0
                self.piezo_voltage.setValue(self.data.piezo_voltage[-1])
                self.data.current_db_id = self.data.db.insert_one(self.data.getDataToDB()).inserted_id
            else:
                self.data.db.update_one({'_id':self.data.current_db_id},{'$set':self.data.getDataToDB()}) #updata database
            status, insr = self.data.srs.readINSR() # check status redister of SRS
            if not status: # if readings unsuccessfull
                # stop lock (stop timer) and color piezo_lock button
                self.handle_SRS_error()
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
            # as now no stop button this function is called when lock is over, so only thing that is needed is to save data to db
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



class Sacher(COMPortDevice):
    baudrate = 57600
    identification_names = ['Sacher Lasertechnik', ' PilotPC 500', ' SN14098015']
    check_answer = 'FTDI'

    # def preCheck(self):
    #     for port in list(list_ports.comports()):
    #         if port.manufacturer == 'FTDI':
    #             self.port = port.device

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
    identification_names = ['Stanford_Research_Systems', 'SIM960','s/n016481']
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


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    inst = BlueLock()
    mainWindow = inst.Widget(data=inst)
    mainWindow.show()
    sys.exit(app.exec_())
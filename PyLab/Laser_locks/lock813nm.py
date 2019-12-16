import os, json, ctypes, sys, inspect
import pyqtgraph as pg
import numpy as np
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(os.path.dirname(currentdir))
sys.path.insert(0,parentdir)

sys.path.insert(0,r"C:\drive\Tm\Python\PyLab")
from device_lib import COMPortWidgetOLD
from Lib import *

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
from collections import OrderedDict

BOX_WIDTH = 100
CurrentLineDict = OrderedDict([
    ("Timer interval, ms",['MIB',100,QIntValidator(10,9999),BOX_WIDTH]),
    ('Channel',['LE','LASER',BOX_WIDTH]),
    ('DAC output', ['MIB', 0, QIntValidator(1,4), BOX_WIDTH]),
    ('Target freq., MHz',['MDB',262955800,QDoubleValidator(200000000.0,999999999.0,1),BOX_WIDTH]),
    ("Window, MHz",['MDB',1, QDoubleValidator(0.1,99.9,1),BOX_WIDTH]),
    ('Threshold, MHz',['MDB',100, QDoubleValidator(10,999,0),BOX_WIDTH]),
    ('Gain, mV/MHz',['MDB',1.0, QDoubleValidator(-99,99,2),BOX_WIDTH]),
    ('K_p',['MDB',1.0, QDoubleValidator(0,999,2),BOX_WIDTH]),
    ('K_i',['MDB',0.0, QDoubleValidator(0,999,2),BOX_WIDTH]),
    ('K_d',['MDB',0.0, QDoubleValidator(0,999,2),BOX_WIDTH]),
    ('Correction limit, V',['MDB',2.5, QDoubleValidator(0,5,3),BOX_WIDTH]),
    ('Initial voltage, V',['MDB',2.5, QDoubleValidator(0,5,3),BOX_WIDTH]),
])

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

class LockTi_Sa(QWidget):
    config_file = 'lock813nm.json'

    output_voltage = 2.5 # V
    max_dead_time = 5 # seconds, dunlocks if readings from WM are old
    last_time = 0
    P = 0 #PID
    I = 0 #PID
    D = 0 #PID
    error2 = 0#PID
    config = {}

    def __init__(self):
        super().__init__()
        self.load()
        # self.arduino = COMPortDevice(default_port='COM12')
        self.device_widget = COMPortWidgetOLD(parent=self, connect=False, data=self.device,
                                           host_port=("192.168.1.227", 9997))
        self.setWindowTitle(self.data["Channel"] + ' Laser Lock')
        # self.setWindowIcon(QIcon('maxresdefault.jpg'))  # circle_blue.ico
        # self.arduino.write_com(('V %.2f!' % (self.initial_voltage)).encode()) # add this later
        self.lock = False

        self.timer = QTimer()
        self.timer.setInterval(self.data["Timer interval, ms"])
        self.timer.timeout.connect(self.routine)

        self.autoUpdate = QTimer()
        self.autoUpdate.setInterval(500)
        self.autoUpdate.timeout.connect(self.update)

        self.initUI()

    def load(self):
        try:
            with open(self.config_file,'r') as f:
                config = json.load(f)
        except json.decoder.JSONDecodeError:
            print('ERROR in reading ', self.config_file)
        self.__dict__.update(config)

    def save(self):
        print("Save")
        with open(self.config_file, 'r') as f:
            # if DEBUG: print('config_load_before_saving')
            config = json.load(f)
        config.update({"data":self.data})
        with open(self.config_file, 'w') as f:
            # if DEBUG: print('config_save')
            json.dump(config, f)

    def initUI(self):
        main_layout = QHBoxLayout()
        self.output_plots = OutputPlotWindow()
        self.output_plots.error_lower_threshold.setValue(-self.data["Window, MHz"])
        self.output_plots.error_upper_threshold.setValue(self.data["Window, MHz"])
        main_layout.addWidget(self.output_plots)

        lock_menu = QVBoxLayout()
        self.widgets = {}
        # print("gere")
        for key, val in CurrentLineDict.items():
            # print(key,val)
            # print(key)
            if val[0] == 'CB':
                # create a combo box widget
                items = val[2]
                w = MyComboBox(items=items, current_text=self.data.get(key, val[1]),
                               current_index_changed_handler=self.autoUpdate.start,
                               max_width=val[-1])
            elif val[0] == 'LE':
                w = MyLineEdit(name=self.data.get(key, val[1]),
                               text_changed_handler=self.autoUpdate.start,
                               text_edited_handler=self.autoUpdate.start,
                               max_width=val[-1])
            elif val[0] == 'MDB':
                validator = val[2]
                # print("FEDHDSI",key, self.data)
                w = MyDoubleBox(validator=validator, value=self.data.get(key, val[1]),
                                text_changed_handler=self.autoUpdate.start,
                                text_edited_handler=self.autoUpdate.start,
                                max_width=val[-1])
            elif val[0] == 'MIB':
                w = MyIntBox(validator=val[2], value=self.data.get(key, val[1]),
                             text_changed_handler=self.autoUpdate.start,
                             text_edited_handler=self.autoUpdate.start,
                             max_width=val[-1])
            elif val[0] == 'MChB':
                w = MyCheckBox(is_checked=self.data.get(key, val[1]), handler=self.autoUpdate.start,
                               max_width=val[-1])
            self.widgets[key] = w
            lock_menu.addWidget(QLabel(key))
            lock_menu.addWidget(w, val[-1])

        self.initial_btn = QPushButton('Set initital voltage')
        self.initial_btn.pressed.connect(self.initialBtnPressed)
        lock_menu.addWidget(self.initial_btn)

        lock_menu.addWidget(QLabel('Current change'))
        self.current_change_lbl = QLabel()
        lock_menu.addWidget(self.current_change_lbl)

        self.lock_btn = QPushButton('Lock')
        self.lock_btn.pressed.connect(self.lockBtnPressed)
        lock_menu.addWidget(self.lock_btn)

        lock_menu.addStretch(1)

        main_layout.addLayout(lock_menu)

        # main_layout.addWidget(self.arduino.BasicWidget(data=self.arduino))
        main_layout.addWidget(self.device_widget)
        self.setLayout(main_layout)


    def update(self):
        self.autoUpdate.stop()
        # print('Here1')
        changed_item = {}
        for key, val in CurrentLineDict.items():
            # print(key, val)
            if val[0] == 'CB':  # do a combo box widget
                if self.data[key] != self.widgets[key].currentText():
                    # print(self.data[key])
                    # print(self.widgets[key].currentText())
                    changed_item[key] = (self.data[key], self.widgets[key].currentText())
                    self.data[key] = self.widgets[key].currentText()

            elif val[0] == 'LE':
                if self.data[key] != self.widgets[key].text():
                    changed_item[key] = (self.data[key], self.widgets[key].text())
                    self.data[key] = self.widgets[key].text()
            elif val[0] in ['MDB', 'MIB']:
                if self.data[key] != self.widgets[key].value():
                    changed_item[key] = (self.data[key], self.widgets[key].value())
                    self.data[key] = self.widgets[key].value()
                    if key == "Window, MHz":
                        self.output_plots.error_lower_threshold.setValue(-self.data["Window, MHz"])
                        self.output_plots.error_upper_threshold.setValue(self.data["Window, MHz"])

            elif val[0] in ['MChB']:
                if self.data[key] != self.widgets[key].isChecked():
                    changed_item[key] = (self.data[key], self.widgets[key].isChecked())
                    self.data[key] = self.widgets[key].isChecked()
        self.save()

    def initialBtnPressed(self):
        msg_to_server = json.dumps(
            {"name": "DACs", "msg": 'V %i %.2f!' % (self.data["DAC output"], self.data['Initial voltage, V'])})
        self.device_widget.send(msg_to_server)

    def lockBtnPressed(self):
        print('connectBtnPressed')
        #  Starting parametres for PID
        # print('p =', self.P, 'i =', self.I, 'd =', self.D)
        self.P = 0
        self.I = 0
        self.D = 0
        print('p =', self.P, 'i =', self.I, 'd =', self.D)
        if self.lock:
            self.lock = False
            self.timer.stop()
            self.current_change_lbl.setText('')
            self.lock_btn.setStyleSheet("QWidget { background-color: %s }" % 'grey')
        else:
            self.lock_btn.setStyleSheet("QWidget { background-color: %s }" % 'green')
            self.last_time = datetime.datetime.now().timestamp()
            self.output_voltage = self.data['Initial voltage, V']
            self.error_log = []
            self.voltage_log = []
            self.lock=True
            self.error_flag = False
            self.timer.start()

    def unlock(self,msg):
        self.lock = False
        self.timer.stop()
        self.current_change_lbl.setText(msg)
        self.lock_btn.setStyleSheet("QWidget { background-color: %s }" % 'red')
        # self.arduino.write_com(('V %.2f!' % (self.initial_voltage)).encode())
        msg_to_server = json.dumps({"name": "DACs", "msg": 'V %i %.2f!' % (self.data["DAC output"], self.data['Initial voltage, V'])})
        self.device_widget.send(msg_to_server)

    def routine(self):
        msg = 'LOCK_BY_WM %s\n'%(self.data["Channel"])
        try:
            sock.sendto(bytes(msg, "utf-8"), (HOST, PORT))
            received = str(sock.recv(1024), "utf-8")
            #print("Received: {}".format(received))
        except Exception:
            return
        received = received.strip().split()
        if len(received) != 2:
            self.unlock('No channel')
            return
        meas_time = float(received[0])
        if abs(meas_time - self.last_time) < 1e-3: # no update in Wavemeter readings
            return
        dead_time = meas_time - self.last_time
        self.last_time = meas_time
        frequency = float(received[1])*1e6

        # print(datetime.datetime.now().timestamp(),meas_time,frequency)
        if (datetime.datetime.now().timestamp() - meas_time) > self.max_dead_time or frequency < 0 or abs(self.data['Target freq., MHz'] - frequency)>self.data['Threshold, MHz']:
            if self.error_flag:
                print('Second bad meas',frequency)
                print('Unlocking')
                self.unlock('Bad meas')
                return
            else:
                self.error_flag = True
                print('First bad meas',frequency)
                return
        self.error_flag = False
        error = self.data['Target freq., MHz'] - frequency
        self.error_log.append(error)
        self.output_plots.error_curve.setData(self.error_log)
        if abs(error) > self.data["Window, MHz"]:
            gain = self.data['Gain, mV/MHz']
            self.P = gain*error*1e-3 * self.data['K_p']
            self.I += gain*error*1e-3 * self.data['K_i']#* (dead_time/200e-3)
            self.D = gain * (error - self.error2)*1e-3 * self.data['K_d']
            self.error2 = error

            print ("P = ", self.P, "I = ", self.I, "D = ", self.D)
            self.output_voltage = self.data['Initial voltage, V'] + self.P + self.I + self.D #self.gain*error*1e-3  * (dead_time/50e3)
            if abs(self.output_voltage - self.data['Initial voltage, V']) > 0.5*self.data['Correction limit, V']:
                self.lock_btn.setStyleSheet("QWidget { background-color: %s }" % 'yellow')
            if abs(self.output_voltage - self.data['Initial voltage, V']) > 1*self.data['Correction limit, V']:
                self.unlock('Limit reached')
                return
            #print(self.output_voltage)
            if not self.device_widget.connected:
                self.unlock('Bad arduino')
                return
            # self.arduino.write_com(('V %.2f!'%(self.output_voltage)).encode())
            msg_to_server = json.dumps({"name": "DACs", "msg": 'V %i %.2f!'%(self.data["DAC output"], self.output_voltage)})
            self.device_widget.send(msg_to_server)
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
    mainWindow = LockTi_Sa()
    mainWindow.show()
    sys.exit(app.exec_())

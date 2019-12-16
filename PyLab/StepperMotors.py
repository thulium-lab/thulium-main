import os, re, pickle, json, matplotlib, time
import numpy as np
import sympy as sp
import datetime
#import anytree
from itertools import chain
from PyQt5.QtCore import (Qt, QObject, pyqtSignal, QTimer)
from PyQt5.QtWidgets import (QApplication, QScrollArea, QFrame, QMenu, QGridLayout, QVBoxLayout, QHBoxLayout,
                             QDialog, QLabel, QLineEdit, QPushButton, QWidget, QComboBox,QRadioButton, QCheckBox,
                             QTabWidget, QFileDialog, QAction, QMessageBox, QDoubleSpinBox, QSpinBox,QSpacerItem,
                             QMenuBar,QInputDialog)
from copy import deepcopy
import pyqtgraph as pg
from sympy.utilities.lambdify import lambdify
from sympy.parsing.sympy_parser import parse_expr
try:
    from .device_lib import COMPortDevice
except:
    from device_lib import COMPortDevice, COMPortWidget

DEBUG = 1
# from Devices.shutter import Shutter
# from Devices.DAQ import DAQHandler


matplotlib.use('Qt5Agg',force=True)
from collections import OrderedDict

from Lib import *

SCAN_PARAMS_STR = 'available_scan_params'
NAME_IN_SCAN_PARAMS = 'StepperMotors'

n_steps_validator = QIntValidator(1, 99)
state_validator = QIntValidator(0,1)
StepperLineDict = OrderedDict([
    ('Channel',['CB','Ch0',['Ch0','Ch1'],60]),
    ('Name', ['LE', 'New stepper', 120]),
    ('state',['MIB',0,state_validator,40]),
    ('n_steps',['MIB',0,n_steps_validator,40]),
    ('direction', ['CB', '+',['+','-'], 40]),
    ('forward',['MPB',60]),
    ('backward',['MPB',60]),
])


class StepperWidget(QScrollArea):
    class Line(QWidget):
        def __init__(self, parent, data={}):
            # print('---- shutterLine construct, data',data)
            # print(other_channels)
            super().__init__(parent)
            self.parent = parent
            layout = QHBoxLayout()
            self.data = data
            self._update_from_scanner = False
            self.autoUpdate = QTimer()
            self.autoUpdate.setInterval(500)
            self.autoUpdate.timeout.connect(self.update)
            self.widgets = {}
            for key, val in StepperLineDict.items():
                # print(key,val)
                if val[0] == 'MPB':
                    w = MyPushButton(name=key, handler=self.makeStep, fixed_width=val[-1])
                    layout.addWidget(w, val[-1])
                    continue
                self.data[key] = data.get(key, val[1])
                if val[0] == 'CB':
                    # create a combo box widget
                    w = MyComboBox(items=val[2], current_text=data.get(key, val[1]),
                                   current_index_changed_handler=self.autoUpdate.start,
                                   max_width=val[-1])
                elif val[0] == 'LE':
                    w = MyLineEdit(name=data.get(key, val[1]),
                                   text_changed_handler=self.textEdited,
                                   text_edited_handler=self.textEdited,
                                   max_width=val[-1])
                elif val[0] == 'MDB':
                    w = MyDoubleBox(validator=val[2], value=data.get(key, val[1]),
                                    text_changed_handler=self.update,
                                    text_edited_handler=self.textEdited,
                                    max_width=val[-1])
                elif val[0] == 'MIB':
                    w = MyIntBox(validator=val[2], value=data.get(key, val[1]),
                                 text_changed_handler=self.update,
                                 text_edited_handler=self.textEdited,
                                 max_width=val[-1])
                elif val[0] == 'MChB':
                    w = MyCheckBox(is_checked=data.get(key, val[1]), handler=self.autoUpdate.start,
                                   max_width=val[-1])
                self.widgets[key] = w
                layout.addWidget(w, val[-1])
            # print('---- shutterLine - end construct')
            # layout.setSpacing(0)
            layout.addStretch(1)
            layout.setSpacing(10)
            layout.setContentsMargins(5, 2, 5, 2)
            self.main_layout = layout
            self.setLayout(layout)
            self.setMinimumHeight(20)
            self.setMaximumWidth(550)
            # self.setMinimumHeight(50)
            # self.update()

        def textEdited(self):
            # print('TextEdited')
            if self._update_from_scanner:
                self.update()
            else:
                self.autoUpdate.start()

        def update(self):
            if DEBUG: print('---- StepperLine update')
            # print(str(self))
            self.autoUpdate.stop()
            # print('Here1')
            changed_item = {}
            for key, val in StepperLineDict.items():
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
                elif val[0] in ['MChB']:
                    if self.data[key] != self.widgets[key].isChecked():
                        changed_item[key] = (self.data[key], self.widgets[key].isChecked())
                        self.data[key] = self.widgets[key].isChecked()
            if DEBUG: print('Stepper line data changed: line:', self.data['Name'], changed_item)

            if not self._update_from_scanner:
                # autoSave.start() # do we need it here?
                if self.parent:
                    self.parent.lineChanged(self, changed_item)  # figure out how to handle this properly
            self._update_from_scanner = False

        def makeStep(self):
            key = self.sender().text()
            self.parent.lineChanged(self, {key: (key,key)})

        def constructData(self):
            return {key: self.widgets[key].getValue() for key in self.widgets}

        def getChannel(self):
            return self.data["Channel"]
        def getDirection(self):
            return self.data["direction"]
        def getNSteps(self):
            return self.data["n_steps"]

    def __init__(self,parent=None,globals={},signals={},port=None,data={},config_file=None):
        super().__init__(parent)
        self.config_file = config_file
        self.globals = globals
        self.signals = signals
        self.parent = parent
        self.port = port # now it is arduino com-port
        self.data = data
        self.load()
        # self.device = COMPortDevice(default_port=port)
        # self.device_widget = self.device.ExtendedWidget(data=self.device,connect= False)#(self.port!=None)

        self.device_widget = COMPortWidget(parent=self, connect=False, data=self.device,
                                           host_port=self.globals.get("host_port",("192.168.1.227", 9998)))
        self.device_widget.setMinimumWidth(300)
        self.arduino_readings = {"status":"Not connected",
                                 "last_msgs":[],
                                 "last_readings":[]}
        self.arduino_readings_length = 5
        self.arduino_msg_length = 3
        self.lines = []
        self.menuBar = QMenuBar(self)
        self.initUI()
        self.sendScanParams()
        self.autoSave = QTimer()
        self.autoSave.setInterval(10000)
        self.autoSave.timeout.connect(self.saveClicked)
        if self.signals:
            # self.signals.pulsesChanged.connect(self.constructPulses)
            self.signals.readingsFromArduino.connect(self.updateDeviceReadings)
            self.signals.serverComPortsUpdate.connect(self.device_widget.updateComPorts)

    def initUI(self):
        fileMenu = self.menuBar.addMenu('&File')
        # connect = QAction('&Connect', self)
        # connect.triggered.connect(self.connect)
        # fileMenu.addAction(connect)
        # load = QAction('&Load', self)
        # load.triggered.connect(self.loadDialog)
        # fileMenu.addAction(load)
        save = QAction('&Save', self)
        save.triggered.connect(self.saveClicked)
        fileMenu.addAction(save)

        self.setWindowTitle('Shutters')
        # self.setWindowIcon(QIcon('Devices\dds.jpg'))
        main_widget = QWidget()
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.device_widget)
        mainLayout = QVBoxLayout()
        # mainLayout.addSpacing(10)

        fields = QHBoxLayout()
        # fields.addSpacing(15)
        for key,val in StepperLineDict.items():
            lbl = QLabel(key)
            lbl.setMinimumWidth(val[-1])
            fields.addWidget(lbl)#, val[-1])
        # fields.addStretch(50)
        fields.setSpacing(10)
        fields.addStretch(1)
        mainLayout.addLayout(fields)

        for d in self.data:
            w = self.Line(self, data=d)
            self.lines.append(w)
            mainLayout.addWidget(w)


        mainLayout.addStretch(1)
        top_layout.addLayout(mainLayout)
        main_widget.setLayout(top_layout)
        main_widget.setMaximumWidth(1400)
        self.setWidgetResizable(True)
        self.setWidget(main_widget)
        self.setMinimumHeight(200)
        self.setMinimumWidth(550)
        self.main_layout = mainLayout

    # def addLine(self):
    #     # do not call anything after since one should first set "Channel to lock"
    #     w  = self.Line(parent=self, data={})
    #     self.lines.append(w)
    #     self.main_layout.insertWidget(len(self.lines), self.lines[-1])
    #     # self.save()
    #     return
    #
    # def delete(self, line):
    #     self.main_layout.removeWidget(line)
    #     line.deleteLater()
    #     self.lines.remove(line)
    #     # self.save()
    #     return

    def lineChanged(self,line, changes):
        # if DEBUG: print('--- stepperWidget - stepperChanged', changes)
        self.autoSave.stop()
        channel = line.getChannel()
        key = list(changes.keys())[0]
        new_value = changes[key][1]
        print(channel, key,new_value)
        if key not in ["forward","backward","state"]:
            return
        if key in ["forward","backward"]:
            msg = "move %s %i" % (channel[-1],1 if key=="forward" else -1)
        elif key == "state":
            direction = (1 if new_value == 1 else -1) * (1 if line.getDirection()=="+" else -1)
            msg = "move %s %i" % (channel[-1], direction * line.getNSteps())
        msg_to_server = json.dumps({"name": "Stepper", "msg": msg + "!"})
        print(msg_to_server)
        self.device_widget.send(msg_to_server)
        self.autoSave.start()

    def constructData(self):
        data = [line.constructData() for line in self.lines]
        return data

    def load(self):
        if DEBUG: print('load steppers', end='\t')
        with open(self.config_file, 'r') as f:
            if DEBUG: print('config_load')
            config = json.load(f)
        # print(config[NAME_IN_SCAN_PARAMS])
        self.__dict__.update(config[NAME_IN_SCAN_PARAMS])  # here one should upload current_scheme and available_channels


    def saveClicked(self):
        # print('save shutters', self)
        self.autoSave.stop()
        self.data = self.constructData()
        with open(self.config_file, 'r') as f:
            if DEBUG: print('config_load_before_saving')
            all_config = json.load(f)
        config = all_config[NAME_IN_SCAN_PARAMS]
        for key in config:
            config[key] = self.__dict__[key]
        with open(self.config_file, 'w') as f:
            if DEBUG: print('config_save')
            json.dump(all_config, f)

    def sendScanParams(self):
        params = {}
        data = self.constructData()
        for d in data:
            key = d['Name']
            params[key] = list(d.keys())
        if self.globals != None:
            if SCAN_PARAMS_STR not in self.globals:
                self.globals[SCAN_PARAMS_STR] = {}
            self.globals[SCAN_PARAMS_STR][NAME_IN_SCAN_PARAMS] = params
        return

    def updateDeviceReadings(self,msg):
        # print("updateDeviceReadings", msg)
        try:
            device, data = msg.split(' ', maxsplit=1)
        except ValueError as e:
            print("Exception whle reading msg from device", msg)
            return
        # print(device, self.device["name"])
        if device.strip() == self.device["name"].strip():
            if "connected" in data.lower():
                self.arduino_readings["status"] = data
            elif "IDN" in data:
                self.arduino_readings["status"] = "Connected"
            else:
                if len(self.arduino_readings["last_readings"]) >= self.arduino_readings_length:
                    self.arduino_readings["last_readings"]=self.arduino_readings["last_readings"][1:self.arduino_readings_length]
                self.arduino_readings["last_readings"].append(data)
            # print(self.arduino_readings)
            self.device_widget.updateReadingsNew(self.arduino_readings)

    def newCommandSent(self,msg):
        if len(self.arduino_readings["last_msgs"]) >= self.arduino_msg_length:
            self.arduino_readings["last_msgs"] = self.arduino_readings["last_msgs"][
                                                     1:self.arduino_msg_length]
        self.arduino_readings["last_msgs"].append(msg)
        # print(self.arduino_readings)
        self.device_widget.updateReadingsNew(self.arduino_readings)


if __name__ == '__main__':
    import sys
    # digital_pulses_folder = 'digital_schemes'
    # pulseGroup = PulseGroup
    app = QApplication(sys.argv)
    # mainWindow = PulseGroup(parent=None,name='New group',data=[])
    # mainWindow = PulseScheme()
    mainWindow = StepperWidget(config_file='config.json')
    mainWindow.show()
    sys.exit(app.exec_())

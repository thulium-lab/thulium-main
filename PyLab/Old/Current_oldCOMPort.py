import os, re, pickle, json, matplotlib, time
import numpy as np
import sympy as sp
import datetime
import anytree
from itertools import chain
from PyQt5.QtCore import (Qt, QObject, pyqtSignal, QTimer)
from PyQt5.QtWidgets import (QApplication, QScrollArea, QFrame, QMenu, QGridLayout, QVBoxLayout, QHBoxLayout,
                             QDialog, QLabel, QLineEdit, QPushButton, QWidget, QComboBox,QRadioButton, QCheckBox,
                             QTabWidget, QFileDialog, QAction, QMessageBox, QDoubleSpinBox, QSpinBox,QSpacerItem,
                             QMenuBar,QInputDialog)
from copy import deepcopy
from sympy.utilities.lambdify import lambdify
from sympy.parsing.sympy_parser import parse_expr
try:
    from .device_lib import COMPortDevice
except:
    from device_lib import COMPortDevice

DEBUG = 1
# from Devices.shutter import Shutter
# from Devices.DAQ import DAQHandler


matplotlib.use('Qt5Agg',force=True)
from collections import OrderedDict

from Lib import *

SCAN_PARAMS_STR = 'available_scan_params'
NAME_IN_SCAN_PARAMS = 'Current'

defauld_current_validator = QDoubleValidator(0,300,1)
CurrentLineDict = OrderedDict([
    ("Del",['MPB','Del',40]),
    ('Channel',['CB','C0',['C%i'%i for i in range(8)],60]),
    ('Name', ['LE', 'New shutter', 100]),
    ('I',['MDB',0,defauld_current_validator,60]),
    ('Off',['MChB',False,20]),
    ('Range',['CB',"300",["1","5","100","300"],60]),
])


class CurrentWidget(QScrollArea):
    class Line(QWidget):
        def __init__(self, parent, current_channels=[], data={}):
            # if DEBUG: print('---- currentLine construct, data',data)
            super().__init__(parent)
            self.parent = parent
            layout = QHBoxLayout()
            self.data = data
            self._update_from_scanner = False
            self.autoUpdate = QTimer()
            self.autoUpdate.setInterval(500)
            self.autoUpdate.timeout.connect(self.update)
            self.widgets = {}
            # print("gere")
            for key, val in CurrentLineDict.items():
                # print(key,val)
                # print(key)
                if key == 'Del':
                    w = MyPushButton(name=key,handler=lambda: self.parent.delete(self), fixed_width=val[-1])
                    layout.addWidget(w, val[-1])
                    continue
                self.data[key] = data.get(key, val[1])
                if val[0] == 'CB':
                    # create a combo box widget
                    items = val[2]
                    if key == 'Channel':
                        items = current_channels if current_channels != [] else val[2]
                    w = MyComboBox(items=items, current_text=data.get(key, val[1]),
                                   current_index_changed_handler=self.autoUpdate.start,
                                   max_width=val[-1])
                elif val[0] == 'LE':
                    w = MyLineEdit(name=data.get(key, val[1]),
                                   text_changed_handler=self.update,
                                   text_edited_handler=self.textEdited,
                                   max_width=val[-1])
                elif val[0] == 'MDB':
                    validator = val[2]
                    # print("FEDHDSI",key, self.data)
                    if key == "I":
                        # print("NEW OHGD")
                        if "Range" in self.data:
                            # print("NEW VALIDATOR")
                            validator = QDoubleValidator(0,float(self.data["Range"]),1)
                    w = MyDoubleBox(validator=validator, value=data.get(key, val[1]),
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
            # print('---- currentLine - end construct')
            # layout.setSpacing(0)
            layout.addStretch(1)
            layout.setSpacing(10)
            self.main_layout = layout
            self.setLayout(layout)
            self.setMinimumHeight(40)
            self.setMaximumWidth(550)
            # self.setMinimumHeight(50)
            # self.update()

        def update(self):
            # if DEBUG: print('---- currentLine update', self.data["Name"])
            # print(str(self))
            self.autoUpdate.stop()
            # print('Here1')
            changed_item = {}
            for key, val in CurrentLineDict.items():
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
            # if DEBUG: print('Current line data changed: line:', self.data['Name'], changed_item)

            if not self._update_from_scanner:
                # autoSave.start() # do we need it here?
                if self.parent:
                    self.parent.lineChanged(self, changed_item)  # figure out how to handle this properly
            self._update_from_scanner = False

        def textEdited(self):
            # print('TextEdited')
            if self._update_from_scanner:
                self.update()
            else:
                self.autoUpdate.start()

        def constructData(self):
            return {key: self.widgets[key].getValue() for key in self.widgets}

        def getName(self):
            return self.widgets["Name"].getValue()

        def updateFromScanner(self, param, value):
            self._update_from_scanner = True
            self.widgets[param].setValue(str(value))

    def __init__(self, parent=None, globals={}, signals={}, port=None, current_channels=[], data={}, config_file=None):
        super().__init__(parent)
        self.config_file = config_file
        self.globals = globals
        self.signals = signals
        self.parent = parent
        self.port = port # now it is arduino com-port
        self.data = data
        self.available_channels = current_channels
        self.load()
        self.device = COMPortDevice(default_port=port)
        self.lines = []
        self.menuBar = QMenuBar(self)
        self.device_widget = self.device.ExtendedWidget(data=self.device,connect= (self.port!=None))
        self.initUI()
        self.sendScanParams()
        self.old_pulses = {}
        self._update_from_scanner = False
        if self.signals:
            self.signals.pulsesChanged.connect(self.constructPulses)
            self.signals.updateFromScanner.connect(self.updateFromScanner)

    def initUI(self):
        fileMenu = self.menuBar.addMenu('&File')
        connect = QAction('&Connect', self)
        connect.triggered.connect(self.connect)
        fileMenu.addAction(connect)
        # load = QAction('&Load', self)
        # load.triggered.connect(self.loadDialog)
        # fileMenu.addAction(load)
        save = QAction('&Save', self)
        save.triggered.connect(self.saveClicked)
        fileMenu.addAction(save)

        self.setWindowTitle('Current')
        # self.setWindowIcon(QIcon('Devices\dds.jpg'))
        main_widget = QWidget()
        mainLayout = QVBoxLayout()
        # mainLayout.addSpacing(10)

        fields = QHBoxLayout()
        # fields.addSpacing(15)
        for key,val in CurrentLineDict.items():
            lbl = QLabel(key)
            lbl.setMinimumWidth(val[-1])
            fields.addWidget(lbl)#, val[-1])
        # fields.addStretch(50)
        fields.setSpacing(10)
        fields.addStretch(1)
        mainLayout.addLayout(fields)

        for d in self.data:
            w = self.Line(self, data=d, current_channels=self.available_channels)
            self.lines.append(w)
            mainLayout.addWidget(w)

        addLine = QPushButton('add current channel')
        addLine.setMaximumWidth(550)
        addLine.clicked.connect(self.addLine)
        mainLayout.addWidget(addLine)
        mainLayout.addStretch(1)
        main_widget.setLayout(mainLayout)
        main_widget.setMaximumWidth(1400)
        self.setWidgetResizable(True)
        self.setWidget(main_widget)
        self.setMinimumHeight(200)
        self.setMinimumWidth(550)
        self.main_layout = mainLayout

    def addLine(self):
        # do not call anything after since one should first set Channel to lock
        w  = self.Line(parent=self, current_channels=self.available_channels, data={"Off":True})
        self.lines.append(w)
        self.main_layout.insertWidget(len(self.lines), self.lines[-1])
        # self.save()
        return

    def delete(self, line):
        self.main_layout.removeWidget(line)
        line.deleteLater()
        self.lines.remove(line)
        # self.save()
        return

    def connect(self):
        print('--- CurrentWidget - connect')
        self.device_widget.show()

    def lineChanged(self,line, changes):
        # if DEBUG: print('--- currentWidget - lineChanged', changes)
        self.sendScanParams()
        self.constructPulses()
        # line_data = line.constructData()
        # print(line_data)

    def constructData(self):
        data = [line.constructData() for line in self.lines]
        return data

    def constructPulses(self):
        """constructs and updates pulses produced by Current channels"""
        if self.globals and "pulses" in self.globals:
            new_pulses = {channel:self.globals["pulses"][channel] for channel in self.globals["pulses"] if channel in self.available_channels}
            # if DEBUG: print('current pulses', new_pulses)
        else:
            new_pulses = {}
        lines_channeled = {line.data["Channel"]:line for line in self.lines}
        channels_data = {}
        for channel,line in lines_channeled.items():
            if line.data["Off"]:
                channels_data[channel]=[[0,0]]
            else:
                channels_data[channel] = [[0,line.data["I"]]]
            if channel in new_pulses:
                all_points = new_pulses[channel]
                # print(channel, [line.data["Channel"] for line in self.lines])
                # line = [line for line in self.lines if line.data["Channel"]==channel][0]
                if line.data["Off"]:
                    channels_data[channel]=[[0,0]]
                    continue
                new_points = []
                for points_group in all_points:
                    if new_points == []:
                        new_points.extend(points_group)
                    else:
                        # now assume that points_group has only 2 points!!! - otherwise it is nightmare
                        p_up = points_group[0]
                        p_down= points_group[1]
                        up_point_inserted=False
                        down_point_inserted = False
                        for p_new in new_points:
                            if p_up[0] <= p_new[0]:
                                if p_up[0] == p_new[0]:
                                    p_new[1] += p_up[1]
                                    up_index = new_points.index(p_new)
                                elif new_points.index(p_new) == 0:
                                    up_index = 0
                                    new_points.insert(up_index, p_up)
                                else:
                                    up_index = new_points.index(p_new)
                                    new_points.insert(up_index, p_up)
                                up_point_inserted = True
                                for p2_new in new_points[up_index+1:]:
                                    if p_down[0] > p2_new[0]:
                                        p2_new[1] += p_up[1]
                                    elif p_down[0] == p2_new[0]:
                                        down_point_inserted = True
                                        break
                                    else:
                                        down_index = new_points.index(p2_new)
                                        new_points.insert(down_index,[p_down[0],p2_new[1]])
                                        down_point_inserted = True
                                        break
                                if not down_point_inserted:
                                    new_points.append(p_down)
                                    break
                        if not up_point_inserted:
                            new_points.extend([p_up,p_down])
                    # print('new points',new_points)
                offset = line.data["I"]
                channels_data[channel]+=[[p[0],np.sign(p[1]+offset)*np.min([np.abs(p[1]+offset),float(line.data["Range"])])] for p in new_points]
        # print("current final data",channels_data)
        msg_to_server = json.dumps({"Current":channels_data})

        print("massege to server:", type(msg_to_server),msg_to_server)
        if self.signals:
            self.signals.sendMessageToDeviceServer.emit(msg_to_server)
            # send data to Current Controller

    def load(self):
        if DEBUG: print('load currents', end='\t')
        with open(self.config_file, 'r') as f:
            if DEBUG: print('config_load')
            config = json.load(f)
        # print(config)
        self.__dict__.update(config['Current'])

    def saveClicked(self):
        if DEBUG: print('save current')
        self.data = self.constructData()
        with open(self.config_file, 'r') as f:
            if DEBUG: print('config_load_before_saving')
            all_config = json.load(f)
        config = all_config['Current']
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

    def updateFromScanner(self):
        if DEBUG: print("Current - update from scanner")
        self._update_from_scanner = True
        params = self.globals["scan_running_data"]["new_main_params"] + self.globals["scan_running_data"]["new_low_params"]
        was_updated = False
        for param in params:
            if param["Param"][0] == "Current":
                for w in self.lines:
                    if w.getName() == param["Param"][1]:
                        was_updated = True
                        w.updateFromScanner(param=param["Param"][2],value=param["Value"])
        print(params)

if __name__ == '__main__':
    import sys
    # digital_pulses_folder = 'digital_schemes'
    # pulseGroup = PulseGroup
    app = QApplication(sys.argv)
    # mainWindow = PulseGroup(parent=None,name='New group',data=[])
    # mainWindow = PulseScheme()
    mainWindow = CurrentWidget(config_file='config.json')
    mainWindow.show()
    sys.exit(app.exec_())

import os, re, pickle, json, matplotlib, time
import numpy as np
import sympy as sp
import datetime
import anytree
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


SCHEMES_FOLDER = 'schemes'
CONFIG_FILE = 'config_pulses.json'
CONFIG_SHUTTERS_FILE = 'config_shutters.json'
config_scheme_file = 'config_scheme'
pulse_name_suffix = '.pls'
scan_params_str = 'scan_params'
name_in_scan_params = 'Pulses'
pulse_output_str = 'pulse_output'
last_scheme_setup = 'last_scheme'

from Lib import *

# LineDict form ('name of variable',[widget type, default value,other parameters,width of the widget])
# 'CB' - ComboBox, 'LE' - LineEdit, 'MB' - MyBox
time_validator = QDoubleValidator(-9999,9999,3)
group_time_validator = QDoubleValidator(0.001,9999,3)
n_validator = QIntValidator(1,99)
shutter_validator = QDoubleValidator(0,9.9,1)
PulseLineDict = OrderedDict([
    ('Channel',['CB','0',list(map(str, range(16))),60]),
    ('Name',['LE','New line',120]),
    ('Edge',['CB','Begin',['Begin', 'End'],60]),
    ('Delay',['MDB',0,time_validator,60]),
    ('Length',['MDB',0,time_validator,60]),
    ('N',['MIB',1,n_validator,20]),
    ('On',['MChB',False,20])
])

ShutterLineDict = OrderedDict([
    ("Del",['MPB','Del',40]),
    ('Channel',['CB','S0',['S%i'%i for i in range(8)],60]),
    ('Name', ['LE', 'New shutter', 120]),
    ('t_open',['MDB',0,shutter_validator,60]),
    ('t_close',['MDB',0,shutter_validator,60]),
    ('oOn', ['MChB', False, 20]),
    ('oOff',['MChB',False,20]),
    ('Lock to Channel',['CB',None,[],60]),
])

autoSave = QTimer()
autoSave.setInterval(5000)

class ShutterWidget(QScrollArea):
    class Line(QWidget):
        def __init__(self, parent,shutter_channels=[],other_channels=[], data={}):
            print('---- shutterLine construct, data',data)
            print(other_channels)
            super().__init__(parent)
            self.parent = parent
            layout = QHBoxLayout()
            self.data = data
            self._update_from_scanner = False
            self.autoUpdate = QTimer()
            self.autoUpdate.setInterval(500)
            self.autoUpdate.timeout.connect(self.update)
            self.widgets = {}
            for key, val in ShutterLineDict.items():
                # print(key,val)
                if key == 'Del':
                    w = MyPushButton(name=key,handler=lambda: self.parent.delete(self), fixed_width=val[-1])
                    layout.addWidget(w, val[-1])
                    continue
                self.data[key] = data.get(key, val[1])
                if val[0] == 'CB':
                    # create a combo box widget
                    if key == 'Channel':
                        items = shutter_channels if shutter_channels != [] else val[2]
                    elif key == 'Lock to Channel':
                        items = ['0'] + (other_channels if other_channels != [] else val[2])
                    w = MyComboBox(items=items, current_text=data.get(key, val[1]),
                                   current_index_changed_handler=self.autoUpdate.start,
                                   max_width=val[-1])
                elif val[0] == 'LE':
                    w = MyLineEdit(name=data.get(key, val[1]),
                                   text_changed_handler=self.update,
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
            print('---- shutterLine - end construct')
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
            if DEBUG: print('---- ShutterLine update')
            # print(str(self))
            self.autoUpdate.stop()
            # print('Here1')
            changed_item = {}
            for key, val in ShutterLineDict.items():
                if val[0] == 'CB':  # do a combo box widget
                    if self.data[key] != self.widgets[key].currentText():
                        print(self.data[key])
                        print(self.widgets[key].currentText())
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
            if DEBUG: print('Shutter line data changed: line:', self.data['Name'], changed_item)

            if not self._update_from_scanner:
                # autoSave.start() # do we need it here?
                if self.parent:
                    self.parent.lineChanged(self, changed_item)  # figure out how to handle this properly
            self._update_from_scanner = False

        def textEdited(self):
            print('TextEdited')
            if self._update_from_scanner:
                self.update()
            else:
                self.autoUpdate.start()

        def constructData(self):
            return {key: self.widgets[key].getValue() for key in self.widgets}

    def __init__(self,parent=None,port=None,shutter_channels=[],other_channels=[],data={}):
        super().__init__(parent)
        self.parent = parent
        self.port = port # now it is arduino com-port
        self.data = data
        self.device = COMPortDevice(default_port=port)
        self.lines = []
        self.shutter_channels = shutter_channels
        self.other_channels = other_channels
        self.menuBar = QMenuBar(self)
        # self.delayedSaveTime = QTimer()
        # self.delayedSaveTime.setInterval()
        # # specify identifications
        # if self.port != None:
        #     try:
        #         self.device.connect()
        #     except:
        #         print('Can not connect shutter device', self.port)
        #         self.device.connected = False
        self.device_widget = self.device.ExtendedWidget(data=self.device,connect= (self.port!=None))
        self.initUI()

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

        self.setWindowTitle('Shutter')
        # self.setWindowIcon(QIcon('Devices\dds.jpg'))
        main_widget = QWidget()
        mainLayout = QVBoxLayout()
        # mainLayout.addSpacing(10)

        fields = QHBoxLayout()
        # fields.addSpacing(15)
        for key,val in ShutterLineDict.items():
            lbl = QLabel(key)
            lbl.setMinimumWidth(val[-1])
            fields.addWidget(lbl)#, val[-1])
        # fields.addStretch(50)
        fields.setSpacing(10)
        fields.addStretch(1)
        mainLayout.addLayout(fields)

        for d in self.data:
            w = self.Line(self, data=d, shutter_channels=[], other_channels={})
            self.lines.append(w)
            mainLayout.addWidget(w)

        addLine = QPushButton('add shutter')
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
        w  = self.Line(parent=self, shutter_channels=self.shutter_channels, other_channels=self.other_channels,data={})
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
        print('--- ShutterWidget - connect')
        self.device_widget.show()

    def lineChanged(self,line, changes):
        if DEBUG: print('--- shutterWidget - shutterChanged', changes)
        line_data = line.constructData()
        print(line_data)
        if 'Lock to Channel' in changes:
            PulseSignals().shutterChannelChangedSignal.emit

        # print(isinstance(pulse,GroupLine))
        # if isinstance(pulse,GroupLine) and 'Name' in changes.keys(): # or one can replace to pulse_data['Type']=='Group'
        #     if DEBUG: print('GroupLine pulse changed')
        #     self.name = changes['Name'][1]
        #     self.parent.groupChanged(self,'group_name_changed',changes['Name'])
        # else:
        #     self.parent.groupChanged(self, 'pulse_changed')

    def constructData(self):
        data = [line.constructData() for line in self.lines]
        return data

    def saveClicked(self):
        print('save shutters', self)
        with open(CONFIG_SHUTTERS_FILE, 'r') as f:
            if DEBUG: print('config_load_before_saving')
            config = json.load(f)
        for key in config:
            config[key] = self.__dict__[key]
            config = {'data'}
        with open(CONFIG_SHUTTERS_FILE, 'w') as f:
            if DEBUG: print('config_save')
            json.dump(config, f)


class PulseSignals(QObject):
    # here all possible signals by Pulse class should be declared
    onAnyChangeSignal = pyqtSignal()
    shutterChannelChangedSignal = pyqtSignal()

class SimpleLine(QWidget):
    def __init__(self, parent, data={}):
        super().__init__(parent)
        self.parent = parent
        layout = QHBoxLayout()
        self.data = data
        self._update_from_scanner = False
        self.autoUpdate = QTimer()
        self.autoUpdate.setInterval(500)
        self.autoUpdate.timeout.connect(self.update)
        self.widgets = {}
        for key, val in PulseLineDict.items():
            # print(key,val)
            self.data[key] = data.get(key, val[1])
            if key in ['Channel']:
                # self.data[key]=None
                continue

            if val[0] == 'CB':
                # create a combo box widget
                w = MyComboBox(items=val[2], current_text=data.get(key, val[1]),
                               current_index_changed_handler=self.autoUpdate.start,
                               max_width=val[-1])
            elif val[0] == 'LE':
                w = MyLineEdit(name=data.get(key, val[1]),
                               text_changed_handler=self.update,
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
                w = MyCheckBox(is_checked=data.get(key, val[1]),handler=self.autoUpdate.start,
                               max_width=val[-1])
            self.widgets[key] = w
            layout.addWidget(w, val[-1])


        layout.addStretch(1)
        layout.setSpacing(10)
        self.main_layout = layout
        self.setLayout(layout)
        self.setMinimumHeight(40)
        self.setMaximumWidth(700)
        # self.setMinimumHeight(50)
        # self.update()

    def update(self):
        if DEBUG: print('PulseLine update')
        # print(str(self))
        self.autoUpdate.stop()
        print('Here1')
        changed_item = {}
        for key, val in PulseLineDict.items():
            if key == 'Channel' and 'Channel' not in self.widgets:
                self.data['Channel'] = None
                continue
            if val[0] == 'CB':  # do a combo box widget
                if self.data[key] != self.widgets[key].currentText():
                    print(self.data[key])
                    print(self.widgets[key].currentText())
                    changed_item[key] = (self.data[key],self.widgets[key].currentText())
                    self.data[key] = self.widgets[key].currentText()
            elif val[0] == 'LE':
                if self.data[key] != self.widgets[key].text():
                    changed_item[key] = (self.data[key], self.widgets[key].text())
                    self.data[key] = self.widgets[key].text()
            elif val[0] in ['MDB','MIB']:
                if self.data[key] != self.widgets[key].value():
                    changed_item[key] = (self.data[key], self.widgets[key].value())
                    self.data[key] = self.widgets[key].value()
            elif val[0] in ['MChB']:
                if self.data[key] != self.widgets[key].isChecked():
                    changed_item[key] = (self.data[key], self.widgets[key].isChecked())
                    self.data[key] = self.widgets[key].isChecked()
        if DEBUG: print('Pulse line data changed: line:', self.data['Name'], changed_item)

        if not self._update_from_scanner:
            # autoSave.start() # do we need it here?
            if self.parent:
                self.parent.pulseChanged(self,changed_item)  # figure out how to handle this properly
        self._update_from_scanner = False

    def textEdited(self):
        print('TextEdited')
        if self._update_from_scanner:
            self.update()
        else:
            self.autoUpdate.start()

    def constructData(self):
        return {key:self.widgets[key].getValue() for key in self.widgets}

    def updateFromScanner(self, param, val):
        self._update_from_scanner = True
        if param not in self.widgets:
            print('PulseLine, param not in the dictionary')
            return 1
        if self.widgets[param].setValue(val):  # returns 1 if error
            return 1
        else:
            return 0


class PulseLine(SimpleLine):
    def __init__(self, parent, data={},channels=[]):
        # data is a dictionary of
        self.data = {'Type':'Pulse'}
        self.data.update(data)
        super().__init__(parent,self.data)
        if channels == []:
            channels = PulseLineDict['Channel'][2]
        self.delBtn = MyPushButton(name='del', handler=lambda: self.parent.deleteLine(self), fixed_width=30)
        self.main_layout.insertWidget(0,self.delBtn)
        w = MyComboBox(items=channels, current_text=data.get('Channel', PulseLineDict['Channel'][1]),
                                                      current_index_changed_handler=self.autoUpdate.start,
                                                      max_width=PulseLineDict['Channel'][-1])
        self.widgets['Channel']=w
        self.main_layout.insertWidget(1,w)
        # self.data['Channel']
        # self.update()

    def constructData(self):
        self.data.update(super().constructData())
        self.data['Channel'] = self.widgets['Channel'].getValue()
        # res['Type'] = 'Pulse'
        return self.data

    def getPoints(self,group_times):
        print('Get points, group_times', group_times, self.widgets['Name'].getValue())
        if not self.widgets['On'].isChecked():
            return []
        group_single_pulse_length = group_times[0][1]-group_times[0][0]
        if self.widgets['Edge'].getValue() == 'Begin':
            print('HERERE')
            t_start = self.widgets['Delay'].getValue()
            if self.widgets['Length'].getValue() == 0:
                t_end = group_single_pulse_length
            elif self.widgets['Length'].getValue() > 0:
                t_end = t_start + self.widgets['Length'].getValue()
            else:
                t_end = group_single_pulse_length + self.widgets['Length'].getValue()
        else:
            if self.widgets['Length'].getValue() == 0:
                t_start =  group_single_pulse_length - abs(self.widgets['Delay'].getValue())
                t_end = group_single_pulse_length
            elif self.widgets['Length'].getValue() > 0:
                t_start = group_single_pulse_length + self.widgets['Delay'].getValue()
                t_end = t_start + self.widgets['Length'].getValue()
            else:
                t_end = group_single_pulse_length + self.widgets['Delay'].getValue()
                t_start = t_end + self.widgets['Length'].getValue()
        points = []
        print('getPoints, t_start, t_end', t_start, t_end)
        for gp in group_times: # more carefully handle all possibilities
            points.extend([ (gp[0] + t_start + i*(t_start+t_end),gp[0] + t_end +i*(t_start+t_end))
                            for i in range(self.widgets['N'].getValue())])
        print('---- before return',self.widgets['Channel'].getValue())
        return [self.widgets['Channel'].getValue(),points]

    @staticmethod
    def combinePoints(points):
        return points


class GroupLine(SimpleLine):
    def __init__(self, parent, data={}):
        # data is a dictionary of
        self.data = {'Type': 'Group'}
        self.data.update(data)
        print('---- Group line, data:',self.data)
        super().__init__(parent,data)

        w =QLabel('')
        w.setFixedWidth(78)
        self.main_layout.insertWidget(0,w)
        # self.widgets['Length'].setValue('1')
        self.widgets['Length'].setValidator(group_time_validator)
        # self.update()

    def constructData(self):
        self.data.update(super().constructData())
        self.data['Channel'] = 'None'
        # res['Type'] = 'Group'
        return self.data

class DigitalLine(PulseLine):
    def __init__(self, parent, data={},channels=[]):
        # data is a dictionary of
        print('---- Digital Line')
        self.data = {'Type': 'Digital'}
        self.data.update(data)
        super().__init__(parent,data=self.data,channels=channels)
        self.shutterBtn = MyPushButton(name='Shutter',handler=self.shutterBtnPressed,
                                       fixed_width=50)
        self.main_layout.insertWidget(8,self.shutterBtn)

    def shutterBtnPressed(self):
        print('---- Digital line - shutter')

    @staticmethod
    def combinePoints(points):
        combined_points = []
        for point in sorted(points):
            if combined_points == []:
                combined_points.append(list(point))
            else:
                if point[0] > combined_points[-1][1]:
                    combined_points.append(list(point))
                else:
                    if point[1] > combined_points[-1][1]:
                        combined_points[-1][1] = point[1]
        return combined_points

class AnalogLine(PulseLine):
    def __init__(self, parent, data={},channels=[]):
        # data is a dictionary of
        print('---- Analog Line')
        self.data = {'Type': 'Analog'}
        self.data.update(data)
        super().__init__(parent,data=self.data,channels=channels)
        self.shapeBtn = MyPushButton(name='Shape',handler=self.shapeBtnPressed,
                                       fixed_width=50)
        self.main_layout.insertWidget(8,self.shapeBtn)

    def shapeBtnPressed(self):
        print('---- Analog line - shape')

class InputLine(PulseLine):
    def __init__(self, parent, data={},channels=[]):
        # data is a dictionary of
        print('---- Input Line')
        self.data = {'Type': 'Input'}
        self.data.update(data)
        super().__init__(parent,data=self.data,channels=channels)
        self.shapeBtn = MyPushButton(name='Conf',handler=self.confBtnPressed,
                                       fixed_width=50)
        self.main_layout.insertWidget(8,self.shapeBtn)

    def confBtnPressed(self):
        print('---- Input line - config')

class CurrentLine(PulseLine):
    def __init__(self, parent, data={},channels=[]):
        # data is a dictionary of
        print('---- Current Line')
        self.data = {'Type': 'Current'}
        self.data.update(data)
        print('---- Current channels',channels)
        super().__init__(parent,data=self.data,channels=channels)
        self.shapeBtn = MyPushButton(name='Conf',handler=self.confBtnPressed,
                                       fixed_width=50)
        self.main_layout.insertWidget(8,self.shapeBtn)

    def confBtnPressed(self):
        print('---- Current line - config')
# PULSE_LINE_CONSTRUCTORS = {'Digital':DigitalPulse,
#                            'Analog':AnalogPulse,
#                            'Input':InputPulse,
#                            'Current':CurrentPulse}

PULSE_LINE_CONSTRUCTORS = OrderedDict({'Digital':DigitalLine,
                           'Analog':AnalogLine,
                           'Input':InputLine,
                           'Current':CurrentLine,
                           'Pulse':PulseLine})

# class PulseLine(QWidget):
#     def __init__(self, parent, data={}):
#         # data is a dictionary of
#         super().__init__(parent)
#         self.parent = parent
#         layout = QHBoxLayout()
#         self.data = data
#         self._update_from_scanner = False
#         self.autoUpdate = QTimer()
#         self.autoUpdate.setInterval(100)
#         self.autoUpdate.timeout.connect(self.update)
#         self.delBtn = MyPushButton(name='del', handler=lambda: self.parent.deleteLine(self), fixed_width=30)
#         layout.addWidget(self.delBtn)
#         self.widgets = {}
#         for key, val in PulseLineDict.items():
#             # print(key,val)
#             self.data[key] = data.get(key, val[1])
#             if val[0] == 'CB':
#                 # create a combo box widget
#                 w = MyComboBox(items=val[2], current_text=data.get(key, val[1]),
#                                current_index_changed_handler=self.autoUpdate.start,
#                                max_width=val[-1])
#             elif val[0] == 'LE':
#                 w = MyLineEdit(name=data.get(key, val[1]),
#                                text_changed_handler=self.update,
#                                text_edited_handler=self.textEdited,
#                                max_width=val[-1])
#             elif val[0] == 'MDB':
#                 w = MyDoubleBox(validator=val[2], value=data.get(key, val[1]),
#                                 text_changed_handler=self.update,
#                                 text_edited_handler=self.textEdited,
#                                 max_width=val[-1])
#             elif val[0] == 'MIB':
#                 w = MyIntBox(validator=val[2], value=data.get(key, val[1]),
#                              text_changed_handler=self.update,
#                              text_edited_handler=self.textEdited,
#                              max_width=val[-1])
#             self.widgets[key] = w
#             layout.addWidget(w, val[-1])
#
#         layout.addStretch(1)
#         layout.setSpacing(10)
#         self.setLayout(layout)
#         self.setMinimumHeight(40)
#         self.setMaximumWidth(700)
#         # self.setMinimumHeight(50)
#         self.update()
#
#     def update(self):
#         if DEBUG: print('PulseLine update')
#         # print(str(self))
#         self.autoUpdate.stop()
#         for key, val in PulseLineDict.items():
#             if val[0] == 'CB':  # do a combo box widget
#                 self.data[key] = self.widgets[key].currentText()
#             elif val[0] == 'LE':
#                 self.data[key] = self.widgets[key].text()
#             elif val[0] in ['MDB','MIB']:
#                 self.data[key] = self.widgets[key].value()
#         if DEBUG: print('Pulse line data', self.data)
#
#         if not self._update_from_scanner:
#             # autoSave.start() # do we need it here?
#             if self.parent:
#                 self.parent.pulseChanged(self)  # figure out how to handle this properly
#         self._update_from_scanner = False
#
#     def textEdited(self):
#         print('TextEdited')
#         if self._update_from_scanner:
#             self.update()
#         else:
#             self.autoUpdate.start()
#
#     def updateFromScanner(self,param, val):
#         self._update_from_scanner = True
#         if param not in self.widgets:
#             print('PulseLine, param not in the dictionary')
#             return 1
#         if self.widgets[param].setValue(val):  # returns 1 if error
#             return 1
#         else:
#             return 0
#     # def __call__(self):
#     #     # self.data={}
#     #     for key, val in PulseLineDict.items():
#     #         if val[0] == 'CB':  # do a combo box widget
#     #             self.data[key] = self.widgets[key].currentText()
#     #         elif val[0] == 'LE':
#     #             self.data[key] = self.widgets[key].text()
#     #         elif val[0] in ['MDB','MIB']:
#     #             self.data[key] = self.widgets[key].value()
#     #     # data['formula'] =
#     #     # return self.data
#     #
#     # def __str__(self):
#     #     data = self.__call__()
#     #     i = data['name'].find('<0')
#     #     m = 1
#     #     if i >= 0:
#     #         m = float(data['name'][i + 1:])
#     #     m = min(m, 1)
#     #     m = max(m, 0)
#     #     if data['mode'] == 'SingleTone':
#     #         points = ''
#     #     else:
#     #         sp_form = re.split("([+-/*()])", data['wForm'])
#     #         sp_form = [s.strip() for s in sp_form]
#     #         for i, s in enumerate(sp_form):
#     #             if s in PulseLineDict.keys():
#     #                 sp_form[i] = str(data[s])
#     #         formula = ''.join(sp_form)
#     #         try:
#     #             formula = parse_expr(formula)
#     #             t = sp.symbols('t')
#     #             func = np.vectorize(lambdify(t, formula, 'numpy'))
#     #             xs = np.linspace(start=0, stop=float(data['length']), num=1024)
#     #             ys = func(xs)
#     #             points = ' '.join("{:.5f}".format(min(max(y, 0), m)) for y in ys)
#     #         except Exception as e:
#     #             print("dds: bad formula")
#     #             points = '0 0 0'
#     #     data['amp'] = str(min(max(float(data['amp']), 0), m))
#     #     data['amp2'] = str(min(max(float(data['amp2']), 0), m))
#     #     args = [data['index'], data['name'], data['mode'], int(data['osk']),
#     #             int(data['ndl']), int(data['ndh']), data['freq'], data['amp'],
#     #             data['fall'], data['rise'], data['lower'], data['upper'], points,
#     #             data['length'], data['freq2'], data['amp2'], 0, 0, 0, '', 1, 1, 1]
#     #     return 'setChannel(' + ','.join(map(str, args)) + ');'

# class GroupLine(QWidget):
#     def __init__(self, parent, data={}):
#         super().__init__(parent)
#         self.parent = parent
#         layout = QHBoxLayout()
#         self.data = data
#         self._update_from_scanner = False
#         self.autoUpdate = QTimer()
#         self.autoUpdate.setInterval(100)
#         self.autoUpdate.timeout.connect(self.update)
#         w = QLabel('')
#         w.setFixedWidth(90)
#         layout.addWidget(w)
#         self.widgets = {}
#         for key, val in PulseLineDict.items():
#             # print(key,val)
#             if key in ['Channel']:
#                 continue
#             self.data[key] = data.get(key, val[1])
#             if val[0] == 'CB':
#                 # create a combo box widget
#                 w = MyComboBox(items=val[2], current_text=data.get(key, val[1]),
#                                current_index_changed_handler=self.autoUpdate.start,
#                                max_width=val[-1])
#             elif val[0] == 'LE':
#                 w = MyLineEdit(name=data.get(key, val[1]),
#                                text_changed_handler=self.update,
#                                text_edited_handler=self.textEdited,
#                                max_width=val[-1])
#             elif val[0] == 'MDB':
#                 w = MyDoubleBox(validator=val[2], value=data.get(key, val[1]),
#                                 text_changed_handler=self.update,
#                                 text_edited_handler=self.textEdited,
#                                 max_width=val[-1])
#             elif val[0] == 'MIB':
#                 w = MyIntBox(validator=val[2], value=data.get(key, val[1]),
#                              text_changed_handler=self.update,
#                              text_edited_handler=self.textEdited,
#                              max_width=val[-1])
#             self.widgets[key] = w
#             layout.addWidget(w, val[-1])
#
#         layout.addStretch(1)
#         layout.setSpacing(10)
#         self.setLayout(layout)
#         self.setMinimumHeight(40)
#         self.setMaximumWidth(700)
#         # self.setMinimumHeight(50)
#         self.update()
#
#     def textEdited(self):
#         print('TextEdited')
#         if self._update_from_scanner:
#             self.update()
#         else:
#             self.autoUpdate.start()
#
#     def updateFromScanner(self, param, val):
#         self._update_from_scanner = True
#         if param not in self.widgets:
#             print('PulseLine, param not in the dictionary')
#             return 1
#         if self.widgets[param].setValue(val):  # returns 1 if error
#             return 1
#         else:
#             return 0

class PulseGroup(QScrollArea):

    def __init__(self, parent=None, name='Default group', reference='0', reference_list=['0'], data=[]):
        """data is a dictionary of lines"""
        super(PulseGroup,self).__init__(parent)
        self.parent = parent
        self.name = name
        self.data = data
        self.update_from_scheme = False
        self.autoUpdate = QTimer()
        self.autoUpdate.setInterval(100)
        self.delayTimer = QTimer()
        self.delayTimer.setInterval(100)
        # print(self.data)
        if not self.data and 'Group' not in [d['Type'] for d in self.data]:
            self.data.insert(0,{'Type':'Group','Channel':None,'Name':self.name, 'Edge':'Begin', 'Delay':0,'Lendth':10,'N':1})
        self.reference = reference
        self.pulses = []
        # print(self.data)
        main_widget = QWidget()
        main_layout = QVBoxLayout()

        topbox = QHBoxLayout()

        topbox.addWidget(QLabel('Reference'))
        # items = ['0']
        # if self.parent and hasattr(self.parent, 'getGroupNames'):
        #     items += self.parent.getGroupNames()
        self.refBox = MyComboBox(current_text=reference,items=[x for x in reference_list if x != self.name],
                       current_text_changed_handler=self.refChanged,min_width=70)
        # self.setReferenceList(reference_list)
        topbox.addWidget(self.refBox)
        self.addBtn = MyPushButton(name='Add Pulse', handler=self.addPulse, fixed_width=60)
        topbox.addWidget(self.addBtn)
        self.delBtn = MyPushButton(name='Del Group', handler=lambda: self.parent.deleteGroup(self), fixed_width=60)
        topbox.addWidget(self.delBtn)
        topbox.addStretch(1)
        topbox.setSpacing(10)
        main_layout.addLayout(topbox)

        # construct pulse group
        self.group_line = GroupLine(parent=self,data=[d for d in self.data if d['Type']=='Group'][0])
        self.pulses.append(self.group_line)
        main_layout.addWidget(self.group_line)
        main_layout.addLayout(self.addLabelLine())

        for pulse in self.data:
            if pulse['Type'] != 'Group':
                if self.parent:
                    # print('HereThere')
                    channels = self.parent.__dict__["available_channels"][pulse['Type']]
                    # print(channels)
                else:
                    channels = []
                w = PULSE_LINE_CONSTRUCTORS[pulse['Type']](parent=self, data=pulse,channels=channels)
                self.pulses.append(w)
                main_layout.addWidget(w)

        main_layout.addStretch(1)
        self.main_layout = main_layout
        main_widget.setLayout(main_layout)
        self.main_layout.setSpacing(0)
        self.setWidget(main_widget)
        self.setMinimumHeight(400)
        self.setWidgetResizable(True)
        self.setMinimumWidth(700)
        print('FINISHED GROUP',self.name)
        self.update_from_scheme = False

    def refChanged(self,new_ref): # new
        print('--- refChanged')
        self.reference = new_ref
        if not self.update_from_scheme:
            self.parent.groupChanged(self,'reference')
        self.update_from_scheme = False

    def setReferemceList(self,reference_list,changes=[]): # new
        print("Set reference", self.name, self.reference)
        if changes:
            if self.reference == changes[0]: # this group was reference to changed group
                self.reference = changes[1] # set new name for the reference
        temp = self.reference
        while self.refBox.count():
            self.refBox.removeItem(0)
        self.refBox.addItems([x for x in reference_list if x != self.name])
        # print('check', self.reference in [x for x in referene_list if x != self.name])
        self.reference = temp
        self.update_from_scheme = True
        self.refBox.setCurrentText(self.reference)
        print(self.name, 'ref->', self.reference)

    def addLabelLine(self):
        layout = QHBoxLayout()
        w = QLabel("")
        w.setFixedWidth(40)
        layout.addWidget(w)
        for key,val in PulseLineDict.items():
            w = QLabel(key)
            w.setFixedWidth(val[-1])
            layout.addWidget(w)
        layout.addStretch(1)
        layout.setSpacing(10)
        return layout

    def deleteLine(self, line):
        self.main_layout.removeWidget(line)
        line.deleteLater()
        self.pulses.remove(line)
        # del self.data[line.data['Name']]
        # self.save()
        self.parent.groupChanged(self,'pulse_deleted')
        return

    def addPulse(self):
        new_pulse_type, ok_pressed = QInputDialog.getItem(self, "Choose type of new pulse",
                                     "Type:", PULSE_LINE_CONSTRUCTORS.keys(),
                                     0, False)
        if ok_pressed:
            print('New pulse type', new_pulse_type)
            if self.parent:
                # print('HereThere')
                channels = self.parent.__dict__["available_channels"][new_pulse_type]
                # print(channels)
            else:
                channels = []
            self.pulses.append( PULSE_LINE_CONSTRUCTORS[new_pulse_type](parent=self,data={'Name':'New','Type':new_pulse_type},
                                                                        channels=channels))
            # print(self.layout())
            self.main_layout.insertWidget(len(self.pulses)+1,self.pulses[-1],0)
            self.main_layout.setSpacing(0)
            self.parent.groupChanged(self, 'pulse_added')
        # self.main_widget.setMinimumHeight(self.main_widget.minimumHeight() + 50)
        # self.save()
        return

    def constructData(self):
        # print('pulseGroup-construct data',self.name)
        res = {"name": self.name, "reference": self.reference, "data": [pulse.constructData() for pulse in self.pulses]}
        # print('data', res)
        return res

    def pulseChanged(self,pulse,changes):
        if DEBUG: print('PulseGroup: Pulse changed')
        # pulse_data = pulse.constructData()
        # print(isinstance(pulse,GroupLine))
        if isinstance(pulse,GroupLine) and 'Name' in changes.keys(): # or one can replace to pulse_data['Type']=='Group'
            if DEBUG: print('GroupLine pulse changed')
            self.name = changes['Name'][1]
            self.parent.groupChanged(self,'group_name_changed',changes['Name'])
        else:
            self.parent.groupChanged(self, 'pulse_changed')
            # if pulse_data['Name'] != self.name:
            #     self.name = pulse_data['Name']
            #     self.parent.groupNameChanged(self)

        # if len(self.pulses) == 0:
        #     self.pulses.append(IndividualPulse())

        # t_start  # absolute time of the beginning of the group
        # t_end  # absolute time of the end of the group

    def constructTiming(self,ref_boundaties):
        print('REF BOUNDARIES', ref_boundaties)
        if ref_boundaties == 0: # starts from the beginning, ignore edge
            t0 = 0
        else:
            t0 = ref_boundaties[0] if self.group_line.widgets['Edge'].getValue() == 'Begin' else ref_boundaties[1]
        # print(self.group_line.widgets)
        t_start = t0 + self.group_line.widgets['Delay'].getValue()
        t_end = t_start + self.group_line.widgets['Length'].getValue()
        print(t_start,t_end)
        self.group_times = [(t_start + i*(t_end-t0),t_end + i*(t_end-t0)) for i in range(self.group_line.widgets['N'].getValue())]
        print('GT',self.group_times)
        if self.group_line.widgets['On'].isChecked():
            print('Here')
            # print([line.__dict__ for line in self.pulses])
            # print(self.pulses)
            points_by_channel = [line.getPoints(self.group_times) for line in self.pulses if line.data['Type'] != 'Group']
            points_by_channel = [p for p in points_by_channel if p!=[]]
            print('pbch1',points_by_channel)

            print('end',self.group_times)
            return points_by_channel
        else:
            return []

    def getGroupBoundaries(self):
        return (self.group_times[0][0],self.group_times[-1][1])

    def getReferencePoint(self,scheme): #old
        if self.ref == '0':
            return 0
        else:
            predecessor = scheme.pulseByName(self.ref)
            return self.edge * predecessor.length + predecessor.getReferencePoint(scheme)

    # class PulseGroupQt(QWidget):
    #
    #     def __init__(self, data=None,scheme=None):
    #         # self.channels = [str(i) for i in range(10)]
    #         self.n_decimals = 2
    #         self.data = data
    #         self.scheme = scheme
    #         super().__init__()
    #         self.initUI()
    #
    #     def initUI(self):
    #         print('initUI-scheme PulseGroup')
    #         main_box = QVBoxLayout()
    #         topbox = QHBoxLayout()
    #         # main_box.setSpacing(2)
    #
    #         topbox.addWidget(QLabel('Reference:'))
    #
    #         self.ref_channel_combo_box = QComboBox()
    #         self.ref_channel_combo_box.addItem('0')
    #         self.ref_channel_combo_box.addItems([group.name for group in self.scheme.current_groups if group!=self.data])
    #         self.ref_channel_combo_box.setCurrentText(self.data.reference)
    #         self.ref_channel_combo_box.currentTextChanged.connect(self.groupReferenceChanged)
    #         topbox.addWidget(self.ref_channel_combo_box)
    #
    #         self.add_pulse_btn = QPushButton('Add pulse')
    #         self.add_pulse_btn.clicked.connect(self.addPulse)
    #         topbox.addWidget(self.add_pulse_btn)
    #
    #         self.del_group_btn = QPushButton('Del Group')
    #         self.del_group_btn.clicked.connect(self.deleteGroup)
    #         topbox.addWidget(self.del_group_btn)
    #         # main_box.addLayout(topbox)
    #
    #         self.redraw_btn = QPushButton('Redraw')
    #         self.redraw_btn.clicked.connect(self.redraw)
    #         topbox.addWidget(self.redraw_btn)
    #         topbox.addStretch(1)
    #         main_box.addLayout(topbox)
    #
    #         self.columns = ['Del','Channel','Name','Edge','Delay','Length','N','Active','Special']
    #         self.edges = ['Begin', 'End']
    #         self.label_row = 1
    #         self.group_row = 0
    #         self.grid_layout = QGridLayout()
    #
    #         for i, name in enumerate(self.columns):
    #             label = QLabel(name)
    #             if name == 'Active':
    #                 label.setText('On')
    #             elif name == "Special":
    #                 label.setText('')
    #             self.grid_layout.addWidget(label, self.label_row, i)
    #
    #         # add pulse_group data
    #         group_name = QLineEdit(self.data.name)
    #         group_name.editingFinished.connect(self.groupNameChanged)
    #         self.grid_layout.addWidget(group_name, self.group_row, self.columns.index('Name'))
    #
    #         group_edge = QComboBox()
    #         group_edge.addItems(self.edges)
    #         group_edge.setCurrentIndex(self.data.edge)
    #         group_edge.setMaximumWidth(70)
    #         group_edge.currentIndexChanged.connect(self.edgeChanged)
    #         self.grid_layout.addWidget(group_edge, self.group_row, self.columns.index('Edge'))
    #
    #         group_delay = QDoubleSpinBox()
    #         group_delay.setDecimals(self.n_decimals)
    #         group_delay.setMaximum(10000-1)
    #         group_delay.setMinimum(-10000+1)
    #         group_delay.setValue(self.data.variables['delay'])
    #         group_delay.valueChanged.connect(self.delayChanged)
    #         self.grid_layout.addWidget(group_delay, self.group_row, self.columns.index('Delay'))
    #
    #         group_length = QDoubleSpinBox()
    #         group_length.setDecimals(self.n_decimals)
    #         group_length.setMaximum(10000-1)
    #         group_length.setMinimum(-10000+1)
    #         group_length.setValue(self.data.variables['length'])
    #         group_length.valueChanged.connect(self.lengthChanged)
    #         self.grid_layout.addWidget(group_length, self.group_row, self.columns.index('Length'))
    #
    #         group_is_active = QCheckBox()
    #         group_is_active.setChecked(self.data.is_active)
    #         group_is_active.stateChanged.connect(self.isActiveChanged)
    #         self.grid_layout.addWidget(group_is_active, self.group_row, self.columns.index('Active'),Qt.AlignCenter)
    #         # add individual pulse data
    #         for i, pulse in enumerate(self.data.pulses):
    #             #print(pulse)
    #             # print('pulse',i)
    #             pulse_row = i + 2
    #             if 'N' not in pulse.__dict__:
    #                 pulse.N = 1
    #             del_button = QPushButton('Del')
    #             del_button.setMaximumWidth(40)
    #             del_button.clicked.connect(self.deletePulse)
    #             self.grid_layout.addWidget(del_button, pulse_row, self.columns.index('Del'))
    #
    #             pulse_channel = QComboBox()
    #             # pulse_channel.addItems(self.data.scheme.all_channels)
    #             pulse_channel.addItems(self.scheme.available_channels)
    #             pulse_channel.setCurrentText(getattr(pulse, 'channel', '0'))
    #             pulse_channel.setMaximumWidth(60)
    #             pulse_channel.currentTextChanged.connect(self.pulseChannelChanged)
    #             self.grid_layout.addWidget(pulse_channel, pulse_row, self.columns.index('Channel'))
    #
    #             pulse_name = QLineEdit(pulse.name)
    #             pulse_name.editingFinished.connect(self.pulseNameChanged)
    #             self.grid_layout.addWidget(pulse_name, pulse_row, self.columns.index('Name'))
    #
    #             pulse_edge = QComboBox()
    #             pulse_edge.addItems(self.edges)
    #             pulse_edge.setCurrentIndex(pulse.edge)
    #             pulse_edge.setMaximumWidth(70)
    #             pulse_edge.currentIndexChanged.connect(self.edgeChanged)
    #             self.grid_layout.addWidget(pulse_edge, pulse_row, self.columns.index('Edge'))
    #
    #             pulse_delay = QDoubleSpinBox()
    #             pulse_delay.setDecimals(self.n_decimals)
    #             pulse_delay.setMaximum(10000-1)
    #             pulse_delay.setMinimum(-10000+1)
    #             pulse_delay.setValue(pulse.variables['delay'])
    #             pulse_delay.valueChanged.connect(self.delayChanged)
    #             self.grid_layout.addWidget(pulse_delay, pulse_row, self.columns.index('Delay'))
    #
    #             pulse_length = QDoubleSpinBox()
    #             pulse_length.setDecimals(self.n_decimals)
    #             pulse_length.setMaximum(10000-1)
    #             pulse_length.setMinimum(-10000+1)
    #             pulse_length.setValue(pulse.variables['length'])
    #             pulse_length.valueChanged.connect(self.lengthChanged)
    #             self.grid_layout.addWidget(pulse_length, pulse_row, self.columns.index('Length'))
    #
    #             pulse_N = QSpinBox()
    #             pulse_N.setMinimum(1)
    #             pulse_N.setMaximum(999)
    #             pulse_N.setValue(pulse.N)
    #             pulse_N.valueChanged.connect(self.nChanged)
    #             self.grid_layout.addWidget(pulse_N, pulse_row, self.columns.index('N'))
    #
    #             pulse_is_active = QCheckBox()
    #             pulse_is_active.setChecked(pulse.is_active)
    #             pulse_is_active.stateChanged.connect(self.isActiveChanged)
    #             self.grid_layout.addWidget(pulse_is_active, pulse_row, self.columns.index('Active'),Qt.AlignCenter)
    #
    #             if pulse.channel in self.scheme.analog_channels:
    #                 analog_config = QPushButton('Conf')
    #                 analog_config.clicked.connect(self.analogConfig)
    #                 self.grid_layout.addWidget(analog_config,pulse_row,self.columns.index('Special'))
    #             if pulse.channel in self.scheme.digital_channels:
    #                 # print('DIGITAL_CHANNEL')
    #                 shutter_config = QPushButton('Shutter')
    #                 shutter_config.clicked.connect(self.shutterConfig)
    #                 self.grid_layout.addWidget(shutter_config,pulse_row,self.columns.index('Special'))
    #
    #         main_box.addLayout(self.grid_layout)
    #         # print(self.scheme.digital_channels)
    #         main_box.addStretch(1)
    #         self.setLayout(main_box)
    #         # self.setMinimumHeight(400)
    #         # self.setMinimumWidth(700)
    #         # self.adjustSize()
    #         # print('Finish redraw')
    #         # print(self)
    #         # self.show()
    #         # self.setMaximumHeight(200)
    #         # QScrollArea().setWidget(self)
    #
    #     def getPulseNumber(self):
    #         print('getPulseNumber', end='    ')
    #         index = self.grid_layout.indexOf(self.sender())
    #         print(index)
    #         row, column, cols, rows = self.grid_layout.getItemPosition(index)
    #         #print(row, column, cols, rows)
    #         if row == self.group_row:
    #             return -1
    #         else:
    #             return row - 2
    #
    #     def redraw(self):
    #         print('redraw-Scheme')
    #         QWidget().setLayout(self.layout())
    #         print('after QWidget')
    #         self.initUI()
    #         # self.show()
    #
    #     def getNewText(self):
    #         return self.sender().text()
    #
    #     def addPulse(self):
    #         print('addPulse')
    #         self.data.pulses.append(IndividualPulse(channel='12'))
    #         self.redraw()
    #         self.scheme.changeInGroup() # call for parent method
    #
    #     def deletePulse(self):
    #         print('deletePulse')
    #         # send to gui programm sender() to get back index of pulse to delete
    #         quit_msg = "Are you sure you want to delete this pulse?"
    #         reply = QMessageBox.question(self, 'Message',
    #                                      quit_msg, QMessageBox.Yes, QMessageBox.No)
    #         if reply == QMessageBox.Yes:
    #             print('Delete')
    #             pulse_number = self.getPulseNumber()
    #             print(pulse_number)
    #             print(self.data.pulses[pulse_number])
    #             self.data.pulses.pop(pulse_number)
    #             while self.grid_layout.count():
    #                 item = self.grid_layout.takeAt(0)
    #                 item.widget().deleteLater()
    #             self.redraw()
    #             self.scheme.changeInGroup() # call for parent method
    #
    #     def deleteGroup(self):
    #         print('deleteGroup')
    #         quit_msg = "Are you sure you want to delete this pulse group?"
    #         reply = QMessageBox.question(self, 'Message',
    #                                      quit_msg, QMessageBox.Yes, QMessageBox.No)
    #
    #         if reply == QMessageBox.Yes:
    #             print('Delete')
    #             self.scheme.deleteGroup(self)
    #
    #     def pulseChannelChanged(self, new_channel):
    #         print('pulseChannelChanged')
    #         pulse_number = self.getPulseNumber()
    #         old_channel = self.data.pulses[pulse_number].channel
    #         self.data.pulses[pulse_number].channel = new_channel
    #         if old_channel.startswith('A'):
    #             if not new_channel.startswith('A'):
    #                 # we changed from analog to dogotal chanel
    #                 old_pulse =  self.data.pulses[pulse_number]
    #                 new_pulse = IndividualPulse()
    #                 for key in new_pulse.__dict__:
    #                     new_pulse.__dict__[key] = deepcopy(old_pulse.__dict__[key])
    #                 self.data.pulses[pulse_number] = new_pulse
    #                 self.grid_layout.addWidget(QLabel(''), pulse_number+2, self.columns.index('Special'))
    #                 # self.redraw()
    #         if not old_channel.startswith('A'):
    #             if new_channel.startswith('A'):
    #                 # we changed from digital to analog chanel
    #                 old_pulse =  self.data.pulses[pulse_number]
    #                 new_pulse = AnalogPulse()
    #                 for key in old_pulse.__dict__:
    #                     new_pulse.__dict__[key] = deepcopy(old_pulse.__dict__[key])
    #                 self.data.pulses[pulse_number] = new_pulse
    #                 analog_config = QPushButton('Conf')
    #                 analog_config.clicked.connect(self.analogConfig)
    #                 self.grid_layout.addWidget(analog_config, pulse_number+2, self.columns.index('Special'))
    #
    #         self.scheme.changeInGroup()  # call for parent method
    #
    #     def pulseNameChanged(self):
    #         print('pulseNameChanged')
    #         # there is no need to recalculate pulses if only name has changed
    #         pulse_number = self.getPulseNumber()
    #         old_name = self.data.pulses[pulse_number].name
    #         self.data.pulses[pulse_number].name = self.getNewText()#self.gui.sender().text()
    #         self.data.pulses[pulse_number].updateConnectedShutters(old_name='->'.join([self.data.name, old_name]), new_name='->'.join([self.data.name, self.data.pulses[pulse_number].name]))
    #         self.scheme.changeInGroup()
    #
    #     def edgeChanged(self,new_edge):
    #         print('edgeChanged')
    #         pulse_number = self.getPulseNumber()
    #         if pulse_number == -1:
    #             # group edge was changed
    #             self.data.edge = new_edge
    #         else:
    #             self.data.pulses[pulse_number].edge = new_edge
    #         self.scheme.changeInGroup() # call for parent method
    #
    #     def isActiveChanged(self,new_is_active):
    #         print('isActiveChanged')
    #         pulse_number = self.getPulseNumber()
    #         if pulse_number == -1:
    #             # group edge was changed
    #             self.data.is_active = new_is_active
    #         else:
    #             self.data.pulses[pulse_number].is_active = new_is_active
    #         self.scheme.changeInGroup() # call for parent method
    #
    #     def delayChanged(self,new_delay):
    #         print('delayChanged')
    #         pulse_number = self.getPulseNumber()
    #         if pulse_number == -1:
    #             # group edge was changed
    #             if self.data.reference == '0' and new_delay < 0: # if group referenced to 0
    #                 self.sender().setValue(0)
    #                 return
    #             self.data.variables['delay'] = new_delay
    #
    #         else:
    #             self.data.pulses[pulse_number].variables['delay'] = new_delay
    #         self.scheme.changeInGroup() # call for parent method
    #
    #     def lengthChanged(self,new_length):
    #         print('lengthChanged')
    #         pulse_number = self.getPulseNumber()
    #         if pulse_number == -1:
    #             # group edge was changed
    #             self.data.variables['length'] = new_length
    #         else:
    #             self.data.pulses[pulse_number].variables['length'] = new_length
    #         self.scheme.changeInGroup() # call for parent method
    #
    #     def nChanged(self,new_N):
    #         print('lengthChanged')
    #         pulse_number = self.getPulseNumber()
    #         if pulse_number == -1:
    #             # group edge was changed
    #             self.data.variables['length'] = new_N
    #         else:
    #             self.data.pulses[pulse_number].N = new_N
    #         self.scheme.changeInGroup() # call for parent method
    #
    #     def groupNameChanged(self):
    #         print('groupNameChanged')
    #         old_name = self.data.name
    #         self.data.name = self.getNewText()
    #         for pulse in self.data.pulses:
    #             if 'shutters' in pulse.__dict__:
    #                 pulse.updateConnectedShutters(old_name='->'.join([old_name, pulse.name]),
    #                                          new_name='->'.join([self.data.name, pulse.name]))
    #         # print('jjj')
    #         # update scheme becaus tab name and references has to be changed
    #         self.scheme.schemeRedraw()
    #
    #     def groupReferenceChanged(self, new_reference):
    #         print('groupReferenceChanged')
    #         # Посмотреть, можно ли просто использовать новое имя
    #         self.data.reference = new_reference
    #         self.scheme.changeInGroup()
    #
    #     def analogConfig(self):
    #         print('analogConfig')
    #         pulse_number = self.getPulseNumber()
    #         # for pulse in self.data.pulses:
    #         #     print(pulse.__dict__)
    #         a = self.analogWidget(parent=self,pulse=self.data.pulses[pulse_number])
    #         a.show()
    #
    #     def shutterConfig(self):
    #         print('pulses-shutterConfig')
    #         pulse_number = self.getPulseNumber()
    #         a = self.digitalWidget(parent=self, pulse=self.data.pulses[pulse_number])
    #         a.show()
    #         # self.scheme.changeInGroup()

class ChannelsWidget(QScrollArea):
    def __init__(self, parent=None, pulse_data=[]):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.initUI()

    def initUI(self):
        print('channelsDraw')
        grid = QGridLayout()
        grid.addWidget(QLabel('#'), 0, 0)
        grid.addWidget(QLabel('On'), 0, 1)
        grid.addWidget(QLabel('Off'), 0, 2)
        grid.addWidget(QLabel('Opt'), 0, 3)

        for j, channel in enumerate(self.sortedActive()):#,key=lambda x:int(x,base=16)
            i=j+1
            grid.addWidget(QLabel(channel), i, 0)
            if channel not in self.analog_channels:
                alwais_on = QCheckBox()
                if self.active_channels[channel]['state'] == 'On':
                    alwais_on.setChecked(True)
                alwais_on.stateChanged.connect(self.channelStateChanged)
                grid.addWidget(alwais_on, i, 1)
            alwais_off = QCheckBox()
            if self.active_channels[channel]['state'] == 'Off':
                alwais_off.setChecked(True)
            alwais_off.stateChanged.connect(self.channelStateChanged)
            grid.addWidget(alwais_off, i, 2)
            if channel not in self.analog_channels and self.findShutterForChannel(channel):
                shutter_btn = QPushButton('Sh')
                shutter_btn.setMaximumWidth(20)
                shutter_btn.clicked.connect(self.shutterChanged)
                grid.addWidget(shutter_btn,i,3)
        # grid.
        self.channel_box.setLayout(grid)


class PulseScheme(QWidget):
    # can be done as QWidget
    def __init__(self,parent=None,available_channels=[],globals={},signals=None,config_file=None):

        self.timerToStartDAQ = QTimer()
        self.timerToStartDAQ.setInterval(1000)
        self.timerToStartDAQ.timeout.connect(self.DAQTimerHandler)

        self.cycleTimer = QTimer()
        self.cycleTimer.timeout.connect(self.cycleTimerHandler)
        self.cycleN = 0

        super().__init__(parent)
        # self.pulse_signals = PulseSignals()
        self.globals = globals
        self.signals = signals
        self.config_file = config_file
        self.globals['Pulses'] = {}
        self.data = [] # list of groups in current scheme
        self.call_from_scanner = False
        self.parent = parent
        self.available_channels = available_channels
        self.digital_channels = []
        self.analog_channels = []
        self.active_channels = {}
        self.all_schemes = {}
        self.scan_params = {}
        self.active_shutters = []
        self.config={}
        self.time_step = 0.1
        self.current_scheme = None
        self.current_groups = []
        self.output = {}
        # self.dq = DAQHandler()# self.signals.scanCycleFinished.emit)
        # self.globals['DAQ'] = self.dq
        self.load()


        if 'Signals' not in globals:
            globals['Signals'] ={}
        if 'Pulses' not in globals['Signals']:
            globals['Signals']['Pulses'] = {}
        # globals['Signals']['Pulses']['onAnyChange'] = self.pulse_signals.onAnyChangeSignal
        self.globals['Pulses']['analog_channels']=self.analog_channels
        self.globals['Pulses']['digital_channels'] = self.digital_channels

        self.initUI()
        self.setMinimumWidth(750)

        # self.connect(self.)
        # self.pulse_signal.onAnyChangeSignal()

    def DAQTimerHandler(self):
        self.timerToStartDAQ.stop()
        self.dq.write(self.output)
        self.dq.run()
        self.cycleTimer.setInterval(self.t_last)
        self.cycleN = 0
        self.cycleTimer.start()

    def updateActiveShutters(self):
        print('pulses-updateActiveShutters')
        for group in self.current_groups:
            for pulse in group.pulses:
                if 'shutters' in pulse.__dict__:
                    # print(pulse.shutters)
                    for shutter in pulse.shutters:
                        # print(shutter.name)
                        if shutter not in self.active_shutters:
                            self.active_shutters.append(shutter)

    def initUI(self,tab_index=0):
        self.main_box = QVBoxLayout()
        topbox = QHBoxLayout()

        topbox.addWidget(QLabel('Scheme'))

        self.scheme_combo_box = MyComboBox(items=self.all_schemes,current_text=self.current_scheme,
                                           current_text_changed_handler=self.schemeChanged)
        topbox.addWidget(self.scheme_combo_box)

        self.add_group_button = MyPushButton(name='Add group', handler=self.addGroup)
        topbox.addWidget(self.add_group_button)

        self.save_button = MyPushButton(name='Save',handler=self.saveScheme)
        topbox.addWidget(self.save_button)

        self.save_as_button = MyPushButton(name='Save as',handler=self.saveAsScheme)
        topbox.addWidget(self.save_as_button)

        self.main_box.addLayout(topbox)

        self.hor_box = QHBoxLayout()
        self.hor_box.setSpacing(0)
        self.channel_box = QWidget()
        self.channelsDraw()
        xx = QScrollArea()
        xx.setWidget(self.channel_box)
        xx.setMaximumWidth(150)
        xx.setMinimumWidth(140)
        xx.setFrameShape(QFrame.NoFrame)
        xx.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.hor_box.addWidget(xx)

        self.tabbox = QTabWidget()
        self.tabbox.setMovable(True)
        print('Current scheme: ', self.current_scheme)
        reference_list = ['0'] + [group['name'] for group in self.data]
        for group in self.data:
            tab = QScrollArea()
            tab.setWidget(PulseGroup(parent=self,reference_list=reference_list, **group))
            tab.setFrameShape(QFrame.NoFrame)
            tab.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
            self.tabbox.addTab(tab, group['name'])
            # tab.activateWindow()
            # self.tabbox.addTab(group.PulseGroupQt(scheme=self, data=group), group.name)
        # scroll2 = QScrollArea()
        # scroll2.setWidget(self.tabbox)

        self.tabbox.setCurrentIndex(tab_index)
        self.hor_box.addWidget(self.tabbox)
        self.main_box.addLayout(self.hor_box)
        self.main_box.setSpacing(0)
        self.setLayout(self.main_box)
        # self.onAnyChange()
        self.setMinimumHeight(350)

    def channelsDraw(self):
        print('channelsDraw')
        grid = QGridLayout()
        grid.addWidget(QLabel('#'), 0, 0)
        grid.addWidget(QLabel('On'), 0, 1)
        grid.addWidget(QLabel('Off'), 0, 2)
        grid.addWidget(QLabel('Opt'), 0, 3)

        for j, channel in enumerate(self.sortedActive()):#,key=lambda x:int(x,base=16)
            i=j+1
            grid.addWidget(QLabel(channel), i, 0)
            if channel not in self.analog_channels:
                alwais_on = QCheckBox()
                if self.active_channels[channel]['state'] == 'On':
                    alwais_on.setChecked(True)
                alwais_on.stateChanged.connect(self.channelStateChanged)
                grid.addWidget(alwais_on, i, 1)
            alwais_off = QCheckBox()
            if self.active_channels[channel]['state'] == 'Off':
                alwais_off.setChecked(True)
            alwais_off.stateChanged.connect(self.channelStateChanged)
            grid.addWidget(alwais_off, i, 2)
            if channel not in self.analog_channels and self.findShutterForChannel(channel):
                shutter_btn = QPushButton('Sh')
                shutter_btn.setMaximumWidth(20)
                shutter_btn.clicked.connect(self.shutterChanged)
                grid.addWidget(shutter_btn,i,3)
        # grid.
        self.channel_box.setLayout(grid)

    def findShutterForChannel(self,channel):
        for shutter in self.active_shutters:
            for pulse_full_name in shutter.linked_digital_channels:
                group_name, pulse_name = pulse_full_name.split('->')
                # print(group_name, pulse_name)
                group = [group for group in self.current_groups if group.name == group_name][0]
                pulse = [pulse for pulse in group.pulses if pulse.name == pulse_name][0]
                # print(pulse.channel)
                if pulse.channel == channel:
                    return shutter
        return None

    def shutterChanged(self):
        # handles click on "Sh' button in the left - do not remember why did I need this
        print('shutterChanged')
        layout = self.channel_box.layout()
        index = layout.indexOf(self.sender())
        row, column, cols, rows = layout.getItemPosition(index)
        channel = list(sorted(self.active_channels, key=lambda x: int(x, base=16)))[row - 1]
        # print(channel)
        # found = False
        # for shutter in self.active_shutters:
        #     for pulse_full_name in shutter.linked_digital_channels:
        #         group_name, pulse_name = pulse_full_name.split('->')
        #         # print(group_name, pulse_name)
        #         group = [group for group in self.current_groups if group.name == group_name][0]
        #         pulse = [pulse for pulse in group.pulses if pulse.name == pulse_name][0]
        #         # print(pulse_name)
        #         if pulse.channel == channel:
        #             found = True
        #             break
        #     if found:
        #         break
        shutter = self.findShutterForChannel(channel)
        print(shutter)
        if shutter:
            shutter.ShutterWidget(data=shutter,parent=self).exec_()
            self.onAnyChange()
        # self.onAnyChange()
        # self.updateFromScanner({('1 stage cooling', 'Blue', 'length'): 10.0, ('2 stage cooling', 'Green', 'length'): 22.0, ('1 stage cooling', 'Green', 'length'): 43.0})

    def sortedActive(self):
        return sorted(self.active_channels,key=lambda x:int(x,base=16))

    def channelStateChanged(self, new_state):
        print('channelStateChanged')
        layout = self.channel_box.layout()
        index = layout.indexOf(self.sender())
        row, column, cols, rows = layout.getItemPosition(index)
        if new_state:
            self.active_channels[list(self.sortedActive())[row-1]]['state'] = 'On' if column==1 else 'Off'
        else:
            self.active_channels[list(self.sortedActive())[row-1]]['state'] = 'StandBy'
        self.channelsRedraw()
        self.onAnyChange()

    def channelsRedraw(self):
        QWidget().setLayout(self.channel_box.layout())
        self.channelsDraw()

    def updateChannels(self):
        print('updateChannels')
        channels_in_pulses = set()
        old_channels = {}# set(self.active_channels.keys())
        for pulse_group in self.current_groups:
                for pulse in pulse_group.pulses:
                        channels_in_pulses.add(pulse.channel)
        if old_channels != channels_in_pulses:
            new_active_channels = {}
            for channel in channels_in_pulses:
                new_active_channels[channel] = self.active_channels[channel] if channel in self.active_channels else {'state':'StandBy','shuttes':[]}
            self.active_channels = new_active_channels

        self.updateActiveShutters()
        self.onAnyChange()

    def schemeRedraw(self,tab_index=None):
        # print('schemeRedraw')
        if tab_index == None:
            tab_index = self.tabbox.currentIndex()
        self.tabbox.clear()
        # print('Current scheme: ', self.current_scheme)
        for group in self.current_groups:
            tab = QScrollArea()
            tab.setWidget(group.PulseGroupQt(scheme=self, data=group))
            tab.setFrameShape(QFrame.NoFrame)
            tab.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
            self.tabbox.addTab(tab, group.name)
        self.tabbox.setCurrentIndex(tab_index)
        self.updateChannels()

    # def load(self): #old
    #     if DEBUG: print('loadSchemes')
    #     if not os.path.exists(SCHEMES_FOLDER):
    #         print('create folder ', SCHEMES_FOLDER)
    #         os.mkdir(SCHEMES_FOLDER)
    #     self.all_schemes = os.listdir(SCHEMES_FOLDER)
    #     with open(CONFIG_FILE, 'r') as f:
    #         if DEBUG: print('config_load')
    #         config = json.load(f)
    #     self.__dict__.update(config) # here one should upload current_scheme and available_channels
    #     self.loadScheme()
    def load(self):  # new
        if DEBUG: print('loadSchemes')
        if not os.path.exists(SCHEMES_FOLDER):
            print('create folder ', SCHEMES_FOLDER)
            os.mkdir(SCHEMES_FOLDER)
        self.all_schemes = os.listdir(SCHEMES_FOLDER)
        with open(self.config_file, 'r') as f:
            if DEBUG: print('config_load')
            config = json.load(f)
        self.__dict__.update(config['pulse_scheme'])  # here one should upload current_scheme and available_channels
        self.loadScheme()

    def loadScheme(self):
        if self.current_scheme in self.all_schemes: # name in config corresponds to one of scheme files
            with open(os.path.join(SCHEMES_FOLDER, self.current_scheme), 'r') as f:
                print('load_current_scheme', self.current_scheme)
                self.data = json.load(f)
                # print(self.data)

        # if len(files) != 0:
        #     for fname in files:
        #         if fname.startswith('config_scheme.j'):
        #             with open(os.path.join(SCHEMES_FOLDER, fname), 'r') as f:
        #                 print('config_load')
        #                 self.config = json.load(f)
        #                 # print(self.congi)
        #         if fname.endswith(pulse_name_suffix):
        #             with open(os.path.join(SCHEMES_FOLDER, fname), 'rb') as f:
        #                 # print(fname)
        #                 data_to_read = pickle.load(f)
        #                 self.all_schemes[fname[:fname.find(pulse_name_suffix)]] = data_to_read['current_groups']
        #                 self.active_channels = data_to_read['active_channels']
        #                 if 'time_step' in data_to_read:
        #                     self.time_step = data_to_read['time_step']
        # if 'current_scheme' in self.config:
        #     self.current_scheme = self.config['current_scheme']
        # if 'digital_channels' in self.config:
        #     self.digital_channels = self.config['digital_channels']
        # if 'analog_channels' in self.config:
        #     self.analog_channels = self.config['analog_channels']
        # elif len(self.all_schemes):
        #     self.current_scheme = list(self.all_schemes.keys())[0]
        # else:
        #     self.all_schemes['Default']=[PulseGroup()]
        #     self.current_scheme = 'Default'
        # self.current_groups = self.all_schemes[self.current_scheme]
        # self.available_channels = self.digital_channels + self.analog_channels
        # self.updateChannels()

    def schemeChanged(self, new_scheme): # new
        print('schemeChanged')
        self.current_scheme = new_scheme
        self.loadScheme()
        QWidget().setLayout(self.layout())
        self.initUI()
        self.saveConfig()
        # self.current_groups = self.all_schemes[self.current_scheme]
        # self.updateConfig()
        # self.schemeRedraw()
        # self.channelsRedraw()

    def addGroup(self):
        print('addGroup')
        tab = QScrollArea()
        name = 'New group'
        tab.setWidget(PulseGroup(parent=self, name=name,reference='0',reference_list=['0'] + [group['name'] for group in self.data]))
        tab.setFrameShape(QFrame.NoFrame)
        tab.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.tabbox.addTab(tab, name)
        print('HERERE')
        self.updateGroupsReferences()
        # print(self.current_groups)
        # do some updates

    def saveConfig(self):
        with open(self.config_file, 'r') as f:
            if DEBUG: print('config_load_before_saving')
            all_config = json.load(f)
            config = all_config['pulse_scheme']
        for key in config:
            config[key] = self.__dict__[key]
        with open(CONFIG_FILE, 'w') as f:
            if DEBUG: print('config_save')
            json.dump(config, f)

    def saveScheme(self,save_last=False):
        print('saveScheme', self.current_scheme)
        self.data = self.constructData()
        if DEBUG: print('Data to save:', self.data)
        if not os.path.exists(SCHEMES_FOLDER):
            print('create folder')
            os.mkdir(SCHEMES_FOLDER)
        if save_last:
            path_to_save = os.path.join(SCHEMES_FOLDER,
                                        last_scheme_setup + pulse_name_suffix)
        else:
            path_to_save = os.path.join(SCHEMES_FOLDER,self.current_scheme)
        with open(path_to_save, 'w') as f:
            json.dump(self.data,f)

    def saveAsScheme(self):
        print('saveAsScheme')
        self.data = self.constructData()
        if DEBUG: print(self.data)
        if not os.path.exists(SCHEMES_FOLDER):
            print('create folder')
            os.mkdir(SCHEMES_FOLDER)
        fname = QFileDialog.getSaveFileName(self, directory=SCHEMES_FOLDER)[0]
        with open(fname, 'w') as f:
            json.dump(self.data, f)
        fname = os.path.basename(fname)
        self.all_schemes.append(fname)
        self.current_scheme = fname
        self.scheme_combo_box.addItem(self.current_scheme)
        self.scheme_combo_box.setCurrentText(self.current_scheme)

    def constructData(self):
        res= [w.widget().constructData() for w in self.tabbox.children()[0].children() if isinstance(w,QScrollArea)] # before it wasstr(type(w)).split('.')[-1] == "QScrollArea'>"
        return res

    def deleteGroup(self, group):
        if DEBUG: print("deleteGroup")
        confirm = QMessageBox.question(self,"Confirm!!!",'Delete group',buttons=QMessageBox.StandardButtons(QMessageBox.Yes|QMessageBox.No))
        if confirm == QMessageBox.Yes:
            try:
                w  = [w for w in self.tabbox.children()[0].children()
                      if isinstance(w,QScrollArea) and w.widget()==group][0]
            except:
                print('Can not find widget for group', group)
            # print(w)
            # print(self.tabbox.indexOf(group))
            self.tabbox.removeTab(self.tabbox.indexOf(w))
            w.deleteLater()
            group.deleteLater()
            self.updateGroupsReferences()
        # self.current_groups.remove(group.data)
        # self.schemeRedraw()

    def groupChanged(self,group,change_type,changes=[]):
        if DEBUG: print('PULSE_SCHEME: groupChanged', group.name, change_type, changes)
        if change_type in ['group_name_changed']:
            try:
                w = [w for w in self.tabbox.children()[0].children()
                     if isinstance(w, QScrollArea) and w.widget() == group][0]
            except:
                print('Can not find widget for group', group)
            # print('SETTING group name', group.name)
            self.tabbox.setTabText(self.tabbox.indexOf(w), group.name)

            self.updateGroupsReferences(changes)
        elif change_type in ['pulse_added','pulse_changed','pulse_deleted']:
            pass # now nothing special to do

        # timer is needed since error happened in reference assignment
        self.delayTimer = QTimer()
        self.delayTimer.setInterval(100)
        self.delayTimer.timeout.connect(self.delayedConstructPulseSequence)
        self.delayTimer.start()
        # self.pulse_sequence = self.constructPulseSequence()

    def delayedConstructPulseSequence(self):
        self.delayTimer.stop()
        self.pulse_sequence = self.constructPulseSequence()
    # def groupNameChanged(self,group):
    #     if DEBUG: print('PulseScheme: groupNameChanged')
    #     try:
    #         w  = [w for w in self.tabbox.children()[0].children()  if isinstance(w,QScrollArea) and w.widget()==group][0]
    #     except:
    #         print('Can not find widget for group', group)
    #     self.tabbox.setTabText(self.tabbox.indexOf(w),group.name)
    #     self.updateGroupsReferences()

    def updateGroupsReferences(self,changes=[]):
        if DEBUG: print('PulseScheme: updateGroupsReferences')
        self.data = self.constructData()
        # print(self.data)
        reference_list = ['0'] + [group['name'] for group in self.data]
        print('REF LIST', reference_list)
        for w in self.tabbox.children()[0].children():
            if isinstance(w,QScrollArea):
                w.widget().update_frome
                w.widget().setReferemceList(reference_list,changes)
        self.delayTimer.start(100) # construct pulse sequence

    # def changeInGroup(self):
    #     print('changeInGroup')
    #     self.updateChannels()
    #     self.channelsRedraw()
    #
    # def updateConfig(self):
    #     print('updateConfig')
    #     if not os.path.exists(os.path.join(SCHEMES_FOLDER, config_scheme_file) + '.json'):
    #         config = {}
    #     else:
    #         with open(os.path.join(SCHEMES_FOLDER, config_scheme_file) + '.json', 'r') as f:
    #             print('here-there')
    #             config = json.load(f)
    #             if type(config) != type(dict()):
    #                 print('smth rong with config file')
    #                 config = {}
    #     config['current_scheme'] = self.current_scheme
    #     print('CONFIG',config)
    #     with open(os.path.join(SCHEMES_FOLDER, config_scheme_file) + '.json', 'w') as f:
    #         config['digital_channels']=[str(i) for i in range(8,31)]
    #         json.dump(config, f)



            # def updateScheme(self):
    def constructPulseSequence(self):
        self.data = self.constructData()
        # print(self.data)
        groups_named = {w.widget().name:w.widget() for w in self.tabbox.children()[0].children()
                     if isinstance(w, QScrollArea)}
        groups_and_refs = {group['name']:[group['reference']] for group in self.data}
        print('REFS AND GROUPS', groups_and_refs)
        group_chains = []
        for group_name, refs in groups_and_refs.items():
            # print(group_name,refs)
            i=10
            while refs[0] != '0':
                if i <=0:
                    print('ERROR - cicled ')
                    break
                # print(refs,*groups_and_refs[refs[0]])
                groups_and_refs[group_name] = groups_and_refs[refs[0]] + groups_and_refs[group_name]
                # refs.insert(0,*groups_and_refs[refs[0]])
                refs = groups_and_refs[group_name]
                i -= 1
                # print(refs)
            group_chains.append(groups_and_refs[group_name] + [group_name])
        print('NEW GROUPS AND REFS', group_chains)
        updated_groups = ['0']
        points = []
        for chain in group_chains:
            print('chain',chain)
            for group_name in chain:
                print('current group name',group_name)
                if group_name in updated_groups:
                    continue
                else:
                    print(chain, chain.index(group_name)-1)
                    ref = chain[chain.index(group_name)-1]
                    print(group_name,ref)
                    if ref == '0':
                        pfg = groups_named[group_name].constructTiming(0)
                    else:
                        pfg = groups_named[group_name].constructTiming(groups_named[ref].getGroupBoundaries())
                    print('pfg',pfg)
                    points.extend(pfg)
                    updated_groups.append(group_name)
        print('HERE FINISHED')
        print('all points',points)
        points_by_channel = {}
        for sp in points:
            channel, pts = sp
            if channel in points_by_channel:
                points_by_channel[channel].extend(pts)
            else:
                points_by_channel[channel] = pts
        print('points by channel _ before', points_by_channel)
        for channel in points_by_channel:
            pulse_type = [t for t in self.available_channels if channel in self.available_channels[t]][0]
            print('Channel', channel, 'in', pulse_type)
            # print(PULSE_LINE_CONSTRUCTORS[pulse_type])
            points_by_channel[channel] = PULSE_LINE_CONSTRUCTORS[pulse_type].combinePoints(points_by_channel[channel])
        print('points by channel _ after', points_by_channel)
            # if False: # replace with self.channel_widget.channels[channel].isAlwaysOn()
            #     points_by_channel[channel] = [[0,1]] # get value depending on channel type
            # elif False: # replace with self.channel_widget.channels[channel].isAlwaysOff()
            #     points_by_channel[channel] = [[0, 0]]
            # else: # when no constant value is set
            #     pts = sorted(points_by_channel[channel])

        # ref_tree_root = anytree.Node('0')
        # nodes = {name:anytree.Node(name) for name in groups_and_refs}
        # nodes['0']= anytree.Node('0')
        # print(nodes)
        # for node in nodes:
        #     if node != '0':
        #         nodes[node].parent = nodes[groups_and_refs[node]]


        # for item in refs_and_groups:
        #     ref, group = item
        #     a = anytree.Node(group,parent=ref)
        # for pre, fill, node in anytree.RenderTree(nodes['0']):
        #     print("%s%s" % (pre, node.name))
        # ref_tree = {'0':[]}
        # while refs_and_groups:
        #     for ref in ref_tree:
        #         if



    def calculateOutput(self):
        print('calculateOutput')
        self.output = {}
        res = self.updateGroupTime()
        channels_affiliation = {}
        if res==0:
            output = {}
            for pulse_group in self.current_groups:
                if pulse_group.is_active:
                    for pulse in pulse_group.pulses:
                        if pulse.is_active:
                            if not pulse.channel in output.keys():
                                output[pulse.channel] = []
                                channels_affiliation[pulse.channel] = []
                            channels_affiliation[pulse.channel].append(pulse.name)
                            if self.active_channels[pulse.channel]['state'] == 'StandBy':
                                pulse.updateTime(pulse_group)
                                # print('here', pulse.channel)
                                new_points = pulse.getPoints(self.time_step)
                                #print(pulse.channel, new_points)
                                output[pulse.channel].extend(new_points)
                            elif self.active_channels[pulse.channel]['state'] == 'On':
                                if len(output[pulse.channel]) == 0:
                                    output[pulse.channel].append((0,1))
                            else:
                                if len(output[pulse.channel]) == 0:
                                    output[pulse.channel].append((0, 0))
            self.t_last = 0
            self.t_first = 10000
            self.end_delay = 10
            self.first_pre = 100
            self.globals['channels_affiliation'] = channels_affiliation
            # print(list(output.keys()))
            for channel, points in output.items():
                output[channel] = list(sorted(points))
                # print(channel)
                # print(output[channel][0])

                if len(output[channel]) == 0 or output[channel][0][0] != 0:
                    # print('dsd')
                    output[channel].insert(0,(0,0))

                if channel in self.analog_channels:
                    # print('analog', output[channel])
                    continue
                if channel in self.digital_channels:
                    points_to_drop = []
                    for i in range(1,len(output[channel])):
                        if output[channel][i-1][0] == output[channel][i][0]:
                            points_to_drop.extend([i-1,i])
                        if output[channel][i-1][1] == output[channel][i][1]:
                            points_to_drop.append(i if output[channel][i-1][1] else i-1)

                    output[channel] = [output[channel][i] for i in range(len(output[channel])) if i not in points_to_drop]
                    # print(channel, points_to_drop)
                    if len(output[channel]) > 1:
                        if output[channel][1][0] < self.t_first:
                            self.t_first = output[channel][1][0]
                if output[channel][-1][0] > self.t_last:
                        self.t_last = output[channel][-1][0]
            # print('werewer')

            # add last point
            for channel, points in output.items():
                points.append((self.t_last + self.end_delay, points[-1][1]))
            self.output = output
            # print(self.t_first, self.t_last)
            # print(self.output)
            # update shutters times now
            # print('proceed with shutters')
            def getPosition(point,list_of_points):
                for i,p1 in enumerate(list_of_points):
                    if point[0] < p1[0]:
                        return i-1
                return len(list_of_points)-1
            shutters_data={}
            for shutter in self.active_shutters:
                linked_digital_channels = set() # set of channels connected with shutter
                for pulse_full_name in shutter.linked_digital_channels:
                    group_name, pulse_name = pulse_full_name.split('->')
                    # print(group_name, pulse_name)
                    group = [group for group in self.current_groups if group.name == group_name][0]
                    pulse = [pulse for pulse in group.pulses if pulse.name == pulse_name][0]
                    # print(pulse_name)
                    linked_digital_channels.add(pulse.channel)
                # print(linked_digital_channels)
                linked_digital_channels = list(linked_digital_channels)
                # from here I assume that only one channel is connected to particular shutter.
                # if not - rewrite code below
                if len(linked_digital_channels):

                    if shutter.always_on:
                        shutters_data[shutter.channel] = [(0,1)]
                    elif shutter.always_off:
                        shutters_data[shutter.channel] = [(0, 0)]
                    else:
                        ch_out = self.output[linked_digital_channels[0]].copy()
                        for i in range(len(ch_out)):
                            if ch_out[i][1] == 1 and ch_out[i][0] >= shutter.start_delay: # rising
                                ch_out[i] = (ch_out[i][0] -shutter.start_delay,1)
                            elif ch_out[i][1] == 0 and ch_out[i][0] >= shutter.stop_delay: # rising
                                ch_out[i] = (ch_out[i][0] -shutter.stop_delay,0)
                        shutters_data[shutter.channel]=ch_out[:-1]
                    # for chan in linked_digital_channels[1:]:
                    #     for point in self.output[chan]:
                    #         i = getPosition(point,sh_out)
                    #         if point[1]:
                    #             pass
            if len(shutters_data):
                # t_points = sorted(set([int(y[0]+0.5) for x in shutters_data.values() for y in x]))
                # # print(t_points)
                # msg = 'BS '
                # for t in t_points:
                #     msg += str(t)+'_'
                #     for sh, val in shutters_data.items():
                #         msg += str(sh)# + '_'
                #         for i in range(len(val)):
                #             if val[i][0] > t:
                #                 msg += str(val[i-1][1])# + '_'
                #                 break
                #             if i==len(val)-1:
                #                 msg += str(val[i][1])# + '_'
                #     msg += ' '
                # msg = msg[:-1] + '!'
                #print('OLD MSG ', self.constructArduinoMessageOld(shutters_data))
                msg = self.constructArduinoMessageNew(shutters_data)
                #print(msg)
                self.signals.shutterChange.emit(msg)
                # status, res = self.parent.arduino.write_read_com(msg.encode('ascii'))
                # if status:
                #     self.parent.arduino.append_readings(res)
                # # # res = self.parent.arduino.readline().decode()
                # print(res)

    def constructArduinoMessageOld(self,shutters_data):
        t_points = sorted(set([int(y[0] + 0.5) for x in shutters_data.values() for y in x]))
        # print(t_points)
        msg = 'BS '
        for t in t_points:
            msg += str(t) + '_'
            for sh, val in shutters_data.items():
                msg += str(sh)  # + '_'
                for i in range(len(val)):
                    if val[i][0] > t:
                        msg += str(val[i - 1][1])  # + '_'
                        break
                    if i == len(val) - 1:
                        msg += str(val[i][1])  # + '_'
            msg += ' '
        msg = msg[:-1] + '!'
        return msg

    def constructArduinoMessageNew(self,shutters_data):
        t_points = sorted(set([int(y[0] + 0.5) for x in shutters_data.values() for y in x]))
        # print(t_points)
        msg = 'BS ' + ''.join(str(sh) for sh in shutters_data) + ' '
        for t in t_points:
            msg += str(t) + '_'
            sh_sum_state = 0
            for j, val in enumerate(shutters_data.values()):
                # msg += str(sh)  # + '_'
                for i in range(len(val)):
                    if val[i][0] > t:
                        c_s = val[i - 1][1]  # + '_'
                        break
                    if i == len(val) - 1:
                        c_s = val[i][1]  # + '_'
                sh_sum_state += c_s * 2**(len(shutters_data)-j-1)
            msg += str(sh_sum_state)+' '
        msg = msg[:-1] + '!'
        return msg

    def updateGroupTime(self):
        # print('updateGroupTime')
        handled = []
        for group in self.current_groups:
            # print(group.__dict__)
            if group.reference == '0':
                group.t_start = group.variables['delay']
                group.t_end = group.t_start + group.variables['length']
                handled.append(group.name)
        itr = len(self.current_groups)
        while len(handled) != len(self.current_groups):
            # print(handled)
            itr -= 1
            for group in self.current_groups:
                if group.name not in handled:
                    if group.reference in handled:
                        ref = [g for g in self.current_groups if g.name == group.reference][0]
                        group.t_start = (ref.t_end if group.edge else ref.t_start) + group.variables['delay']
                        group.t_end = group.t_start + group.variables['length']
                        handled.append(group.name)
            if itr <= 0:
                msgBox = QMessageBox()
                msgBox.setText('There are recurtion in pulse references. Please check it')
                msgBox.exec()
                return -1
        return 0

    def onAnyChange(self):
        print('onAnyChange')
        # write new output to DAQ
        self.dq.stop()
        if self.call_from_scanner:
            self.call_from_scanner = False
        else:
            self.updateAndSendScanParameters()
            self.saveScheme(save_last=True)
        self.calculateOutput()
        # print(self.output)
        self.globals['Pulses'][pulse_output_str] = deepcopy(self.output)
        # write new output to DAQ
        self.dq.stop()
        self.cycleTimer.stop()
        print('DAQ stopped at',datetime.datetime.now().time())
        self.timerToStartDAQ.start()
        # time.sleep(1)
        # self.dq.run()
        # self.globals['Pulses'][pulse_output_str] = self.output
        self.globals['Pulses']['t_first']=self.t_first

        # print(self.globals['Pulses'][pulse_output_str])
        # print(self.globals['Pulses']['t_first'])
        # self.pulse_signals.onAnyChangeSignal.emit()
        self.signals.anyPulseChange.emit()
        # print('Globals\n',self.globals)

    def cycleTimerHandler(self):
        self.cycleN += 1
        self.signals.scanCycleFinished.emit(self.cycleN)
        return

    def updateAndSendScanParameters(self):
        print('updateAndSendScanParameters')
        self.scan_params = {}
        for group in self.current_groups:
            self.scan_params[group.name] = {}
            self.scan_params[group.name]['group'] = list(group.variables.keys())
            for pulse in group.pulses:
                self.scan_params[group.name][pulse.name] = list(pulse.variables.keys())
        # print('Scan params',self.scan_params)
        # send scan parameters to global
        if self.globals != None:
            if scan_params_str not in self.globals:
                self.globals[scan_params_str] = {}
            self.globals[scan_params_str][name_in_scan_params] = self.scan_params
                # print(self.scan_params)

    def updateFromScanner(self,param_dict=None):
        print('updateFromScanner')
        self.call_from_scanner = True
        for key, val in param_dict.items():
            # print(key)
            group_names = [group.name for group in self.current_groups]
            group = self.current_groups[group_names.index(key[0])]
            # print(key[1])
            if key[1] == 'group':
                item_to_change = group
            else:
                pulse_names = [pulse.name for pulse in group.pulses]
                # print(pulse_names)
                item_to_change = group.pulses[pulse_names.index(key[1])]
            # print(item_to_change.variables)
            item_to_change.variables[key[2]] = val
        # print('Here')
        self.schemeRedraw()
        # if everything is ok return 0, if not - smth else
        return 0

    def getUpdateMethod(self):
        return self.updateFromScanner


# class PulseGroup():
#
#     def __init__(self,name='Default', edge=0,  delay=0, length=0, is_active=False, reference='0',):
#         self.name = name
#         self.edge = edge
#         self.variables = {'delay': delay,
#                           'length': length}
#         self.is_active = is_active
#         self.reference = reference
#         self.pulses = []
#         if len(self.pulses) == 0:
#             self.pulses.append(IndividualPulse())
#
#         # t_start  # absolute time of the beginning of the group
#         # t_end  # absolute time of the end of the group
#
#     def getReferencePoint(self,scheme):
#         if self.ref == '0':
#             return 0
#         else:
#             predecessor = scheme.pulseByName(self.ref)
#             return self.edge * predecessor.length + predecessor.getReferencePoint(scheme)
#
#     class PulseGroupQt(QWidget):
#
#         def __init__(self, data=None,scheme=None):
#             # self.channels = [str(i) for i in range(10)]
#             self.n_decimals = 2
#             self.data = data
#             self.scheme = scheme
#             super().__init__()
#             self.initUI()
#
#         def initUI(self):
#             print('initUI-scheme PulseGroup')
#             main_box = QVBoxLayout()
#             topbox = QHBoxLayout()
#             # main_box.setSpacing(2)
#
#             topbox.addWidget(QLabel('Reference:'))
#
#             self.ref_channel_combo_box = QComboBox()
#             self.ref_channel_combo_box.addItem('0')
#             self.ref_channel_combo_box.addItems([group.name for group in self.scheme.current_groups if group!=self.data])
#             self.ref_channel_combo_box.setCurrentText(self.data.reference)
#             self.ref_channel_combo_box.currentTextChanged.connect(self.groupReferenceChanged)
#             topbox.addWidget(self.ref_channel_combo_box)
#
#             self.add_pulse_btn = QPushButton('Add pulse')
#             self.add_pulse_btn.clicked.connect(self.addPulse)
#             topbox.addWidget(self.add_pulse_btn)
#
#             self.del_group_btn = QPushButton('Del Group')
#             self.del_group_btn.clicked.connect(self.deleteGroup)
#             topbox.addWidget(self.del_group_btn)
#             # main_box.addLayout(topbox)
#
#             self.redraw_btn = QPushButton('Redraw')
#             self.redraw_btn.clicked.connect(self.redraw)
#             topbox.addWidget(self.redraw_btn)
#             topbox.addStretch(1)
#             main_box.addLayout(topbox)
#
#             self.columns = ['Del','Channel','Name','Edge','Delay','Length','N','Active','Special']
#             self.edges = ['Begin', 'End']
#             self.label_row = 1
#             self.group_row = 0
#             self.grid_layout = QGridLayout()
#
#             for i, name in enumerate(self.columns):
#                 label = QLabel(name)
#                 if name == 'Active':
#                     label.setText('On')
#                 elif name == "Special":
#                     label.setText('')
#                 self.grid_layout.addWidget(label, self.label_row, i)
#
#             # add pulse_group data
#             group_name = QLineEdit(self.data.name)
#             group_name.editingFinished.connect(self.groupNameChanged)
#             self.grid_layout.addWidget(group_name, self.group_row, self.columns.index('Name'))
#
#             group_edge = QComboBox()
#             group_edge.addItems(self.edges)
#             group_edge.setCurrentIndex(self.data.edge)
#             group_edge.setMaximumWidth(70)
#             group_edge.currentIndexChanged.connect(self.edgeChanged)
#             self.grid_layout.addWidget(group_edge, self.group_row, self.columns.index('Edge'))
#
#             group_delay = QDoubleSpinBox()
#             group_delay.setDecimals(self.n_decimals)
#             group_delay.setMaximum(10000-1)
#             group_delay.setMinimum(-10000+1)
#             group_delay.setValue(self.data.variables['delay'])
#             group_delay.valueChanged.connect(self.delayChanged)
#             self.grid_layout.addWidget(group_delay, self.group_row, self.columns.index('Delay'))
#
#             group_length = QDoubleSpinBox()
#             group_length.setDecimals(self.n_decimals)
#             group_length.setMaximum(10000-1)
#             group_length.setMinimum(-10000+1)
#             group_length.setValue(self.data.variables['length'])
#             group_length.valueChanged.connect(self.lengthChanged)
#             self.grid_layout.addWidget(group_length, self.group_row, self.columns.index('Length'))
#
#             group_is_active = QCheckBox()
#             group_is_active.setChecked(self.data.is_active)
#             group_is_active.stateChanged.connect(self.isActiveChanged)
#             self.grid_layout.addWidget(group_is_active, self.group_row, self.columns.index('Active'),Qt.AlignCenter)
#             # add individual pulse data
#             for i, pulse in enumerate(self.data.pulses):
#                 #print(pulse)
#                 # print('pulse',i)
#                 pulse_row = i + 2
#                 if 'N' not in pulse.__dict__:
#                     pulse.N = 1
#                 del_button = QPushButton('Del')
#                 del_button.setMaximumWidth(40)
#                 del_button.clicked.connect(self.deletePulse)
#                 self.grid_layout.addWidget(del_button, pulse_row, self.columns.index('Del'))
#
#                 pulse_channel = QComboBox()
#                 # pulse_channel.addItems(self.data.scheme.all_channels)
#                 pulse_channel.addItems(self.scheme.available_channels)
#                 pulse_channel.setCurrentText(getattr(pulse, 'channel', '0'))
#                 pulse_channel.setMaximumWidth(60)
#                 pulse_channel.currentTextChanged.connect(self.pulseChannelChanged)
#                 self.grid_layout.addWidget(pulse_channel, pulse_row, self.columns.index('Channel'))
#
#                 pulse_name = QLineEdit(pulse.name)
#                 pulse_name.editingFinished.connect(self.pulseNameChanged)
#                 self.grid_layout.addWidget(pulse_name, pulse_row, self.columns.index('Name'))
#
#                 pulse_edge = QComboBox()
#                 pulse_edge.addItems(self.edges)
#                 pulse_edge.setCurrentIndex(pulse.edge)
#                 pulse_edge.setMaximumWidth(70)
#                 pulse_edge.currentIndexChanged.connect(self.edgeChanged)
#                 self.grid_layout.addWidget(pulse_edge, pulse_row, self.columns.index('Edge'))
#
#                 pulse_delay = QDoubleSpinBox()
#                 pulse_delay.setDecimals(self.n_decimals)
#                 pulse_delay.setMaximum(10000-1)
#                 pulse_delay.setMinimum(-10000+1)
#                 pulse_delay.setValue(pulse.variables['delay'])
#                 pulse_delay.valueChanged.connect(self.delayChanged)
#                 self.grid_layout.addWidget(pulse_delay, pulse_row, self.columns.index('Delay'))
#
#                 pulse_length = QDoubleSpinBox()
#                 pulse_length.setDecimals(self.n_decimals)
#                 pulse_length.setMaximum(10000-1)
#                 pulse_length.setMinimum(-10000+1)
#                 pulse_length.setValue(pulse.variables['length'])
#                 pulse_length.valueChanged.connect(self.lengthChanged)
#                 self.grid_layout.addWidget(pulse_length, pulse_row, self.columns.index('Length'))
#
#                 pulse_N = QSpinBox()
#                 pulse_N.setMinimum(1)
#                 pulse_N.setMaximum(999)
#                 pulse_N.setValue(pulse.N)
#                 pulse_N.valueChanged.connect(self.nChanged)
#                 self.grid_layout.addWidget(pulse_N, pulse_row, self.columns.index('N'))
#
#                 pulse_is_active = QCheckBox()
#                 pulse_is_active.setChecked(pulse.is_active)
#                 pulse_is_active.stateChanged.connect(self.isActiveChanged)
#                 self.grid_layout.addWidget(pulse_is_active, pulse_row, self.columns.index('Active'),Qt.AlignCenter)
#
#                 if pulse.channel in self.scheme.analog_channels:
#                     analog_config = QPushButton('Conf')
#                     analog_config.clicked.connect(self.analogConfig)
#                     self.grid_layout.addWidget(analog_config,pulse_row,self.columns.index('Special'))
#                 if pulse.channel in self.scheme.digital_channels:
#                     # print('DIGITAL_CHANNEL')
#                     shutter_config = QPushButton('Shutter')
#                     shutter_config.clicked.connect(self.shutterConfig)
#                     self.grid_layout.addWidget(shutter_config,pulse_row,self.columns.index('Special'))
#
#             main_box.addLayout(self.grid_layout)
#             # print(self.scheme.digital_channels)
#             main_box.addStretch(1)
#             self.setLayout(main_box)
#             # self.setMinimumHeight(400)
#             # self.setMinimumWidth(700)
#             # self.adjustSize()
#             # print('Finish redraw')
#             # print(self)
#             # self.show()
#             # self.setMaximumHeight(200)
#             # QScrollArea().setWidget(self)
#
#         def getPulseNumber(self):
#             print('getPulseNumber', end='    ')
#             index = self.grid_layout.indexOf(self.sender())
#             print(index)
#             row, column, cols, rows = self.grid_layout.getItemPosition(index)
#             #print(row, column, cols, rows)
#             if row == self.group_row:
#                 return -1
#             else:
#                 return row - 2
#
#         def redraw(self):
#             print('redraw-Scheme')
#             QWidget().setLayout(self.layout())
#             print('after QWidget')
#             self.initUI()
#             # self.show()
#
#         def getNewText(self):
#             return self.sender().text()
#
#         def addPulse(self):
#             print('addPulse')
#             self.data.pulses.append(IndividualPulse(channel='12'))
#             self.redraw()
#             self.scheme.changeInGroup() # call for parent method
#
#         def deletePulse(self):
#             print('deletePulse')
#             # send to gui programm sender() to get back index of pulse to delete
#             quit_msg = "Are you sure you want to delete this pulse?"
#             reply = QMessageBox.question(self, 'Message',
#                                          quit_msg, QMessageBox.Yes, QMessageBox.No)
#             if reply == QMessageBox.Yes:
#                 print('Delete')
#                 pulse_number = self.getPulseNumber()
#                 print(pulse_number)
#                 print(self.data.pulses[pulse_number])
#                 self.data.pulses.pop(pulse_number)
#                 while self.grid_layout.count():
#                     item = self.grid_layout.takeAt(0)
#                     item.widget().deleteLater()
#                 self.redraw()
#                 self.scheme.changeInGroup() # call for parent method
#
#         def deleteGroup(self):
#             print('deleteGroup')
#             quit_msg = "Are you sure you want to delete this pulse group?"
#             reply = QMessageBox.question(self, 'Message',
#                                          quit_msg, QMessageBox.Yes, QMessageBox.No)
#
#             if reply == QMessageBox.Yes:
#                 print('Delete')
#                 self.scheme.deleteGroup(self)
#
#         def pulseChannelChanged(self, new_channel):
#             print('pulseChannelChanged')
#             pulse_number = self.getPulseNumber()
#             old_channel = self.data.pulses[pulse_number].channel
#             self.data.pulses[pulse_number].channel = new_channel
#             if old_channel.startswith('A'):
#                 if not new_channel.startswith('A'):
#                     # we changed from analog to dogotal chanel
#                     old_pulse =  self.data.pulses[pulse_number]
#                     new_pulse = IndividualPulse()
#                     for key in new_pulse.__dict__:
#                         new_pulse.__dict__[key] = deepcopy(old_pulse.__dict__[key])
#                     self.data.pulses[pulse_number] = new_pulse
#                     self.grid_layout.addWidget(QLabel(''), pulse_number+2, self.columns.index('Special'))
#                     # self.redraw()
#             if not old_channel.startswith('A'):
#                 if new_channel.startswith('A'):
#                     # we changed from digital to analog chanel
#                     old_pulse =  self.data.pulses[pulse_number]
#                     new_pulse = AnalogPulse()
#                     for key in old_pulse.__dict__:
#                         new_pulse.__dict__[key] = deepcopy(old_pulse.__dict__[key])
#                     self.data.pulses[pulse_number] = new_pulse
#                     analog_config = QPushButton('Conf')
#                     analog_config.clicked.connect(self.analogConfig)
#                     self.grid_layout.addWidget(analog_config, pulse_number+2, self.columns.index('Special'))
#
#             self.scheme.changeInGroup()  # call for parent method
#
#         def pulseNameChanged(self):
#             print('pulseNameChanged')
#             # there is no need to recalculate pulses if only name has changed
#             pulse_number = self.getPulseNumber()
#             old_name = self.data.pulses[pulse_number].name
#             self.data.pulses[pulse_number].name = self.getNewText()#self.gui.sender().text()
#             self.data.pulses[pulse_number].updateConnectedShutters(old_name='->'.join([self.data.name, old_name]), new_name='->'.join([self.data.name, self.data.pulses[pulse_number].name]))
#             self.scheme.changeInGroup()
#
#         def edgeChanged(self,new_edge):
#             print('edgeChanged')
#             pulse_number = self.getPulseNumber()
#             if pulse_number == -1:
#                 # group edge was changed
#                 self.data.edge = new_edge
#             else:
#                 self.data.pulses[pulse_number].edge = new_edge
#             self.scheme.changeInGroup() # call for parent method
#
#         def isActiveChanged(self,new_is_active):
#             print('isActiveChanged')
#             pulse_number = self.getPulseNumber()
#             if pulse_number == -1:
#                 # group edge was changed
#                 self.data.is_active = new_is_active
#             else:
#                 self.data.pulses[pulse_number].is_active = new_is_active
#             self.scheme.changeInGroup() # call for parent method
#
#         def delayChanged(self,new_delay):
#             print('delayChanged')
#             pulse_number = self.getPulseNumber()
#             if pulse_number == -1:
#                 # group edge was changed
#                 if self.data.reference == '0' and new_delay < 0: # if group referenced to 0
#                     self.sender().setValue(0)
#                     return
#                 self.data.variables['delay'] = new_delay
#
#             else:
#                 self.data.pulses[pulse_number].variables['delay'] = new_delay
#             self.scheme.changeInGroup() # call for parent method
#
#         def lengthChanged(self,new_length):
#             print('lengthChanged')
#             pulse_number = self.getPulseNumber()
#             if pulse_number == -1:
#                 # group edge was changed
#                 self.data.variables['length'] = new_length
#             else:
#                 self.data.pulses[pulse_number].variables['length'] = new_length
#             self.scheme.changeInGroup() # call for parent method
#
#         def nChanged(self,new_N):
#             print('lengthChanged')
#             pulse_number = self.getPulseNumber()
#             if pulse_number == -1:
#                 # group edge was changed
#                 self.data.variables['length'] = new_N
#             else:
#                 self.data.pulses[pulse_number].N = new_N
#             self.scheme.changeInGroup() # call for parent method
#
#         def groupNameChanged(self):
#             print('groupNameChanged')
#             old_name = self.data.name
#             self.data.name = self.getNewText()
#             for pulse in self.data.pulses:
#                 if 'shutters' in pulse.__dict__:
#                     pulse.updateConnectedShutters(old_name='->'.join([old_name, pulse.name]),
#                                              new_name='->'.join([self.data.name, pulse.name]))
#             # print('jjj')
#             # update scheme becaus tab name and references has to be changed
#             self.scheme.schemeRedraw()
#
#         def groupReferenceChanged(self, new_reference):
#             print('groupReferenceChanged')
#             # Посмотреть, можно ли просто использовать новое имя
#             self.data.reference = new_reference
#             self.scheme.changeInGroup()
#
#         def analogConfig(self):
#             print('analogConfig')
#             pulse_number = self.getPulseNumber()
#             # for pulse in self.data.pulses:
#             #     print(pulse.__dict__)
#             a = self.analogWidget(parent=self,pulse=self.data.pulses[pulse_number])
#             a.show()
#
#         def shutterConfig(self):
#             print('pulses-shutterConfig')
#             pulse_number = self.getPulseNumber()
#             a = self.digitalWidget(parent=self, pulse=self.data.pulses[pulse_number])
#             a.show()
#             # self.scheme.changeInGroup()
#
#         class analogWidget(QDialog):
#
#             def __init__(self,parent=None,pulse=None,):
#                 print(pulse.__dict__)
#                 super(parent.analogWidget,self).__init__(parent.scheme)
#                 self.parent = parent
#                 self.pulse = pulse
#                 self.initUI()
#                 self.show()
#                 self.add_btn.setDefault(False)
#
#             def initUI(self):
#                 main_layout = QVBoxLayout(self)
#                 hor_box1 = QHBoxLayout(self)
#                 hor_box1.addWidget(QLabel('Time Step'))
#
#                 time_step_val = QDoubleSpinBox()
#                 time_step_val.setDecimals(self.parent.n_decimals)
#                 time_step_val.setMaximum(10)
#                 time_step_val.setMinimum(0)
#                 time_step_val.setValue(self.parent.scheme.time_step)
#                 time_step_val.valueChanged.connect(self.timeStepChanged)
#                 hor_box1.addWidget(time_step_val)
#
#                 main_layout.addLayout(hor_box1)
#
#                 hor_box2 = QHBoxLayout()
#                 point_radio = QRadioButton(self)
#                 # print(self.pulse)
#                 point_radio.setChecked(True if self.pulse.type=='Points' else False)
#                 hor_box2.addWidget(QLabel('Points'))
#                 point_radio.toggled.connect(self.typeChanged)
#                 hor_box2.addWidget(point_radio)
#                 hor_box2.addWidget(QLabel('Formula'))
#
#                 formula_radio = QRadioButton(self)
#                 formula_radio.setChecked(False if self.pulse.type == 'Points' else True)
#                 hor_box2.addWidget(formula_radio)
#
#                 main_layout.addLayout(hor_box2)
#
#                 self.grid = QGridLayout()
#                 labels = ['name','value']
#                 self.grid.addWidget(QLabel(labels[0]),0,0)
#                 self.grid.addWidget(QLabel(labels[1]), 0, 1)
#                 self.add_btn = QPushButton('Add')
#                 self.add_btn.clicked.connect(self.addVariable)
#                 self.add_btn.setDefault(False)
#                 self.grid.addWidget(self.add_btn,0,2)
#                 variables = [key for key in self.pulse.variables if key not in ['delay','length']]
#                 print(variables)
#                 for i,var in enumerate(variables):
#                     name_line = QLineEdit(var)
#                     name_line.editingFinished.connect(self.varNameChanged)
#                     self.grid.addWidget(name_line,i+1,0)
#
#                     value = QDoubleSpinBox()
#                     value.setDecimals(self.parent.n_decimals)
#                     value.setMaximum(10000)
#                     value.setMinimum(-10000)
#                     value.setValue(self.pulse.variables[var])
#                     value.valueChanged.connect(self.varValueChanged)
#                     self.grid.addWidget(value,i+1,1)
#
#                     del_btn = QPushButton('Del')
#                     del_btn.clicked.connect(self.delVariable)
#                     self.grid.addWidget(del_btn,i+1,2)
#
#                 main_layout.addLayout(self.grid)
#
#                 main_layout.addWidget(QLabel('t - time from impulse start'))
#                 main_layout.addWidget(QLabel('l - impulse length'))
#
#                 formula_line = QLineEdit(self.pulse.formula)
#                 formula_line.editingFinished.connect(self.formulaChanged)
#                 main_layout.addWidget(formula_line)
#
#                 hor_box3 = QHBoxLayout()
#
#                 apply_btn = QPushButton('Apply')
#                 apply_btn.clicked.connect(self.applyChanges)
#                 hor_box3.addWidget(apply_btn)
#
#                 ok_btn = QPushButton('Ok')
#                 ok_btn.clicked.connect(self.okPressed)
#                 hor_box3.addWidget(ok_btn)
#
#                 main_layout.addLayout(hor_box3)
#
#                 self.setLayout(main_layout)
#                 print(self.pulse.__dict__)
#
#             def timeStepChanged(self, new_value):
#                 print('timeStepChanged')
#                 self.parent.scheme.time_step = new_value
#                 print(new_value)
#
#             def typeChanged(self,new_type):
#                 print('typeChanged')
#                 self.pulse.type= 'Points' if new_type else 'Formula'
#                 print(new_type)
#
#             def addVariable(self):
#                 print('addVariable')
#                 self.pulse.variables['new']=0
#                 QWidget().setLayout(self.layout())
#                 self.initUI()
#
#             def varNameChanged(self):
#                 print('varNameChanged')
#                 index = self.grid.indexOf(self.sender())
#                 row, column, cols, rows = self.grid.getItemPosition(index)
#                 variables = [key for key in self.pulse.variables if key not in ['delay', 'length']]
#                 old_name = variables[row-1]
#                 val = self.pulse.variables.pop(old_name)
#                 self.pulse.variables[self.sender().text()]=val
#                 print(self.pulse.__dict__)
#
#             def varValueChanged(self, new_value):
#                 print('varValueChanged')
#                 index = self.grid.indexOf(self.sender())
#                 row, column, cols, rows = self.grid.getItemPosition(index)
#                 variables = [key for key in self.pulse.variables if key not in ['delay', 'length']]
#                 name = variables[row-1]
#                 self.pulse.variables[name]=new_value
#                 print(self.pulse.__dict__)
#
#             def delVariable(self):
#                 print('delVariable')
#                 index = self.grid.indexOf(self.sender())
#                 row, column, cols, rows = self.grid.getItemPosition(index)
#                 variables = [key for key in self.pulse.variables if key not in ['delay', 'length']]
#                 name = variables[row - 1]
#                 self.pulse.variables.pop(name)
#                 QWidget().setLayout(self.layout())
#                 self.initUI()
#
#             def formulaChanged(self):
#                 print('formulaChanged')
#                 self.pulse.formula = self.sender().text()
#                 print(self.pulse.__dict__)
#
#             def applyChanges(self):
#                 print('applyChanges')
#                 QWidget().setLayout(self.layout())
#                 self.initUI()
#                 self.parent.scheme.changeInGroup()
#
#             def okPressed(self):
#                 print('okPressed')
#                 self.applyChanges()
#                 self.close()
#
#         class digitalWidget(QDialog):
#
#             def __init__(self,parent=None,pulse=None,):
#                 print(pulse.__dict__)
#                 super().__init__(parent.scheme)
#                 self.parent = parent
#                 self.pulse = pulse
#                 if 'shutters' not in self.pulse.__dict__:
#                     self.pulse.shutters = []
#                 self.initUI()
#                 self.show()
#                 # self.add_btn.setDefault(False)
#
#             def initUI(self):
#                 main_layout = QVBoxLayout()
#
#                 add_shutter_btn = QPushButton('Add shutter')
#                 add_shutter_btn.clicked.connect(self.addShutter)
#                 param_menu = QMenu(add_shutter_btn)
#                 param_menu.aboutToShow.connect(self.updateMenu)
#                 add_shutter_btn.setMenu(param_menu)
#                 main_layout.addWidget(add_shutter_btn)
#                 self.grid_layout = QGridLayout()
#                 self.drawGrid()
#                 main_layout.addLayout(self.grid_layout)
#
#                 ok_btn = QPushButton('Ok')
#                 ok_btn.clicked.connect(self.okBtnClicked)
#                 main_layout.addWidget(ok_btn)
#
#                 self.setLayout(main_layout)
#
#             def drawGrid(self):
#                 while self.grid_layout.count():
#                     item = self.grid_layout.takeAt(0)
#                     item.widget().deleteLater()
#                 if 'shutters' not in self.pulse.__dict__:
#                     self.pulse.shutters = []
#                 for i, shutter in enumerate(self.pulse.shutters):
#                     self.grid_layout.addWidget(QLabel(shutter.name), i, 0)
#                     self.grid_layout.addWidget(QLabel(str(shutter.channel)), i, 1)
#
#                     conf_shutter = QPushButton('conf')
#                     conf_shutter.clicked.connect(self.confShutter)
#                     self.grid_layout.addWidget(conf_shutter, i, 2)
#
#                     del_shutter = QPushButton('del')
#                     del_shutter.clicked.connect(self.deleteShutter)
#                     self.grid_layout.addWidget(del_shutter, i, 3)
#
#             def updateMenu(self):
#                 print('shutter_btn-udateMenu')
#                 btn = self.sender()
#                 btn.clear()
#                 for shutter in self.parent.scheme.active_shutters:
#                     if shutter not in self.pulse.shutters:
#                         act = btn.addAction(shutter.name + '  ch.' + str(shutter.channel))
#                         act.triggered.connect(self.addShutter)
#                 act = btn.addAction('New')
#                 act.triggered.connect(self.addShutter)
#
#             def addShutter(self):
#                 print('pulse-addShutter')
#                 print(self.sender().text())
#                 if self.sender().text() == 'New':
#                     new_shutter = Shutter()
#                     res = new_shutter.ShutterWidget(data=new_shutter,parent=self).exec_()
#                     self.raise_()
#
#                     if not res:
#                         del new_shutter
#                         return
#
#                     self.parent.scheme.active_shutters.append(new_shutter)
#                 else:
#                     new_shutter = [shutter for shutter in self.parent.scheme.active_shutters if shutter.name == self.sender().text().split()[0]][0]
#
#                 if 'shutters' not in self.pulse.__dict__:
#                     self.pulse.shutters = []
#
#                 self.pulse.shutters.append(new_shutter)
#                 new_shutter.linked_digital_channels.append('->'.join([self.parent.data.name, self.pulse.name]))
#                 self.drawGrid()
#                 self.repaint()
#                 print('Heee')
#
#             def getShutterIndex(self):
#                 index = self.grid_layout.indexOf(self.sender())
#                 row, column, cols, rows = self.grid_layout.getItemPosition(index)
#                 return row
#
#             def confShutter(self):
#                 print('pulse-confShutter')
#                 shutter = self.pulse.shutters[self.getShutterIndex()]
#                 # print(shutter.__dict__)
#                 res = shutter.ShutterWidget(parent=self, data=shutter).exec_()
#                 # print(res)
#                 # print(shutter.__dict__)
#                 self.drawGrid()
#                 self.raise_()
#
#             def deleteShutter(self):
#                 print('pulse-deleteShutter')
#                 reply = QMessageBox.question(self, 'Message',
#                                              "Do you want to delete shutter", QMessageBox.Yes, QMessageBox.No)
#
#                 if reply == QMessageBox.Yes:
#                     shutter = self.pulse.shutters[self.getShutterIndex()]
#                     self.pulse.shutters.remove(shutter)
#                     pulse_name = '->'.join([self.parent.data.name, self.pulse.name])
#                     if pulse_name in shutter.linked_digital_channels:
#                         shutter.linked_digital_channels.remove(pulse_name)
#                     self.drawGrid()
#                     self.raise_()
#
#             def okBtnClicked(self):
#                 print('shutter-okBtnClicked')
#                 self.parent.scheme.changeInGroup()
#                 self.done(0)
#
#             class addShutterWidget(QDialog):
#                 def __init__(self,parent=None):
#                     super().__init__(parent)
#                     self.initUI()
#                     self.show()
#                 def initUI(self):
#                     layout = QVBoxLayout()
#                     for i in range(2):
#                         btn = QPushButton(str(i))
#                         btn.clicked.connect(self.doReturn)
#                         layout.addWidget(btn)
#                     self.setLayout(layout)
#                 def doReturn(self):
#                     self.accept()
#                     return 345


class IndividualPulse():

    def __init__(self, group=None, name='',channel='0', edge=0, delay=0, length=0, is_active=False, N=1):
        self.name = name   # name of the pulse
        # self.group = group # group of pulses it belongs to
        self.channel = channel # physical channel of the signal (or may be name in dictionary)
        self.edge = edge # start the pulse from group's t_start=0 or t_end=1
        self.variables = {'delay':delay,
                          'length':length}  # for easy scanning
        self.is_active = is_active
        self.shutters = []
        self.N = N

    def updateTime(self,group):
        if not self.edge:
            self.t_start = group.t_start + self.variables['delay']
            if self.variables['length'] == 0:
                self.t_end = group.t_end
            elif self.variables['length'] > 0:
                self.t_end = self.t_start + self.variables['length']
            else:
                self.t_end = group.t_end + self.variables['length']
        else:
            if self.variables['length'] == 0:
                self.t_start = group.t_start + self.variables['delay']
                self.t_end = group.t_end
            elif self.variables['length'] > 0:
                self.t_start = group.t_end + self.variables['delay']
                self.t_end = self.t_start + self.variables['length']
            else:
                self.t_end = group.t_end + self.variables['delay']
                self.t_start = self.t_end + self.variables['length']

    def getPoints(self,idle):
        if 'N' not in self.__dict__:
            self.N = 1
        if self.N == 1:
            if self.t_start == self.t_end: #i.e. pulse length is 0
                return []
            else:
                return [(self.t_start,1),(self.t_end,0)]
        elif self.N > 1:
            t_d = self.variables['delay']
            t_l = self.variables['length']
            if t_d <=0 or t_l <= 0:
                return []
            t0 = self.t_start - t_d
            res = []
            for i in range(self.N):
                res.extend([(t0+i*(t_d+t_l),1),(t0+t_l+i*(t_d+t_l),0)])
            #[(t0+i*(t_d+t_l),1),(t0+t_l+i*(t_d+t_l)) for i in range(self.N)]
            print(res)
            return res

    def updateConnectedShutters(self, old_name, new_name):
        print('updateConnectedShutters')
        for shutter in self.shutters:
            for i,name in enumerate(shutter.linked_digital_channels):
                if name == old_name:
                    shutter.linked_digital_channels[i] = new_name


class AnalogPulse(IndividualPulse):

    def __init__(self,type='Points'):
        super().__init__()
        self.type = type
        self.formula = '' # iether string of points if type Point ore string of formula if type Formula
        # self.timeStep # to define timestap if type=='Formula'

    def getPoints(self,time_step=1):
        # print(self.t_start, self.t_end)
        # print(self.__dict__)
        self.variables['l'] = self.t_end - self.t_start
        time_step = time_step
        points = []
        if self.type == 'Points':
            temp1 = re.findall('[(](.*?)[)]', self.formula)
            temp1 = [t.split(',') for t in temp1]
            temp1 = [[t[0].strip(), t[1].strip()] for t in temp1]
            for point in temp1:
                for i, value in enumerate(point):
                    sp_value = re.split("([+-/*])", value)
                    for j, elem in enumerate(sp_value):
                        if elem in self.variables:
                            sp_value[j] = str(self.variables[elem])
                    point[i] = ''.join(sp_value)
                    try:
                        # print(point[i])
                        point[i] = eval(point[i])
                    except ValueError:
                        self.errorInFormula()
                        return -1
            # print(temp1)
            for i in range(1, len(temp1)):
                # print(temp1)
                if not i == len(temp1) - 1:
                    xs = self.t_start + np.arange(temp1[i - 1][0], temp1[i][0], time_step)
                    # print(xs)
                else:
                    xs = self.t_start + np.arange(temp1[i - 1][0], temp1[i][0] + time_step, time_step)
                    # print(xs)
                ys = 1.0 * temp1[i - 1][1] + (temp1[i][1] - temp1[i - 1][1]) / (xs[-1] - xs[0]) * (xs - xs[0])
                p = np.reshape(np.array([xs, ys]).T, (-1, 2))
                points.extend(p)
        else:
            sp_form = re.split("([+-/*()])", self.formula)
            sp_form = [s.strip() for s in sp_form]
            for i, s in enumerate(sp_form):
                if s in self.variables:
                    sp_form[i] = str(self.variables[s])
            formula = ''.join(sp_form)
            formula = parse_expr(formula)
            t = sp.symbols('t')
            func = np.vectorize(lambdify(t, formula, 'numpy'))
            # xs = np.arange(0, self.t_end + time_step, time_step)
            # ys = np.zeros_like(xs)
            xs = np.arange(0, self.t_end - self.t_start + time_step, time_step)
            ys = func(xs)
            xs += self.t_start
            # for i in range(len(xs)):
            #     if i*time_step < self.t_start:
            #         ys[i] = 0
            #     else:
            #         ys[i] = func(xs[i])
            points = [(xs[i], ys[i]) for i in range(len(xs))]
            # print('hello there', xs, ys)
            # points = np.reshape(np.array([xs, ys]).T, (-1, 2))
        # print("ANALOG_GET", points[0])
        # print('hello there', points)
        # res = [(i, points[0][1]) for i in points[0][0]]
        # print(type(res[0]), "TYTYTYT")
        # print("NEW_NA", res)
        # return [list(point) for point in points]
        return points


if __name__ == '__main__':
    import sys
    # digital_pulses_folder = 'digital_schemes'
    # pulseGroup = PulseGroup
    app = QApplication(sys.argv)
    # mainWindow = PulseGroup(parent=None,name='New group',data=[])
    # mainWindow = PulseScheme()
    mainWindow = ShutterWidget(shutter_channels=['S%i'%i for i in range(8)],other_channels=['D%i'%i for i in range(8)])
    mainWindow.show()
    sys.exit(app.exec_())

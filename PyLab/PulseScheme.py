import os, re, json, matplotlib, time
import numpy as np
import sympy as sp
import datetime
import socket
import pyqtgraph as pg
from collections import OrderedDict
from itertools import chain
from PyQt5.QtCore import (Qt, QObject, pyqtSignal, QTimer)
from PyQt5.QtWidgets import (QApplication, QScrollArea, QFrame, QMenu, QGridLayout, QVBoxLayout, QHBoxLayout,
                             QDialog, QLabel, QLineEdit, QPushButton, QWidget, QComboBox, QRadioButton, QCheckBox,
                             QTabWidget, QFileDialog, QAction, QMessageBox, QDoubleSpinBox, QSpinBox, QSpacerItem,
                             QMenuBar, QInputDialog, QMainWindow)
from Lib import (MyComboBox, MyDoubleBox, MyIntBox, MyLineEdit, MyCheckBox, MyPushButton,
                 QDoubleValidator, QIntValidator)
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


matplotlib.use('Qt5Agg', force=True)

SCAN_PARAMS_STR = 'available_scan_params'
NAME_IN_SCAN_PARAMS = 'Pulses'

SCHEMES_FOLDER = 'schemes'
CONFIG_FILE = 'config_pulses.json'
CONFIG_SHUTTERS_FILE = 'config_shutters.json'
config_scheme_file = 'config_scheme'
pulse_name_suffix = '.pls'
scan_params_str = 'scan_params'
name_in_scan_params = 'Pulses'
pulse_output_str = 'pulse_output'
last_scheme_setup = 'last_scheme'

# LineDict form ('name of variable',[widget type, default value,other parameters,width of the widget])
# 'CB' - ComboBox, 'LE' - LineEdit, 'MB' - MyBox
time_validator = QDoubleValidator(-9999, 9999, 3)
group_time_validator = QDoubleValidator(0.001, 9999, 3)
n_validator = QIntValidator(1, 99)
PULSE_LINE_DICT = OrderedDict([
    ('Channel', ['CB', '0', list(map(str, range(16))), 45]),
    ('Name', ['LE', 'New line', 120]),
    ('Edge', ['CB', 'Begin', ['Begin', 'End'], 60]),
    ('Delay', ['MDB', 0, time_validator, 60]),
    ('Length', ['MDB', 0, time_validator, 60]),
    ('N', ['MIB', 1, n_validator, 20]),
    ('On', ['MChB', False, 20])
])
CHANNEL_LINE_DICT = OrderedDict([
    ("Channel", ['LB', 20]),
    ("On", ['MChB', False, 20]),
    ("Off", ['MChB', False, 20]),
    ("Name", ["LE","New",50])
    # ,("Sh",['MChB',False,20])
])


class SimpleLine(QWidget):
    def __init__(self, parent, data={}):
        super().__init__(parent)
        self.parent = parent
        layout = QHBoxLayout()
        self.data = data
        self._update_from_scanner = False
        self.autoUpdate = QTimer()
        self.autoUpdate.setInterval(1000)
        self.autoUpdate.timeout.connect(self.update)
        self.widgets = {}

        for key, val in PULSE_LINE_DICT.items():
            # print(key,val)
            self.data[key] = data.get(key, val[1])
            if key in ['Channel']:
                # self.data[key]=None
                continue
            w = None
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
                                text_changed_handler=self.textEdited,
                                text_edited_handler=self.textEdited,
                                max_width=val[-1])
            elif val[0] == 'MIB':
                w = MyIntBox(validator=val[2], value=data.get(key, val[1]),
                             text_changed_handler=self.textEdited,
                             text_edited_handler=self.textEdited,
                             max_width=val[-1])
            elif val[0] == 'MChB':
                w = MyCheckBox(is_checked=data.get(key, val[1]), handler=self.autoUpdate.start,
                               max_width=val[-1])
            self.widgets[key] = w
            layout.addWidget(w, val[-1])

        layout.addStretch(1)
        layout.setSpacing(10)
        layout.setContentsMargins(5, 2, 5, 2)
        self.main_layout = layout
        self.setLayout(layout)
        self.setMinimumHeight(20)
        self.setMaximumWidth(700)
        # self.setMinimumHeight(50)
        # self.update()

    def update(self):
        if DEBUG: print('PulseLine update', self.data["Name"])
        # print(str(self))
        self.autoUpdate.stop()
        # print('Here1')
        changed_item = {}
        for key, val in PULSE_LINE_DICT.items():
            if key == 'Channel' and 'Channel' not in self.widgets:
                self.data['Channel'] = None
                continue
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
        if DEBUG: print('Pulse line data changed: line:', self.data['Name'], changed_item)

        if not self._update_from_scanner:
            # autoSave.start() # do we need it here?
            if self.parent:
                self.parent.pulseChanged(self, changed_item)  # figure out how to handle this properly
        self._update_from_scanner = False

    def textEdited(self):
        # print('TextEdited')
        if self._update_from_scanner:
            # self.update()
            self.autoUpdate.start()
        else:
            self.autoUpdate.start()

    def constructData(self):
        return {key: self.widgets[key].getValue() for key in self.widgets}

    def getScanParams(self):
        return list(self.widgets.keys())

    def updateFromScanner(self, param, value):
        # print("update", self.widgets.keys())
        self._update_from_scanner = True
        if param not in self.widgets:
            if DEBUG: print('PulseLine, param not in the dictionary')
            return 1
        if self.widgets[param].setValue(str(value)):  # returns 1 if error
            return 1
        else:
            return 0

    def getName(self):
        return self.data["Name"]


class PulseLine(SimpleLine):
    def __init__(self, parent, data={}, channels=[]):
        # data is a dictionary of
        self.data = {'Type': 'Pulse'}
        self.data.update(data)
        super().__init__(parent, self.data)
        if not channels:
            channels = PULSE_LINE_DICT['Channel'][2]
        self.delBtn = MyPushButton(name='del', handler=lambda: self.parent.deleteLine(self), fixed_width=30)
        self.main_layout.insertWidget(0, self.delBtn)
        w = MyComboBox(items=channels, current_text=data.get('Channel', PULSE_LINE_DICT['Channel'][1]),
                       current_index_changed_handler=self.autoUpdate.start,
                       max_width=PULSE_LINE_DICT['Channel'][-1],
                       min_width=PULSE_LINE_DICT['Channel'][-1])
        self.widgets['Channel'] = w
        self.main_layout.insertWidget(1, w)

    def constructData(self):
        self.data.update(super().constructData())
        self.data['Channel'] = self.widgets['Channel'].getValue()
        # res['Type'] = 'Pulse'
        return self.data

    def getPoints(self, group_times):
        # if DEBUG: print('---PulseLine -get points, group_times', group_times, self.widgets['Name'].getValue())
        if not self.widgets['On'].isChecked():
            return []
        group_single_pulse_length = group_times[0][1] - group_times[0][0]
        if self.widgets['Edge'].getValue() == 'Begin':
            # print('HERERE')
            t_start = self.widgets['Delay'].getValue()
            if self.widgets['Length'].getValue() == 0:
                t_end = group_single_pulse_length
            elif self.widgets['Length'].getValue() > 0:
                t_end = t_start + self.widgets['Length'].getValue()
            else:
                t_end = group_single_pulse_length + self.widgets['Length'].getValue()
        else:
            if self.widgets['Length'].getValue() == 0:
                t_start = group_single_pulse_length - abs(self.widgets['Delay'].getValue())
                t_end = group_single_pulse_length
            elif self.widgets['Length'].getValue() > 0:
                t_start = group_single_pulse_length + self.widgets['Delay'].getValue()
                t_end = t_start + self.widgets['Length'].getValue()
            else:
                t_end = group_single_pulse_length + self.widgets['Delay'].getValue()
                t_start = t_end + self.widgets['Length'].getValue()
        points = []
        # print('getPoints, t_start, t_end', t_start, t_end)
        for gp in group_times:  # more carefully handle all possibilities
            for i in range(self.widgets['N'].getValue()):
                points.extend([[gp[0] + t_start + i * (t_start+t_end), 1], [gp[0] + t_end + i * (t_start+t_end), 0]])
            # points.extend([*[(gp[0] + t_start + i * (t_start + t_end),0),( gp[0] + t_end + i * (t_start + t_end))]
            #                for i in range(self.widgets['N'].getValue())])
        # print('---- before return', self.widgets['Channel'].getValue())
        return [self.widgets['Channel'].getValue(), points]

    @staticmethod
    def combinePoints(points):
        return points


class GroupLine(SimpleLine):
    def __init__(self, parent, data={}):
        # data is a dictionary of
        self.data = {'Type': 'Group'}
        self.data.update(data)
        # print('---- Group line, data:', self.data)
        super().__init__(parent, data)

        w = QLabel('')
        w.setFixedWidth(78)
        self.main_layout.insertWidget(0, w)
        # self.widgets['Length'].setValue('1')
        self.widgets['Length'].setValidator(group_time_validator)
        # self.update()

    def constructData(self):
        self.data.update(super().constructData())
        self.data['Channel'] = 'None'
        # res['Type'] = 'Group'
        return self.data


class DigitalLine(PulseLine):
    def __init__(self, parent, data={}, channels=[]):
        # data is a dictionary of
        # print('---- Digital Line')
        self.data = {'Type': 'Digital'}
        self.data.update(data)
        super().__init__(parent, data=self.data, channels=channels)
        # self.shutterBtn = MyPushButton(name='Shutter', handler=self.shutterBtnPressed,
        #                                fixed_width=50)
        # self.main_layout.insertWidget(8, self.shutterBtn)

    def shutterBtnPressed(self):
        if DEBUG: print('---- Digital line - shutter')

    @staticmethod
    def combinePoints(points):
        combined_points = []
        flatten_points = []
        for ps in points:
            flatten_points.extend(ps)
        for point in sorted(flatten_points):
            if combined_points == []:
                combined_points.append(list(point))
            else:
                if point[0] == combined_points[-1][0]:  # the same moment of time
                    if point[1] != combined_points[-1][1]:                   # turn on edge
                        combined_points.pop(-1)
                else:
                    if point[1] != combined_points[-1][1]:
                        combined_points.append(point)
                    else:
                        combined_points[-1] = point
        return combined_points


class AnalogLine(PulseLine):
    def __init__(self, parent, data={}, channels=[]):
        # data is a dictionary of
        # print('---- Analog Line')
        self.data = {'Type': 'Analog'}
        self.data.update(data)
        super().__init__(parent, data=self.data, channels=channels)
        self.shapeBtn = MyPushButton(name='Shape', handler=self.shapeBtnPressed,
                                     fixed_width=50)
        self.main_layout.insertWidget(8, self.shapeBtn)

    def shapeBtnPressed(self):
        if DEBUG: print('---- Analog line - shape')


class InputLine(PulseLine):
    def __init__(self, parent, data={}, channels=[]):
        # data is a dictionary of
        # print('---- Input Line')
        self.data = {'Type': 'Input'}
        self.data.update(data)
        super().__init__(parent, data=self.data, channels=channels)


class CurrentLine(PulseLine):
    def __init__(self, parent, data={}, channels=[]):
        # data is a dictionary of
        # print('---- Current Line')
        self.data = {'Type': 'Current', "Config": {}}
        self.data.update(data)
        # print('---- Current channels', channels)
        super().__init__(parent, data=self.data, channels=channels)
        self.shapeBtn = MyPushButton(name='Conf', handler=self.confBtnPressed,
                                     fixed_width=50)
        self.main_layout.insertWidget(8, self.shapeBtn)

    def confBtnPressed(self):
        if DEBUG: print('---- Current line - config')

        data_from_config = self.data.get("Config", {})
        w = self.ConfigWidget(parent=self, data=data_from_config).exec_()
        del w
        self.data["Config"] = data_from_config
        self.parent.pulseChanged(self)
        # print('data from config',self.data["Config"])

    def updateFromScanner(self, param, value):
        # print("update", self.widgets.keys())
        self._update_from_scanner = True
        if param == "value":
            self.data["Config"]["value"] = value
            return 0
        if param not in self.widgets:
            if DEBUG: print('PulseLine, param not in the dictionary')
            return 1
        if self.widgets[param].setValue(str(value)):  # returns 1 if error
            return 1
        else:
            return 0

    def getScanParams(self):
        if self.data["Config"] == {}:
            add_params = []
        else:
            add_params = ["value"] + list(self.data["Config"]["params"].keys())
        return super().getScanParams() + add_params

    def getPoints(self, group_times):
        if super().getPoints(group_times) == []:
            return []
        channel, points = super().getPoints(group_times)
        # print('get points from current', self.data["Config"])
        if self.data["Config"] == {}:
            return [channel, points]
        if self.data["Config"]["mode"] == "value":
            points = [[p[0], p[1]*self.data["Config"]["value"]] for p in points]
        elif self.data["Config"]["mode"] == "points":
            if not self.data["Config"]["scale"]:
                # implement scaling!!!
                new_points = []
                for i in range(0, len(points), 2):
                    ti = points[i][0]
                    for p in self.data["Config"]["points"]:
                        new_points.append([p[0]+ti, p[1]])
                points = new_points
        elif self.data["Config"]["mode"] == "func":
            func_text = self.data["Config"]["func"]
            # print("params",self.data["params"])
            for p, val in self.data["Config"]["params"].items():
                func_text = func_text.replace(p, str(val))
            points = [[t, eval(func_text.replace('t', str(t)))] for t in eval(self.data["Config"]["times"])]
        return [channel, points]

    class ConfigWidget(QDialog):
        def __init__(self, parent=None, data={}):
            super().__init__()
            self.data = data
            self.parent = parent
            main_layout = QVBoxLayout()
            layout0 = QGridLayout()

            self.rb1 = QRadioButton("value")
            self.rb1.setChecked(data.get("mode", "value") == "value")
            layout0.addWidget(self.rb1, 0, 0)
            self.value_box = MyDoubleBox(validator=QDoubleValidator(-300, 300, 1), value=data.get("value", 0))
            layout0.addWidget(self.value_box, 0, 1)

            self.rb2 = QRadioButton("points")
            self.rb2.setChecked(data.get("mode", "value") == "points")
            layout0.addWidget(self.rb2, 1, 0)
            ps = data.get("points", [(0, 1), (1, 2), (2, 0)])
            self.points_line = MyLineEdit(name=','.join(['(%.1f,%.1f)' % (p[0], p[1]) for p in ps]))
            layout0.addWidget(self.points_line, 1, 1)
            self.scale_chbox = MyCheckBox(is_checked=data.get("scale", False))
            layout0.addWidget(self.scale_chbox, 2, 0)
            layout0.addWidget(QLabel("scale to pulse length"), 2, 1)

            self.rb3 = QRadioButton("func")
            self.rb3.setChecked(data.get("mode", "value") == "func")
            layout0.addWidget(self.rb3, 3, 0)
            self.func_line = MyLineEdit(name=data.get("func", "a*t + b"))
            layout0.addWidget(self.func_line, 3, 1)
            layout0.addWidget(QLabel("params:"), 4, 0)
            p = data.get("params", {"a": 1, "b": 3})
            self.params_line = MyLineEdit(name=','.join([key + ':' + str(p[key]) for key in p]))
            layout0.addWidget(self.params_line, 4, 1)

            layout0.addWidget(QLabel("times"), 5, 0)
            self.times_line = MyLineEdit(name=data.get("times", "np.linspace(0,10,11)"))
            layout0.addWidget(self.times_line, 5, 1)

            main_layout.addLayout(layout0)

            layout4 = QHBoxLayout()
            for lbl in ["Check", "Ok", "Cancel"]:
                w = MyPushButton(name=lbl, handler=self.btnPressed)
                layout4.addWidget(w)

            main_layout.addLayout(layout4)
            self.setLayout(main_layout)
            self.show()
            # layout1 = QHBoxLayout()
            # self.rb1 = QRadioButton("value")
            # self.rb1.setChecked(data.get("mode","value")=="value")
            # layout1.addWidget(self.rb1)
            # self.value = MyDoubleBox(validator=QDoubleValidator(-300,300,1),value=data.get("value",0))
            # layout1.addWidget(self.value)
            # main_layout.addLayout(layout1)
            #
            # layout2 = QHBoxLayout()
            # self.rb2 = QRadioButton("points")
            # self.rb2.setChecked(data.get("mode", "value") == "points")
            # layout2.addWidget(self.rb2)
            # self.points_line = MyLineEdit(name='(0,1),(1,2),(2,0)')
            # layout2.addWidget(self.points_line)
            # main_layout.addLayout(layout2)
            #
            # self.scale_chbox = MyCheckBox(name="scale to pulse length",is_checked=data.get("scale",False))
            # main_layout.addWidget(self.scale_chbox)
            #
            # layout3 = QHBoxLayout()
            # self.rb3 = QRadioButton("func")
            # self.rb3.setChecked(data.get("mode", "value") == "func")
            # layout3.addWidget(self.rb3)
            # self.func_line = MyLineEdit(name="a*t + b")
            # layout3.addWidget(self.func_line)
            #
            # layout4 = QHBoxLayout

        def btnPressed(self):
            lbl = self.sender().text()
            # print('btnPressed', lbl)
            # self.parent._data_from_config = {}
            if lbl == "Cancel":
                self.close()
            elif lbl == "Check":
                self.checkInput()
            elif lbl == "Ok":
                if self.checkInput():
                    # print('data',self.data)
                    self.close()

        def checkInput(self):
            print('checking')
            if self.rb1.isChecked():
                self.data["mode"] = "value"
            elif self.rb2.isChecked():
                self.data["mode"] = "points"
            elif self.rb3.isChecked():
                self.data["mode"] = "func"
            self.data["value"] = self.value_box.getValue()
            self.data["scale"] = self.scale_chbox.isChecked()
            try:
                self.data["points"] = []
                # points = self.points_line.text().split(',')
                for point in re.findall("\((.*?)\)", self.points_line.text()):
                    p = point.split(',')
                    if len(p) > 2:
                        raise Exception()
                    self.data["points"].append((float(p[0].strip()), float(p[1].strip())))
                self.points_line.setStyleSheet("QLineEdit { background-color : white}")
            except:
                # print('in exception')
                self.points_line.setStyleSheet("QLineEdit { background-color : red}")
                return False

            try:
                self.data["params"] = {}
                # points = self.points_line.text().split(',')
                for point in self.params_line.text().split(','):
                    p = point.split(':')
                    if len(p) > 2:
                        raise Exception()
                    self.data["params"][p[0].strip()] = float(p[1].strip())
                self.params_line.setStyleSheet("QLineEdit { background-color : white}")
            except:
                # print('in exception')
                self.params_line.setStyleSheet("QLineEdit { background-color : red}")
                return False

            try:
                self.data["times"] = self.times_line.text()
                times = eval(self.data["times"])
                self.times_line.setStyleSheet("QLineEdit { background-color : white}")
                print('times', self.data["times"])
            except:
                self.times_line.setStyleSheet("QLineEdit { background-color : red}")
                return False

            try:
                func_text = self.func_line.text()
                self.data["func"] = func_text
                # print("params",self.data["params"])
                for p,val in self.data["params"].items():
                    func_text = func_text.replace(p, str(val))
                self.func_values = [eval(func_text.replace('t', str(t))) for t in times]
                print('func values',self.func_values)
                self.func_line.setStyleSheet("QLineEdit { background-color : white}")
            except:
                self.func_line.setStyleSheet("QLineEdit { background-color : red}")
                return False
            return True


PULSE_LINE_CONSTRUCTORS = OrderedDict({'Digital': DigitalLine,
                                       'Analog': AnalogLine,
                                       'Input': InputLine,
                                       'Current': CurrentLine,
                                       'Pulse': PulseLine})


class PulseGroup(QScrollArea):

    def __init__(self, parent=None, name='Default group', reference='0', reference_list=['0'], data=[]):
        """data is a dictionary of lines"""
        super(PulseGroup, self).__init__(parent)
        self.parent = parent
        self.name = name
        self.data = data
        self.update_from_scheme = False
        self.autoUpdate = QTimer()
        self.autoUpdate.setInterval(100)
        # print(self.data)
        if not self.data and 'Group' not in [d['Type'] for d in self.data]:
            self.data.insert(0, {'Type': 'Group', 'Channel': None, 'Name': self.name, 'Edge': 'Begin', 'Delay': 0,
                                 'Lendth': 10, 'N': 1})
        self.reference = reference
        self.pulses = []
        # print(self.data)
        main_widget = QWidget()
        main_layout = QVBoxLayout()

        topbox = QHBoxLayout()

        topbox.addWidget(QLabel('Reference'))
        self.refBox = MyComboBox(current_text=reference, items=[x for x in reference_list if x != self.name],
                                 current_text_changed_handler=self.refChanged, min_width=70)
        topbox.addWidget(self.refBox)
        self.addBtn = MyPushButton(name='Add Pulse', handler=self.addPulse, fixed_width=60)
        topbox.addWidget(self.addBtn)
        self.delBtn = MyPushButton(name='Del Group', handler=lambda: self.parent.deleteGroup(self), fixed_width=60)
        topbox.addWidget(self.delBtn)
        topbox.addStretch(1)
        topbox.setSpacing(10)
        main_layout.addLayout(topbox)

        # construct pulse group
        self.group_line = GroupLine(parent=self, data=[d for d in self.data if d['Type'] == 'Group'][0])
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
                w = PULSE_LINE_CONSTRUCTORS[pulse['Type']](parent=self, data=pulse, channels=channels)
                self.pulses.append(w)
                main_layout.addWidget(w)

        main_layout.addStretch(1)
        self.main_layout = main_layout
        main_widget.setLayout(main_layout)
        self.main_layout.setSpacing(0)
        self.setWidget(main_widget)
        self.setMinimumHeight(400)
        self.setWidgetResizable(True)
        self.setMinimumWidth(600)
        self.setMaximumWidth(650)
        print('FINISHED GROUP', self.name)
        self.update_from_scheme = False

    def refChanged(self, new_ref):  # new
        if DEBUG: print('--- refChanged')
        self.reference = new_ref
        if not self.update_from_scheme:
            self.parent.groupChanged(self, 'reference')
        self.update_from_scheme = False

    def setReferenceList(self, reference_list, changes=[]):  # new
        if DEBUG: print("---PulseGroup - set reference", self.name, self.reference)
        if changes:
            if self.reference == changes[0]:  # this group was reference to changed group
                self.reference = changes[1]  # set new name for the reference
        temp = self.reference
        while self.refBox.count():
            self.refBox.removeItem(0)
        self.refBox.addItems([x for x in reference_list if x != self.name])
        # print('check', self.reference in [x for x in referene_list if x != self.name])
        self.reference = temp
        self.update_from_scheme = True
        self.refBox.setCurrentText(self.reference)
        # print(self.name, 'ref->', self.reference)

    def addLabelLine(self):
        layout = QHBoxLayout()
        w = QLabel("")
        w.setFixedWidth(40)
        layout.addWidget(w)
        for key, val in PULSE_LINE_DICT.items():
            w = QLabel(key)
            w.setFixedWidth(val[-1])
            layout.addWidget(w)
        layout.addStretch(1)
        layout.setSpacing(10)
        return layout

    def deleteLine(self, line):
        self.main_layout.removeWidget(line)
        deleted_line_channel = line.data['Channel']
        line.deleteLater()
        self.pulses.remove(line)
        # del self.data[line.data['Name']]
        # self.save()
        self.parent.groupChanged(self, 'pulse_deleted', changes=deleted_line_channel)
        return

    def addPulse(self):
        new_pulse_type, ok_pressed = QInputDialog.getItem(self, "Choose type of new pulse",
                                                          "Type:", PULSE_LINE_CONSTRUCTORS.keys(),
                                                          0, False)
        if ok_pressed:
            if DEBUG: print('---PulseGroup - pulse type for new pulse', new_pulse_type)
            if self.parent:
                # print('HereThere')
                channels = self.parent.__dict__["available_channels"][new_pulse_type]
                # print(channels)
            else:
                channels = []
            self.pulses.append(
                PULSE_LINE_CONSTRUCTORS[new_pulse_type](parent=self, data={'Name': 'New', 'Type': new_pulse_type},
                                                        channels=channels))
            # print(self.layout())
            self.main_layout.insertWidget(len(self.pulses) + 1, self.pulses[-1], 0)
            self.main_layout.setSpacing(0)
            self.parent.groupChanged(self, 'pulse_added')
        # self.save()
        return

    def constructData(self):
        # print('pulseGroup-construct data',self.name)
        res = {"name": self.name, "reference": self.reference, "data": [pulse.constructData() for pulse in self.pulses]}
        # print('data', res)
        return res

    def getScanParams(self):
        res = {(pulse.data["Name"] if pulse.data["Type"] != "Group" else "Group"):
                pulse.getScanParams() for pulse in self.pulses}
        return res

    def pulseChanged(self, pulse, changes={}):
        if DEBUG: print('---PulseGroup -pulse changed')
        # pulse_data = pulse.constructData()
        # print(isinstance(pulse,GroupLine))
        if isinstance(pulse,
                      GroupLine) and 'Name' in changes.keys():  # or one can replace to pulse_data['Type']=='Group'
            if DEBUG: print('---PulseGroup - groupLine pulse changed')
            self.name = changes['Name'][1]
            self.parent.groupChanged(self, 'group_name_changed', changes['Name'])
        else:
            self.parent.groupChanged(self, 'pulse_changed', changes)

    def constructTiming(self, ref_boundaties):
        # print('REF BOUNDARIES', ref_boundaties)
        if ref_boundaties == 0:  # starts from the beginning, ignore edge
            t0 = 0
        else:
            t0 = ref_boundaties[0] if self.group_line.widgets['Edge'].getValue() == 'Begin' else ref_boundaties[1]
        # print(self.group_line.widgets)
        t_start = t0 + self.group_line.widgets['Delay'].getValue()
        t_end = t_start + self.group_line.widgets['Length'].getValue()
        # print(t_start, t_end)
        self.group_times = [(t_start + i * (t_end - t0), t_end + i * (t_end - t0)) for i in
                            range(self.group_line.widgets['N'].getValue())]
        # print('GT', self.group_times)
        if self.group_line.widgets['On'].isChecked():
            # print('Here')
            # print([line.__dict__ for line in self.pulses])
            # print(self.pulses)
            points_by_channel = [line.getPoints(self.group_times) for line in self.pulses if
                                 line.data['Type'] != 'Group']
            points_by_channel = [p for p in points_by_channel if p != []]
            # print('pbch1', points_by_channel)

            # print('end', self.group_times)
            return points_by_channel
        else:
            return []

    def getGroupBoundaries(self):
        return self.group_times[0][0], self.group_times[-1][1]

    def updateFromScanner(self,param, value):
        # print("update in widget", param)
        for w in self.pulses:
            # print(w.getName())
            if w.getName() == param[0] or w.data["Type"]==param[0]:
                # was_updated = True
                # print("update in pulse", w)
                w.updateFromScanner(param=param[1],value=value)


class ChannelsWidget(QScrollArea):

    class Line(QWidget):
        def __init__(self, parent, data):
            super().__init__()
            self.autoUpdate = QTimer()
            self.autoUpdate.setInterval(500)
            self.autoUpdate.timeout.connect(self.updateDelayed)
            self.parent = parent
            layout = QHBoxLayout()
            self.data = data
            self.widgets = {}

            for key, val in CHANNEL_LINE_DICT.items():
                # print("Channel data", self.data)
                if val[0] == 'LB':
                    w = QLabel(self.data["Channel"])
                    # w.setMaximumWidth(70)
                elif val[0] == 'MChB':
                    if self.data[key] is None:
                        w = MyCheckBox(is_checked=False, handler=self.update,
                                   max_width=val[-1])
                        w.setCheckable(False)
                    else:
                        w = MyCheckBox(is_checked=self.data[key], handler=self.update,
                                       max_width=val[-1])
                elif val[0] == "LE":
                    if key not in self.data:
                        self.data["Name"] = "New"
                    w = MyLineEdit(name=self.data["Name"],text_changed_handler=self.textEdited,
                                        text_edited_handler=self.textEdited)
                self.widgets[key] = w
                layout.addWidget(w, val[-1])
            layout.addStretch(1)
            layout.setSpacing(10)
            layout.setContentsMargins(5,1,5,1)
            self.main_layout = layout
            self.setLayout(layout)
            self.setMinimumHeight(10)
            self.setMinimumWidth(200)

        def update(self):
            if DEBUG: print('---- channelLine update')
            # print(self.data)
            # changed_item = {}
            for key, val in CHANNEL_LINE_DICT.items():
                if key in ["Channel","Name"]:
                    continue
                if self.data[key] != self.widgets[key].isChecked():
                    # changed_item[key] = (self.data[key], self.widgets[key].isChecked())
                    self.data[key] = self.widgets[key].isChecked()
                    if self.data[key]:  # if I set checked
                        # print(key)
                        other_key = 'On' if key == 'Off' else 'Off'
                        self.data[other_key] = False
                        self.widgets[other_key].setChecked(False)

            # if DEBUG: print('----channel line data changed: line:', self.data)

            if self.parent:
                self.parent.lineChanged()  # figure out how to handle this properly

        def textEdited(self):
            self.autoUpdate.start()

        def updateDelayed(self):
            self.autoUpdate.stop()
            self.data["Name"] = self.widgets["Name"].text()

        def isOn(self):
            # if DEBUG: print('----- isOn',self.data)
            return self.data['On']

        def isOff(self):
            return self.data['Off']

    def __init__(self, parent=None, channels=[]):
        super().__init__(parent)
        self.parent = parent
        self.channels = channels
        self.lines = []
        main_widget = QWidget()
        self.main_layout = QVBoxLayout()
        # layout0 = QHBoxLayout()
        # layout0.addWidget(QLabel('Chan.'))
        # layout0.addWidget(QLabel('On'))
        # layout0.addWidget(QLabel('Off'))
        # layout0.addWidget(QLabel('Name'))
        # self.main_layout.addLayout(layout0)
        self.main_layout.addWidget(QLabel("Channel     On     Off     Name"))

        for channel in sorted(self.channels,key=lambda x:x[0]+"%02i"%int(x[1:])):
            data = self.channels[channel].copy()
            data['Channel'] = channel
            # print('--- channel data',data)
            w = self.Line(parent=self, data=data)
            self.lines.append(w)
            self.main_layout.addWidget(w)
        self.main_layout.addStretch(1)
        main_widget.setLayout(self.main_layout)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0,0,0,0)
        self.setWidget(main_widget)
        self.setMinimumWidth(200)
        self.setMaximumWidth(220)

    def lineChanged(self):
        if DEBUG: print('---ChannelWidget - lineChanged')
        if self.parent:
            self.parent.delayedConstructPulseSequence()

    def isChannelOn(self, channel_name):
        # print('---- isChannelOn',channel_name,self.lines)
        for line in self.lines:
            if line.data["Channel"] == channel_name:
                return line.data['On']
        # return self.lines[channel_name].isOn()

    def isChannelOff(self, channel_name):
        for line in self.lines:
            if line.data["Channel"] == channel_name:
                return line.data['Off']
        # return self.lines[channel_name].isOff()

    def addLine(self, data):
        # do not call anything after since one should first set Channel to lock
        w = self.Line(parent=self, data=data)
        self.lines.append(w)
        self.main_layout.insertWidget(len(self.lines), self.lines[-1])
        # self.save()
        return

    def removeLine(self, channel_name):
        for line in self.lines:
            if line.data["Channel"] == channel_name:
                # print('try to remove', line)
                self.main_layout.removeWidget(line)
                line.deleteLater()
                self.lines.remove(line)
                break
        # print('removed')

    def getChannels(self):
        return [line.data["Channel"] for line in self.lines]

    def insertChannel(self, new_channel):
        print("Insert Channel", new_channel)
        w = self.Line(parent=self, data={"Channel": new_channel, "On": False, "Off": False, "Name":"New"})
        for i, line in enumerate(self.lines):
            if line.data["Channel"] > new_channel and int(line.data["Channel"][1:]) > int(new_channel[1:]):
                self.lines.insert(i, w)
                self.main_layout.insertWidget(i, w)
                return
        self.lines.insert(len(self.lines), w)
        self.main_layout.insertWidget(len(self.lines), w)

    def constructData(self):
        return {line.data["Channel"]: {"On": line.data["On"], "Off": line.data["Off"],"Name":line.data["Name"]} for line in self.lines}


class PulseScheme(QWidget):
    # can be done as QWidget
    def __init__(self, parent=None, available_channels={}, globals={}, signals=None, config_file=None):

        self.delayTimer = QTimer()
        self.delayTimer.setInterval(100)
        self.delayTimer.timeout.connect(self.delayedConstructPulseSequence)
        # self.timerToStartDAQ = QTimer()
        # self.timerToStartDAQ.setInterval(1000)
        # self.timerToStartDAQ.timeout.connect(self.DAQTimerHandler)

        self.cycleTimer = QTimer()
        self.cycleTimer.timeout.connect(self.cycleTimerHandler)
        self.cycleN = 0

        self.timeToWriteDAQ = QTimer()
        self.timeToWriteDAQ.timeout.connect(self.sendTriggerToDAQ)

        super().__init__(parent)
        # self.pulse_signals = PulseSignals()
        self.globals = globals
        self.signals = signals
        self.config_file = config_file
        self.channels_data = {}
        self.data = []  # list of groups in current scheme
        self.t_start = 0
        self.t_scan_finish = 0
        self.call_from_scanner = False
        self.parent = parent
        self.available_channels = available_channels
        self.digital_channels = []
        self.analog_channels = []
        self.active_channels = {}
        self.all_schemes = {}
        self.scan_params = {}
        self.active_shutters = []
        self.config = {}
        self.time_step = 0.1
        self.current_scheme = None
        self.current_groups = []
        self.output = {}
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(0.01)
        self.sock.sendto(bytes("Connect " + json.dumps({"name": "DAQ", "device": "DAQ"}), "utf-8"),
                         self.globals["host_port"])
        self.sock.sendto(bytes("Connect " + json.dumps({"name": "DAQin", "device": "DAQin"}), "utf-8"),
                         self.globals["host_port"])
        # self.dq = DAQHandler()# self.signals.scanCycleFinished.emit)
        # self.globals['DAQ'] = self.dq
        self.load()

        # self.signals.shutterChannelChangedSignal.connect(self.shutterChannelChanged)

        # if 'Signals' not in globals:
        #     globals['Signals'] = {}
        # if 'Pulses' not in globals['Signals']:
        #     globals['Signals']['Pulses'] = {}
        # # globals['Signals']['Pulses']['onAnyChange'] = self.pulse_signals.onAnyChangeSignal
        # self.globals['Pulses']['analog_channels'] = self.analog_channels
        # self.globals['Pulses']['digital_channels'] = self.digital_channels

        self.initUI()
        self.sendScanParams()
        # self.constructPulseSequence() # this will be done after all widgets are loaded
        if self.signals and self.signals.updateFromScanner:
            self.signals.updateFromScanner.connect(self.updateFromScanner)
            self.signals.singleScanFinished.connect(self.handleScanFinish)
        # self.connect(self.)
        # self.pulse_signal.onAnyChangeSignal()

    def initUI(self, tab_index=0):
        self.main_box = QVBoxLayout()
        topbox = QHBoxLayout()

        topbox.addWidget(QLabel('Scheme'))

        self.scheme_combo_box = MyComboBox(items=self.all_schemes, current_text=self.current_scheme,
                                           current_text_changed_handler=self.schemeChanged)
        topbox.addWidget(self.scheme_combo_box)

        self.add_group_button = MyPushButton(name='Add group', handler=self.addGroup)
        topbox.addWidget(self.add_group_button)

        self.save_button = MyPushButton(name='Save', handler=self.saveScheme)
        topbox.addWidget(self.save_button)

        self.save_as_button = MyPushButton(name='Save as', handler=self.saveAsScheme)
        topbox.addWidget(self.save_as_button)

        self.main_box.addLayout(topbox)

        self.hor_box = QHBoxLayout()
        self.hor_box.setSpacing(0)

        if self.channels_data == {}:
            for group in self.data:
                for pulse in group['data']:
                    if pulse['Type'] != "Group":
                        self.channels_data[pulse['Channel']] = {"On": False, "Off": False,"Name":"New"}
        # print('-- channel_data',self.channels_data)
        self.channel_box = ChannelsWidget(parent=self, channels=self.channels_data)
        self.hor_box.addWidget(self.channel_box)

        self.tabbox = QTabWidget()
        self.tabbox.setMovable(True)
        # print('Current scheme: ', self.current_scheme)
        reference_list = ['0'] + [group['name'] for group in self.data]
        for group in self.data:
            tab = QScrollArea()
            tab.setWidget(PulseGroup(parent=self, reference_list=reference_list, **group))
            tab.setFrameShape(QFrame.NoFrame)
            tab.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
            self.tabbox.addTab(tab, group['name'])
        self.tabbox.setMinimumWidth(600)
        self.tabbox.setCurrentIndex(tab_index)
        self.hor_box.addWidget(self.tabbox)

        self.main_box.addLayout(self.hor_box)
        self.main_box.setSpacing(0)
        self.setLayout(self.main_box)
        self.setMinimumHeight(350)
        self.setMaximumHeight(600)
        self.setMinimumWidth(800)
        self.setMaximumWidth(850)

    def load(self):  # new
        if DEBUG: print('--PulseScheme - loadSchemes')
        if not os.path.exists(SCHEMES_FOLDER):
            print('create folder ', SCHEMES_FOLDER)
            os.mkdir(SCHEMES_FOLDER)
        self.all_schemes = os.listdir(SCHEMES_FOLDER)
        with open(self.config_file, 'r') as f:
            if DEBUG: print('config_load')
            all_config = json.load(f)
        self.__dict__.update(all_config['PulseScheme'])  # here one should upload current_scheme and available_channels
        self.available_channels = {conf: all_config[conf]['available_channels'] for conf in all_config
                                   if conf in ["Digital", "Shutters", "Analog", "Input", "Current"]}
        # self.available_channels = list(chain.from_iterable([all_config[conf]['available_channels'] for conf in all_config
        #                                                 if conf in ["Digital","Shutters","Analog"]]))
        # print('available channels', self.available_channels)
        self.loadScheme()

    def loadScheme(self):
        if self.current_scheme in self.all_schemes:  # name in config corresponds to one of scheme files
            with open(os.path.join(SCHEMES_FOLDER, self.current_scheme), 'r') as f:
                print('load_current_scheme', self.current_scheme)
                loaded_data = json.load(f)
                # print(self.data)
            self.data = loaded_data["data"]
            self.channels_data = loaded_data["channels_data"]

    def schemeChanged(self, new_scheme):  # new
        # print('schemeChanged')
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
        # print('addGroup')
        tab = QScrollArea()
        name = 'New group'
        tab.setWidget(PulseGroup(parent=self, name=name, reference='0',
                                 reference_list=['0'] + [group['name'] for group in self.data]))
        tab.setFrameShape(QFrame.NoFrame)
        tab.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.tabbox.addTab(tab, name)
        # print('HERERE')
        self.updateGroupsReferences()
        # print(self.current_groups)
        # do some updates

    def saveConfig(self):
        with open(self.config_file, 'r') as f:
            if DEBUG: print('config_load_before_saving')
            all_config = json.load(f)
            config = all_config['PulseScheme']
        for key in config:
            config[key] = self.__dict__[key]
        with open(CONFIG_FILE, 'w') as f:
            if DEBUG: print('config_save')
            json.dump(config, f)

    def saveScheme(self, save_last=False):
        # print('saveScheme', self.current_scheme)
        self.data = self.constructData()
        self.channels_data = self.channel_box.constructData()
        if DEBUG: print('Data to save:', self.data)
        if not os.path.exists(SCHEMES_FOLDER):
            print('create folder')
            os.mkdir(SCHEMES_FOLDER)
        if save_last:
            path_to_save = os.path.join(SCHEMES_FOLDER,
                                        last_scheme_setup + pulse_name_suffix)
        else:
            path_to_save = os.path.join(SCHEMES_FOLDER, self.current_scheme)
        with open(path_to_save, 'w') as f:
            json.dump({"data":self.data,"channels_data":self.channels_data}, f)

    def saveAsScheme(self):
        if DEBUG: print('saveAsScheme')
        self.data = self.constructData()
        self.channels_data = self.channel_box.constructData()
        self.channels_data = self.channel_box.constructData()
        if DEBUG: print(self.data)
        if not os.path.exists(SCHEMES_FOLDER):
            print('create folder')
            os.mkdir(SCHEMES_FOLDER)
        fname = QFileDialog.getSaveFileName(self, directory=SCHEMES_FOLDER)[0]
        with open(fname, 'w') as f:
            json.dump({"data":self.data,"channels_data":self.channels_data}, f)
        fname = os.path.basename(fname)
        self.all_schemes.append(fname)
        self.current_scheme = fname
        self.scheme_combo_box.addItem(self.current_scheme)
        self.scheme_combo_box.setCurrentText(self.current_scheme)

    def constructData(self):
        res = [w.widget().constructData() for w in self.tabbox.children()[0].children() if
               isinstance(w, QScrollArea)]  # before it wasstr(type(w)).split('.')[-1] == "QScrollArea'>"
        # self.sendScanParams()
        return res

    def deleteGroup(self, group):
        if DEBUG: print("--PulseScheme - deleteGroup")
        confirm = QMessageBox.question(self, "Conferm!!!", 'Delete group',
                                       buttons=QMessageBox.StandardButtons(QMessageBox.Yes | QMessageBox.No))
        if confirm == QMessageBox.Yes:
            try:
                w = [w for w in self.tabbox.children()[0].children()
                     if isinstance(w, QScrollArea) and w.widget() == group][0]
            except:
                print('Can not find widget for group', group)
            # print(w)
            # print(self.tabbox.indexOf(group))
            self.tabbox.removeTab(self.tabbox.indexOf(w))
            w.deleteLater()
            group.deleteLater()
            self.updateGroupsReferences()

    def groupChanged(self, group, change_type, changes=[]):
        if DEBUG: print('--PulseScheme - groupChanged', group.name, change_type, changes)
        if change_type in ['group_name_changed']:
            try:
                w = [w for w in self.tabbox.children()[0].children()
                     if isinstance(w, QScrollArea) and w.widget() == group][0]
                self.tabbox.setTabText(self.tabbox.indexOf(w), group.name)
            except:
                print('ERROR: Can not find widget for group', group)
            # print('SETTING group name', group.name)

            self.updateGroupsReferences(changes)
        elif change_type in ['pulse_deleted']:
            # check if channel assosiated with pulse is still there
            self.data = self.constructData()
            updated_channels = set()
            for group in self.data:
                for pulse in group['data']:
                    if pulse['Type'] != "Group":
                        updated_channels.add(pulse['Channel'])
            if changes not in updated_channels: # deleted line channel was unique
                # print('remove channel', changes)
                self.channel_box.removeLine(changes)
        elif change_type in ['pulse_changed']:
            # print('---pulse_changed', changes)
            if "Channel" in changes:
                old_channel, new_channel = changes["Channel"]
                self.data = self.constructData()
                updated_channels = set()
                for group in self.data:
                    for pulse in group['data']:
                        if pulse['Type'] != "Group":
                            updated_channels.add(pulse['Channel'])
                if old_channel not in updated_channels:
                    print('-updated channels', updated_channels)
                    self.channel_box.removeLine(old_channel)
                if new_channel not in self.channel_box.getChannels():
                    self.channel_box.insertChannel(new_channel)
        elif change_type in ['pulse_added']:
            pass

        # timer is needed since error happened in reference assignment
        self.delayTimer.start()

    def delayedConstructPulseSequence(self):
        self.delayTimer.stop()
        self.constructPulseSequence()

    def updateGroupsReferences(self, changes=[]):
        if DEBUG: print('--PulseScheme - updateGroupsReferences')
        self.data = self.constructData()
        # print(self.data)
        reference_list = ['0'] + [group['name'] for group in self.data]
        # print('REF LIST', reference_list)
        for w in self.tabbox.children()[0].children():
            if isinstance(w, QScrollArea):
                # w.widget().update_frome
                w.widget().setReferenceList(reference_list, changes)
        self.delayTimer.start(100)  # construct pulse sequence

    def handleScanFinish(self,t_finish):
        self.t_scan_finish = t_finish
        return
        self.startDelayedDAQTimer()

    def startDelayedDAQTimer(self):
        print("In delayed timer")
        print(time.perf_counter(),self.t_scan_finish,self.t_start * 1e-3)
        if abs(time.perf_counter() - self.t_scan_finish) > self.t_start * 1e-3:
            self.sendTriggerToDAQ()
        else:
            t_wait = abs(self.t_scan_finish + self.t_start * 1e-3 - time.perf_counter())*1e3
            print("Timer wait for ", t_wait)
            self.timeToWriteDAQ.start(t_wait)

    def constructPulseSequence(self):
        self.data = self.constructData()
        self.sendScanParams()
        # print(self.data)
        groups_named = {w.widget().name: w.widget() for w in self.tabbox.children()[0].children()
                        if isinstance(w, QScrollArea)}
        groups_and_refs = {group['name']: [group['reference']] for group in self.data}
        # print('REFS AND GROUPS', groups_and_refs)
        group_chains = []
        for group_name, refs in groups_and_refs.items():
            # print(group_name,refs)
            i = 10
            while refs[0] != '0':
                if i <= 0:
                    print('ERROR - cycled ')
                    break
                # print(refs,*groups_and_refs[refs[0]])
                groups_and_refs[group_name] = groups_and_refs[refs[0]] + groups_and_refs[group_name]
                # refs.insert(0,*groups_and_refs[refs[0]])
                refs = groups_and_refs[group_name]
                i -= 1
                # print(refs)
            group_chains.append(groups_and_refs[group_name] + [group_name])
        # print('NEW GROUPS AND REFS', group_chains)
        updated_groups = ['0']
        points = []
        for chain in group_chains:
            # print('chain', chain)
            for group_name in chain:
                # print('current group name', group_name)
                if group_name in updated_groups:
                    continue
                else:
                    # print(chain, chain.index(group_name) - 1)
                    ref = chain[chain.index(group_name) - 1]
                    # print(group_name, ref)
                    if ref == '0':
                        pfg = groups_named[group_name].constructTiming(0)
                    else:
                        pfg = groups_named[group_name].constructTiming(groups_named[ref].getGroupBoundaries())
                    # print('pfg', pfg)
                    points.extend(pfg)
                    updated_groups.append(group_name)
        # print('HERE FINISHED')
        # print('all points', points)
        points_by_channel = {}
        for sp in points:
            channel, pts = sp
            if channel in points_by_channel:
                points_by_channel[channel].append(pts)
            else:
                points_by_channel[channel] = [pts]
        # if True: print('points by channel before processing\n', points_by_channel)
        # print("available channels", self.available_channels)

        # handle channel always on/off
        for channel in points_by_channel:
            # pulse_type = [t for t in self.available_channels if channel in self.available_channels[t]][0]
            # print('Channel', channel, 'in', pulse_type)
            if self.channel_box.isChannelOn(channel):  # replace with self.channel_widget.channels[channel].isAlwaysOn()
                points_by_channel[channel] = [[[0,1]]]  # get value depending on channel type
            elif self.channel_box.isChannelOff(channel):  # replace with self.channel_widget.channels[channel].isAlwaysOff()
                points_by_channel[channel] = [[[0, 0]]]
        # find time of end of sequence
        t_end = 0
        for channel in points_by_channel:
            for pulse in points_by_channel[channel]:
                for point in pulse:
                    if point[0] > t_end:
                        t_end = point[0]
        t_end += 10
        print("Last t in sequence (10ms encluded) ", t_end)

        # taking into account trigger front fo Digital channels
        self.t_start = points_by_channel["D21"][0][0][0]
        print("Start of the trigger",self.t_start)
        for channel in points_by_channel:
            if channel in self.available_channels["Digital"]:
                points_by_channel[channel] = DigitalLine.combinePoints(points_by_channel[channel])
                if len(points_by_channel[channel]) == 1 or len(points_by_channel[channel]) == 0: # single point in channel
                    # print("Do not touch", channel)
                    continue
                if points_by_channel[channel][0][0] > 0:
                    points_by_channel[channel].insert(0, [0, (points_by_channel[channel][0][1]+1)%2])
        if self.globals:
            self.globals['pulses'] = points_by_channel

        if self.signals:
            # self.t_start = 0
            self.signals.pulsesChanged.emit(self.t_start,t_end)
        # trigger delayed start - NOT USED NOW
        # self.timeToWriteDAQ.stop()
        # self.startDelayedDAQTimer()

    def sendTriggerToDAQ(self):
        # TODO check that pulses were written to DAQ if needed
        print("In send to dac")
        print(time.perf_counter())
        self.timeToWriteDAQ.stop()
        data = {"name": "DAQ", "device": "DAQ"}
        data.update({"msg": "start"})
        msg = 'Send ' + json.dumps(data)
        print("SEND TO DAQ", msg, time.perf_counter())
        self.sock.sendto(bytes(msg, "utf-8"), self.globals["host_port"])

    def cycleTimerHandler(self):  # old
        self.cycleN += 1
        self.signals.scanCycleFinished.emit(self.cycleN)
        return

    def updateAndSendScanParameters(self):  # old
        print('updateAndSendScanParameters')
        self.scan_params = {}
        for group in self.current_groups:
            self.scan_params[group.name] = {}
            self.scan_params[group.name]['group'] = list(group.variables.keys())
            for pulse in group.pulses:
                self.scan_params[group.name][pulse.name] = list(pulse.variables.keys())
        # print('Scan params',self.scan_params)
        # send scan parameters to global
        if self.globals:
            if scan_params_str not in self.globals:
                self.globals[scan_params_str] = {}
            self.globals[scan_params_str][name_in_scan_params] = self.scan_params
            # print(self.scan_params)

    def updateFromScanner(self):
        current_shot = self.globals["scan_running_data"]["current_meas_number"]
        changed = False
        for param,path in {**self.globals["scan_params"]["main"],**self.globals["scan_params"]["low"]}.items():
            if path[0] == "Pulses" and (current_shot==0 or
            self.globals["scan_running_table"].loc[current_shot,param] != self.globals["scan_running_table"].loc[current_shot-1,param]):
                changed = True
                if DEBUG: print("Pulses - update from scanner - ",param, path)
                try:
                    w = [w for w in self.tabbox.children()[0].children()
                         if isinstance(w, QScrollArea) and w.widget().name == path[1]][0]
                    # print("Found group", w.widget().name)
                    w.widget().updateFromScanner(param=path[2:],value=self.globals["scan_running_table"].loc[current_shot,param])
                except:
                    print('Can not find widget for group', param["Param"][1])
        if changed:
            self.constructPulseSequence()

    def getUpdateMethod(self):  # old
        return self.updateFromScanner

    def sendScanParams(self):
        self.constructData()
        # data = self.constructData()
        # print(data)
        params = {w.widget().name: w.widget().getScanParams() for w in
                  self.tabbox.children()[0].children() if isinstance(w, QScrollArea)}

        # for group in data:
        #     g_key = group['name']
        #     g_params = {}
        #     for pulse in group["data"]:
        #         key = pulse["Name"] if pulse["Type"] != "Group" else "Group"
        #         g_params[key] = list(pulse.keys())
        #     params[g_key] = g_params
        if self.globals:
            if SCAN_PARAMS_STR not in self.globals:
                self.globals[SCAN_PARAMS_STR] = {}
            self.globals[SCAN_PARAMS_STR][NAME_IN_SCAN_PARAMS] = params
        return


class PlotPulse(pg.GraphicsWindow):
    def __init__(self, parent=None, globals={}, signals=None, **argd):
        self.signals = signals
        self.parent = parent
        self.globals = globals
        super().__init__(title="PulsePlot")
        # self.resize(600, 600)
        self.signals.updateDigitalPlot.connect(self.updatePlot)
        self.setMinimumHeight(250)
        # self.updatePlot()

    def updatePlot(self,t_start,t_end):
        """used as a slot called by Pulses class to redraw pulses
            CAN BE DONE IN THREAD"""
        self.plotPulses(t_start,t_end)

    def plotPulses(self,t_start,t_end):
        print('PlotPulses')
        self.clear()    # clear plot
        self.setBackground('w')
        # self.s
        d_plot = self.addPlot()
        d_plot.getAxis('left').setPen(pg.Color('k'))
        d_plot.getAxis('bottom').setPen(pg.Color('k'))
        d_plot.showGrid(x=True)
        digital_height = 1.2  # place for each curve of height=1graphic
        digital_counter = 0   # number of plotted channel
        digital_list = []     # list of active digital channels
        # print(self.globals["pulses"])
        t_first = min(min(x[0] for x in value if x[0] > 0) for name, value in
                      self.globals['pulses'].items() if 'D' in name and  len(value)>1)
        t_last = t_end
        # t_last = max(max(x[0] for x in value if x[0] > 0) for name, value in
        #               self.globals['pulses'].items() if 'D' in name and  len(value)>1) + 10

        for name in sorted([key for key in self.globals['pulses'].keys() if "D" in key], key=lambda x: -int(x, base=16)):
            digital_list.append(name)
            value = self.globals['pulses'][name]
            xx = []
            yy = []

            # construct points to show
            for i, point in enumerate(value):
                if i == 0:
                    xx.append(t_first-(100 if t_first > 100 else t_first))
                    yy.append(point[1])
                    continue
                # if not i == len(value) - 1:
                xx.append(point[0])
                yy.append(not point[1])
                xx.append(point[0])
                yy.append(point[1])
            xx.append(t_last)
            yy.append(point[1])
            d_plot.plot(np.array(xx), np.array(yy)+digital_counter*digital_height,
                        pen=pg.mkPen(pg.intColor(digital_counter), width=2))  # plot data
            d_plot.plot(np.array(xx), np.ones_like(xx)*digital_counter*digital_height,
                        pen=pg.mkPen(pg.intColor(digital_counter), width=0.5, style=Qt.DashLine))  # plot zero
            digital_counter += 1
        # set ticks names
        if 'channels_affiliation' in self.globals:
            tick_names = [' '.join([x] + list(set(self.globals['channels_affiliation'][x]))) for x in digital_list]
        else:
            tick_names = digital_list
        d_plot.getAxis('left').setTicks([list(zip((np.arange(len(digital_list))+1/2) * digital_height, tick_names))])

if __name__ == '__main__':
    import sys
    # digital_pulses_folder = 'digital_schemes'
    # pulseGroup = PulseGroup
    app = QApplication(sys.argv)
    # mainWindow = PulseGroup(parent=None,name='New group',data=[])
    # mainWindow = PulseScheme()
    mainWindow = PulseScheme(config_file='config.json')
    mainWindow.show()
    sys.exit(app.exec_())

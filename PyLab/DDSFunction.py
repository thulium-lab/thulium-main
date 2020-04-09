import os, re, pickle, json, matplotlib, time, socket
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
NAME_IN_SCAN_PARAMS = 'DDS_function'

voltage_validator = QDoubleValidator(-10.0,10.0,1)
n_avr_validator = QIntValidator(1,1000)
AnalogInLineDict = OrderedDict([
    ("Del",['MPB','Del',40]),
    ('Channel',['CB','I0',['I%i'%i for i in range(8)]+['I23'],60]),
    ('Name', ['LE', 'New shutter', 120]),
    ('Vmin',['MDB',0,voltage_validator,60]),
    ('Vmax',['MDB',1,voltage_validator,60]),
    ('Navr',['MIB',1,n_avr_validator,50]),
    ('oOff',['MChB',False,20]),
])


class AnalogInWidget(QScrollArea):
    class Line(QWidget):
        def __init__(self, parent,input_channels=[],data={}):
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
            for key, val in AnalogInLineDict.items():
                # print(key,val)
                if key == 'Del':
                    w = MyPushButton(name=key,handler=lambda: self.parent.delete(self), fixed_width=val[-1])
                    layout.addWidget(w, val[-1])
                    continue
                self.data[key] = data.get(key, val[1])
                if val[0] == 'CB':
                    # create a combo box widget
                    if key == 'Channel':
                        items = input_channels if input_channels != [] else val[2]
                    w = MyComboBox(items=items, current_text=data.get(key, val[1]),
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

        def update(self):
            if DEBUG: print('---- AnalogInLine update')
            # print(str(self))
            self.autoUpdate.stop()
            # print('Here1')
            changed_item = {}
            for key, val in AnalogInLineDict.items():
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
            if DEBUG: print('AnalogIn line data changed: line:', self.data['Name'], changed_item)

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

        def getVmin(self):
            return self.widgets["Vmin"].value()

        def getVmax(self):
            return self.widgets["Vmax"].value()

        def getNavr(self):
            return self.widgets["Navr"].value()

    def __init__(self,parent=None,globals={},signals={},port=None,input_channels=[],data={},config_file=None):
        super().__init__(parent)
        self.config_file = config_file
        self.globals = globals
        self.signals = signals
        self.parent = parent
        self.port = port # now it is arduino com-port
        self.data = data
        self.input_channels = input_channels
        self.rates = ["1","2","5","10","20","50","100"]
        self.current_rate = "10"
        self.lines = []
        self.load()
        self.plot_widget = PlotPulse(parent=self)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(0.01)
        self.menuBar = QMenuBar(self)
        self.initUI()
        # self.sendScanParams()
        self.t_start = 0
        self.t_end = 1000
        if self.signals:
            self.signals.pulsesChanged.connect(self.constructPulses)

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

        self.setWindowTitle('AnalogIN')
        # self.setWindowIcon(QIcon('Devices\dds.jpg'))
        main_widget = QWidget()
        top_layout = QHBoxLayout()

        rate_layout = QVBoxLayout()
        rate_layout.addWidget(QLabel(""))
        rate_layout.addWidget(QLabel("dt, us"))
        self.rate_box = MyComboBox(items=self.rates,current_text=self.current_rate,current_text_changed_handler=self.currentRateChanged)
        rate_layout.addWidget(self.rate_box)
        rate_layout.addStretch(1)
        top_layout.addLayout(rate_layout)

        mainLayout = QVBoxLayout()

        fields = QHBoxLayout()
        # fields.addSpacing(15)
        for key,val in AnalogInLineDict.items():
            lbl = QLabel(key)
            lbl.setMinimumWidth(val[-1])
            fields.addWidget(lbl)#, val[-1])
        # fields.addStretch(50)
        fields.setSpacing(10)
        fields.addStretch(1)
        mainLayout.addLayout(fields)

        for d in self.data:
            w = self.Line(self, data=d, input_channels=self.input_channels)
            self.lines.append(w)
            mainLayout.addWidget(w)

        updateAllBtn = MyPushButton(name="update all", handler=lambda :self.constructPulses(None,None), max_width=550)
        mainLayout.addWidget(updateAllBtn)

        addLine = QPushButton('add channel')
        addLine.setMaximumWidth(550)
        addLine.clicked.connect(self.addLine)
        mainLayout.addWidget(addLine)
        mainLayout.addStretch(1)
        top_layout.addLayout(mainLayout)
        top_layout.addWidget(self.plot_widget)
        main_widget.setLayout(top_layout)
        main_widget.setMaximumWidth(1400)
        self.setWidgetResizable(True)
        self.setWidget(main_widget)
        self.setMinimumHeight(200)
        self.setMinimumWidth(550)
        self.main_layout = mainLayout

    def addLine(self):
        # do not call anything after since one should first set "Channel to lock"
        w  = self.Line(parent=self, input_channels=self.input_channels, data={})
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

    def lineChanged(self,line, changes):
        if DEBUG: print('--- AnalogInWidget - lineChanged', changes)
        # self.sendScanParams()
        self.constructPulses(self.t_start,self.t_end)

    def currentRateChanged(self, new_rate):
        self.current_rate = new_rate
        self.constructPulses(None,None)

    def constructData(self):
        data = [line.constructData() for line in self.lines]
        return data

    def constructPulses(self,t_start,t_end):
        """constructs and updates pulses produced by Shutters channels"""
        if t_start == None:
            update_all_command = True
        else:
            self.t_start = t_start
            self.t_end = t_end
            update_all_command = False
        lines_channeled = {line.data["Channel"]:line for line in self.lines}
        if self.globals and "pulses" in self.globals:
            new_pulses = {channel: self.globals["pulses"][channel] for channel in self.globals["pulses"] if
                          channel in sorted(self.available_channels)}
            # if DEBUG: print('current pulses', new_pulses)
        else:
            new_pulses = {}
        channels_data = {}
        for channel in sorted(lines_channeled):
            line = lines_channeled[channel]
            if line.data["oOff"]: # if channel is turned off
                continue
            elif channel not in new_pulses or len(new_pulses[channel][0])==1: # if there are no pulses in this channel
                continue
            else:
                channels_data[channel] = []
                for pulse in new_pulses[channel]:
                    channels_data[channel].append([pulse[0][0]-self.t_start,pulse[1][0]-self.t_start]) # add start and end time
        self.channels_data = deepcopy(channels_data)
        data_to_send = {"rate":1e6/int(self.current_rate),
                        "lines":{},
                        "limits":{},
                        "n_avrs":{},
                        "samples":0}
        t_max = 0
        for channel in channels_data:
            data_to_send["n_avrs"][channel] = lines_channeled[channel].getNavr()
            data_to_send["limits"][channel] = (lines_channeled[channel].getVmin(),lines_channeled[channel].getVmax())
            data_to_send["lines"][channel] = [[int(pulse[0]*(data_to_send["rate"]/1e3)),int(pulse[1]*(data_to_send["rate"]/1e3))] for pulse in channels_data[channel]]
            t_pulse_max = max([pulse[1] for pulse in channels_data[channel]]) # compare ends of each pulse
            if t_pulse_max > t_max:
                t_max = t_pulse_max
        data_to_send["samples"] = int(t_max*(data_to_send["rate"]/1e3))
        # print("AnalogIn data", data_to_send)
        # msg += final_msg
        # print("Message to shutters")
        # print(msg)
        msg_to_server = "Send " + json.dumps({"name":"DAQin","msg":data_to_send})
        print(msg_to_server)
        self.sock.sendto(bytes(msg_to_server, "utf-8"), self.globals["host_port"])
        self.plot_widget.updatePlot(self.t_start,self.t_end)

    def load(self):
        if DEBUG: print('load AnalogIn', end='\t')
        with open(self.config_file, 'r') as f:
            if DEBUG: print('config_load')
            config = json.load(f)
        print(config['Input'])
        self.__dict__.update(config['Input'])  # here one should upload current_scheme and available_channels
        # print('other channels',self.other_channels)

    def saveClicked(self):
        # print('save shutters', self)
        self.data = self.constructData()
        with open(self.config_file, 'r') as f:
            if DEBUG: print('config_load_before_saving')
            all_config = json.load(f)
        config = all_config['Input']
        for key in config:
            config[key] = self.__dict__[key]
        with open(self.config_file, 'w') as f:
            if DEBUG: print('config_save')
            json.dump(all_config, f)

    # def sendScanParams(self):
    #     params = {}
    #     data = self.constructData()
    #     for d in data:
    #         key = d['Name']
    #         params[key] = list(d.keys())
    #     if self.globals != None:
    #         if SCAN_PARAMS_STR not in self.globals:
    #             self.globals[SCAN_PARAMS_STR] = {}
    #         self.globals[SCAN_PARAMS_STR][NAME_IN_SCAN_PARAMS] = params
    #     return


class PlotPulse(pg.GraphicsWindow):
    def __init__(self, parent=None, globals={}, signals=None, **argd):
        self.signals = signals
        self.parent = parent
        self.globals = globals
        super().__init__(title="AnalogInPlot")
        # self.resize(600, 600)
        # self.signals.updateDigitalPlot.connect(self.updatePlot)
        self.setMinimumHeight(150)
        # self.updatePlot()

    def updatePlot(self,t_start,t_end):
        """used as a slot called by Pulses class to redraw pulses
            CAN BE DONE IN THREAD"""
        self.plotPulses(t_start,t_end)

    def plotPulses(self,t_start,t_end):
        print('PlotAnalogIn')
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
        if self.parent.channels_data == {}:
            return
        t_first = min(min(x[0] for x in value if x[0] > 0) for name, value in
                      self.parent.channels_data.items() if 'I' in name)
        t_last = t_end
        # t_last = max(max(x[0] for x in value if x[0] > 0) for name, value in
        #               self.globals['pulses'].items() if 'D' in name and  len(value)>1) + 10
        pulse_counter = 0
        for name in sorted(self.parent.channels_data.keys(),reverse=True):
            if 'I' not in name:
                continue
            digital_list.append(name)
            value = self.parent.channels_data[name]


            # construct points to show
            for i, pulse in enumerate(value):
                xx = [t_first-(100 if t_first > 100 else t_first),pulse[0],pulse[0],pulse[1],pulse[1],t_last-t_start]
                yy = [0,0,1,1,0,0]
                # xx.append(t_first-(100 if t_first > 100 else t_first))
                # yy.append(0)
                # xx.append(pulse[0])
                # yy.append(1)
                # xx.append(pulse[1])
                # yy.append(0)
                # xx.append(t_last-t_start)
                # yy.append(0)
                d_plot.plot(np.array(xx), np.array(yy)+digital_counter*digital_height,
                            pen=pg.mkPen(pg.intColor(pulse_counter), width=2))  # plot data
                pulse_counter += 1
            d_plot.plot(np.array(xx), np.ones_like(xx)*digital_counter*digital_height,
                        pen=pg.mkPen(width=0.5, style=Qt.DashLine))  # plot zero
            digital_counter += 1
        # set ticks names

        tick_names = digital_list
        d_plot.getAxis('left').setTicks([list(zip((np.arange(len(digital_list))+1/2) * digital_height, tick_names))])

if __name__ == '__main__':
    import sys
    # digital_pulses_folder = 'digital_schemes'
    # pulseGroup = PulseGroup
    app = QApplication(sys.argv)
    # mainWindow = PulseGroup(parent=None,name='New group',data=[])
    # mainWindow = PulseScheme()
    mainWindow = AnalogInWidget(config_file='config.json')
    mainWindow.show()
    sys.exit(app.exec_())

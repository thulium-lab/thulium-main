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
NAME_IN_SCAN_PARAMS = 'Shutters'

shutter_validator = QDoubleValidator(-99.9,99.9,1)
ShutterLineDict = OrderedDict([
    ("Del",['MPB','Del',40]),
    ('Channel',['CB','S0',['S%i'%i for i in range(13)],60]),
    ('Name', ['LE', 'New shutter', 120]),
    ('t_open',['MDB',0,shutter_validator,60]),
    ('t_close',['MDB',0,shutter_validator,60]),
    ('oOn', ['MChB', False, 20]),
    ('oOff',['MChB',False,20]),
    ('Lock to Channel',['CB',None,[],60]),
])


class ShutterWidget(QScrollArea):
    class Line(QWidget):
        def __init__(self, parent,shutter_channels=[],other_channels=[], data={}):
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
                        # print('other channels',other_channels)
                        items = ['0'] + (other_channels if other_channels != [] else val[2])
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
            if DEBUG: print('---- ShutterLine update')
            # print(str(self))
            self.autoUpdate.stop()
            # print('Here1')
            changed_item = {}
            for key, val in ShutterLineDict.items():
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
            if DEBUG: print('Shutter line data changed: line:', self.data['Name'], changed_item)

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

    def __init__(self,parent=None,globals={},signals={},port=None,shutter_channels=[],other_channels=[],data={},config_file=None):
        super().__init__(parent)
        self.config_file = config_file
        self.globals = globals
        self.signals = signals
        self.parent = parent
        self.port = port # now it is arduino com-port
        self.data = data
        self.shutter_channels = shutter_channels
        self.other_channels = other_channels
        self.load()
        # self.device = COMPortDevice(default_port=port)
        # self.device_widget = self.device.ExtendedWidget(data=self.device,connect= False)#(self.port!=None)
        self.plot_widget = PlotPulse(parent=self)
        self.device_widget = COMPortWidget(parent=self, connect=False, data=self.device,
                                           host_port=self.globals["host_port"])
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
        self.delayedSendTimer = QTimer()
        self.delayedSendTimer.setInterval(50)
        self.delayedSendTimer.timeout.connect(self.delayedWrite)
        self.t_start = 0
        self.t_end = 1000
        if self.signals:
            self.signals.pulsesChanged.connect(self.constructPulses)
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

        self.setWindowTitle('Shutter')
        # self.setWindowIcon(QIcon('Devices\dds.jpg'))
        main_widget = QWidget()
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.device_widget)
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
            w = self.Line(self, data=d, shutter_channels=self.shutter_channels, other_channels=self.other_channels)
            self.lines.append(w)
            mainLayout.addWidget(w)

        updateAllBtn = MyPushButton(name="update all", handler=lambda :self.constructPulses(None,None), max_width=550)
        mainLayout.addWidget(updateAllBtn)

        addLine = QPushButton('add shutter')
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

    def lineChanged(self,line, changes):
        if DEBUG: print('--- shutterWidget - shutterChanged', changes)
        self.sendScanParams()
        self.constructPulses(self.t_start,self.t_end)
        # line_data = line.constructData()
        # print(line_data)
        # if 'Lock to Channel' in changes and  self.signals:
        #     if DEBUG:  print('emit shutterChannelChangedSignal',' '.join([line.data['Channel'],changes['Lock to Channel'][0],
        #                                                             changes['Lock to Channel'][1]]))
        #     # send Shutter_channel, Old_PulseChannel, New_pulse_channel
        #     self.signals.shutterChannelChangedSignal.emit(' '.join([line.data['Channel'],changes['Lock to Channel'][0],
        #                                                             changes['Lock to Channel'][1]]))

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
        channels_data = {}
        for channel in sorted(lines_channeled):
            line = lines_channeled[channel]
            if line.data["oOff"]:
                channels_data[channel]=[[0,0]]
            elif line.data["oOn"]:
                channels_data[channel] = [[0, 1]]
            else:
                if self.globals and "pulses" in self.globals and line.data['Lock to Channel'] in self.globals["pulses"]:
                    channel_pulses = self.globals["pulses"][line.data['Lock to Channel']]
                else:
                    channels_data[channel]=[[0,0]]
                    continue
                # print("Shutter ", channel, "digital pulse data")
                # print(channel_pulses)
                channels_data[channel] = []
                for edge in channel_pulses:
                    if edge[0]==0:
                        channels_data[channel].append([0,edge[1]])
                    else:
                        if edge[1] == 0:    # turning off
                            channels_data[channel].append([edge[0]-line.data["t_close"], edge[1]])
                        else:               # turning on
                            channels_data[channel].append([edge[0] - line.data["t_open"], edge[1]])
                points_to_drop = set()
                if len(channels_data[channel]) > 2:
                    for i, edge in enumerate(channels_data[channel]):
                        if i==0:
                            continue
                        if edge[0] < channels_data[channel][i-1][0]: # i.e. if time for openning of next pulse is before closing previous one
                            points_to_drop.update([i-1,i])
                channels_data[channel] = [edge for edge in channels_data[channel] if channels_data[channel].index(edge) not in points_to_drop]

        # print("Shutters data BEFORE", channels_data)
        self.full_channels_data = {key: deepcopy(channels_data[key]) for key in channels_data}
        # print("t_start, t_end",self.t_start, self.t_end)
        # shift by t_start
        if self.t_start != 0:
            for channel, points in channels_data.items():
                new_points = []
                for point in deepcopy(points):
                    # print(point)
                    if point[0] == 0:  # beginning of the pulses
                        end_point = [self.t_end - self.t_start, point[1]]  # calculate ending point
                        new_points.append(point)  # add this point in the beginning of new pulses
                    elif point[0] < self.t_start:
                        new_points[0][1] = point[1]  # assume here that shutter edge can be a bit earlier than t_start
                    elif point[0] == self.t_start:  # if front directly at t_start
                        new_points[0][1] = point[1]  # rewrite first point
                    else:
                        new_points.append([point[0] -self.t_start, point[1]])
                        # print(1)
                        # point[0] -= t_start
                new_points.append(end_point)
                channels_data[channel] = new_points
        # print("Shutters data AFTER", channels_data)
         # to use in ShuttersPlot
        edges = set()
        for channel,points in channels_data.items():
            for point in points:
                edges.add(point[0])
        edges = sorted(edges)
        msg = "BS " + "".join([channel[1:] for channel in sorted(lines_channeled,reverse=True)])
        final_msg = ''
        for t in edges:
            val=0
            for j,channel in enumerate(sorted(lines_channeled)):
                channel_points = channels_data[channel]
                flag = False
                for i,point in enumerate(channel_points):
                    if t == point[0]:
                        val += point[1]*(2**j)
                        flag = True
                        break
                    elif t < point[0]:
                        if i!=0:
                            val += channel_points[i-1][1]*(2**j)
                        flag = True
                        break
                if not flag:
                    val += channel_points[-1][1] * (2 ** j)
            if t==0:
                msg += " " + str(int(t))+"_"+str(val)
                # final_msg = " " + str(int(t_end-t_start))+"_"+str(val)
            else:
                msg += " " + str(int(t)) + "_" + str(val)
        # msg += final_msg
        # print("Message to shutters")
        # print(msg)
        if len(msg) >=60: # this is done to ensure less than 64 bites transmission to arduino
            w_spaces = [x.start() for x in re.finditer(" ",msg)]
            for w in w_spaces[::-1]:
                if w < 60:
                    break
            msg1 = msg[:w] + "!"
            msg_to_server = json.dumps({"name": "Shutters", "msg": msg1})
            print(msg_to_server)
            self.device_widget.send(msg_to_server)
            # time.sleep(0.2)
            msg2 = "BS " + msg[w+1:] + "!"
            msg_to_server = json.dumps({"name": "Shutters", "msg": msg2})
            print(msg_to_server)
            self.msg_to_write = msg_to_server
            self.delayedSendTimer.start()
            # self.device_widget.send(msg_to_server)
        else:
            msg_to_server = json.dumps({"name":"Shutters","msg":msg+"!"})
            print(msg_to_server)
            self.device_widget.send(msg_to_server)
        self.plot_widget.updatePlot(self.t_start,self.t_end)

    def delayedWrite(self):
        self.delayedSendTimer.stop()
        self.device_widget.send(self.msg_to_write)

    def load(self):
        if DEBUG: print('load shutters', end='\t')
        with open(self.config_file, 'r') as f:
            if DEBUG: print('config_load')
            config = json.load(f)
        # print(config['Shutters'])
        self.__dict__.update(config['Shutters'])  # here one should upload current_scheme and available_channels
        self.other_channels = list(chain.from_iterable([config[conf]['available_channels'] for conf in config
                                                        if conf in ["Digital"]]))
        # print('other channels',self.other_channels)

    def saveClicked(self):
        # print('save shutters', self)
        self.data = self.constructData()
        with open(self.config_file, 'r') as f:
            if DEBUG: print('config_load_before_saving')
            all_config = json.load(f)
        config = all_config['Shutters']
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

class PlotPulse(pg.GraphicsWindow):
    def __init__(self, parent=None, globals={}, signals=None, **argd):
        self.signals = signals
        self.parent = parent
        self.globals = globals
        super().__init__(title="ShuttersPlot")
        # self.resize(600, 600)
        # self.signals.updateDigitalPlot.connect(self.updatePlot)
        self.setMinimumHeight(150)
        # self.updatePlot()

    def updatePlot(self,t_start,t_end):
        """used as a slot called by Pulses class to redraw pulses
            CAN BE DONE IN THREAD"""
        self.plotPulses(t_start,t_end)

    def plotPulses(self,t_start,t_end):
        # print('PlotShutters')
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
                      self.parent.full_channels_data.items() if 'S' in name and  len(value)>1)
        t_last = t_end
        # t_last = max(max(x[0] for x in value if x[0] > 0) for name, value in
        #               self.globals['pulses'].items() if 'D' in name and  len(value)>1) + 10

        for name in sorted(self.parent.full_channels_data.keys(),reverse=True):
            if 'S' not in name:
                continue
            digital_list.append(name)
            value = self.parent.full_channels_data[name]
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

        tick_names = digital_list
        d_plot.getAxis('left').setTicks([list(zip((np.arange(len(digital_list))+1/2) * digital_height, tick_names))])

if __name__ == '__main__':
    import sys
    # digital_pulses_folder = 'digital_schemes'
    # pulseGroup = PulseGroup
    app = QApplication(sys.argv)
    # mainWindow = PulseGroup(parent=None,name='New group',data=[])
    # mainWindow = PulseScheme()
    mainWindow = ShutterWidget(config_file='config.json')
    mainWindow.show()
    sys.exit(app.exec_())

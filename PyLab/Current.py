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
from PyQt5.QtGui import (QBrush, QColor, QPainter,QIcon, QDoubleValidator,QTextCursor)
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
NAME_IN_SCAN_PARAMS = 'Current'

defauld_current_validator = QDoubleValidator(0,300,1)
CurrentLineDict = OrderedDict([
    ("Del",['MPB','Del',40]),
    ('Channel',['CB','C0',['C%i'%i for i in range(8)],60]),
    ('Name', ['LE', 'New shutter', 100]),
    ('I',['MDB',0,defauld_current_validator,60]),
    ("Neg On",['MChB',False,30]),
    ('Range',['CB',"200",["3.125","6.25","12.5","25","50","100","200","300"],60]),
    ('On',['MChB',False,20]),
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
                                   text_changed_handler=self.textEdited,
                                   text_edited_handler=self.textEdited,
                                   max_width=val[-1])
                elif val[0] == 'MDB':
                    validator = val[2]
                    # print("FEDHDSI",key, self.data)
                    if key == "I":
                        # print("NEW OHGD")
                        if "Range" in self.data:
                            top_val = float(self.data["Range"])
                            bottom_val = -top_val if self.data["Neg On"] else 0
                            validator = QDoubleValidator(bottom_val,top_val,1)
                    w = MyDoubleBox(validator=validator, value=data.get(key, val[1]),
                                    text_changed_handler=self.textEdited,
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
                        if key == "Range": #if range changed one need to check current to be inside the range
                            top_val = float(self.data["Range"])
                            bottom_val = -top_val if self.data["Neg On"] else 0
                            validator = QDoubleValidator(bottom_val, top_val, 1)
                            self.widgets["I"].setValidator(validator)
                            if abs(self.data["I"]) > float(self.data["Range"]):
                                self.data["I"] = np.sign(self.data["I"])*float(self.data["Range"])
                                self.widgets["I"].setValue(str(self.data["I"]))
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
                        if key=="Neg On":
                            top_val = float(self.data["Range"])
                            bottom_val = -top_val if self.data["Neg On"] else 0
                            validator = QDoubleValidator(bottom_val, top_val, 1)
                            self.widgets["I"].setValidator(validator)
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

        def getRangeFloat(self):
            return float(self.data["Range"])

        def getCurrentFloat(self):
            return self.data["I"]

        def getChannelNstr(self):
            return self.data["Channel"][1:]

        def getChannel(self):
            return self.data["Channel"]

        def isChannelOn(self):
            return self.data["On"]

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
        self.plot_widget = PlotPulse(parent=self)
        self.arduino_readings = {"status": "Not connected",
                                 "data": [""]*6,
                                 "last_msgs": [],
                                 "last_readings": []}
        self.arduino_readings_length = 3
        self.arduino_msg_length = 2
        # self.device = COMPortDevice(default_port=port)
        self.lines = []
        self.menuBar = QMenuBar(self)
        self.device_widget = COMPortWidget(parent=self, connect=False, data=self.device,host_port=self.globals["host_port"])
        self.device_widget.setMinimumWidth(300)
        self.initUI()
        self.sendScanParams()
        self.old_pulses = {}
        self._update_from_scanner = False
        self.t_start=0
        self.t_end = 1000
        if self.signals:
            self.signals.pulsesChanged.connect(self.constructPulses)
            self.signals.updateFromScanner.connect(self.updateFromScanner)
            self.signals.readingsFromArduino.connect(self.updateDeviceReadings)
            self.signals.serverComPortsUpdate.connect(self.device_widget.updateComPorts)

    def initUI(self):
        fileMenu = self.menuBar.addMenu('&File')
        save = QAction('&Save', self)
        save.triggered.connect(self.saveClicked)
        fileMenu.addAction(save)

        self.setWindowTitle('Current')
        # self.setWindowIcon(QIcon('Devices\dds.jpg'))
        main_widget = QWidget()
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.device_widget)
        mainLayout = QVBoxLayout()

        fields = QHBoxLayout()
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

        updateAllBtn = MyPushButton(name="update all",handler=self.updateAllBtnPressed,max_width=550)
        mainLayout.addWidget(updateAllBtn)

        addLine = QPushButton('add current channel')
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

    def updateAllBtnPressed(self):
        msgs = []
        msg = "all_ranges " + " ".join([str(int(1000 * line.getRangeFloat())) for line in self.lines]) + "!"
        msg_to_server = json.dumps({"name": "Current", "msg": msg})
        print(msg_to_server)
        self.device_widget.send(msg_to_server)

        self.constructPulses(None,None)
        # msg = "all_currents " + " ".join(["%.1f"%(line.getCurrentFloat() if line.isChannelOn() else 0) for line in self.lines])  + "!"
        # msg_to_server = json.dumps({"name": "Current", "msg": msg})
        # print(msg_to_server)
        # self.device_widget.send(msg_to_server)

        # for line in self.lines:
        #     # msg_to_server = json.dumps({"name": "Current", "msg": "range %s %i!" % (
        #     #                             line.getChannelNstr(), int(1000 * line.getRangeFloat()))})
        #     # print(msg_to_server)
        #     # self.device_widget.send(msg_to_server)
        #     msgs.append("range %s %i!" % (line.getChannelNstr(), int(1000 * line.getRangeFloat())))
        #     current = line.getCurrentFloat() if line.isChannelOn() else 0
        #     # msg_to_server = json.dumps({"name": "Current", "msg": "current %s %.3f!" % (
        #     #                             line.getChannelNstr(), current)})
        #     # print(msg_to_server)
        #     # self.device_widget.send(msg_to_server)
        #     msgs.append("current %s %.0f!" % (line.getChannelNstr(), current))
        # msg_to_server =  json.dumps({"name": "Current", "msg":'\n'.join(msgs)})
        # print(msg_to_server)
        # self.device_widget.send(msg_to_server)

    def addLine(self):
        # do not call anything after since one should first set Channel to lock
        w  = self.Line(parent=self, current_channels=self.available_channels, data={"On":False})
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
        """changes = {param:(old_value,,new_value)}"""
        if "Range" in changes: #if range changed send messege to device
            msg_to_server = json.dumps({"name": "Current", "msg": "range %s %i!" %
                                        (line.getChannelNstr(), int(1000*line.getRangeFloat()))})
            print(msg_to_server)
            self.device_widget.send(msg_to_server)
        self.sendScanParams()
        self.constructPulses(None,None)

    def constructData(self):
        data = [line.constructData() for line in self.lines]
        return data

    def constructPulses(self, t_start, t_end):
        if t_start == None:
            update_all_command = True
        else:
            self.t_start = t_start
            self.t_end = t_end
            update_all_command = False
        """constructs and updates pulses produced by Current channels"""
        if self.globals and "pulses" in self.globals:
            new_pulses = {channel:self.globals["pulses"][channel] for channel in self.globals["pulses"] if channel in sorted(self.available_channels)}
            # if DEBUG: print('current pulses', new_pulses)
        else:
            new_pulses = {}
        lines_channeled = {line.getChannel():line for line in self.lines}
        channels_data = {}
        self.channels_data = {}
        # print('current pulses', new_pulses)
        msg_default_currents = "all_currents"
        for channel,line in lines_channeled.items():
            if (channel not in new_pulses) or len(new_pulses[channel][0])==1:# (new_pulses[channel]==[[[0,0]]]): # no pulses for channel
                current = line.getCurrentFloat() if line.isChannelOn() else 0
                current += (new_pulses[channel][0][0][1] if channel in new_pulses else 0)
                self.channels_data[channel]=[[0,current]]
                msg_default_currents += " " + str(current)
                # msg_to_server = json.dumps({"name":"Current","msg":"current %s %.1f!"%
                #                             (line.getChannelNstr(), current)})
                # print(msg_to_server)
                # self.device_widget.send(msg_to_server)
            else:
                if not line.isChannelOn():
                    current = 0
                    msg_default_currents += " " + str(current)
                    continue
                # channels_data[channel] = [[0,line.getCurrentFloat()]] # offset for this channel
                all_points = new_pulses[channel]    # raw data from Pulses
                new_points = [[0,line.getCurrentFloat()]]
                for points_group in all_points:
                    # now assume that points_group has only 2 points!!! - otherwise it is nightmare
                    p_up = points_group[0]
                    p_down= points_group[1]
                    up_point_inserted=False
                    down_point_inserted = False
                    for p_new in new_points:
                        if p_up[0] <= p_new[0]:
                            if p_up[0] == p_new[0]: # add value to point and remember when this started
                                before_p_up = p_new[1]
                                p_new[1] += p_up[1]
                                up_index = new_points.index(p_new)
                            else:
                                before_p_up = new_points[new_points.index(p_new)-1][1]
                                up_index = new_points.index(p_new)
                                new_points.insert(up_index, [p_up[0],p_up[1]+before_p_up])
                            up_point_inserted = True
                            for p2_new in new_points[up_index+1:]:
                                if p_down[0] > p2_new[0]: # if p_down is later than point - add value
                                    before_p_up = p2_new[1]
                                    p2_new[1] += p_up[1]
                                elif p_down[0] == p2_new[0]: # points coinside - finish adding values
                                    # print("IN DOWN1")
                                    down_point_inserted = True
                                    break
                                else: #insert d_down before p2_new
                                    # print("IN DOWN2")
                                    down_index = new_points.index(p2_new)
                                    new_points.insert(down_index,[p_down[0],before_p_up])
                                    down_point_inserted = True
                                    break
                            if down_point_inserted:
                                break
                            if not down_point_inserted:
                                # print("IN NOT DOWN")
                                new_points.append([p_down[0],new_points[-1][1]-p_up[1]]) # add falling edge with value before rise
                                break
                    if not up_point_inserted:
                        # print("IN DNOT UP")
                        new_points.extend([[p_up[0],new_points[-1][1]+p_up[1]],[p_down[0],new_points[-1][1]]])
                # drop_points_list = [i for i in range(1,len(new_points)) if new_points[i][1]==new_points[i-1][1]]
                # print("new_points",new_points, "drop list", drop_points_list)
                # new_points = [new_points[i] for i in range(len(new_points)) if i not in drop_points_list]
                # print("new_points", new_points)
                start_point = new_points[0]
                channels_data[channel] = new_points
                self.channels_data[channel] = deepcopy(new_points)
                msg_default_currents += " " + str(start_point[1])
        msg_to_server = json.dumps({"name":"Current","msg":msg_default_currents + "!"})
        print("Default currents", msg_to_server)
        self.device_widget.send(msg_to_server)
                    # print('new points',new_points)
                # offset = line.getCurrentFloat()
                # channels_data[channel]+=[[p[0],np.sign(p[1]+offset)*np.min([np.abs(p[1]+offset),line.getRangeFloat()])] for p in new_points]

        # print("current final data",channels_data)
        edges = set()

        for channel,points in channels_data.items():
            for point in points:
                edges.add(point[0])
        edges = sorted(edges)
        if len(edges) == 0: #there are no pulses
            msg_to_server = json.dumps({"name": "Current", "msg": "pulse!"})
            self.device_widget.send(msg_to_server)
            print(msg_to_server)
        else:
            if self.t_start > 0: # write value at self.t_end
                msg = 'pulse %i ' % (int(0))
                msg += ",".join(["%s:%.1f" % (channel[1:], points[0][1]) for channel, points in channels_data.items()])
                # for channel, points in channels_data.items():
                #     msg += " %s:%.1f" % (channel[1:], points[0][1])
                msg_to_server = json.dumps({"name": "Current", "msg": msg + "!"})
                self.device_widget.send(msg_to_server)
                print(msg_to_server)
            for t in edges:
                if t >= self.t_start:
                    msg = 'pulse %i '%(int(t-self.t_start))
                    msg_arr = []
                    for channel, points in channels_data.items():
                        for point in points:
                            if t==point[0]:
                                msg_arr.append("%s:%.1f"%(channel[1:],point[1]))
                                break
                    msg += ','.join(msg_arr)
                    msg_to_server = json.dumps({"name": "Current", "msg": msg+"!"})
                    self.device_widget.send(msg_to_server)
                    print(msg_to_server)
            if self.t_start > 0: # write value at self.t_end
                msg = 'pulse %i ' % (int(self.t_end - self.t_start))
                msg += ",".join(["%s:%.1f" % (channel[1:], points[0][1]) for channel, points in channels_data.items()])
                # for channel, points in channels_data.items():
                #     msg += " %s:%.1f" % (channel[1:], points[0][1])
                msg_to_server = json.dumps({"name": "Current", "msg": msg + "!"})
                self.device_widget.send(msg_to_server)
                print(msg_to_server)
        self.plot_widget.updatePlot(self.t_start, self.t_end)

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
        """uploads available scan parameters to globals"""
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
        current_shot = self.globals["scan_running_data"]["current_meas_number"]
        for param,path in {**self.globals["scan_params"]["main"],**self.globals["scan_params"]["low"]}.items():
            if path[0] == "Current" and ( current_shot==0 or
            self.globals["scan_running_table"].loc[current_shot,param] != self.globals["scan_running_table"].loc[current_shot-1,param]):
                if DEBUG: print("Current - update from scanner - ",param, path)
                for w in self.lines:
                    if w.getName() == path[1]:
                        w.updateFromScanner(param=path[2],value=self.globals["scan_running_table"].loc[current_shot,param])
        self.constructPulses(0,1000)

    def updateDeviceReadings(self, msg):
        # print("updateDeviceReadings", msg)
        try:
            device, data_all = msg.split(' ', maxsplit=1)
        except ValueError as e:
            print("Exception whle reading msg from device", msg)
            return
        # print(device, self.device["name"])
        if device.strip() == self.device["name"].strip():
            for data in data_all.split("\n"):
                if "connected" in data.lower():
                    self.arduino_readings["status"] = data
                elif "IDN" in data:
                    self.arduino_readings["status"] = "Connected"
                    if len(self.arduino_readings["last_readings"]) >= self.arduino_readings_length:
                        self.arduino_readings["last_readings"] = self.arduino_readings["last_readings"][
                                                                 1:self.arduino_readings_length]
                    self.arduino_readings["last_readings"].append(data)
                elif "T=" in data:
                    data = [d for d in data.split("\n") if "T=" in d][0]
                    # print("current data", data)
                    data = data.split(" ")
                    # print(repr(self.arduino_readings))
                    # print(data)
                    self.arduino_readings["data"][0] = data[0]
                    updated_channels = []
                    for channel in data[1:]:
                        # print(channel)
                        d = channel.split(",") # data should be like Ok,2,100.00,104.52,0.57
                        channel_n = int(d[0])
                        updated_channels.append(channel_n)
                        self.arduino_readings["data"][channel_n+1] = "Ch %i, Tset=%s, Iact=%s, V=%s" % (channel_n, d[1], d[2],d[3])
                    for i in range(5):
                        if i in updated_channels:
                            continue
                        self.arduino_readings["data"][i+1] = "Ch %i is off"%(i)
                else:
                    if len(self.arduino_readings["last_readings"]) >= self.arduino_readings_length:
                        self.arduino_readings["last_readings"] = self.arduino_readings["last_readings"][
                                                                 1:self.arduino_readings_length]
                    self.arduino_readings["last_readings"].append(data)
                # print(self.arduino_readings)
            self.device_widget.updateReadingsNew(self.arduino_readings)

    def newCommandSent(self, msg):
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
        super().__init__(title="CurrentsPlot")
        # self.resize(600, 600)
        # self.signals.updateDigitalPlot.connect(self.updatePlot)
        self.setMinimumHeight(150)
        # self.updatePlot()

    def updatePlot(self, t_start, t_end):
        """used as a slot called by Pulses class to redraw pulses
            CAN BE DONE IN THREAD"""
        self.plotPulses(t_start, t_end)

    def plotPulses(self, t_start, t_end):
        # print('PlotCurrents')
        self.clear()  # clear plot
        self.setBackground('w')
        # self.s
        d_plot = self.addPlot()
        d_plot.addLegend()
        d_plot.getAxis('left').setPen(pg.Color('k'))
        d_plot.getAxis('bottom').setPen(pg.Color('k'))
        d_plot.showGrid(x=True)
        digital_list = []  # list of active digital channels
        # print("Current channels_data", self.parent.channels_data)
        t_first = min(min([1000] + [x[0] for x in value if x[0] > 0]) for name, value in
                      self.parent.channels_data.items() if 'C' in name)
        t_last = t_end
        # t_last = max(max(x[0] for x in value if x[0] > 0) for name, value in
        #               self.globals['pulses'].items() if 'D' in name and  len(value)>1) + 10
        digital_counter = 0
        for name in sorted(self.parent.channels_data.keys(), reverse=True):
            if 'C' not in name:
                continue
            digital_list.append(name)
            value = self.parent.channels_data[name]
            xx = []
            yy = []

            # construct points to show
            for i, point in enumerate(value):
                if i == 0:
                    xx.append(t_first - (100 if t_first > 100 else t_first))
                    yy.append(point[1])
                    continue
                # if not i == len(value) - 1:
                xx.append(point[0])
                yy.append(value[i-1][1])
                xx.append(point[0])
                yy.append(point[1])
            xx.append(t_last)
            yy.append(point[1])
            d_plot.plot(np.array(xx), np.array(yy), pen=pg.mkPen(pg.intColor(digital_counter,hues=5),width=2),name=name)  # plot data
            digital_counter += 1
        # set ticks names

        # tick_names = digital_list
        # d_plot.getAxis('left').setTicks(
        #     [list(zip((np.arange(len(digital_list)) + 1 / 2) * digital_height, tick_names))])

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

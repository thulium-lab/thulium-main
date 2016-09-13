# from PyQt5.QtCore import QObject
import os, sys
import pickle
import random
import numpy as np
import matplotlib
matplotlib.use('Qt5Agg',force=True)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from copy import deepcopy

from PyQt5.QtCore import (QLineF, QPointF, QRectF, Qt, QTimer)
from PyQt5.QtGui import (QBrush, QColor, QPainter)
from PyQt5.QtWidgets import (QApplication, QGraphicsView, QGraphicsScene, QGraphicsItem,
                             QGridLayout, QVBoxLayout, QHBoxLayout, QSizePolicy,QMainWindow, QDialog,
                             QLabel, QLineEdit, QPushButton, QWidget, QComboBox,QRadioButton, QSpinBox, QCheckBox, QTabWidget, QFileDialog,QMessageBox, QDoubleSpinBox)
import pyqtgraph as pg
import json
import time
from sympy.utilities.lambdify import lambdify
import re
import numpy as np
from numpy import *
import sympy as sp
from sympy.parsing.sympy_parser import parse_expr

digital_pulses_folder = 'digatal_schemes'
config_scheme_file = 'config_scheme'
pulse_name_suffix = '.pls'

class pulseScheme(QWidget):
    # can be done as QWidget
    def __init__(self,parent=None,available_channels=[]):

        self.parent = parent
        self.available_channels = available_channels
        self.digital_channels = []
        self.analog_channels = []
        self.active_channels = {}
        self.all_schemes = {}
        self.config={}
        self.time_step = 0.1
        self.current_scheme = None
        self.current_groups = []
        self.output = {}
        self.load()
        super().__init__()
        self.initUI()

    def initUI(self):
        self.main_box = QVBoxLayout(self)
        topbox = QHBoxLayout(self)

        topbox.addWidget(QLabel('Scheme'))

        self.scheme_combo_box = QComboBox()
        self.scheme_combo_box.addItems(self.all_schemes.keys())
        self.scheme_combo_box.setCurrentText(self.current_scheme)
        self.scheme_combo_box.currentTextChanged.connect(self.schemeChanged)
        topbox.addWidget(self.scheme_combo_box)

        self.add_group_button = QPushButton('Add group')
        self.add_group_button.clicked.connect(self.addGroup)
        topbox.addWidget(self.add_group_button)

        self.save_button = QPushButton('Save')
        self.save_button.clicked.connect(self.saveScheme)
        topbox.addWidget(self.save_button)

        self.save_as_button = QPushButton('Save as')
        self.save_as_button.clicked.connect(self.saveAsScheme)
        topbox.addWidget(self.save_as_button)

        self.main_box.addLayout(topbox)

        self.hor_box = QHBoxLayout(self)
        self.channel_box = QWidget()
        self.channelsDraw()
        self.hor_box.addWidget(self.channel_box)

        self.tabbox = QTabWidget()
        self.tabbox.setMovable(True)
        print('Current scheme: ', self.current_scheme)
        for group in self.current_groups:
            tab = group.PulseGroupQt(scheme=self, data=group)
            self.tabbox.addTab(tab, group.name)
        self.hor_box.addWidget(self.tabbox)
        self.main_box.addLayout(self.hor_box)
        self.setLayout(self.main_box)

    def channelsDraw(self):
        print('channelsDraw')
        grid = QGridLayout()
        grid.addWidget(QLabel('#'), 0, 0)
        grid.addWidget(QLabel('On'), 0, 1)
        grid.addWidget(QLabel('Off'), 0, 2)
        grid.addWidget(QLabel('Sh'), 0, 3)

        for j, channel in enumerate(sorted(self.active_channels)):
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
            if channel not in self.analog_channels:
                shutter_btn = QPushButton('Sh')
                shutter_btn.setMaximumWidth(20)
                shutter_btn.clicked.connect(self.shutterChanged)
                grid.addWidget(shutter_btn,i,3)
        self.channel_box.setLayout(grid)

    def shutterChanged(self):
        print('shutterChanged')
        layout = self.channel_box.layout()
        index = layout.indexOf(self.sender())
        row, column, cols, rows = layout.getItemPosition(index)

        self.calculateOutput()

    def channelStateChanged(self, new_state):
        print('channelStateChanged')
        layout = self.channel_box.layout()
        index = layout.indexOf(self.sender())
        row, column, cols, rows = layout.getItemPosition(index)
        if new_state:
            self.active_channels[list(sorted(self.active_channels))[row-1]]['state'] = 'On' if column==1 else 'Off'
        else:
            self.active_channels[list(sorted(self.active_channels))[row - 1]]['state'] = 'StandBy'
        self.channelsRedtaw()

    def channelsRedtaw(self):
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

    def schemeRedraw(self):
        print('schemeRedraw')
        self.tabbox.clear()
        print('Current scheme: ', self.current_scheme)
        for group in self.current_groups:
            tab = group.PulseGroupQt(scheme=self, data=group)
            self.tabbox.addTab(tab, group.name)
        self.updateChannels()

    def load(self):
        print('loadSchemes')
        if not os.path.exists(digital_pulses_folder):
            print('create folder ', digital_pulses_folder)
            os.mkdir(digital_pulses_folder)
        files = os.listdir(digital_pulses_folder)
        if len(files) != 0:
            for fname in files:
                if fname.startswith('config'):
                    with open(os.path.join(digital_pulses_folder, fname), 'r') as f:
                        print('config_load')
                        self.config = json.load(f)
                if fname.endswith(pulse_name_suffix):
                    with open(os.path.join(digital_pulses_folder, fname), 'rb') as f:
                        data_to_read =  pickle.load(f)
                        self.all_schemes[fname[:fname.find(pulse_name_suffix)]] = data_to_read['current_groups']
                        self.active_channels = data_to_read['active_channels']
                        if 'time_step' in data_to_read:
                            self.time_step = data_to_read['time_step']
        if 'current_scheme' in self.config:
            self.current_scheme = self.config['current_scheme']
        if 'digital_channels' in self.config:
            self.digital_channels = self.config['digital_channels']
        if 'analog_channels' in self.config:
            self.analog_channels = self.config['analog_channels']
        elif len(self.all_schemes):
            self.current_scheme = list(self.all_schemes.keys())[0]
        else:
            self.all_schemes['Default']=[pulseGroup()]
            self.current_scheme = 'Default'
        self.current_groups = self.all_schemes[self.current_scheme]
        self.available_channels = self.digital_channels + self.analog_channels
        self.updateChannels()

    def schemeChanged(self, new_scheme):
        print('schemeChanged')
        self.current_scheme = new_scheme
        self.current_groups = self.all_schemes[self.current_scheme]
        self.updateChannels()
        self.updateConfig()
        self.channelsRedtaw()
        self.schemeRedraw()

    def addGroup(self):
        print('addGroup')
        new_group = pulseGroup()
        print(new_group)
        print(new_group.__dict__)
        self.current_groups.append(new_group)
        print(self.current_groups)
        self.schemeRedraw()

    def saveScheme(self):
        print('saveScheme')
        if not os.path.exists(digital_pulses_folder):
            print('create folder')
            os.mkdir(digital_pulses_folder)
        with open(os.path.join(digital_pulses_folder,self.current_scheme+pulse_name_suffix), 'wb') as f:
            dict_to_write = {'current_groups':self.current_groups,'active_channels':self.active_channels,
                             'time_step':self.time_step}
            pickle.dump(dict_to_write,f)

    def saveAsScheme(self):
        print('saveAsScheme')
        if not os.path.exists(digital_pulses_folder):
            print('create folder')
            os.mkdir(digital_pulses_folder)
        fname = QFileDialog.getSaveFileName(self,directory=digital_pulses_folder)[0]
        if not fname.endswith(pulse_name_suffix):
            fname += pulse_name_suffix
        with open(fname, 'wb') as f:
            dict_to_write = {'current_groups': self.current_groups, 'active_channels': self.active_channels,
                             'time_step':self.time_step}
            pickle.dump(dict_to_write, f)
        fname = os.path.basename(fname)
        fname = fname[:fname.find(pulse_name_suffix)]
        self.all_schemes[fname] = deepcopy(self.current_groups)
        self.current_scheme = fname
        self.current_groups = self.all_schemes[self.current_scheme]
        self.schemeRedraw()

    def deleteGroup(self, group):
        print("deleteGroup")
        self.current_groups.remove(group.data)
        self.schemeRedraw()

    def changeInGroup(self):
        print('changeInGroup')
        self.updateChannels()
        self.channelsRedtaw()

    def updateConfig(self):
        print('updateConfig')
        if not os.path.exists(os.path.join(digital_pulses_folder, config_scheme_file)+'.json'):
            config = {}
        else:
            with open(os.path.join(digital_pulses_folder, config_scheme_file)+'.json', 'r') as f:
                print('here-there')
                config = json.load(f)
                if type(config) != type(dict()):
                    print('smth rong with config file')
                    config = {}
        config['current_scheme'] = self.current_scheme
        with open(os.path.join(digital_pulses_folder, config_scheme_file)+'.json', 'w') as f:
            config['digital_channels']=[str(i) for i in range(8,31)]
            json.dump(config, f)



            # def updateScheme(self):
    #     print('updateScheme')
    #     self.tabbox.clear()
    #     self.current_scheme = self.scheme_combo_box.currentText()
    #     for group in self.schemes[self.current_scheme]:
    #         tab = group.PulseGroupWidget(parent=self, data=group)
    #         # tab.updateReferences()
    #         self.tabbox.addTab(tab, group.name)
    #     self.updateConfig()
    #     self.onAnyChange()
    #
    # def updateConfig(self):
    #     print('updateConfig')
    #     if not os.path.exists(os.path.join(digital_pulses_folder, config_scheme_file)):
    #         config = {}
    #     else:
    #         with open(os.path.join(digital_pulses_folder, config_scheme_file), 'rb') as f:
    #             print('here-there')
    #             config = pickle.load(f)
    #             if type(config) != type(dict()):
    #                 print('smth rong with config file')
    #                 config = {}
    #     config['current_scheme'] = self.current_scheme
    #     with open(os.path.join(digital_pulses_folder, config_scheme_file), 'wb') as f:
    #         pickle.dump(config,f)
    #
    # def saveScheme(self):
    #     print('saveScheme')
    #     if not os.path.exists(digital_pulses_folder):
    #         print('create folder')
    #         os.mkdir(digital_pulses_folder)
    #     print(self.schemes[self.current_scheme][0].__dict__)
    #     with open(os.path.join(digital_pulses_folder,self.current_scheme), 'wb') as f:
    #         pickle.dump(self.schemes[self.current_scheme],f)
    #
    # def saveAsScheme(self):
    #     print('saveAsScheme')
    #     if not os.path.exists(digital_pulses_folder):
    #         print('create folder')
    #         os.mkdir(digital_pulses_folder)
    #     fname = QFileDialog.getSaveFileName(self,directory=digital_pulses_folder)[0]
    #     with open(fname, 'wb') as f:
    #         pickle.dump(self.schemes[self.current_scheme],f)
    #     QWidget().setLayout(self.layout())
    #     fname = os.path.basename(fname)
    #     self.schemes[fname] = deepcopy(self.schemes[self.current_scheme])
    #     self.current_scheme = fname
    #     print('lll')
    #     self.initUI()
    #
    # def loadSchemes(self):
    #     print('loadSchemes')
    #     self.schemes = {}
    #     self.current_scheme = None
    #     if not os.path.exists(digital_pulses_folder):
    #         print('create folder')
    #         os.mkdir(digital_pulses_folder)
    #     files = os.listdir(digital_pulses_folder)
    #     if len(files) != 0:
    #         for fname in files:
    #             if not fname.startswith('config'):
    #                 with open(os.path.join(digital_pulses_folder, fname), 'rb') as f:
    #                     print('here')
    #                     self.schemes[fname] = pickle.load(f)
    #         if not os.path.exists(os.path.join(digital_pulses_folder, config_scheme_file)):
    #             config = {}
    #         else:
    #             with open(os.path.join(digital_pulses_folder, config_scheme_file), 'rb') as f:
    #                 print('here-there')
    #                 config = pickle.load(f)
    #                 if type(config) != type(dict()):
    #                     print('smth rong with config file')
    #                     config = {}
    #         if 'current_scheme' in config.keys():
    #             self.current_scheme = config['current_scheme']
    #         elif len(self.schemes):
    #             self.current_scheme = list(self.schemes.keys())[0]
    #
    # def pulseByName(self,name):
    #     group_names = [group.name for group in self.schemes[self.current_scheme]]
    #     return self.schemes[self.current_scheme][group_names.index(name)]
    #
    # def calculateOutputData(self):
    #     self.output_data = {}
    #     end_time = 0
    #     first_time = 0
    #     for pulse_group in self.schemes[self.current_scheme]:
    #         if pulse_group.is_active:
    #             for pulse in pulse_group.pulses:
    #                 if pulse.is_active:
    #                     if not pulse.channel in self.output_data.keys():
    #                         self.output_data[pulse.channel] = []
    #                     new_points = self.getPoints(pulse,pulse_group)
    #                     for point in new_points:
    #                         if point[0] not in [point[0] for point in self.output_data[pulse.channel]]:
    #                             self.output_data[pulse.channel].append(point)
    #                         else:
    #                             self.output_data[pulse.channel].remove((point[0],not point[1]))
    #                     # if new_points[-1][0] > end_time:
    #                     #     end_time = new_points[-1][0]
    #
    #     for point_list in self.output_data.values():
    #         point_list.sort(key=lambda x: x[0])
    #         if point_list[0][0] != 0:
    #             point_list.insert(0,(0,0))
    #     for points in self.output_data.values():
    #         if points[-1][0] > end_time:
    #             end_time = points[-1][0]
    #         if first_time == 0:
    #             first_time = end_time
    #         if points[1][0] < first_time:
    #             first_time = points[1][0]
    #     for points in self.output_data.values():
    #         points.append((end_time+10,points[-1][1]))
    #         points.insert(1,(first_time - 100, points[0][1]))
    #     self.first_time = first_time
    #     self.end_time = end_time
    #
    # def getPoints(self,pulse, group):
    #     group_begin = group.delay + group.getReferencePoint(self)
    #     if not pulse.edge:
    #         if pulse.length == 0:
    #             return ((group_begin + pulse.delay,1),(group_begin + group.length,0))
    #         elif pulse.length > 0:
    #             return ((group_begin + pulse.delay,1),(group_begin +  pulse.delay + pulse.length,0))
    #         else:
    #             return ((group_begin +  pulse.delay,1),(group_begin + group.length + pulse.length,0))
    #     else:
    #         if pulse.length == 0:
    #             return ((group_begin + pulse.delay,1),(group_begin + group.length,0))
    #         elif pulse.length > 0:
    #             return ((group_begin + group.length + pulse.delay,1),(group_begin + group.length + pulse.delay + pulse.length,0))
    #         else:
    #             return ((group_begin + group.length + pulse.delay + pulse.length,1),(group_begin + group.length + pulse.delay,0))
    #
    # def onAnyChange(self):
    #     self.updateChannelPannel()
    #     self.calculateOutputData()
    #     # self.plotPulses()
    #     print(self.output_data)
    #
    # def updateChannelPannel(self):
    #     print('updateChannelPannel')
    #     flag_to_redraw = False
    #     channels_in_pulses = set()
    #     for pulse_group in self.schemes[self.current_scheme]:
    #             for pulse in pulse_group.pulses:
    #                     channels_in_pulses.add(pulse.channel)
    #                     if pulse.channel not in self.active_channels:
    #                         self.active_channels[pulse.channel] = 'StandBy'
    #                         flag_to_redraw = True
    #     to_remove = []
    #     for key in self.active_channels:
    #         if key not in channels_in_pulses:
    #             to_remove.append(key)
    #     for key in to_remove:
    #         self.active_channels.pop(key)
    #         flag_to_redraw = True
    #     print(self.active_channels)
    #     if not flag_to_redraw:
    #         self.showChannelPannel()
    #     else:
    #         QWidget().setLayout(self.layout())
    #         self.initUI()
    #
    # def showChannelPannel(self):
    #     print('Now',self.ch_grid)
    #     # self.ch_grid = QGridLayout()
    #     for i,channel in enumerate(sorted(self.active_channels)):
    #         self.ch_grid.addWidget(QLabel(channel),i,0)
    #         alwais_on = QCheckBox()
    #         if self.active_channels[channel] == 'On':
    #             alwais_on.setChecked(True)
    #         self.ch_grid.addWidget(alwais_on, i, 1)
    #         alwais_off = QCheckBox()
    #         if self.active_channels[channel] == 'Off':
    #             alwais_on.setChecked(True)
    #         self.ch_grid.addWidget(alwais_off, i, 2)
    #     # self.initUI()
    #
    # def deleteGroup(self, group_name):
    #     print("deleteGroup")
    #     group_names = [group.name for group in self.schemes[self.current_scheme]]
    #     # print(group_name, group_names.index(group_name))
    #     self.schemes[self.current_scheme].pop(group_names.index(group_name))
    #     self.updateScheme()
    #
    # def plotPulses(self):
    #     self.win.clear()
    #     for name in sorted(self.output_data):
    #         value = self.output_data[name]
    #         p = self.win.addPlot(title=name)
    #         xx = []
    #         yy = []
    #         for i,point in enumerate(value[1:]):
    #             if (not i==0) and (not i == (len(value[1:])-1)):
    #                 xx.append(point[0])
    #                 yy.append(not point[1])
    #             xx.append(point[0])
    #             yy.append(point[1])
    #         p.plot(xx,yy)
    #         self.win.nextRow()
    #

    def calculateOutput(self):
        self.output = {}
        res = self.updateGroupTime()
        # for group in self.current_groups:
        #     print(group.t_start, group.t_end)
        # print('result',res)
        output = {}
        for pulse_group in self.current_groups:
            if pulse_group.is_active:
                for pulse in pulse_group.pulses:
                    if pulse.is_active:
                        if not pulse.channel in output.keys():
                            output[pulse.channel] = []
                        if self.active_channels[pulse.channel]['state'] == 'StandBy':
                            pulse.updateTime(pulse_group)
                            # print('here', pulse.channel)
                            new_points = pulse.getPoints(self.time_step)
                            # print(pulse.channel, new_points)
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
        print(list(output.keys()))
        for channel, points in output.items():
            output[channel] = list(sorted(points))
            # print(channel)
            # print(output[channel][0])
            if len(output[channel])==0 or output[channel][0][0] != 0:
                # print('dsd')
                output[channel].insert(0,(0,0))
            if channel in self.digital_channels:
                points_to_drop = []
                for i in range(1,len(output[channel])):
                    if output[channel][i-1][0] == output[channel][i][0]:
                        points_to_drop.extend([i-1,i])
                    if output[channel][i-1][1] == output[channel][i][1]:
                        points_to_drop.append(i if output[channel][i-1][1] else i-1)

                output[channel] = [output[channel][i] for i in range(len(output[channel])) if i not in points_to_drop]
                print(channel, points_to_drop)
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
        print(self.t_first, self.t_last)
        print(self.output)
                        # for point in new_points:
                        #     if point[0] not in [point[0] for point in self.output_data[pulse.channel]]:
                        #         self.output_data[pulse.channel].append(point)
                        #     else:
                        #         self.output_data[pulse.channel].remove((point[0], not point[1]))
                        #         if new_points[-1][0] > end_time:
                        #             end_time = new_points[-1][0]
        #
        # for point_list in self.output_data.values():
        #     point_list.sort(key=lambda x: x[0])
        #     if point_list[0][0] != 0:
        #         point_list.insert(0, (0, 0))
        # for points in self.output_data.values():
        #     if points[-1][0] > end_time:
        #         end_time = points[-1][0]
        #     if first_time == 0:
        #         first_time = end_time
        #     if points[1][0] < first_time:
        #         first_time = points[1][0]
        # for points in self.output_data.values():
        #     points.append((end_time + 10, points[-1][1]))
        #     points.insert(1, (first_time - 100, points[0][1]))
        # self.first_time = first_time
        # self.end_time = end_time

    def updateGroupTime(self):
        handled = []
        for group in self.current_groups:
            print(group.__dict__)
            if group.reference == '0':
                group.t_start = group.variables['delay']
                group.t_end = group.t_start + group.variables['length']
                handled.append(group.name)
        itr = len(self.current_groups)
        while len(handled) != len(self.current_groups):
            print(handled)
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

class pulseGroup():

    def __init__(self,name='Default', edge=0,  delay=0, length=0, is_active=False, reference='0',):
        self.name = name
        self.edge = edge
        self.variables = {'delay': delay,
                          'length': length}
        self.is_active = is_active
        self.reference = reference
        self.pulses = []
        if len(self.pulses) == 0:
            self.pulses.append(IndividualPulse())

        # t_start  # absolute time of the beginning of the group
        # t_end  # absolute time of the end of the group

    class PulseGroupQt(QWidget):

        def __init__(self, data=None,scheme=None):
            # self.channels = [str(i) for i in range(10)]
            self.n_decimals = 2
            self.data = data
            self.scheme = scheme
            super().__init__()
            self.initUI()

        def initUI(self):
            main_box = QVBoxLayout(self)

            topbox = QHBoxLayout(self)

            topbox.addWidget(QLabel('Reference:'))

            self.ref_channel_combo_box = QComboBox()
            self.ref_channel_combo_box.addItem('0')
            self.ref_channel_combo_box.addItems([group.name for group in self.scheme.current_groups])
            self.ref_channel_combo_box.setCurrentText(self.data.reference)
            self.ref_channel_combo_box.currentTextChanged.connect(self.groupReferenceChanged)
            topbox.addWidget(self.ref_channel_combo_box)

            self.add_pulse_btn = QPushButton('Add pulse')
            self.add_pulse_btn.clicked.connect(self.addPulse)
            topbox.addWidget(self.add_pulse_btn)

            self.del_group_btn = QPushButton('Del Group')
            self.del_group_btn.clicked.connect(self.deleteGroup)
            topbox.addWidget(self.del_group_btn)
            main_box.addLayout(topbox)

            self.redraw_btn = QPushButton('Redraw')
            self.redraw_btn.clicked.connect(self.redraw)
            topbox.addWidget(self.redraw_btn)
            main_box.addLayout(topbox)

            self.columns = ['Del','Channel','Name','Edge','Delay','Length','Active','Special']
            self.edges = ['Begin', 'End']
            self.label_row = 1
            self.group_row = 0
            self.grid_layout = QGridLayout()

            for i, name in enumerate(self.columns):
                self.grid_layout.addWidget(QLabel(name), self.label_row, i)

            # add pulse_group data
            group_name = QLineEdit(self.data.name)
            group_name.returnPressed.connect(self.groupNameChanged)
            self.grid_layout.addWidget(group_name, self.group_row, self.columns.index('Name'))

            group_edge = QComboBox()
            group_edge.addItems(self.edges)
            group_edge.setCurrentIndex(self.data.edge)
            group_edge.currentIndexChanged.connect(self.edgeChanged)
            self.grid_layout.addWidget(group_edge, self.group_row, self.columns.index('Edge'))

            group_delay = QDoubleSpinBox()
            group_delay.setDecimals(self.n_decimals)
            group_delay.setMaximum(10000)
            group_delay.setMinimum(-10000)
            group_delay.setValue(self.data.variables['delay'])
            group_delay.valueChanged.connect(self.delayChanged)
            self.grid_layout.addWidget(group_delay, self.group_row, self.columns.index('Delay'))

            group_length = QDoubleSpinBox()
            group_length.setDecimals(self.n_decimals)
            group_length.setMaximum(10000)
            group_length.setMinimum(-10000)
            group_length.setValue(self.data.variables['length'])
            group_length.valueChanged.connect(self.lengthChanged)
            self.grid_layout.addWidget(group_length, self.group_row, self.columns.index('Length'))

            group_is_active = QCheckBox()
            group_is_active.setChecked(self.data.is_active)
            group_is_active.stateChanged.connect(self.isActiveChanged)
            self.grid_layout.addWidget(group_is_active, self.group_row, self.columns.index('Active'))
            # add individual pulse data
            for i, pulse in enumerate(self.data.pulses):
                # print('pulse',i)
                pulse_row = i + 2

                del_button = QPushButton('Del')
                del_button.setMaximumWidth(40)
                del_button.clicked.connect(self.deletePulse)
                self.grid_layout.addWidget(del_button, pulse_row, self.columns.index('Del'))

                pulse_channel = QComboBox()
                # pulse_channel.addItems(self.data.scheme.all_channels)
                pulse_channel.addItems(self.scheme.available_channels)
                pulse_channel.setCurrentText(getattr(pulse, 'channel', '0'))
                pulse_channel.currentTextChanged.connect(self.pulseChannelChanged)
                self.grid_layout.addWidget(pulse_channel, pulse_row, self.columns.index('Channel'))

                pulse_name = QLineEdit(pulse.name)
                pulse_name.returnPressed.connect(self.pulseNameChanged)
                self.grid_layout.addWidget(pulse_name, pulse_row, self.columns.index('Name'))

                pulse_edge = QComboBox()
                pulse_edge.addItems(self.edges)
                pulse_edge.setCurrentIndex(pulse.edge)
                pulse_edge.currentIndexChanged.connect(self.edgeChanged)
                self.grid_layout.addWidget(pulse_edge, pulse_row, self.columns.index('Edge'))

                pulse_delay = QDoubleSpinBox()
                pulse_delay.setDecimals(self.n_decimals)
                pulse_delay.setMaximum(10000)
                pulse_delay.setMinimum(-10000)
                pulse_delay.setValue(pulse.variables['delay'])
                pulse_delay.valueChanged.connect(self.delayChanged)
                self.grid_layout.addWidget(pulse_delay, pulse_row, self.columns.index('Delay'))

                pulse_length = QDoubleSpinBox()
                pulse_length.setDecimals(self.n_decimals)
                pulse_length.setMaximum(10000)
                pulse_length.setMinimum(-10000)
                pulse_length.setValue(pulse.variables['length'])
                pulse_length.valueChanged.connect(self.lengthChanged)
                self.grid_layout.addWidget(pulse_length, pulse_row, self.columns.index('Length'))

                pulse_is_active = QCheckBox()
                pulse_is_active.setChecked(pulse.is_active)
                pulse_is_active.stateChanged.connect(self.isActiveChanged)
                self.grid_layout.addWidget(pulse_is_active, pulse_row, self.columns.index('Active'))

                if pulse.channel in self.scheme.analog_channels:
                    analog_config = QPushButton('analog')
                    analog_config.clicked.connect(self.analogConfig)
                    self.grid_layout.addWidget(analog_config,pulse_row,self.columns.index('Special'))
            main_box.addLayout(self.grid_layout)
            self.setLayout(main_box)

        def getPulseNumber(self):
            print('getPulseNumber')
            index = self.grid_layout.indexOf(self.sender())
            row, column, cols, rows = self.grid_layout.getItemPosition(index)
            if row == self.group_row:
                return -1
            else:
                return row - 2

        def redraw(self):
            print('redraw')
            QWidget().setLayout(self.layout())
            self.initUI()

        def getNewText(self):
            return self.sender().text()

        def addPulse(self):
            print('addPulse')
            self.data.pulses.append(IndividualPulse())
            self.redraw()
            self.scheme.changeInGroup() # call for parent method

        def deletePulse(self):
            print('deletePulse')
            # send to gui programm sender() to get back index of pulse to delete
            quit_msg = "Are you sure you want to delete this pulse?"
            reply = QMessageBox.question(self, 'Message',
                                         quit_msg, QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.Yes:
                print('Delete')
                pulse_number = self.getPulseNumber()
                self.data.pulses.pop(pulse_number)
                self.redraw()
                self.scheme.changeInGroup() # call for parent method

        def deleteGroup(self):
            print('deleteGroup')
            quit_msg = "Are you sure you want to delete this pulse group?"
            reply = QMessageBox.question(self, 'Message',
                                         quit_msg, QMessageBox.Yes, QMessageBox.No)

            if reply == QMessageBox.Yes:
                print('Delete')
                self.scheme.deleteGroup(self)

        def pulseChannelChanged(self, new_channel):
            print('pulseChannelChanged')
            pulse_number = self.getPulseNumber()
            old_channel = self.data.pulses[pulse_number].channel
            self.data.pulses[pulse_number].channel = new_channel
            if old_channel.startswith('A'):
                if not new_channel.startswith('A'):
                    # we changed from analog to dogotal chanel
                    old_pulse =  self.data.pulses[pulse_number]
                    new_pulse = IndividualPulse()
                    for key in new_pulse.__dict__:
                        new_pulse.__dict__[key] = deepcopy(old_pulse.__dict__[key])
                    self.data.pulses[pulse_number] = new_pulse
                    self.grid_layout.addWidget(QLabel(''), pulse_number+2, self.columns.index('Special'))
                    # self.redraw()
            if not old_channel.startswith('A'):
                if new_channel.startswith('A'):
                    # we changed from digital to analog chanel
                    old_pulse =  self.data.pulses[pulse_number]
                    new_pulse = AnalogPulse()
                    for key in old_pulse.__dict__:
                        new_pulse.__dict__[key] = deepcopy(old_pulse.__dict__[key])
                    self.data.pulses[pulse_number] = new_pulse
                    analog_config = QPushButton('analog')
                    analog_config.clicked.connect(self.analogConfig)
                    self.grid_layout.addWidget(analog_config, pulse_number+2, self.columns.index('Special'))

            self.scheme.changeInGroup()  # call for parent method

        def pulseNameChanged(self):
            print('pulseNameChanged')
            # there is no need to recalculate pulses if only name has changed
            pulse_number = self.getPulseNumber()
            self.data.pulses[pulse_number].name = self.getNewText()#self.gui.sender().text()

        def edgeChanged(self,new_edge):
            print('edgeChanged')
            pulse_number = self.getPulseNumber()
            if pulse_number == -1:
                # group edge was changed
                self.data.edge = new_edge
            else:
                self.data.pulses[pulse_number].edge = new_edge
            self.scheme.changeInGroup() # call for parent method

        def isActiveChanged(self,new_is_active):
            print('isActiveChanged')
            pulse_number = self.getPulseNumber()
            if pulse_number == -1:
                # group edge was changed
                self.data.is_active = new_is_active
            else:
                self.data.pulses[pulse_number].is_active = new_is_active
            self.scheme.changeInGroup() # call for parent method

        def delayChanged(self,new_delay):
            print('delayChanged')
            pulse_number = self.getPulseNumber()
            if pulse_number == -1:
                # group edge was changed
                self.data.variables['delay'] = new_delay
            else:
                self.data.pulses[pulse_number].variables['delay'] = new_delay
            self.scheme.changeInGroup() # call for parent method

        def lengthChanged(self,new_length):
            print('lengthChanged')
            pulse_number = self.getPulseNumber()
            if pulse_number == -1:
                # group edge was changed
                self.data.variables['length'] = new_length
            else:
                self.data.pulses[pulse_number].variables['length'] = new_length
            self.scheme.changeInGroup() # call for parent method

        def groupNameChanged(self):
            print('groupNameChanged')
            self.data.name = self.getNewText()
            # print('jjj')
            # update scheme becaus tab name and references has to be changed
            self.scheme.schemeRedraw()

        def groupReferenceChanged(self, new_reference):
            print('groupReferenceChanged')
            # Посмотреть, можно ли просто использовать новое имя
            self.data.reference = new_reference
            self.scheme.changeInGroup()

        def analogConfig(self):
            print('analogConfig')
            pulse_number = self.getPulseNumber()
            # for pulse in self.data.pulses:
            #     print(pulse.__dict__)
            a = self.analogWidget(parent=self,pulse=self.data.pulses[pulse_number])
            a.show()

        class analogWidget(QDialog):
            def __init__(self,parent=None,pulse=None,):
                print(pulse.__dict__)
                super(parent.analogWidget,self).__init__(parent.scheme)
                self.parent = parent
                self.pulse = pulse
                self.initUI()
                self.show()
                self.add_btn.setDefault(False)
            def initUI(self):
                main_layout = QVBoxLayout(self)
                hor_box1 = QHBoxLayout(self)
                hor_box1.addWidget(QLabel('Time Step'))

                time_step_val = QDoubleSpinBox()
                time_step_val.setDecimals(self.parent.n_decimals)
                time_step_val.setMaximum(10)
                time_step_val.setMinimum(0)
                time_step_val.setValue(self.parent.scheme.time_step)
                time_step_val.valueChanged.connect(self.timeStepChanged)
                hor_box1.addWidget(time_step_val)

                main_layout.addLayout(hor_box1)

                hor_box2 = QHBoxLayout()
                point_radio = QRadioButton(self)
                # print(self.pulse)
                point_radio.setChecked(True if self.pulse.type=='Points' else False)
                hor_box2.addWidget(QLabel('Points'))
                point_radio.toggled.connect(self.typeChanged)
                hor_box2.addWidget(point_radio)
                hor_box2.addWidget(QLabel('Formula'))

                formula_radio = QRadioButton(self)
                formula_radio.setChecked(False if self.pulse.type == 'Points' else True)
                hor_box2.addWidget(formula_radio)

                main_layout.addLayout(hor_box2)

                self.grid = QGridLayout()
                labels = ['name','value']
                self.grid.addWidget(QLabel(labels[0]),0,0)
                self.grid.addWidget(QLabel(labels[1]), 0, 1)
                self.add_btn = QPushButton('Add')
                self.add_btn.clicked.connect(self.addVariable)
                self.add_btn.setDefault(False)
                self.grid.addWidget(self.add_btn,0,2)
                variables = [key for key in self.pulse.variables if key not in ['delay','length']]
                print(variables)
                for i,var in enumerate(variables):
                    name_line = QLineEdit(var)
                    name_line.returnPressed.connect(self.varNameChanged)
                    self.grid.addWidget(name_line,i+1,0)

                    value = QDoubleSpinBox()
                    value.setDecimals(self.parent.n_decimals)
                    value.setMaximum(10000)
                    value.setMinimum(-10000)
                    value.setValue(self.pulse.variables[var])
                    value.valueChanged.connect(self.varValueChanged)
                    self.grid.addWidget(value,i+1,1)

                    del_btn = QPushButton('Del')
                    del_btn.clicked.connect(self.delVariable)
                    self.grid.addWidget(del_btn,i+1,2)

                main_layout.addLayout(self.grid)

                main_layout.addWidget(QLabel('t - time from impulse start'))
                main_layout.addWidget(QLabel('l - impulse length'))

                formula_line = QLineEdit(self.pulse.formula)
                formula_line.returnPressed.connect(self.formulaChanged)
                main_layout.addWidget(formula_line)

                hor_box3 = QHBoxLayout()

                apply_btn = QPushButton('Apply')
                apply_btn.clicked.connect(self.applyChanges)
                hor_box3.addWidget(apply_btn)

                ok_btn = QPushButton('Ok')
                ok_btn.clicked.connect(self.okPressed)
                hor_box3.addWidget(ok_btn)

                main_layout.addLayout(hor_box3)

                self.setLayout(main_layout)
                print(self.pulse.__dict__)

            def timeStepChanged(self, new_value):
                print('timeStepChanged')
                self.parent.scheme.time_step = new_value
                print(new_value)

            def typeChanged(self,new_type):
                print('typeChanged')
                self.pulse.type= 'Points' if new_type else 'Formula'
                print(new_type)

            def addVariable(self):
                print('addVariable')
                self.pulse.variables['new']=0
                QWidget().setLayout(self.layout())
                self.initUI()

            def varNameChanged(self):
                print('varNameChanged')
                index = self.grid.indexOf(self.sender())
                row, column, cols, rows = self.grid.getItemPosition(index)
                variables = [key for key in self.pulse.variables if key not in ['delay', 'length']]
                old_name = variables[row-1]
                val = self.pulse.variables.pop(old_name)
                self.pulse.variables[self.sender().text()]=val
                print(self.pulse.__dict__)
            def varValueChanged(self, new_value):
                print('varValueChanged')
                index = self.grid.indexOf(self.sender())
                row, column, cols, rows = self.grid.getItemPosition(index)
                variables = [key for key in self.pulse.variables if key not in ['delay', 'length']]
                name = variables[row-1]
                self.pulse.variables[name]=new_value
                print(self.pulse.__dict__)

            def delVariable(self):
                print('delVariable')
                index = self.grid.indexOf(self.sender())
                row, column, cols, rows = self.grid.getItemPosition(index)
                variables = [key for key in self.pulse.variables if key not in ['delay', 'length']]
                name = variables[row - 1]
                self.pulse.variables.pop(name)
                QWidget().setLayout(self.layout())
                self.initUI()

            def formulaChanged(self):
                print('formulaChanged')
                self.pulse.formula = self.sender().text()
                print(self.pulse.__dict__)

            def applyChanges(self):
                print('applyChanges')
                QWidget().setLayout(self.layout())
                self.initUI()
                self.parent.scheme.changeInGroup()

            def okPressed(self):
                print('okPressed')
                self.applyChanges()
                self.close()


    def getReferencePoint(self,scheme):
        if self.ref == '0':
            return 0
        else:
            predecessor = scheme.pulseByName(self.ref)
            return self.edge * predecessor.length + predecessor.getReferencePoint(scheme)

    # class PulseGroupWidget(QWidget):
    #     def __init__(self,parent=None,data=None):
    #         self.parent = parent
    #         self.data = data
    #         self.channels = [str(i) for i in range(10)]
    #         self.n_decimals = 2
    #         super().__init__()
    #         self.initUI()
    #
    #     def initUI(self):
    #         vbox = QVBoxLayout(self)
    #         topbox = QHBoxLayout(self)
    #
    #         ref_channel_lbl = QLabel('Ref. channel:')
    #         topbox.addWidget(ref_channel_lbl)
    #
    #         self.ref_channel_combo_box = QComboBox()
    #         self.ref_channel_combo_box.addItem('0')
    #         self.ref_channel_combo_box.addItems([group.name for group in self.parent.schemes[self.parent.current_scheme]])
    #         self.ref_channel_combo_box.setCurrentText(self.data.ref)
    #         self.ref_channel_combo_box.currentIndexChanged.connect(self.refChannelChanged)
    #         topbox.addWidget(self.ref_channel_combo_box)
    #
    #         self.add_pulse_btn = QPushButton('Add pulse')
    #         self.add_pulse_btn.clicked.connect(self.add_pulse)
    #         topbox.addWidget(self.add_pulse_btn)
    #
    #         self.del_group_btn = QPushButton('Del Group')
    #         self.del_group_btn.clicked.connect(self.deleteGroup)
    #         topbox.addWidget(self.del_group_btn)
    #         vbox.addLayout(topbox)
    #
    #         self.columns = ['Del','Channel','Name','Edge','Delay','Length','Active']
    #         self.edges = ['Begin', 'End']
    #         self.grid_layout = self.drawGrid()
    #         vbox.addLayout(self.grid_layout)
    #         self.setLayout(vbox)
    #         self.show
    #
    #     def deleteGroup(self):
    #         print('deleteGroup')
    #         quit_msg = "Are you sure you want to delete this pulse group?"
    #         reply = QMessageBox.question(self, 'Message',
    #                                            quit_msg, QMessageBox.Yes, QMessageBox.No)
    #
    #         if reply == QMessageBox.Yes:
    #             self.parent.deleteGroup(self.data.name)
    #
    #     def refChannelChanged(self):
    #         print('refChannelChanged')
    #         self.data.ref = self.ref_channel_combo_box.currentText()
    #         self.parent.onAnyChange()
    #         # print(self.data.__dict__)
    #         # self.redrawGroup()
    #
    #     def redrawGroup(self):
    #         # the way i found to redraw all layout
    #         print('redrawGroup')
    #         QWidget().setLayout(self.layout())
    #         self.initUI()
    #         # self.updateReferences()
    #
    #     def add_pulse(self):
    #         print('addPulse')
    #         self.data.pulses.append(IndividualPulse())
    #         self.redrawGroup()
    #         self.parent.onAnyChange()
    #         # self.draw_pulses()
    #
    #     def drawGrid(self):
    #         print('drawGrid')
    #         grid_layout = QGridLayout()
    #
    #         # add column names
    #         label_row = 1
    #         for i,name in enumerate(self.columns):
    #             grid_layout.addWidget(QLabel(name),label_row,i)
    #
    #         # add pulse_group data
    #         group_row=0
    #         self.group_row = group_row
    #         group_name = QLineEdit(self.data.name)
    #         group_name.returnPressed.connect(self.groupNameChanged)
    #         grid_layout.addWidget(group_name,group_row,self.columns.index('Name'))
    #
    #         group_edge = QComboBox()
    #         group_edge.addItems(self.edges)
    #         group_edge.setCurrentIndex(self.data.edge)
    #         group_edge.currentIndexChanged.connect(self.edgeChanged)
    #         grid_layout.addWidget(group_edge,group_row,self.columns.index('Edge'))
    #
    #         group_delay = QDoubleSpinBox()
    #         group_delay.setDecimals(self.n_decimals)
    #         group_delay.setMaximum(10000)
    #         group_delay.setMinimum(-10000)
    #         group_delay.setValue(self.data.delay)
    #         group_delay.valueChanged.connect(self.delayChanged)
    #         grid_layout.addWidget(group_delay, group_row, self.columns.index('Delay'))
    #
    #         group_length = QDoubleSpinBox()
    #         group_length.setDecimals(self.n_decimals)
    #         group_length.setMaximum(10000)
    #         group_length.setMinimum(-10000)
    #         group_length.setValue(self.data.length)
    #         group_length.valueChanged.connect(self.lengthChanged)
    #         grid_layout.addWidget(group_length, group_row, self.columns.index('Length'))
    #
    #         group_is_active = QCheckBox()
    #         group_is_active.setChecked(self.data.is_active)
    #         group_is_active.stateChanged.connect(self.isActiveChanged)
    #         grid_layout.addWidget(group_is_active, group_row, self.columns.index('Active'))
    #         # add individual pulse data
    #         for i,pulse in enumerate(self.data.pulses):
    #             # print('pulse',i)
    #             pulse_row = i + 2
    #
    #             del_button = QPushButton('Del')
    #             del_button.setMaximumWidth(40)
    #             del_button.clicked.connect(self.delButtonClicked)
    #             grid_layout.addWidget(del_button,pulse_row,self.columns.index('Del'))
    #
    #             # pulse_as_group = QRadioButton()
    #             # pulse_as_group.setChecked(pulse.as_group)
    #             # grid_layout.addWidget(pulse_as_group,pulse_row,self.columns.index('As group'))
    #             pulse_channel = QComboBox()
    #             pulse_channel.addItems(self.channels)
    #             pulse_channel.setCurrentText(getattr(pulse,'channel','0'))
    #             pulse_channel.currentTextChanged.connect(self.pulseChannelChanged)
    #             grid_layout.addWidget(pulse_channel,pulse_row,self.columns.index('Channel'))
    #
    #             pulse_name = QLineEdit(pulse.name)
    #             pulse_name.returnPressed.connect(self.pulseNameChanged)
    #             grid_layout.addWidget(pulse_name,pulse_row,self.columns.index('Name'))
    #
    #             pulse_edge = QComboBox()
    #             pulse_edge.addItems(self.edges)
    #             pulse_edge.setCurrentIndex(pulse.edge)
    #             pulse_edge.currentIndexChanged.connect(self.edgeChanged)
    #             grid_layout.addWidget(pulse_edge,pulse_row,self.columns.index('Edge'))
    #
    #             pulse_delay = QDoubleSpinBox()
    #             pulse_delay.setDecimals(self.n_decimals)
    #             pulse_delay.setMaximum(10000)
    #             pulse_delay.setMinimum(-10000)
    #             pulse_delay.setValue(pulse.delay)
    #             pulse_delay.valueChanged.connect(self.delayChanged)
    #             grid_layout.addWidget(pulse_delay,pulse_row,self.columns.index('Delay'))
    #
    #             pulse_length = QDoubleSpinBox()
    #             pulse_length.setDecimals(self.n_decimals)
    #             pulse_length.setMaximum(10000)
    #             pulse_length.setMinimum(-10000)
    #             pulse_length.setValue(pulse.length)
    #             pulse_length.valueChanged.connect(self.lengthChanged)
    #             grid_layout.addWidget(pulse_length,pulse_row,self.columns.index('Length'))
    #
    #             pulse_is_active = QCheckBox()
    #             pulse_is_active.setChecked(pulse.is_active)
    #             pulse_is_active.stateChanged.connect(self.isActiveChanged)
    #             grid_layout.addWidget(pulse_is_active,pulse_row,self.columns.index('Active'))
    #
    #         return grid_layout
    #
    #     def delButtonClicked(self):
    #         # layout = self.layout()
    #         print('delButtonClicked')
    #         index = self.grid_layout.indexOf(self.sender())
    #         row, column, cols, rows = self.grid_layout.getItemPosition(index)
    #         # print(row, column, cols, rows)
    #         self.data.pulses.pop(row-2)
    #         self.redrawGroup()
    #         self.parent.onAnyChange()
    #
    #     def groupNameChanged(self):
    #         print('groupNameChanged')
    #         # print('new name', self.sender().text())
    #         self.data.name = self.sender().text()
    #         self.parent.updateScheme()
    #
    #     # def updateReferences(self):
    #     #     self.ref_channel_combo_box.clear()
    #     #     self.ref_channel_combo_box.addItem('0')
    #     #     self.ref_channel_combo_box.addItems([group.name for group in self.parent.schemes[self.parent.current_scheme]])
    #     #     self.ref_channel_combo_box.setCurrentText(self.data.ref)
    #
    #     def edgeChanged(self, new_index):
    #         print('edgeChanged')
    #         index = self.grid_layout.indexOf(self.sender())
    #         row, column, cols, rows = self.grid_layout.getItemPosition(index)
    #         # print(row,column,new_index)
    #         if row == self.group_row:
    #             # group edge has been changed
    #             self.data.edge = new_index
    #         else:
    #             # individual pulse edge has been changed
    #             self.data.pulses[row-2].edge = new_index
    #         self.parent.onAnyChange()
    #
    #     def delayChanged(self,new_value):
    #         print('delayChanged')
    #         index = self.grid_layout.indexOf(self.sender())
    #         row, column, cols, rows = self.grid_layout.getItemPosition(index)
    #         # print(row,column,new_value)
    #         if row == self.group_row:
    #             # group edge has been changed
    #             self.data.delay = new_value
    #         else:
    #             # individual pulse edge has been changed
    #             self.data.pulses[row-2].delay = new_value
    #         self.parent.onAnyChange()
    #
    #     def lengthChanged(self,new_value):
    #         print('lengthChanged')
    #         index = self.grid_layout.indexOf(self.sender())
    #         row, column, cols, rows = self.grid_layout.getItemPosition(index)
    #         # print(row,column,new_value)
    #         if row == self.group_row:
    #             # group edge has been changed
    #             self.data.length = new_value
    #         else:
    #             # individual pulse edge has been changed
    #             self.data.pulses[row-2].length = new_value
    #         self.parent.onAnyChange()
    #
    #     def isActiveChanged(self,new_value):
    #         print('isActiveChanged')
    #         index = self.grid_layout.indexOf(self.sender())
    #         row, column, cols, rows = self.grid_layout.getItemPosition(index)
    #         # print(row,column,new_value)
    #         if row == self.group_row:
    #             # group edge has been changed
    #             self.data.is_active = new_value
    #         else:
    #             # individual pulse edge has been changed
    #             self.data.pulses[row-2].is_active = new_value
    #         self.parent.onAnyChange()
    #
    #     def pulseChannelChanged(self,new_value):
    #         print('pulseChannelChanged')
    #         index = self.grid_layout.indexOf(self.sender())
    #         row, column, cols, rows = self.grid_layout.getItemPosition(index)
    #         # print(row, column, new_value)
    #         self.data.pulses[row - 2].channel = new_value
    #         self.parent.onAnyChange()
    #
    #     def pulseNameChanged(self):
    #         print('pulseNameChanged')
    #         index = self.grid_layout.indexOf(self.sender())
    #         row, column, cols, rows = self.grid_layout.getItemPosition(index)
    #         # print(row, column, self.sender().text())
    #         self.data.pulses[row - 2].name = self.sender().text()
    #         self.parent.onAnyChange()


class IndividualPulse():
    def __init__(self, group = None,name='',channel = '0', edge = 0, delay=0, length=0,is_active=False):
        self.name = name   # name of the pulse
        # self.group = group # group of pulses it belongs to
        self.channel = channel # physical channel of the signal (or may be name in dictionary)
        self.edge = edge # start the pulse from group's t_start=0 or t_end=1
        self.variables = {'delay':delay,
                          'length':length}  # for easy scanning
        self.is_active = is_active
    def getPoints(self):
        pass

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
        return [(self.t_start,1),(self.t_end,0)]

class AnalogPulse(IndividualPulse):
    def __init__(self,type='Points'):
        super().__init__()
        self.type = type
        self.formula = '' # iether string of points if type Point ore string of formula if type Formula
        # self.timeStep # to define timestap if type=='Formula'

    def getPoints(self,time_step=1):
        # print(self.t_start, self.t_end)
        print(self.__dict__)
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
                print(temp1)
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
            func = lambdify(t, formula, 'numpy')
            xs = np.arange(0, self.t_end - self.t_start + time_step, time_step)
            ys = func(xs)
            xs += self.t_start
            points = np.reshape(np.array([xs, ys]).T, (-1, 2))
        return [list(point) for point in points]


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    mainWindow = pulseScheme()

    mainWindow.show()
    sys.exit(app.exec_())
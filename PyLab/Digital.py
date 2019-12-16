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

shutter_validator = QDoubleValidator(0,9.9,1)
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


class DigitalOutoutWidget(QWidget):

    def __init__(self,parent=None,globals={},signals={},config_file=None):
        super().__init__(parent)
        self.config_file = config_file
        self.globals = globals
        self.signals = signals
        self.parent = parent
        self.load()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(0.01)
        # self.device = COMPortDevice(default_port=port)
        # self.device_widget = self.device.ExtendedWidget(data=self.device,connect= False)#(self.port!=None)
        self.menuBar = QMenuBar(self)
        self.initUI()
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

        self.setWindowTitle('DigitalOutput')
        # self.setWindowIcon(QIcon('Devices\dds.jpg'))
        main_layout = QHBoxLayout()# mainLayout.addSpacing(10)
        self.setLayout(main_layout)
        self.setMinimumHeight(200)
        self.setMinimumWidth(550)


    def constructPulses(self,t_start,t_end):
        """constructs and updates pulses produced by Shutters channels"""
        digital_points = {}
        # print("BEFORE", self.globals["pulses"])
        for channel in self.globals["pulses"]:
            if channel in self.available_channels:
                # self.globals["pulses"][channel] = self.combinePoints(self.globals["pulses"][channel])
                # if self.globals["pulses"][channel][0][0] > 0:
                #     self.globals["pulses"][channel].insert(0, [0, (self.globals["pulses"][channel][0][1]+1)%2])
                if len(self.globals["pulses"][channel]) == 1: # single point in channel
                    # print("Do not touch", channel)
                    digital_points[channel] = self.globals["pulses"][channel]
                    continue
                if t_start == 0: # do nothing with points
                    digital_points[channel] = deepcopy(self.globals["pulses"][channel])
                else: # shift all points by t_start and add point in the end. assume that self.globals["pulses"][channel][0] is point at t=0
                    new_points = []
                    for point in deepcopy(self.globals["pulses"][channel]):
                        # print(point)
                        if point[0] == 0: # beginning of the pulses
                            end_point = [t_end-t_start,point[1]] # calculate ending point
                            new_points.append(point) # add this point in the beginning of new pulses
                        elif point[0] < t_start:
                            continue # skip points which a before t_start and not at t==0
                            # print("0")
                            # point[0]=0
                            # pulse.remove(point)
                        elif point[0] == t_start: #if front directly at t_start
                            new_points[0][1] = point[1] # rewrite first point
                        else:
                            new_points.append([point[0]-t_start,point[1]])
                            # print(1)
                            # point[0] -= t_start
                    new_points.append(end_point)
                    digital_points[channel] = new_points

        # if True: print('points by channel after processing\n', points_by_channel)
        # digital_points = {channel: self.globals["pulses"][channel] for channel in
        #                   self.globals["pulses"] if channel in self.available_channels}
        data = {"name": "DAQ", "device": "DAQ"}
        data.update({"msg": {"t_start":t_start,"points":digital_points}})
        msg = 'Send ' + json.dumps(data)
        print("SEND TO DAQ")
        print(msg)
        self.sock.sendto(bytes(msg, "utf-8"), self.globals["host_port"])
        self.signals.updateDigitalPlot.emit(t_start,t_end)

    def load(self):
        if DEBUG: print('--PulseScheme - loadSchemes')
        with open(self.config_file, 'r') as f:
            if DEBUG: print('config_load')
            all_config = json.load(f)
        self.available_channels = all_config["Digital"]['available_channels']

    def saveClicked(self):
        print('nothing to save for now in DigitalOutputWidget', self)
        # self.data = self.constructData()
        # with open(self.config_file, 'r') as f:
        #     if DEBUG: print('config_load_before_saving')
        #     all_config = json.load(f)
        # config = all_config['Shutters']
        # for key in config:
        #     config[key] = self.__dict__[key]
        # with open(self.config_file, 'w') as f:
        #     if DEBUG: print('config_save')
        #     json.dump(all_config, f)


if __name__ == '__main__':
    import sys
    # digital_pulses_folder = 'digital_schemes'
    # pulseGroup = PulseGroup
    app = QApplication(sys.argv)
    # mainWindow = PulseGroup(parent=None,name='New group',data=[])
    # mainWindow = PulseScheme()
    mainWindow = DigitalOutoutWidget(config_file='config.json')
    mainWindow.show()
    sys.exit(app.exec_())

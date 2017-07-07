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
from PyQt5.QtWidgets import (QApplication, QGraphicsView, QGraphicsScene, QGraphicsItem, QMenu, QAction, QScrollArea,QFrame,
                             QGridLayout, QVBoxLayout, QHBoxLayout, QSizePolicy,QMainWindow, QDialog,QTextEdit,
                             QLabel, QLineEdit, QPushButton, QWidget, QComboBox,QRadioButton, QSpinBox, QCheckBox, QTabWidget, QFileDialog,QMessageBox, QDoubleSpinBox)
# import pyqtgraph as pg
import json
import time
from sympy.utilities.lambdify import lambdify
import re
import numpy as np
from numpy import *
import sympy as sp
from sympy.parsing.sympy_parser import parse_expr
from itertools import chain
from scanParameters import  SingleScanParameter,AllScanParameters,MeasurementFolderClass
import time
import datetime
import threading

scanner_config_file = 'config_scanner.json'
data_directory = '..'
scan_params_str = 'scan_params'
scan_folder_data_str = 'scan_folder_data'
single_folder_suffix = 'ms'
meas_config_file = 'meas_config.json'
EMPTY_CONFIG_FILE = -1

class Scanner(QWidget):

    def __init__(self,globals=None,all_updates_methods=None,signals=None,parent=None,**argd):
        self.parent = parent
        self.all_updates_methods = all_updates_methods
        self.globals = globals
        self.globals['image_stack']=[]
        self.signals = signals
        self.scan_parameters = AllScanParameters(globals=globals,parent=self)
        self.meas_folder1 = MeasurementFolderClass(globals=globals,parent=self)
        self.add_points_flag = False
        # self.all_scan_params = {}#{'pulses':a}
        self.notes = ''
        self.current_meas_number = 0
        self.on_scan = False
        self.scan_interrupted = False
        self.number_of_shots = 5
        self.current_shot_number = 0
        self.single_meas_folder = ''
        self.loadConfig()
        super().__init__()
        self.initUI()
        # for now while without real scan
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        # self.timer.timeout.connect(self.cycleFinished)
        self.signals.scanCycleFinished.connect(self.cycleFinished)
        # add variable to global namespace
        self.updateGlobals()

    def loadConfig(self):
        print('loadConfigScanner')
        print(os.getcwd())
        try:
            with open(scanner_config_file,'r') as f:
                self.config = json.load(f)
        except json.decoder.JSONDecodeError:
            print('ERROR in reading ', scanner_config_file)
            print('Default configuration will be loaded')
            self.scan_parameters.load()
            self.meas_folder1.load()
            self.config={}
            return EMPTY_CONFIG_FILE
        for key in self.config:
            self.__dict__[key] = self.config[key]
        self.scan_parameters.load(self.config[scan_params_str])
        self.meas_folder1.load(self.config[scan_folder_data_str])

    def saveConfig(self,changed_key=None,changed_value=None):
        print('saveConfig')
        if changed_key:
            print('Changed Value',changed_value)
            self.config[changed_key] =changed_value if changed_value!=None else self.__dict__[changed_key]
        try:
            with open(scanner_config_file, 'r') as f:
                old_config = json.load(f)
        except json.decoder.JSONDecodeError:
            old_config = {}
        with open(scanner_config_file, 'w') as f:
            try:
                json.dump(self.config,f)
            except: # find what error does it raise when cannot dump
                json.dump(old_config, f)
                QMessageBox.warning(None, 'Message', "can not dump config to json, old version will be saved",
                                    QMessageBox.Ok)
        # maybe introduce here updateGlobals() call

    def initUI(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(5)

        self.meas_folder1.gui = self.meas_folder1.folderUI(data=self.meas_folder1,parent=self)
        main_layout.addWidget(self.meas_folder1.gui)

        hor3 = QHBoxLayout()

        add_points_box = QCheckBox()
        add_points_box.setChecked(self.add_points_flag)
        add_points_box.stateChanged.connect(self.addPointsChanged)
        hor3.addWidget(add_points_box)

        hor3.addWidget(QLabel('add points to the folder'))
        # hor3.addStretch(0.5)
        number_of_shots_box = QSpinBox()
        number_of_shots_box.setMinimum(0)
        number_of_shots_box.setMaximum(100)
        number_of_shots_box.setValue(self.number_of_shots)
        number_of_shots_box.valueChanged.connect(self.numberOfShotsChanged)
        hor3.addWidget(number_of_shots_box)

        hor3.addWidget(QLabel('Shots'))

        self.stop_btn = QPushButton('Stop')
        self.stop_btn.clicked.connect(self.stopBtnPressed)
        hor3.addWidget(self.stop_btn)

        self.scan_btn = QPushButton('New scan')
        self.scan_btn.clicked.connect(self.scanBtnPressed)
        hor3.addWidget(self.scan_btn)

        main_layout.addLayout(hor3)

        # scroll = QScrollArea()
        # scroll.setFrameShape(QFrame.NoFrame)
        # scroll.setWidget(self.scan_box)
        self.scan_parameters.gui = self.scan_parameters.scanUI(data=self.scan_parameters,parent=self)
        main_layout.addWidget(self.scan_parameters.gui)

        notes_box = QTextEdit(self.notes)
        notes_box.textChanged.connect(self.notesChanged)
        notes_box.setMaximumHeight(200)
        main_layout.addWidget(notes_box)
        self.setLayout(main_layout)

    def addPointsChanged(self, new_value):
        print('addPointsChanged')
        self.add_points_flag = new_value
        self.saveConfig('add_points_flag')

    def numberOfShotsChanged(self, new_value):
        print('numberOfShotsChanged')
        self.number_of_shots = new_value
        self.saveConfig('number_of_shots')

    def stopBtnPressed(self):
        print('stopBtnPressed')
        if self.on_scan:
            self.stopScan(stop_btn_text='Continue', is_scan_interrupted=True)
        elif self.scan_interrupted:
            self.startScan()
            print('Scan restarted')

    def scanBtnPressed(self):
        print('scanBtnPressed')
        if not self.on_scan:        # then start should be started
            # check equal length of params in each group
            is_ok = self.scan_parameters.checkLength()
            if not is_ok:
                return -1
            self.current_shot_number = 0
            changed_index = self.scan_parameters.updateIndexes(start=True)
            # print('Data folder: ', os.path.join(self.meas_folder1.day_folder,self.meas_folder1.name))
            self.globals['current_measurement_folder'] = self.meas_folder1.day_folder.strip() + '/' + self.meas_folder1.name.strip()
            os.mkdir(self.globals['current_measurement_folder'])    # create new measurement folder
            self.writeMeasConfig()
            print('Data folder: ',self.globals['current_measurement_folder'])
            # self.globals['DAQ'].stop()
            # time.sleep(1)
            self.updateParamAndSend(changed_index)
            self.updateSingleMeasFolder()
            self.startScan()
            # sthrd = threading.Thread(target=self.addFirstFolder)
            # sthrd.start()
            # self.globals['image_stack'].append(self.globals['current_data_folder'] + '/' + '0_0.png')
            print('Scan started at ',datetime.datetime.now().time())

    def writeMeasConfig(self):
        fname = self.globals['current_measurement_folder'] + '/' + meas_config_file
        meas_config_data = {}
        if 'image_lower_left_corner' in self.globals:
            meas_config_data['image_lower_left_corner'] = self.globals['image_lower_left_corner']
        with open(fname, 'w') as f:
            try:
                json.dump(meas_config_data,f)
            except: # find what error does it raise when cannot dump
                print("can't dump meas_config_data")
                # json.dump(old_config, f)
                # QMessageBox.warning(None, 'Message', "can not dump config to json, old version will be saved",
                #                     QMessageBox.Ok)

    def addFirstFolder(self):
        time.sleep(0.7)
        self.globals['image_stack'].append(self.globals['current_data_folder'] + '/' + '0_0.png')

    def updateSingleMeasFolder(self):
        print('updateSingleMeasFolder')
        self.single_meas_folder = self.scan_parameters.getSingleFolderName()+single_folder_suffix
        self.globals['current_data_folder']= self.globals['current_measurement_folder'].strip() + '/' + self.single_meas_folder.strip()
        os.mkdir(self.globals['current_data_folder'])        # create new folder
        print('Current folder for images: ',self.globals['current_data_folder'])
        self.updateGlobals()

    def updateGlobals(self):
        self.globals['single_meas_folder'] = self.single_meas_folder
        # self.globals['meas_folder'] = self.meas_folder
        self.globals['on_scan'] = self.on_scan
        self.globals['current_shot_number'] = self.current_shot_number
        # print('Globals: ',self.globals)

    def cycleFinished(self, number=None):
        # self.parent.arduino.read_serial()
        # for i in range(20):
        #     s = self.parent.arduino.stream.readline().decode()
        #     if s=='':
        #         break
        #     print("arduino >>   ",s,end='')
        print(number, 'cycleFinished at ',datetime.datetime.now().time())
        if not self.on_scan:
            return
        # called when one cycle is finished
        self.globals['image_stack'].append(
            self.globals['current_data_folder'] + '/' + '%i_0.png' % self.current_shot_number)
        if self.current_shot_number < self.number_of_shots - 1:
            self.current_shot_number += 1
            # self.globals['image_stack'].append(
            #     self.globals['current_data_folder'] + '/' + '%i_0.png' % self.current_shot_number)
            return 0
        self.current_shot_number = 0
        # self.globals['image_stack'].append(
        #     self.globals['current_data_folder'] + '/' + '%i_0.png' % self.current_shot_number)
        changed_index = self.scan_parameters.updateIndexes()
        if changed_index != 0:
            # we proceed with to the next outter parameter
            self.scan_parameters.updateAdditionalName()     # update additional name
            self.meas_folder1.current_meas_number += 1      # increment meas folder number
            self.meas_folder1.gui.updateMeasFolder()
            # os.mkdir()    # create new folder

        # print(self.scan_parameters.current_indexs)
        self.updateParamAndSend(changed_index)
        if self.on_scan:
            self.updateSingleMeasFolder()
            # self.globals['image_stack'].append(self.globals['current_data_folder'] + '/' + '0_0.png')

    def updateParamAndSend(self,changed_index):
        print('updateParamAndSend')
        # print(changed_index)
        # STOP DAQ
        params_to_send = self.scan_parameters.getParamsToSend()
        print('Scanning parameters: ',params_to_send)
        # update parameters by calling update methods of subprogramm
        is_Ok = True    # now it's not used but may be later
        if self.all_updates_methods != None:
            for name, params in params_to_send.items():
                res_of_update = self.all_updates_methods[name](param_dict=params)
                if res_of_update == -1: # if smth wrong
                    QMessageBox.warning(self, 'Message', "Couldn't change %s parameters\nScan is stopped"%(name), QMessageBox.Yes)
                    self.stopScan(stop_btn_text='Continue',is_scan_interrupted=True)
                    is_Ok = False
                    break

        if changed_index == -1:
            self.stopScan(stop_btn_text='Fihished')
        # START DAQ mayby somehow check if is_Ok
                # print(name, res_of_update)

    def stopScan(self,stop_btn_text='Stop',is_scan_interrupted=False,**argd):
        print('stopScan')
        print(self.globals['image_stack'])
        self.timer.stop()
        self.on_scan = False
        self.stop_btn.setText(stop_btn_text)
        self.scan_btn.setText('New scan')
        self.scan_interrupted = is_scan_interrupted

    def startScan(self,**argd):
        self.scan_interrupted = False
        self.timer.start()
        self.stop_btn.setText('Stop')
        self.scan_btn.setText('On scan!')
        self.on_scan = True

    def notesChanged(self):
        print('notesChanged')
        self.notes = self.sender().toPlainText()
        print(repr(self.notes))
        self.saveConfig('notes')



if __name__ == '__main__':
    # config = {}
    # config['day_folder'] = '2016_10_10'
    # config['all_meas_type'] = ['CL', 'LT', 'FB', 'T']
    # config['current_meas_type'] = 'CL'
    # config['add_points_flag']=  False
    # config['notes'] = 'some note'
    # config['number_of_shots'] = 10
    # with open(scanner_config_file,'w') as f:
    #     json.dump(config,f)
    import sys
    app = QApplication(sys.argv)
    mainWindow = Scanner()
    mainWindow.show()
    sys.exit(app.exec_())
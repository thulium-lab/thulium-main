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

scanner_config_file = 'config_scanner.json'
data_directory = '..'
scan_params_str = 'scan_params'

class Scanner(QWidget):

    def __init__(self,globals=None,all_updates_methods=None):
        # написат загрузку с конфига
        self.all_updates_methods = all_updates_methods
        self.globals = globals
        self.day_folder = ''
        self.all_meas_type = set()
        self.current_meas_type = ''
        self.other_params = ''
        self.meas_folder = ''
        self.add_points_flag = False
        # a = {'1 stage cooling': {'group': ['length', 'delay'], 'Magnetic field': ['t0', 'length', 'delay', 't1'], 'Zeeman': ['length', 'delay'], 'Blue': ['length', 'delay'], 'Green': ['length', 'delay'], 'ttt': ['length', 'delay', 'p']}, '2 stage cooling': {'group': ['length', 'delay'], 'Magnetic fiekd': ['length', 'delay'], 'Green': ['length', 'delay'], 'yyy': ['length', 'delay']}}
        self.all_scan_params = {}#{'pulses':a}
        self.notes = ''
        self.current_meas_number = 0
        self.on_scan = False
        self.scan_interrupted = False
        self.number_of_shots = 10
        self.current_shot_number = 0
        self.current_param_indexs = [] # index for each level of params
        self.scan_params = [[[['1','2'],''],[['3','4'],'']]]
        self.loadConfig()
        # print('Here')
        super().__init__()
        self.initUI()
        # for now while without real scan
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.cycleFinished)
        # print(self.__dict__)

    def loadConfig(self):
        print('loadConfig')
        with open(scanner_config_file,'r') as f:
            self.config = json.load(f)
        for key in self.config:
            self.__dict__[key] = self.config[key]

    def saveConfig(self,changed_key=None):
        print('saveConfig')
        if changed_key:
            self.config[changed_key] =self.__dict__[changed_key]
        with open(scanner_config_file, 'w') as f:
            json.dump(self.config,f)

    def initUI(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(5)
        hor1 = QHBoxLayout()

        self.day_box = QLineEdit(os.path.basename(self.day_folder))
        hor1.addWidget(self.day_box)

        day_folder = QPushButton('Day')
        day_folder.clicked.connect(self.dayBtnPressed)
        hor1.addWidget(day_folder)
        #Day_dialog

        hor1.addWidget(QLabel('Meas. type'))

        self.meas_type_box = QComboBox()
        self.meas_type_box.addItems(self.all_meas_type)
        self.meas_type_box.setCurrentText(self.current_meas_type)
        self.meas_type_box.currentTextChanged.connect(self.measTypeChanged)
        hor1.addWidget(self.meas_type_box)

        hor1.addWidget(QLabel('other params'))

        other_params_box = QLineEdit(self.other_params)
        other_params_box.returnPressed.connect(self.otherParamsChanged)
        hor1.addWidget(other_params_box)

        main_layout.addLayout(hor1)

        hor2 = QHBoxLayout()

        hor2.addWidget(QLabel('folder'))

        self.meas_folder_box = QLineEdit(self.meas_folder)
        self.updateMeasFolder()
        self.meas_folder_box.returnPressed.connect(self.measFolderChanged)
        hor2.addWidget(self.meas_folder_box)

        new_btn = QPushButton('New')
        new_btn.clicked.connect(self.newBtnPressed)
        hor2.addWidget(new_btn)

        open_btn = QPushButton('Open')
        open_btn.clicked.connect(self.openBtnPressed)
        hor2.addWidget(open_btn)

        main_layout.addLayout(hor2)

        hor3 = QHBoxLayout()

        add_points_box = QCheckBox()
        add_points_box.setChecked(self.add_points_flag)
        add_points_box.stateChanged.connect(self.addPointsChanged)
        hor3.addWidget(add_points_box)

        hor3.addWidget(QLabel('add points to the folder'))

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

        hor4 = QHBoxLayout()

        hor4.addWidget(QLabel('Scan parameters'))

        add_param_level = QPushButton('Add level')
        add_param_level.clicked.connect(self.addParamLevelPressed)
        hor4.addWidget(add_param_level)

        main_layout.addLayout(hor4)

        self.scan_box = QWidget()
        # grid = QGridLayout()
        # self.scan_box.setLayout(grid)
        self.scanDraw()
        # scroll = QScrollArea()
        # scroll.setFrameShape(QFrame.NoFrame)
        # scroll.setWidget(self.scan_box)
        main_layout.addWidget(self.scan_box)

        notes_box = QTextEdit(self.notes)
        notes_box.textChanged.connect(self.notesChanged)
        notes_box.setMaximumHeight(200)
        main_layout.addWidget(notes_box)
        self.setLayout(main_layout)
        print('Done')

    def scanDraw(self):
        print('scanDraw')
        grid =  QGridLayout()
        row = 0
        for i,p_level in enumerate(self.scan_params):
            print(p_level)
            for j,param in enumerate(p_level):
                # h_box = QHBoxLayout()
                menu_btn = QPushButton(str(param[0]) if len(param[0])==0 else param[0][-1])
                menu_btn.setToolTip('->'.join(param[0]))
                param_menu = QMenu(menu_btn)
                param_menu.aboutToShow.connect(self.updateAllScanParams)
                self.getParamMenu(param_menu, self.all_scan_params)
                menu_btn.setMenu(param_menu)
                # menu_btn.pressed.connect(self.updateAllScanParams)
                grid.addWidget(menu_btn,row,0)

                grid.addWidget(QLabel(str(i)),row,1)

                param_line = QLineEdit(' '.join([str(i) for i in param[1]]))
                param_line.returnPressed.connect(self.paramLineChanged)
                grid.addWidget(param_line,row,2)

                if not (i == 0 and j==0):
                    del_btn = QPushButton('Del')
                    del_btn.clicked.connect(self.delScanParam)
                    grid.addWidget(del_btn,row,3)
                add_btn = QPushButton('Add')
                add_btn.clicked.connect(self.addScanParam)
                grid.addWidget(add_btn,row,4)
                row +=1

        menu_btn.setMenu(param_menu)
        grid.addWidget(menu_btn)
        self.scan_box.setLayout(grid)
        print('after')

    def updateAllScanParams(self):
        print('updateAllScanParams')
        print(self.globals)
        if self.globals != None:
            del self.all_scan_params
            self.all_scan_params = deepcopy(self.globals[scan_params_str])
            self.sender().clear()
            self.getParamMenu(self.sender(), self.all_scan_params)

    def scanRedraw(self):
        QWidget().setLayout(self.scan_box.layout())
        self.scanDraw()
        self.saveConfig('scan_params')

    def paramLineChanged(self):
        print('paramLineChanged')
        s = self.sender().text()
        arr = []
        print(s)
        for elem in re.findall('(\d+\.?\d*)', s):
            arr.append(float(elem))
        grid = self.scan_box.layout()
        index = grid.indexOf(self.sender())
        row, column, cols, rows = grid.getItemPosition(index)
        sm = 0
        for group in self.scan_params:
            if row < sm + len(group):
                elem = group[row-sm]
                elem[1] = arr
                # self.sender().setText(elem[1])
                break
            else:
                sm += len(group)
        print(self.scan_params)
        self.saveConfig('scan_params')

    def delScanParam(self):
        print('delScanParam')
        grid = self.scan_box.layout()
        index = grid.indexOf(self.sender())
        row, column, cols, rows = grid.getItemPosition(index)
        sm = 0
        for group in self.scan_params:
            if row < sm + len(group):
                elem = group[row - sm]
                group.remove(elem)
                if len(group) == 0:
                    self.scan_params.remove(group)
                break
            else:
                sm += len(group)
        self.scanRedraw()

    def addScanParam(self):
        print("addScanParam")
        grid = self.scan_box.layout()
        index = grid.indexOf(self.sender())
        row, column, cols, rows = grid.getItemPosition(index)
        sm = 0
        for group in self.scan_params:
            if row < sm + len(group):
                group.insert(row - sm + 1,[['1'],''])
                break
            else:
                sm += len(group)
        self.scanRedraw()

    def getParamMenu(self,parent, data):
        # print('getParamMenu')
        if type(data) == type([]):
            for submenu in data:
                    # print('end of the tree')
                    act = parent.addAction(submenu)
                    act.triggered.connect(self.getNewScanParam)
        else :
            # print('-->',list(data.keys()), parent)
            for submenu in data:
                m = parent.addMenu(submenu)
                self.getParamMenu(m,data[submenu])

    def getNewScanParam(self):
        print('getNewScanParam')
        a = self.sender()
        name = []
        name.append(a.text())
        while 1:
            a = a.parent()
            # print(repr(a.title()))
            if a.title() == '':
                break
            name.insert(0,a.title())
        par = a.parent()
        grid = self.scan_box.layout()
        index = grid.indexOf(par)
        row, column, cols, rows = grid.getItemPosition(index)
        # print(row,column)
        sm = 0
        for group in self.scan_params:
            if row < sm + len(group):
                elem = group[row-sm]
                elem[0] = name
                par.setText(name[-1])
                break
            else:
                sm += len(group)
        # print(row, column)
        self.saveConfig('scan_params')

    # def getParamNumbers(self):

    def dayBtnPressed(self):
        print("dayBtnPressed")
        filet = str(QFileDialog.getExistingDirectory(self, "Select Directory",directory=data_directory))
        if filet:
            print(filet)
            self.day_folder = filet
            self.day_box.setText(os.path.basename(self.day_folder))
            self.saveConfig('day_folder')

    def measTypeChanged(self,new_value):
        print('measTypeChanged')
        self.current_meas_type = new_value
        self.saveConfig('current_meas_type')
        print(self.current_meas_type)
        self.updateMeasFolder()

    def otherParamsChanged(self):
        print('otherParamsChanged')
        self.other_params = self.sender().text()
        self.saveConfig('other_params')
        self.updateMeasFolder()

    def updateMeasFolder(self):
        print('updateMeasFolder')
        self.meas_folder = "%02i %s %s" % (self.current_meas_number,self.current_meas_type,self.other_params)
        self.meas_folder_box.setText(self.meas_folder)

    def measFolderChanged(self):
        print('measFolderChanged')
        self.meas_folder = self.sender().text()
        # maybe update self.other params

    def newBtnPressed(self):
        print('newBtnPressed')
        drs = os.listdir(self.day_folder)
        last_index = 0
        for d in drs:
            if d[:2].isdigit():
                n = int(d[:2])
                print(n)
                if n > last_index:
                    last_index = n
        self.current_meas_number = last_index+1
        self.updateMeasFolder()
        # self.

    def openBtnPressed(self):
        print('openBtnPressed')
        filet = str(QFileDialog.getExistingDirectory(self, "Select Directory", directory=os.path.join(data_directory,self.day_folder)))
        if filet:
            print(filet)
            self.meas_folder = os.path.basename(filet)
            self.meas_folder_box.setText(self.meas_folder)
            # maybe update self.other params

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
        is_wrong = False
        if not self.on_scan:
            # check equal length of params in each group
            for group in self.scan_params:
                if len(group) == 1:
                    continue
                else:
                    for i in range(len(group)-1):
                        if len(group[i][1]) != len(group[i+1][1]):
                            QMessageBox.warning(self, 'Message',"Not equal length of params", QMessageBox.Yes)
                            # print(len(group[i][1]))
                            # print(len(group[i+1][1]))
                            is_wrong = True
                            # break
            if is_wrong:
                return
            self.current_shot_number = 0
            self.current_param_indexs = [0] * len(self.scan_params)
            self.updateParamAndSend(len(self.current_param_indexs) - 1)
            self.startScan()
            # self.stop_btn.setText('Stop')
            # self.scan_btn.setText('On scan!')
            # self.current_param_indexs[0]=1
            # self.scan_interrupted = False
            # self.on_scan = True
            print('Scan started')

    def addIndex(self,i):
        # reccursive function to properly update indexs of current scan params
        if self.current_param_indexs[i] < len(self.scan_params[i][0][1]) - 1:
            # i.e. it is not yet end of this level parameter
            self.current_param_indexs[i] += 1
            # return which index is modified
            return i
        else:
            # overflow happend
            self.current_param_indexs[i] = 0  # if put this line late one can realize situation, where after scan
            # indexs are not set back to zero
            if i < len(self.current_param_indexs) - 1:
                return self.addIndex(i + 1)
            else:
                # this means the end of scan
                return -1

    def cycleFinished(self):
        print('cycleFinished')
        # called when one cycle is finished
        if self.current_shot_number < self.number_of_shots:
            self.current_shot_number += 1
            return 0
        else:
            self.current_shot_number = 0
        # reccursive function to properly update indexs of current scan params
        changedIndex = self.addIndex(0)
        if changedIndex == -1:
            # scan is finished
            self.stopScan(stop_btn_text='Fihished')
        else:
            self.updateParamAndSend(changedIndex)

    def updateParamAndSend(self,changed_index):
        print('updateParamAndSend')
        # STOP DAQ

        #construct dict with new values of params to send of type param_full_name:new value
        self.current_params = {}
        for i in range(changed_index + 1): # to handle changed index as well
            for param in self.scan_params[i]:
                self.current_params[tuple(param[0])] = param[1][self.current_param_indexs[i]]

        # reconstruct dict to dictionary submprogam_name:{relativ_param_name:value,...}
        params_to_send = {}
        for key, value in self.current_params.items():
            subprogram_name = key[0]
            if subprogram_name not in params_to_send:
                params_to_send[subprogram_name] = {}
            params_to_send[subprogram_name][tuple(key[1:])]=value
        print(params_to_send)
        # update parameters by calling update methods of subprogramm
        is_Ok = True
        if self.all_updates_methods != None:
            for name, params in params_to_send.items():
                res_of_update = self.all_updates_methods[name](param_dict=params)
                if res_of_update == -1: # if smth wrong
                    QMessageBox.warning(self, 'Message', "Couldn't change %s parameters\nScan is stopped"%(name), QMessageBox.Yes)
                    self.stopScan(stop_btn_text='Continue',is_scan_interrupted=True)
                    is_Ok = False
                    break
        # START DAQ mayby somehow check if is_Ok
                # print(name, res_of_update)

    def stopScan(self,stop_btn_text='Stop',is_scan_interrupted=False,**argd):
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

    def addParamLevelPressed(self):
        print('addParamLevelPressed')
        self.scan_params.append([[['0','2'],'']])
        self.scanRedraw()

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
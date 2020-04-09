import os, time, datetime, json, shutil, traceback, sys
import numpy as np
from PyQt5.QtWidgets import (QApplication, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel, QPushButton, QWidget,
                             QSpinBox, QCheckBox, QMessageBox, QProgressBar,QTableWidget,QHeaderView,QTableWidgetItem,
                             QInputDialog,QMenuBar, QAction, QScrollArea, QMenu, QFileDialog,QSizePolicy,QDialog)
# from DigitalPulses.scanParameters import SingleScanParameter, AllScanParameters, MeasurementFolderClass
from PyQt5.QtCore import (QTimer, Qt)
from PyQt5.QtGui import (QFont)
from Lib import (MyComboBox, MyDoubleBox, MyIntBox, MyLineEdit, MyCheckBox, MyPushButton,
                 QDoubleValidator, QIntValidator)

from collections import OrderedDict
from copy import deepcopy
import pandas as pd

from scipy.optimize import curve_fit
import importlib

import function_lib
from function_lib import *

DEBUG = True
scanner_config_file = 'config_scanner.json'
data_directory = 'DigitalPulses\digital_schemes'
scan_params_str = 'scan_params'
scan_folder_data_str = 'scan_folder_data'
single_folder_suffix = 'ms'
meas_config_file = 'meas_config.json'
EMPTY_CONFIG_FILE = -1
if r'D:\!Data' not in sys.path:
    sys.path.append(r'D:\!Data')
import thulium_python_lib.usefull_functions as usfuncs
import pyqtgraph.console

from inspect import getsource

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class MeasurementFolderClass(QWidget):

    def __init__(self, globals=None,parent=None,signals=None,data={}):
        self.globals = globals
        self.data = data
        self.parent = parent
        self.signals = signals
        super().__init__()
        self.initUI()
        # self.N_params = 10  # should be in data

    def initUI(self):
        main_layout = QVBoxLayout()
        # main_layout.setSpacing(5)
        hor1 = QHBoxLayout()

        self.day_box = MyLineEdit(name=os.path.basename(self.data["day_folder"]))
        hor1.addWidget(self.day_box)

        day_folder = MyPushButton(name='Day',handler=self.dayBtnPressed,fixed_width=40)
        hor1.addWidget(day_folder)

        hor1.addWidget(QLabel('Meas. type'))

        self.meas_type_box = MyComboBox(items=self.data["meas_types"],current_text=self.data["current_meas_type"],
                                        current_text_changed_handler=self.measTypeChanged,min_width=30)
        hor1.addWidget(self.meas_type_box)

        addPparam_btn = MyPushButton(name='Add param',handler=self.addParamClicked)
        hor1.addWidget(addPparam_btn)

        delPparam_btn = MyPushButton(name='Del param', handler=self.delParamClicked)
        hor1.addWidget(delPparam_btn)

        main_layout.addLayout(hor1)

        self.N_params = len(self.data["other_params"])
        self.param_table = QTableWidget(2,self.N_params)
        self.param_table.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)
        self.param_table.horizontalHeader().setMinimumSectionSize(60)
        self.param_table.setVerticalHeaderLabels(['param','value'])
        self.param_table.setMaximumHeight(80)
        # print('other params in MeasFolder',self.data["other_params"])
        for i, item  in enumerate(self.data["other_params"]):
            param, val = item
            self.param_table.setItem(0, i, QTableWidgetItem(param))
            self.param_table.setItem(1, i, QTableWidgetItem(val))
        self.param_table.cellChanged.connect(self.paramTableChanged)
        self.param_table.horizontalHeader().hide()

        main_layout.addWidget(self.param_table)

        hor2 = QHBoxLayout()

        hor2.addWidget(QLabel('Folder'))

        self.meas_folder_box = QLabel(self.data["meas_folder"])
        self.meas_folder_box.setStyleSheet("QLabel { background-color : white}")
        self.meas_folder_box.setFont(QFont("Arial",12))
        hor2.addWidget(self.meas_folder_box)
        hor2.addStretch(1)

        new_btn = MyPushButton(name='New',handler=self.newBtnPressed)
        hor2.addWidget(new_btn)

        open_btn = MyPushButton(name='Open',handler=self.openBtnPressed)
        hor2.addWidget(open_btn)

        main_layout.addLayout(hor2)

        self.setLayout(main_layout)

    def paramTableChanged(self,row,col):
        # print(row, col)
        self.data["other_params"][col][row] = self.param_table.item(row,col).text()

    def addParamClicked(self):
        n_col = self.param_table.columnCount()
        self.data["other_params"].insert(n_col-1, ["new", None])
        self.param_table.insertColumn(n_col-1)
        self.param_table.setItem(0,n_col-1, QTableWidgetItem('new'))
        # self.N_params = n_col+1

    def delParamClicked(self):
        param_list = [item[0] for item in self.data["other_params"]]
        param_to_del, ok_pressed = QInputDialog.getItem(self, "Del item",
                                                        "Choose param:", param_list,
                                                        0, False)
        if ok_pressed:
            if DEBUG:
                print('---delParam - deleting parameter', param_to_del)
            for i, item in enumerate(self.data["other_params"]):
                if item[0] == param_to_del:
                    self.data['other_params'].pop(i)
                    self.param_table.removeColumn(i)
                    self.updateMeasFolder()
        # self.save()
        return

    def dayBtnPressed(self):
        print("---dayBtnPressed")
        filet = str(QFileDialog.getExistingDirectory(self, "Select Directory", directory=data_directory))
        if filet:
            # print(filet)
            self.data["day_folder"] = filet
            self.day_box.setText(os.path.basename(self.data["day_folder"]))
            # self.saveToConfig('day_folder')

    def measTypeChanged(self, new_value):
        print('measTypeChanged')
        self.data["current_meas_type"] = new_value
        self.updateMeasFolder()
        # self.saveToConfig('current_type')

    def updateMeasFolder(self):
        # if DEBUG: print('updateMeasFolder')
        params_str = ''
        for i in range(self.param_table.columnCount()):
            p_item = self.param_table.item(0,i)
            if p_item == None or len(p_item.text()) == 0:
                continue
            else:
                params_str += ' ' + p_item.text()
                v_item = self.param_table.item(1,i)
                if v_item != None and len(v_item.text()) > 0:
                    params_str += '=' + v_item.text()
        params_str = params_str.strip()
        # if DEBUG: print("other_param string", params_str)
        # self.data.other_params = params_str.strip()
        self.data["meas_folder"] = "%02i %s %s" % (self.data["current_meas_number"], self.data["current_meas_type"], params_str)

        # # CHECk what is this
        # if 'additional_scan_param_name' in self.data.globals:
        #     print('in update meas folder globals', self.data.globals['additional_scan_param_name'])
        #     self.data["meas_folder"] += ' ' + self.data.globals['additional_scan_param_name']

        # print('-'*10, self.data["meas_folder"])
        self.meas_folder_box.setText(self.data["meas_folder"])
        self.meas_folder_box.repaint()

    def measFolderChanged(self):
        print('measFolderChanged')
        self.data["meas_folder"] = self.sender().text()
        # maybe update self.other params

    def newBtnPressed(self):
        print('newBtnPressed')
        drs = os.listdir(self.data["day_folder"])
        last_index = 0
        for d in drs:
            n_folder = d.split(' ')[0]
            # if d[:2].isdigit():
            #     n = int(d[:2])
            if n_folder.isdigit():
                n = int(n_folder)
                # if DEBUG: print('last measurement number', n)
                if n > last_index:
                    last_index = n
        self.data["current_meas_number"] = last_index + 1
        self.updateMeasFolder()
        # self.saveToConfig('other_params')

    def openBtnPressed(self):
        print('openBtnPressed')
        filet = str(QFileDialog.getExistingDirectory(None, "Select Directory",
                                                     directory=os.path.join(data_directory, self.data["day_folder"])))
        if filet:
            print("Opened measurement folder", filet)
            self.data["meas_folder"] = os.path.basename(filet)
            self.meas_folder_box.setText(self.data["meas_folder"])
            # maybe update self.other params

    def constructData(self):
        return self.data

    def getMeasFolderName(self):
        # self.updateMeasFolder()
        return self.data["meas_folder"].strip()

    def setMeasFolderNameFromScanner(self,new_name):
        self.data["meas_folder"] = new_name
        self.meas_folder_box.setText(self.data["meas_folder"])
        self.meas_folder_box.repaint()

    def getDayFolder(self):
        return self.data["day_folder"]

depth_validator = QIntValidator(0,9)

SCAN_LINE_DICT = OrderedDict([
    ("Del",['MPB','Del',40]),
    ('Param',['CB',['Empty'],60]),
    ('Name', ['LE', '', 120]),
    ('Depth',['LB',0,20]), #Depth
    ('Line',['LE','',4020]),
    ("Value",['LB','-',30]),
    ('On',['MChB',False,20]),
        ])

class ScanParameters(QScrollArea):

    class Line(QWidget):

        def __init__(self, parent, data={}):
            # if DEBUG: print('---- currentLine construct, data',data)
            super().__init__(parent)
            self.parent = parent
            layout = QHBoxLayout()
            self.data = data
            # print("line data",self.data)
            self.widgets = {}
            # print("gere")
            for key, val in SCAN_LINE_DICT.items():
                # print(key,val)
                # print(key)
                if key == 'Del':
                    self.paramBtn = MyPushButton(name=key,handler=lambda: self.parent.delete(self), fixed_width=val[-1])
                    layout.addWidget(self.paramBtn, val[-1])
                    continue
                self.data[key] = data.get(key, val[1])
                if val[0] == 'CB':
                    # create a combo box widget
                    if key == "Param":
                        w = QPushButton(self.data["Param"][-1])
                        self.param_menu = QMenu(w)
                        self.param_menu.aboutToShow.connect(self.updateParamMenu)
                        w.setMenu(self.param_menu)
                        w.setToolTip('->'.join(self.data["Param"]))
                        w.setMaximumWidth(val[-1])
                elif val[0] == 'LE':
                    w = MyLineEdit(name=data.get(key, val[1]),
                                   text_changed_handler=self.update,
                                   text_edited_handler=self.textEdited,
                                   max_width=val[-1])
                elif val[0] == 'LB':
                    w = QLabel(str(self.data[key]))
                    w.setMinimumWidth(val[-1])
                elif val[0] == 'MChB':
                    # print("Check box initialized", key)
                    w = MyCheckBox(is_checked=data.get(key, val[1]), handler=self.update,
                                   max_width=val[-1])
                # print(key)
                self.widgets[key] = w
                layout.addWidget(w, val[-1])
            # print('---- currentLine - end construct')
            # layout.setSpacing(0)
            layout.addStretch(1)
            layout.setSpacing(10)
            layout.setContentsMargins(5, 2, 5, 2)
            self.main_layout = layout
            self.setLayout(layout)
            self.setMinimumHeight(20)
            # self.setMaximumWidth(550)
            # self.setMinimumHeight(50)
            # self.update()

        def update(self):
            # if DEBUG: print('---- currentLine update', self.data["Name"])
            # print(str(self))
            # self.autoUpdate.stop()
            # print('Here1')
            changed_item = {}
            for key, val in SCAN_LINE_DICT.items():
                if val[0] == 'LE': # check here for proper param line
                    if self.data[key] != self.widgets[key].text():
                        changed_item[key] = (self.data[key], self.widgets[key].text())
                        self.data[key] = self.widgets[key].text()
                elif val[0] in ['MChB']:
                    # print(self.widgets)
                    # print(self.widgets[key])
                    if self.data[key] != self.widgets[key].isChecked():
                        changed_item[key] = (self.data[key], self.widgets[key].isChecked())
                        self.data[key] = self.widgets[key].isChecked()
            if DEBUG: print('Scan line data changed: line:', self.data['Name'], changed_item)

        def textEdited(self):
            # print('TextEdited')
            self.update()

        def updateParamMenu(self):
            self.param_menu.clear()
            self.generateParamMenu(self.param_menu,self.parent.getAvailableScanParams())

        def generateParamMenu(self,parent,data):
            if type(data) == type([]):
                # submenu is str
                for submenu in data:
                    act = parent.addAction(submenu)
                    act.triggered.connect(self.getNewScanParam)
            else:
                # type is dictionary, submenu is key
                for submenu in data:
                    m = parent.addMenu(submenu)
                    self.generateParamMenu(m, data[submenu])

        def getNewScanParam(self):
            print('getNewScanParam')
            a = self.sender()
            name = []
            # not straightforward way to extrack names from all nesting of scan parameter menu
            name.append(a.text())
            while 1:
                a = a.parent()
                if a.title() == '':
                    break
                name.insert(0, a.title())
            print("new param name",name)
            self.data["Param"] = name
            self.widgets['Param'].setText(self.data["Param"][-1])
            self.widgets["Param"].setToolTip('->'.join(self.data["Param"]))

        def constructData(self):
            # print(self.data)
            return self.data

        def getSequence(self):
            try:
                if self.data["Line"].startswith("%"):
                    seq = list(eval(self.data["Line"][1:]))
                else:
                    seq = [float(s.strip()) for s in self.data["Line"].split()]
            except:
                self.widgets["Line"].setStyleSheet("QLineEdit { background-color : red}")
                return None
            self.widgets["Line"].setStyleSheet("QLineEdit { background-color : white}")
            return {'Param':self.data["Param"],"Name":self.data["Name"],"Seq":seq}

        def getName(self):
            return self.data["Name"]

        def setValue(self,value):
            self.widgets["Value"].setText(value)

    def __init__(self,globals={},signals=None,parent=None,data={}):
        """Creates empty container, function load will be called while loading config in parent"""
        # print("globals",globals)
        self.globals = globals
        self.parent = parent
        self.data = data
        self.lines = []
        super().__init__()
        self.initUI()

    def initUI(self):
        main_widget = QWidget()
        layout = QVBoxLayout()
        top_layout = QHBoxLayout()

        top_layout.addWidget(QLabel('Scan parameters'))
        add_level_btn = MyPushButton(name='Add level', handler=self.addParam)
        top_layout.addWidget(add_level_btn)

        layout.addLayout(top_layout)

        for param in self.data:
            w = self.Line(parent=self,data=param)
            self.lines.append(w)
            layout.addWidget(w)
        self.main_layout = layout
        self.main_layout.addStretch(1)
        main_widget.setLayout(layout)
        main_widget.setMaximumWidth(1400)
        self.setWidgetResizable(True)
        self.setWidget(main_widget)
        self.setMinimumHeight(300)
        self.setMinimumWidth(550)
        # print('after')

    @property
    def current_full_depth(self):
        return max([0]+[d["Depth"] for d in self.data])

    def addParam(self):
        self.data = self.constructData()
        # print(self.data)
        current_total_depth = self.current_full_depth
        # print([str(i) for i in range(current_total_depth+2)])
        new_param_depth, ok_pressed = QInputDialog.getItem(self, "Choose",
                                                          "Param depth:", [str(i) for i in range(current_total_depth+2)],
                                                          0, False)
        new_param_depth = int(new_param_depth)
        if ok_pressed:
            w = self.Line(parent=self, data={"Depth": new_param_depth})
            for i,param in enumerate(self.data):
                if new_param_depth == param["Depth"]:
                    self.lines.insert(i, w)
                    self.main_layout.insertWidget(i+1, w)
                    return
            self.lines.insert(len(self.data), w)
            self.main_layout.insertWidget(len(self.data)+1, w)

    def delete(self, line):
        self.main_layout.removeWidget(line)
        line.deleteLater()
        self.lines.remove(line)
        # self.save()
        return

    def constructData(self):
        # print(self.lines)
        return [w.constructData() for w in self.lines]

    def getAvailableScanParams(self):
        # if DEBUG: print("globals in scanParams",self.globals)
        return self.globals.get("available_scan_params",[])

    def constructScanSequence(self):
        active_params_data = {}
        status = True
        for scan_param in self.lines:
            if scan_param.data["On"]:
                param_data = scan_param.getSequence()
                if param_data == None:
                    QMessageBox.about(self, "ERROR", "BAD PARAM LINE")
                    status = False
                    break
                else:
                    depth = scan_param.data["Depth"]
                    if depth not in active_params_data:
                        active_params_data[depth] = []
                    active_params_data[depth].append(param_data)
        if not status:
            print("BAAD")
            QMessageBox.about(self, "ERROR", "BAD PARAMs LINE")
            return None
        else:
            # print('active_scan_params', active_params_data)
            if not list(active_params_data.keys()) == list(range(max(active_params_data.keys())+1)):
                QMessageBox.about(self, "ERROR", "NOT SEQUENTIAL SCAN PARAMS")
                return None
            return active_params_data

    # def updateCurrentParamValue(self):  #new-old
    #     # print(self.globals["scan_running_data"]["new_main_params"])
    #     # print(self.globals["scan_running_data"]["new_low_params"])
    #     params = self.globals["scan_running_data"]["new_main_params"] + self.globals["scan_running_data"]["new_low_params"]
    #     for param in params:
    #         for w in self.lines:
    #             if w.getName() == param["Name"]:
    #                 w.setValue(str(param["Value"]))

    def updateCurrentParamValue(self):
        # print(self.globals["scan_running_data"]["new_main_params"])
        # print(self.globals["scan_running_data"]["new_low_params"])
        params = list(self.globals["scan_params"]["main"].keys()) + list(self.globals["scan_params"]["low"].keys())
        for param in params:
            for w in self.lines:
                if w.getName() == param:
                    w.setValue(str(self.globals["scan_running_table"].loc[self.globals["scan_running_data"]["current_meas_number"],param]))



    @property
    def full_nesting(self):
        return len(self.all_params_list) - 1

    def updateIndexes(self,start=False): # put to scanner
        print('updateIndexes')
        """update current_indexes and return last updated index number to construct params_to_send
        if returned -1 then scan should be finished
        checkLength  should be called before to construct self.active_params_list"""
        if start:
            self.current_indexs = [0] * len(self.active_params_list)
            scan_params_list = []
            for group in self.active_params_list:
                l = []
                for param in group:
                    param.current_value = param.param_list[0]
                    l.append(param.param_list.copy())
                scan_params_list.append(l)
            self.globals['active_params_list'] = scan_params_list
            # print(self.current_indexs)
            return len(self.current_indexs) - 1
        else:
            for i, group in enumerate(self.active_params_list):
                # compare current index with length of the first element in the group (length of all element is equal
                # and checked by checkLength
                if self.current_indexs[i] == len(group[0].param_list)-1:
                    # if scan in current group is finished
                    self.current_indexs[i] = 0
                    for param in group:
                        param.current_value = param.param_list[0]
                    continue
                # if in current group scan is not finished
                self.current_indexs[i] += 1
                for param in group:
                    param.current_value = param.param_list[self.current_indexs[i]]
                return i
            # if not yet returned, then scan is finished
            return "SCAN_FINISHED"

    def getParamsToSend(self):
        """construct params to send based on self.current_indexs
            usually called from scanner with new current_indexs so it's better to updateDisplayedCurrentValues"""
        self.gui.redrawCurrentValues()
        self.updateAdditionalName()
        params_to_send = {}
        for i,group in enumerate(self.active_params_list):
            for param in group:
                # param.name[0] is the subprogramm name
                if param.name[0] not in params_to_send:
                    params_to_send[param.name[0]] = {}
                # tuple(param.name[1:]) - path to set param back in param.name[0] subprogramm
                params_to_send[param.name[0]][tuple(param.name[1:])]=param.param_list[self.current_indexs[i]]
        # print(params_to_send)
        return params_to_send

    def updateActiveParameters(self):
        print('updateActiveParameters')
        self.active_params_list = [[param for param in group if param.is_active] for group in
                                   self.all_params_list]
        self.active_params_list = [group for group in self.active_params_list if group]
        # print(self.active_params_list)

    def checkLength(self):
        print('checkLength')
        """Here we construct self.active_params_list and check its members length"""
        self.updateActiveParameters()
        # print(self.active_params_list)
        for group in self.active_params_list:
            if len(group) == 1:
                continue
            else:
                if len(set([len(param.param_list) for param in group])) > 1:
                    QMessageBox.warning(None,
                                        'Message',
                                        "Not equal length of params in active group #%i"%(self.active_params_list.index(group)),
                                        QMessageBox.Yes)
                    return False
        return True

    def getSingleFolderName(self):
        print('getSingleFolderName')
        return ' '.join([param.short_name +'='+ str(param.param_list[self.current_indexs[0]]) for param in self.active_params_list[0]])

class ScannerWidget(QWidget):

    def __init__(self, globals={}, all_updates_methods=None, signals=None, parent=None,config_file=None):
        super(ScannerWidget, self).__init__()

        self.cycleTimer = QTimer()
        self.cycleTimer.setInterval(1000)
        self.cycleTimer.timeout.connect(self.cycleFinished)

        self.DelayedMeasurementProcessingTimer = QTimer()
        self.DelayedMeasurementProcessingTimer.setInterval(200)
        self.DelayedMeasurementProcessingTimer.timeout.connect(self.startDelayedMeasurementProcessing)
        self.parent = parent
        self.globals = globals
        self.signals = signals
        self.config_file = config_file
        self.all_updates_methods = all_updates_methods  # needed to apply changes while scanning
        self.meas_folder_data = {}
        self.scan_params_data = {}
        self.scan_data = {}

        self.useful_functions = []
        for key in dir(function_lib):
            if not key.startswith("__") and key not in ["np"]:
                # print(key)
                self.useful_functions.append(key)
        self.load()
        self.fit_function_name = self.scan_data["fit_function_name"]
        self.updateFunctions()
        self.meas_windows_counter = -1
        self.low_scan_finished = False
        self.initUI()
        self.scan_running_data = {"scan_interrupted": False,
                                  "shots_per_point": self.scan_data["n_shots"],
                                  "on_scan": False,
                                  "current_meas_number": 0,
                                  "day_folder": self.folder_widget.getDayFolder(),
                                  "current_folder": None  # to be defined in the scan
                                  }
        self.delayed_scan_start = False
        if self.fit_function_name:
            self.fit_function = self.__dict__[self.fit_function_name]
        else:
            self.fit_function = None
        if self.signals:
            self.signals.singleScanFinished.connect(self.cycleFinished)

        self.on_scan = False

    def initUI(self):
        self.menuBar = QMenuBar(self)
        fileMenu = self.menuBar.addMenu('&File')
        save = QAction('&Save', self)
        save.triggered.connect(self.saveClicked)
        fileMenu.addAction(save)

        main_layout = QVBoxLayout()
        # subprogramms
        self.folder_widget = MeasurementFolderClass(parent=self, globals=self.globals,
                                                    signals=self.signals, data=self.meas_folder_data)
        main_layout.addWidget(self.folder_widget)

        self.scan_params_widget = ScanParameters(parent=self, globals=self.globals, signals=self.signals,
                                          data = self.scan_params_data)
        main_layout.addWidget(self.scan_params_widget)

        scan_layout = QHBoxLayout()

        scan_layout.addWidget(QLabel("Threshold"))
        self.threshold_line = MyLineEdit(name=self.scan_data.get("threshold","1"), max_width=300)
        scan_layout.addWidget(self.threshold_line)

        scan_layout.addWidget(QLabel("fit_params"))
        self.fit_params_line = MyLineEdit(name=", ".join(self.scan_data["fit_params"]),max_width=300)
        scan_layout.addWidget(self.fit_params_line)
        self.fit_func_box = MyComboBox(items=self.useful_functions,current_text=self.fit_function_name,
                                       current_text_changed_handler=self.fitFunctionChanged)
        scan_layout.addWidget(self.fit_func_box)
        self.update_func_btn = MyPushButton(name="Update functions",handler=self.updateFunctions)
        scan_layout.addWidget(self.update_func_btn)
        scan_layout.addStretch(1)
        self.add_points_widget = MyCheckBox(is_checked=self.scan_data["add_points"],handler=self.addPointsChanged)
        scan_layout.addWidget(self.add_points_widget)
        scan_layout.addWidget(QLabel("add points to folder"))
        self.n_shots_widget = MyIntBox(value=self.scan_data["n_shots"], validator=QIntValidator(1, 99),
                                       text_edited_handler=self.nShotsChanged,
                                       text_changed_handler=self.nShotsChanged, max_width=40)
        scan_layout.addWidget(self.n_shots_widget)
        scan_layout.addWidget(QLabel("Shots"))

        self.stop_btn = MyPushButton(name="Stop",handler=self.stopBtnPressed)
        scan_layout.addWidget(self.stop_btn)

        self.scan_btn = MyPushButton(name="New scan",handler=self.scanBtnPressed)
        scan_layout.addWidget(self.scan_btn)
        main_layout.addLayout(scan_layout)

        self.setLayout(main_layout)
        self.setMinimumWidth(600)
        # self.add_points_flag = False    # whether add points if meas_folder exists or not
        # self.notes = ''     # textfield to save notes
        # self.current_meas_number = 0
        # self.on_scan = False
        # self.scan_interrupted = False
        # self.number_of_shots = 5        # per parameter to average
        # self.current_shot_number = -1
        # self.single_meas_folder = ''    # folder with pictures
        # self.loadConfig()
        # self.progressBar = QProgressBar(self)

        # self.initUI()


        # self.signals.scanCycleFinished.connect(self.cycleFinished)
        # # add variable to global namespace
        # self.updateGlobals()

    def saveClicked(self):
        if DEBUG: print('save scanner')
        self.meas_folder_data = self.folder_widget.constructData()
        self.scan_params_data = self.scan_params_widget.constructData()
        with open(self.config_file, 'r') as f:
            if DEBUG: print('config_load_before_saving')
            all_config = json.load(f)
        config = all_config['Scanner']
        for key in config:
            config[key] = self.__dict__[key]
        with open(self.config_file, 'w') as f:
            if DEBUG: print('config_save')
            json.dump(all_config, f)

    def load(self):
        if DEBUG: print('--scanner - load')
        with open(self.config_file, 'r') as f:
            if DEBUG: print('config_load')
            all_config = json.load(f)
        self.__dict__.update(all_config['Scanner'])  # here one should upload current_scheme and available_channels

    def loadConfig(self):
        print('loadConfigScanner from ', os.path.join(data_directory, scanner_config_file))
        try:
            with open(os.path.join(data_directory, scanner_config_file), 'r') as f:
                self.config = json.load(f)
        except json.decoder.JSONDecodeError:
            print('ERROR in reading ', scanner_config_file)
            print('Default configuration will be loaded')
            self.scan_params.load()
            self.meas_folder1.load()
            self.config = {}
            return EMPTY_CONFIG_FILE
        for key in self.config:
            self.__dict__[key] = self.config[key]
        self.scan_params.load(self.config[scan_params_str])
        self.meas_folder1.load(self.config[scan_folder_data_str])
        print('Done loading in scanner')

    def saveConfig(self,changed_key=None,changed_value=None):
        print('saveConfig scanner')
        if changed_key: # to specify what in config to update
            # print('Changed Value',changed_value)
            self.config[changed_key] =changed_value if changed_value!=None else self.__dict__[changed_key]
        try:
            with open(os.path.join(data_directory, scanner_config_file), 'r') as f:
                old_config = json.load(f)
        except json.decoder.JSONDecodeError:
            old_config = {}
        with open(os.path.join(data_directory, scanner_config_file), 'w') as f:
            try:
                json.dump(self.config,f)
            except: # find what error does it raise when cannot dump
                json.dump(old_config, f)
                QMessageBox.warning(None, 'Message', "can not dump config to json, old version will be saved",
                                    QMessageBox.Ok)
        # maybe introduce here updateGlobals() call

    def fitFunctionChanged(self, new_value):
        self.fit_function_name = new_value
        self.scan_data["fit_function_name"] = self.fit_function_name
        if self.fit_function_name:
            self.fit_function = self.__dict__[self.fit_function_name]

    def updateFunctions(self):
        importlib.reload(function_lib)
        self.useful_functions = []
        for key in dir(function_lib):
            if not key.startswith("__") and key not in ["np"]:
                # print(key)
                self.useful_functions.append(key)
                self.__dict__[key] = function_lib.__dict__[key]
        # print(function_lib.__dict__)

    def addPointsChanged(self, new_value):
        print('addPointsChanged')
        self.scan_data["n_shots"] = new_value
        print("add_point?",self.scan_data["n_shots"])
        # self.saveConfig('add_points_flag')

    def nShotsChanged(self):
        print('numberOfShotsChanged')
        new_value = self.n_shots_widget.getValue()
        self.scan_data["n_shots"] = new_value
        print("n_shots",self.scan_data["n_shots"])
        # self.globals['number_of_shots'] = new_value
        # self.saveConfig('number_of_shots')

    def stopBtnPressed(self):
        print('stopBtnPressed')
        if self.scan_running_data["on_scan"]:
            self.stopScan(stop_btn_text='Continue', is_scan_interrupted=True)
        elif self.scan_running_data["scan_interrupted"]: # to continue previously statred scan
            self.startScan()
            print('Scan restarted')

    def scanBtnPressed(self):
        print('scanBtnPressed')
        if not self.on_scan:        # then scan should be started
            # construct param dictionary of form {param,short_name,param_list}
            scan_sequence = self.scan_params_widget.constructScanSequence()
            print("scan_sequence",scan_sequence)
            if scan_sequence == "None":
                return # do not start scan

            self.scan_running_params = {"low": {d["Name"]: d["Param"] for d in scan_sequence[0]},
                                   "main": {d["Name"]: d["Param"] for i in sorted(scan_sequence)[1:] for d in
                                            scan_sequence[i]}}
            # construct scan_running_table - later it will be a pandas DataFrame
            scan_running_table = []
            columns = []
            for level in sorted(scan_sequence):
                p_vals = []
                for param in scan_sequence[level]:
                    columns.insert(0, param["Name"])
                    p_vals.insert(0, param["Seq"])
                new_pvals = list(zip(*p_vals))
                if level == 0:
                    old_pvals = deepcopy(new_pvals)
                else:
                    temp_pvals = []
                    for n_pval in new_pvals:
                        for o_pval in old_pvals:
                            temp_pvals.append(list(n_pval) + list(o_pval))
                    old_pvals = temp_pvals
            columns.append("shot_n")
            for l in old_pvals:
                for i in range(self.scan_data["n_shots"]):
                    scan_running_table.append(list(l) + [i])
            self.scan_running_table = pd.DataFrame(scan_running_table, columns=columns,dtype=float)
            self.scan_running_data = {"scan_interrupted": False,
                                      "shots_per_point": self.scan_data["n_shots"],
                                      "on_scan": False, # set True when it will really start
                                      "current_meas_number": 0,
                                      "day_folder": self.folder_widget.getDayFolder(),
                                      "current_folder": None,  # folder for current measurements
                                      "folder_to_save": None,  # folder to save data (since image procesing starts after
                                                               # cycle finished current_folder may change but image should be saved to previous folder
                                      }
            self.updateCurrentFolder()
            self.scan_running_data["folder_to_save"] = self.scan_running_data["current_folder"]
            os.mkdir(os.path.join(self.scan_running_data["day_folder"],
                                                 self.scan_running_data["current_folder"]))
            self.globals["scan_running_table"] = self.scan_running_table
            self.globals["scan_running_data"] = self.scan_running_data
            self.globals["scan_params"] = self.scan_running_params
            print("scan_params", self.scan_running_params)
            print("scan_running_data", self.scan_running_data)
            print("scan_running_table")
            print(self.scan_running_table)


            self.scan_data["fit_params"] = [s.strip() for s in self.fit_params_line.text().split(",")]
            self.scan_data["threshold"] = self.threshold_line.text().strip()
            self.launchMeasurementWindow()
            print('SCAN STARTED at ', datetime.datetime.now().time())
            self.startScan()
            return

    def launchMeasurementWindow(self,n_start=0):
        self.meas_windows_counter +=1
        window = MeasurementWindow(parent=self, globals=self.globals, signals=self.signals,
                                   window_n=self.meas_windows_counter,n_start=n_start,y_params=self.scan_data["fit_params"],
                                   threshold=self.scan_data["threshold"])
        window.windowed = 2
        window.show()

    def updateCurrentFolder(self):
        self.folder_widget.newBtnPressed()
        folder = self.folder_widget.getMeasFolderName().strip()
        f = folder + " " + ' '.join(["%s=%s" % (param,self.scan_running_table.loc[self.scan_running_data["current_meas_number"],param]) for param in self.scan_running_params["main"]])
        self.scan_running_data["current_folder"] = f.strip()

    def writeMeasConfig(self):
        """This function saves configuration (i.e. position of ROI in image) to file in current_meas_folder"""
        fname = self.globals['current_measurement_folder'] + '/' + meas_config_file
        meas_config_data = {}
        if 'image_lower_left_corner' in self.globals: # ROI position
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
        """Not used now. Was written to start in thread and delay creation of first folder name to image_stack """
        time.sleep(0.7)
        self.globals['image_stack'].append(self.globals['current_data_folder'] + '/' + '-1_0.png')

    def updateSingleMeasFolder(self):
        print('updateSingleMeasFolder')
        self.single_meas_folder = self.scan_params.getSingleFolderName() + single_folder_suffix
        self.globals['current_data_folder']= self.globals['current_measurement_folder'].strip() + '/' + self.single_meas_folder.strip()
        # os.makedirs(self.globals['current_data_folder'], exist_ok=True)
        if not os.path.isdir(self.globals['current_data_folder']): # if there no such folder
            os.mkdir(self.globals['current_data_folder'])        # create new folder
        print('Current folder for images: ',self.globals['current_data_folder'])
        self.updateGlobals()

    def updateGlobals(self):
        self.globals['single_meas_folder'] = self.single_meas_folder
        # self.globals['meas_folder'] = self.meas_folder
        self.globals['on_scan'] = self.on_scan
        self.globals['current_shot_number'] = self.current_shot_number
        self.globals['number_of_shots'] = self.number_of_shots
        # print('Globals: ',self.globals)

    def cycleFinished(self, t_finish=None):
        # print(self.globals)
        """called when cycle is finished"""
        # self.cycleTimer.stop() # from self-test
        if self.globals and "scan_running_data" in self.globals and self.globals["scan_running_data"][
                    "on_scan"] and not self.scan_running_data["on_scan"]:
            return # if scan is on but from another scanner
        if not self.scan_running_data["on_scan"]:
            self.signals.scanCycleFinished.emit(-1,t_finish)
            if self.delayed_scan_start: # if programm waits for scan beginninng
                self.delayed_scan_start = False
                self.scan_running_data["on_scan"] = True
                self.signals.scanStarted.emit()
            return
        self.DelayedMeasurementProcessingTimer.start()
        # self.startDelayedMeasurementProcessing() # test if this is the reason
        finished_shot = self.scan_running_data["current_meas_number"]
        new_shot = finished_shot+1
        self.scan_running_data["folder_to_save"] = self.scan_running_data["current_folder"] # updates folder to save
        self.signals.scanCycleFinished.emit(finished_shot,t_finish)
        print(finished_shot, "measurement finished")
        self.scan_running_data["current_meas_number"] = new_shot
        if finished_shot == len(self.scan_running_table)-1: #last measurement was made
            print("SCAN FINISHED")
            self.signals.scanFinished.emit()
            self.low_scan_finished = True
            # print(self.globals["scan_running_table"])
            self.stopScan(stop_btn_text='Stop', is_scan_interrupted=False)
            table_folder = os.path.join(self.scan_running_data["day_folder"], "DataTables")
            try:
                os.mkdir(table_folder)
            except FileExistsError:
                pass
            self.globals["scan_running_table"].to_csv(os.path.join(table_folder,self.scan_running_data["current_folder"])+".csv")
            return
        if self.scan_running_table.loc[new_shot,"shot_n"] == 0:
            low_scan_finished = False
            for param in self.globals["scan_params"]["main"]:
                if self.scan_running_table.loc[new_shot,param] != self.scan_running_table.loc[finished_shot,param]:
                    low_scan_finished = True
            if low_scan_finished:
                print("LOW SCAN FINISHED")
                self.low_scan_finished = True
                print(self.scan_running_table)
                self.updateCurrentFolder()
                os.mkdir(os.path.join(self.scan_running_data["day_folder"],
                                      self.scan_running_data["current_folder"]))
                self.launchMeasurementWindow(n_start = self.scan_running_data["current_meas_number"])
            all_params = {**self.globals["scan_params"]["main"],
                          **self.globals["scan_params"]["low"]}.keys()
            print("New shot", self.scan_running_table.loc[new_shot, all_params])
            self.scan_params_widget.updateCurrentParamValue()
            self.signals.updateFromScanner.emit()
        # self.cycleTimer.start()

    def startDelayedMeasurementProcessing(self):
        self.DelayedMeasurementProcessingTimer.stop()
        if self.low_scan_finished:
            finish_flag = True
            self.low_scan_finished = False
        else:
            finish_flag=False
        self.signals.updateMeasurementPlot.emit(self.meas_windows_counter,self.scan_running_data["current_meas_number"],finish_flag)

    def stopScan(self,stop_btn_text='Stop',is_scan_interrupted=False,**argd):
        print('stopScan')
        self.cycleTimer.stop()
        self.signals.scanFinished.emit() # can be used to set valuues as they were before scan
        self.scan_running_data["on_scan"] = False
        self.scan_running_data["scan_interrupted"] = is_scan_interrupted
        self.globals["scan_running_data"].update({"on_scan":False})
        self.stop_btn.setText(stop_btn_text)
        self.scan_btn.setText('New scan')
        # self.scan_interrupted = is_scan_interrupted

    def startScan(self, **argd):
        self.stop_btn.setText('Stop')
        self.scan_btn.setText('On scan!')
        self.scan_params_widget.updateCurrentParamValue()
        self.signals.updateFromScanner.emit()
        self.delayed_scan_start = True # start scan when previous cycle is finished
        # self.signals.scanStarted.emit()
        # self.cycleTimer.start()

    def notesChanged(self):
        print('notesChanged')
        self.notes = self.sender().toPlainText()
        # print(repr(self.notes))
        self.saveConfig('notes')

class MeasurementWindow(QDialog):
    class MyMplCanvas(FigureCanvas):
        """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""

        def __init__(self, parent=None, width=10, height=6, dpi=100,x_label="time",y_label="N atoms",title=""):
            self.fig = Figure(figsize=(width, height), dpi=dpi)
            self.axes = self.fig.add_subplot(111)
            self.title = title
            self.axes.set_title(title)
            self.parent = parent
            self.fit_text = None
            self.x_label = x_label
            self.y_label = y_label
            self.plot_line = None
            FigureCanvas.__init__(self, self.fig)
            self.setParent(parent)

            FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)
            FigureCanvas.updateGeometry(self)

        def compute_initial_figure(self, xs, yss):
            # for ys in yss:
            #     self.axes.plot(xs, ys, '.r')
            dx = np.max(xs) - np.min(xs)
            self.x_lims = (np.min(xs)-0.1*dx,np.max(xs)+0.1*dx)

        def update_figure(self,xs,yss,params):
            # Build a list of 4 random integers between 0 and 10 (both inclusive)
            self.axes.cla()
            for i in range(len(yss)):
                # print(yss[i])
                self.axes.plot(xs, yss[i], '.', label=params[i],markersize=2)
            self.axes.set_xlim(*self.x_lims)
            self.axes.set_ylim(bottom=0)
            self.axes.set_xlabel(self.x_label)
            self.axes.set_ylabel(self.y_label)
            self.axes.legend()
            self.draw()

        def update_figure_new(self,all_data,median_data):
            # Build a list of 4 random integers between 0 and 10 (both inclusive)
            self.axes.cla()
            self.axes.set_title(self.title)
            self.axes.plot(all_data,'.', markersize=3)
            self.axes.legend(all_data.columns)
            self.axes.plot(median_data,'o',mfc='None')
            # for i in range(len(yss)):
            #     # print(yss[i])
            #     self.axes.plot(xs, yss[i], '.', label=params[i],markersize=2)
            self.axes.set_xlim(*self.x_lims)
            if len(median_data) == 0:
                y_up_lim = 1
            else:
                y_up_lim = np.max(np.max(median_data))*1.2
            self.axes.set_ylim(0,y_up_lim)
            self.axes.set_xlabel(self.x_label)
            self.axes.set_ylabel(self.y_label)
            self.draw()

        def update_figure_new2(self,all_data,mean_data,std_data,mask_data):
            # print("In plot, n=", len(all_data))
            # Build a list of 4 random integers between 0 and 10 (both inclusive)
            self.axes.cla()
            self.axes.set_title(self.title)
            p = self.axes.plot(all_data[mask_data],'.', markersize=3)
            self.axes.plot(all_data[mask_data==False], '*r', markersize=2)
            self.axes.legend(all_data.columns)
            for i,param in enumerate(mean_data.columns):
                self.axes.errorbar(mean_data.index,mean_data[param],yerr=std_data[param],fmt='o',mfc='None',color=p[i]._color)
            # for i in range(len(yss)):
            #     # print(yss[i])
            #     self.axes.plot(xs, yss[i], '.', label=params[i],markersize=2)
            self.axes.set_xlim(*self.x_lims)
            if len(mean_data) == 0:
                y_up_lim = 1
            else:
                y_up_lim = np.max(np.max(mean_data))*1.2
            try:
                self.axes.set_ylim(0,y_up_lim)
            except ValueError:
                print("bad yup_lim",y_up_lim)
            self.axes.set_xlabel(self.x_label)
            self.axes.set_ylabel(self.y_label)
            self.draw()

        def addCureveToCurrentPlot(self,xs,ys, s=""):
            if self.plot_line == None:
                self.plot_line = self.axes.plot(xs, ys)[0]
            else:
                self.plot_line.set_data(xs,ys)
            if s != "":
                if not self.fit_text:
                    self.fit_text = self.axes.text(0.05, 0.2, s,
                                                   horizontalalignment='left',
                                                   verticalalignment='center',
                                                   transform=self.axes.transAxes)
                else:
                    self.fit_text.set_text(s)
            self.draw()

    def __init__(self, parent=None, signals=None, globals=None, window_n=0,y_params=['Wr_x1'],n_start=0,
                 threshold="1"):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.parent = parent
        self.globals = globals
        self.signals = signals
        self.window_n = window_n
        self.n_start = n_start
        self.finished = False
        self.figure_file_name = None
        try:
            self.threshold = float(threshold)
        except ValueError:
            self.threshold = None
        self.p0_change_timer = QTimer()
        self.p0_change_timer.setInterval(1000)
        self.p0_change_timer.timeout.connect(self.p0LineChanged)
        self.setWindowTitle("Measurement %i"%self.window_n)

        self.x_param = list(self.globals["scan_params"]["low"].keys())[0]
        print("x_param", self.x_param)
        self.xs = self.parent.globals["scan_running_table"][self.n_start:][self.parent.globals["scan_running_table"]["shot_n"]!=0][self.x_param]

        self.y_params = y_params
        self.yss = []
        for param in self.y_params:
            self.yss.append(np.zeros_like(self.xs)+0.1)

        self.main_layout = QVBoxLayout()
        self.menu_layout = QHBoxLayout()
        self.save_btn = MyPushButton(name="Save",handler=self.saveClicked)
        self.menu_layout.addWidget(self.save_btn)
        self.save_as_btn = MyPushButton(name="Save as",handler=self.saveAsClicked)
        self.menu_layout.addWidget(self.save_as_btn)
        self.fit_func_box = MyComboBox(items=["None"] + self.parent.useful_functions,current_text=self.parent.fit_function_name,
                                       current_text_changed_handler=self.fitFunctionChanged)
        self.menu_layout.addWidget(self.fit_func_box)
        self.p0_line = MyLineEdit(name="p0 line",text_edited_handler=self.p0_change_timer.start)
        self.menu_layout.addWidget(self.p0_line)
        self.main_layout.addLayout(self.menu_layout)
        self.plot_widget = self.MyMplCanvas(parent=self,x_label=self.x_param,y_label=str(self.y_params),title=self.globals["scan_running_data"]["current_folder"])
        self.plot_widget.compute_initial_figure(self.xs,self.yss)

        self.main_layout.addWidget(self.plot_widget)
        self.setLayout(self.main_layout)
        self.show()

        if self.signals:
            self.signals.updateMeasurementPlot.connect(self.updatePlot)

    def saveClicked(self):
        if self.figure_file_name:
            self.saveFigure(self.figure_file_name)

    def saveAsClicked(self):
        if self.figure_file_name:
            filet = str(QFileDialog.getSaveFileName(self, caption="Select Directory", directory=os.path.dirname(self.figure_file_name)))
            print(filet)
            file,status = filet.strip("()").split(",")
            file = file[1:-1]
            if file:
                self.saveFigure(file)

    def fitFunctionChanged(self,new_fit_func_name):
        self.fit_function_name = new_fit_func_name
        print(self.fit_function_name)
        if self.fit_function_name == "None":
            self.fit_function = None
        elif self.fit_function_name:
            self.fit_function = self.parent.__dict__[self.fit_function_name]
            print(self.fit_function)
        if self.figure_file_name: # equivalent to finished
            self.drawFitMean()

    def p0LineChanged(self):
        self.p0_change_timer.stop()
        print(self.p0_line.text())
        self.drawFitMean(new_p0=True)

    def saveFigure(self,f_name):
        print("Plot will be saved at ", f_name)
        self.plot_widget.fig.savefig(f_name)

    def updatePlot(self,window_n,current_shot,finished=False):
        # print("UpdatePlot", current_shot, " finished=",finished)
        if self.window_n != window_n:
            return
        data = self.parent.globals["scan_running_table"][self.n_start:current_shot]
        plot_params = [param for param in self.y_params if param in data.columns]
        if not len(plot_params): # if number of params to plot is 0
            print("NO GOOD DATA")
            return
        self.all_data_to_plot = data[[self.x_param]+plot_params].set_index(self.x_param)
        # print("all_data_to_plot",self.all_data_to_plot)
        if self.threshold != None:
            mask0 = self.all_data_to_plot[plot_params[0]] > self.threshold # construct a mask of good data based om first plot_param
        else:
            mask0 = self.all_data_to_plot[plot_params[0]] == self.all_data_to_plot[plot_params[0]]
        # print(mask0)
        # if not sum(mask0):
        #     print("NO GOOD DATA")
        #     return
        median_data = self.all_data_to_plot[mask0].groupby(self.x_param).median()
        std_data0 = self.all_data_to_plot[mask0].groupby(self.x_param).std()
        # print(std_data0)
        std_data0 = std_data0.fillna(1)
        # print("std0 after",std_data0)
        mask1 = (abs((self.all_data_to_plot - median_data) / std_data0) < 2)
        # print("mask1",mask1)
        mean_data = self.all_data_to_plot[mask1].groupby(self.x_param).mean()
        # print("mean_data",mean_data)
        std_data1 = self.all_data_to_plot[mask1].groupby(self.x_param).std()
        # print(std_data1)
        std_data1 = std_data1.fillna(1)
        # print("std1 after",std_data1)
        # self.median_data_to_plot = self.all_data_to_plot[self.data_ok_mask].groupby(self.x_param).median()
        # self.median_data_error = self.all_data_to_plot.groupby(self.x_param).std()
        # self.plot_widget.update_figure_new(self.all_data_to_plot, self.median_data_to_plot)
        self.plot_widget.update_figure_new2(self.all_data_to_plot,mean_data=mean_data,std_data=std_data1,mask_data=mask1)
        # print("after plot")
        if finished:
            self.mean_data= mean_data
            self.std_data = std_data1
            self.fit_function = self.parent.fit_function
            self.fit_function_name = self.parent.fit_function_name
            if self.fit_function:
                self.drawFitMean()
                fig_folder = os.path.join(self.parent.scan_running_data["day_folder"],"Figures")
                try:
                    os.mkdir(fig_folder)
                except FileExistsError:
                    pass

                self.figure_file_name = os.path.join(fig_folder,self.parent.scan_running_data["folder_to_save"]+".png")
                self.saveFigure(self.figure_file_name)

    def drawFit(self,new_p0=False):
        if self.fit_function == None:
            self.plot_widget.addCureveToCurrentPlot([], [], "")
            return
        xs = np.array(self.median_data_to_plot.index)
        xs_plot = np.linspace(min(self.median_data_to_plot.index),max(self.median_data_to_plot.index),101)
        yss = []
        for param in self.median_data_to_plot.columns[:1]:
            ys = np.array(self.median_data_to_plot[param])
            ys_err = np.array(self.median_data_error[param])
            if not new_p0:
                p0 = function_lib._p0_dict[self.fit_function_name](xs, ys)
                self.p0_line.setText(",".join(["%.1f"%x for x in p0]))
            else:
                p0 = [float(x.strip()) for x in self.p0_line.text().split(',')]
            try:
                popt_T, pcov_T = curve_fit(self.fit_function, xs, ys, sigma=ys_err, p0=p0)
            except RuntimeError as e:
                print(e)
                popt_T = p0
                pcov_T = np.zeros((len(popt_T), len(popt_T)))
            except Exception as e:  # just in case (if not enough points, ...)
                print(e)
                popt_T = p0
                pcov_T = np.zeros((len(popt_T), len(popt_T)))
            perr_T = np.sqrt(np.diag(pcov_T))
            try:
                s = self.fit_function.__name__ + ' fit:\n' + usfuncs.construct_fit_description(self.fit_function,
                                                                                      list(zip(popt_T, perr_T)), sep='+-')
                self.plot_widget.addCureveToCurrentPlot(xs_plot,self.fit_function(xs_plot,*popt_T), s)
                print(s)
            except Exception as e:
                print(e)

    def drawFitMean(self,new_p0=False):
        if self.fit_function == None:
            self.plot_widget.addCureveToCurrentPlot([], [], "")
            return
        xs = np.array(self.mean_data.index)
        xs_plot = np.linspace(min(self.mean_data.index),max(self.mean_data.index),101)
        yss = []
        for param in self.mean_data.columns[:1]:
            ys = np.array(self.mean_data[param])
            ys_err = np.array(self.std_data[param])
            if not new_p0:
                p0 = function_lib._p0_dict[self.fit_function_name](xs, ys)
                self.p0_line.setText(",".join(["%.1f"%x for x in p0]))
            else:
                p0 = [float(x.strip()) for x in self.p0_line.text().split(',')]
            try:
                popt_T, pcov_T = curve_fit(self.fit_function, xs, ys, sigma=ys_err, p0=p0)
            except RuntimeError as e:
                print(e)
                popt_T = p0
                pcov_T = np.zeros((len(popt_T), len(popt_T)))
            except Exception as e:  # just in case (if not enough points, ...)
                print(e)
                popt_T = p0
                pcov_T = np.zeros((len(popt_T), len(popt_T)))
            perr_T = np.sqrt(np.diag(pcov_T))
            try:
                s = self.fit_function.__name__ + ' fit:\n' + usfuncs.construct_fit_description(self.fit_function,
                                                                                      list(zip(popt_T, perr_T)), sep='+-')
                self.plot_widget.addCureveToCurrentPlot(xs_plot,self.fit_function(xs_plot,*popt_T), s)
                print(s)
            except Exception as e:
                print(e)


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    mainWindow = ScannerWidget(config_file="config.json")
    mainWindow.show()
    sys.exit(app.exec_())

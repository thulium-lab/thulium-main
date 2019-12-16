import os, time, datetime, json, shutil, traceback, sys,re
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

from Scanner_classic import MeasurementFolderClass

import function_lib
from function_lib import *

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

DEBUG = True

NAME_IN_SCAN_PARAMS = 'ScannerLock'

SCAN_LINE_DICT = OrderedDict([
    ("Del",['MPB','Del',40]),
    ('Param',['CB',['Empty'],60]),
    ('Name', ['LE', '', 120]),
    ('Level',['LB',"main",40]),
    ('Df',['LE','',100]),
    ("Sigma",["LE","",100]),
    ('Line',['LE','',300]),
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
                    if key in ["Df","Sigma"]:
                        layout.addWidget(QLabel(key.lower()))
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
            return {'Param':self.data["Param"],"Name":self.data["Name"],"Seq":seq,"df":self.data["Df"],"sigma":self.data["Sigma"]}

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
        add_level_btn = MyPushButton(name='Add param', handler=self.addParam)
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

    def addParam(self):
        self.data = self.constructData()
        # print(self.data)
        # print([str(i) for i in range(current_total_depth+2)])
        new_param_level, ok_pressed = QInputDialog.getItem(self, "Choose",
                                                          "Param level:", ["main","addit"],
                                                          0, False)
        if ok_pressed:
            w = self.Line(parent=self, data={"Level": new_param_level})
            for i,param in enumerate(self.data):
                if new_param_level == param["Level"]:
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
        active_params_data = {"main":{},"additional":[]}
        status = True
        for scan_param in self.lines:
            if scan_param.data["On"]:
                param_data = scan_param.getSequence()
                if param_data == None:
                    QMessageBox.about(self, "ERROR", "BAD PARAM LINE")
                    status = False
                    break
                else:
                    level = scan_param.data["Level"]
                    if level == "main":
                        if active_params_data["main"] != {}:
                            QMessageBox.about(self, "ERROR", "TOO MANY MAIN PARAMS")
                            status = False
                            break
                        active_params_data["main"] = deepcopy(param_data)
                    else:
                        active_params_data["additional"].append(param_data)
        if not status:
            print("BAAD")
            # QMessageBox.about(self, "ERROR", "BAD PARAMs LINE")
            return None
        else:
            # print('active_scan_params', active_params_data)
            return active_params_data

    def updateCurrentParamValue(self):
        # print(self.globals["scan_running_data"]["new_main_params"])
        # print(self.globals["scan_running_data"]["new_low_params"])
        params = list(self.globals["scan_running_params"]["main"].keys())
        for param in params:
            for w in self.lines:
                if w.getName() == param:
                    print(param)
                    w.setValue(str(self.globals["scan_running_table"].loc[self.globals["scan_running_data"]["current_meas_number"],param]))


class ScannerLockWidget(QWidget):
    def __init__(self, globals={}, all_updates_methods=None, signals=None, parent=None,config_file=None):
        super(ScannerLockWidget, self).__init__()

        self.cycleTimer = QTimer()
        self.cycleTimer.setInterval(1000)
        self.cycleTimer.timeout.connect(self.cycleFinished)

        self.DelayedMeasurementPlottingTimer = QTimer()
        self.DelayedMeasurementPlottingTimer.setInterval(200)
        self.DelayedMeasurementPlottingTimer.timeout.connect(self.startDelayedMeasurementPlotting)
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
        # self.fit_function_name = self.scan_data["fit_function_name"]
        # self.updateFunctions()
        self.meas_windows_counter = -1
        self.low_scan_finished = False
        self.initUI()
        self.scan_running_data = {"scan_interrupted": False,
                                  "on_scan": False,
                                  "current_meas_number": 0,
                                  "day_folder": self.folder_widget.getDayFolder(),
                                  "current_folder": None  # to be defined in the scan
                                  }
        # if self.fit_function_name:
        #     self.fit_function = self.__dict__[self.fit_function_name]
        # else:
        #     self.fit_function = None
        if self.signals:
            self.signals.singleScanFinished.connect(self.cycleFinished)

        self.on_scan = False
        # print("scannerLOck loaded")

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

        lock_param_layout = QHBoxLayout()
        self.freq_param_line = QPushButton(self.scan_data["freq_param"][-1])
        self.freq_param_menu = QMenu(self.freq_param_line)
        self.freq_param_menu.aboutToShow.connect(self.updateFreqParamMenu)
        self.freq_param_line.setMenu(self.freq_param_menu)
        self.freq_param_line.setToolTip('->'.join(self.scan_data["freq_param"]))
        self.freq_param_line.setMaximumWidth(100)
        lock_param_layout.addWidget(self.freq_param_line)

        lock_param_layout.addWidget(QLabel("f0"))

        self.f0_line = MyDoubleBox(validator=QDoubleValidator(0,500000,6),value=self.scan_data["f0"],max_width=100,
                                   text_changed_handler=self.lockParamsChanged)
        lock_param_layout.addWidget(self.f0_line)

        lock_param_layout.addWidget(QLabel("algorithm0"))
        self.algorithm0_line = MyLineEdit(name=self.scan_data["algorithm0"], max_width=60,
                                          text_changed_handler=self.lockParamsChanged)
        lock_param_layout.addWidget(self.algorithm0_line)

        lock_param_layout.addWidget(QLabel("algorithm1"))
        self.algorithm1_line = MyComboBox(items=self.scan_data["algorithm1_list"], current_text=self.scan_data["algorithm1"],
                                          max_width=60,current_text_changed_handler=self.lockParamsChanged)
        lock_param_layout.addWidget(self.algorithm1_line)

        lock_param_layout.addWidget(QLabel("n_cycles"))
        self.n_cycles_line = MyIntBox(value=self.scan_data["n_cycles"],validator=QIntValidator(-1,99999),
                                      text_changed_handler=self.lockParamsChanged)
        lock_param_layout.addWidget(self.n_cycles_line)

        lock_param_layout.addWidget(QLabel("feedback_gain"))
        self.feedback_gain_line = MyDoubleBox(value=self.scan_data["feedback_gain"],validator=QDoubleValidator(-9.9,9.9,1),
                                              text_changed_handler=self.lockParamsChanged)
        lock_param_layout.addWidget(self.feedback_gain_line)

        lock_param_layout.addWidget(QLabel("eta="))
        self.eta_formula_line = MyLineEdit(name=self.scan_data["eta_formula"],max_width=100,
                                           text_changed_handler=self.lockParamsChanged)
        lock_param_layout.addWidget(self.eta_formula_line)

        main_layout.addLayout(lock_param_layout)

        self.scan_params_widget = ScanParameters(parent=self, globals=self.globals, signals=self.signals,
                                          data = self.scan_params_data)
        main_layout.addWidget(self.scan_params_widget)

        scan_layout = QHBoxLayout()
        # scan_layout.addWidget(QLabel("fit_params"))
        # self.fit_params_line = MyLineEdit(name=", ".join(self.scan_data["fit_params"]),max_width=300)
        # scan_layout.addWidget(self.fit_params_line)
        # self.fit_func_box = MyComboBox(items=self.useful_functions,current_text=self.fit_function_name,
        #                                current_text_changed_handler=self.fitFunctionChanged)
        # scan_layout.addWidget(self.fit_func_box)
        # self.update_func_btn = MyPushButton(name="Update functions",handler=self.updateFunctions)
        # scan_layout.addWidget(self.update_func_btn)
        # scan_layout.addStretch(1)
        # self.add_points_widget = MyCheckBox(is_checked=self.scan_data["add_points"],handler=self.addPointsChanged)
        # scan_layout.addWidget(self.add_points_widget)
        # scan_layout.addWidget(QLabel("add points to folder"))
        # self.n_shots_widget = MyIntBox(value=self.scan_data["n_shots"], validator=QIntValidator(1, 99),
        #                                text_edited_handler=self.nShotsChanged,
        #                                text_changed_handler=self.nShotsChanged, max_width=40)
        # scan_layout.addWidget(self.n_shots_widget)
        # scan_layout.addWidget(QLabel("Shots"))

        self.stop_btn = MyPushButton(name="Stop",handler=self.stopBtnPressed)
        scan_layout.addWidget(self.stop_btn)

        self.scan_btn = MyPushButton(name="New scan",handler=self.scanBtnPressed)
        scan_layout.addWidget(self.scan_btn)
        main_layout.addLayout(scan_layout)

        self.setLayout(main_layout)
        self.setMinimumWidth(600)

    def lockParamsChanged(self):
        for key in self.scan_data:
            if key in ["freq_param","algorithm1_list","fit_params","fit_function_name","add_points","algorithm0_seq",
                       "algorithm1_seq","eta_dependencies"]:
                continue
            self.scan_data[key] = self.__dict__[key+"_line"].getValue()

    def saveClicked(self):
        if DEBUG: print('save ScannerLock')
        self.meas_folder_data = self.folder_widget.constructData()
        self.scan_params_data = self.scan_params_widget.constructData()
        with open(self.config_file, 'r') as f:
            if DEBUG: print('config_load_before_saving')
            all_config = json.load(f)
        config = all_config[NAME_IN_SCAN_PARAMS]
        for key in config:
            config[key] = self.__dict__[key]
        with open(self.config_file, 'w') as f:
            if DEBUG: print('config_save')
            json.dump(all_config, f)

    def load(self):
        if DEBUG: print('--scannerLock - load')
        with open(self.config_file, 'r') as f:
            if DEBUG: print('config_load')
            all_config = json.load(f)
        self.__dict__.update(all_config[NAME_IN_SCAN_PARAMS])  # here one should upload current_scheme and available_channels

    def updateFreqParamMenu(self):
        self.freq_param_menu.clear()
        self.generateParamMenu(self.freq_param_menu, self.globals.get("available_scan_params",[]))

    def generateParamMenu(self, parent, data):
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
        print("new param name", name)
        self.scan_data["freq_param"] = name
        self.freq_param_line.setText(self.scan_data["freq_param"][-1])
        self.freq_param_line.setToolTip('->'.join(self.scan_data["freq_param"]))

    def updateCurrentFolder(self):
        self.folder_widget.newBtnPressed()
        folder = self.folder_widget.getMeasFolderName().strip()
        self.scan_running_data["current_folder"] = folder

    def scanBtnPressed(self):
        print('scanBtnPressed')
        if not self.on_scan:        # then start should be started

            self.scan_params = self.scan_params_widget.constructScanSequence()
            print("scan_params", self.scan_params)
            if self.scan_params == "None":
                return  # do not start scan

            # self.scan_params = {"main": {scan_sequence["main"]["Name"]: scan_sequence["main"]["Param"]},
            #                             "additional": {d["Name"]: d["Param"] for d in scan_sequence["additional"]}}

            self.scan_running_data = {"scan_interrupted": False,
                                      "on_scan": True,
                                      "current_meas_number": 0,
                                      "day_folder": self.folder_widget.getDayFolder(),
                                      "current_folder": None,  # folder for current measurements
                                      "folder_to_save": None,  # folder to save data (since image procesing starts after
                                      # cycle finished current_folder may change but image should be saved to previous folder
                                      }


            self.scan_running_data["f0s"] = [[self.f0_line.getValue() + self.calculateDf(self.scan_params["main"]["Name"], self.scan_params["main"]["df"], value)
                                              for value in self.scan_params["main"]["Seq"]]]
            self.scan_running_data["sigmas"] = [self.calculateSigma(self.scan_params["main"]["Name"], self.scan_params["main"]["sigma"], value)
                                                for value in self.scan_params["main"]["Seq"]]

            self.scan_data["n_cycles"] = self.n_cycles_line.getValue() # number of cycles to do. If -1 than run contineously
            self.scan_data["algorithm0_seq"] = [d for d in self.algorithm0_line.text().strip() if d != " "]
            print("sequence algorithm  ", self.scan_data["algorithm0_seq"])

            self.scan_data["feedback_gain"] = self.feedback_gain_line.getValue()
            print("1", self.scan_running_data)

            self.scan_data["eta_dependencies"] =  re.findall(r'[a-zA-Z]\w+', self.eta_formula_line.getValue())
            print("eta dependencies", self.scan_data["eta_dependencies"])

            if len(self.scan_running_data["sigmas"]) == 1: # only one parameter to lock to
                self.scan_data["algorithm1_seq"] = [0]
                print("parameters scan algorithm - single parameter")
            else:
                algorithm = self.algorithm1_line.getValue()  # should be a comboBox
                indexes = list(range(len(self.scan_running_data["sigmas"])))
                if algorithm == "up": # values are probed from start to end
                    self.scan_data["algorithm1_seq"] = indexes[:]
                elif algorithm == "down": # values are probed first from start to end and then from end to start
                    self.scan_data["algorithm1_seq"] = indexes[::-1]
                else: # random sampling of values
                    self.scan_data["algorithm1_seq"] = indexes[:]
                    np.random.shuffle(self.scan_data["algorithm1_seq"])
                # self.scan_data["algorithm1"] = self.algorithm1_line.getValue()  # should be a comboBox
                print("parameters scan algorithm ", algorithm, self.scan_data["algorithm1_seq"])


            self.scan_running_data["n0"] = 0 # number of sideband interrogation
            self.scan_running_data["n1"] = 0 # number of parameter interrogation
            self.scan_running_data["n_cycle"] = 0 # cycle number
            self.scan_running_table_columns = ["n_cycle",self.scan_params["main"]["Name"], *[d["Name"] for d in self.scan_params["additional"]], "f0", "sigma", "slope", "eta","f_clock"]
            self.scan_running_table = pd.DataFrame(columns=self.scan_running_table_columns)
            self.calculateCurrentStep()
            self.scan_running_table["T0"]=0
            self.updateCurrentFolder()
            self.scan_running_data["folder_to_save"] = self.scan_running_data["current_folder"]
            os.mkdir(os.path.join(self.scan_running_data["day_folder"],
                                  self.scan_running_data["current_folder"]))
            self.globals["scan_running_table"] = self.scan_running_table
            self.globals["scan_running_data"] = self.scan_running_data
            self.globals["scan_running_params"] = {"low": {"f0": self.scan_data["freq_param"]},
             "main": {self.scan_params["main"]["Name"]:self.scan_params["main"]["Param"],
                      **{d["Name"]: d["Param"] for d in self.scan_params["additional"]}}}
            # self.globals["scan_running_table"]["T0"]=0
            self.startScan()
            self.launchMeasurementWindow()
            print("scan data",self.scan_data)
            print("scan_running_table",self.globals["scan_running_table"])
            print("scan_running_data",self.globals["scan_running_data"])
            print('Scan started at ', datetime.datetime.now().time())

            # for test
            return

    def startScan(self, **argd):
        self.stop_btn.setText('Stop')
        self.scan_btn.setText('On scan!')
        self.scan_params_widget.updateCurrentParamValue()
        # self.signals.updateFromScanner.emit()
        # self.signals.scanStarted.emit()
        self.cycleTimer.start()

    def calculateDf(self,name,df_formula,value):
        res = eval(df_formula.replace(name,str(value)))
        return res

    def calculateSigma(self,name,df_formula,value):
        res = eval(df_formula.replace(name,str(value)))
        return res

    def calculateCurrentStep(self):
        n_cycle = self.scan_running_data["n_cycle"]
        f0 = self.scan_running_data["f0s"][-1][self.scan_running_data["n1"]]
        sigma = self.scan_running_data["sigmas"][self.scan_running_data["n1"]]
        slope = self.scan_data["algorithm0_seq"][self.scan_running_data["n0"]]
        f_clock = f0 + (1 if slope=="+" else -1)*sigma/2
        main_param = self.scan_params["main"]["Seq"][self.scan_data["algorithm1_seq"][self.scan_running_data["n1"]]]
        additional_params = [d["Seq"][self.scan_data["algorithm1_seq"][self.scan_running_data["n1"]]] for d in self.scan_params["additional"]]
        data = [n_cycle,main_param,*additional_params,f0,sigma,slope,0,f_clock]
        self.globals["scan_running_table"] = self.globals["scan_running_table"].append(pd.Series(data,index=self.scan_running_table_columns),ignore_index=True)
        # self.globals["scan_running_table"] = self.scan_running_table

    def genProbeSignal(self):
        f_laser = self.f0_line.getValue()+2 + 0.2*self.scan_running_data["current_meas_number"]
        f_probe = self.globals["scan_running_table"]["f_clock"][self.scan_running_data["current_meas_number"]]
        sigma = self.globals["scan_running_table"]["sigma"][self.scan_running_data["current_meas_number"]]
        signal = np.exp(-2*(f_laser-f_probe)**2/(sigma**2))
        print(signal)
        print(self.globals["scan_running_table"].at[self.scan_running_data["current_meas_number"],"T0"])
        self.globals["scan_running_table"].ix[self.scan_running_data["current_meas_number"],"T0"]=signal
        print(self.globals["scan_running_table"].at[self.scan_running_data["current_meas_number"], "T0"])

    def cycleFinished(self, t_finish=None):
        # print(self.globals)
        """called when cycle is finished"""
        self.cycleTimer.stop() # from self-test
        if self.globals and "scan_running_data" in self.globals and self.globals["scan_running_data"][
                    "on_scan"] and not self.scan_running_data["on_scan"]:
            return # if scan is on but from another scanner
        if not self.scan_running_data["on_scan"]:
            # self.signals.scanCycleFinished.emit(-1)
            return
        self.genProbeSignal()
        self.calculateEta()
        print(self.scan_running_data["current_meas_number"], "cycle finished")
        print(self.globals["scan_running_table"])
        self.scan_running_data["current_meas_number"] += 1
        if self.scan_running_data["n0"] < len(self.scan_data["algorithm0_seq"]) - 1:  # sideband probs are not finished
            self.scan_running_data["n0"] += 1
        else:
            self.scan_running_data["n0"] = 0
            if self.scan_running_data["n1"] < len(self.scan_data["algorithm1_seq"]) - 1:  # parameters probs are not finished
                self.scan_running_data["n1"] += 1
            else:
                self.scan_running_data["n1"] = 0
                self.scan_running_data["n_cycle"] += 1
                self.calculateNewF0s()
                if self.scan_running_data["n_cycle"] == self.scan_data["n_cycles"]:
                    print("SCAN FINISHED")
                    # self.signals.scanFinished.emit()
                    self.stopScan(stop_btn_text='Stop', is_scan_interrupted=False)
                    table_folder = os.path.join(self.scan_running_data["day_folder"], "DataTables")
                    try:
                        os.mkdir(table_folder)
                    except FileExistsError:
                        pass
                    self.globals["scan_running_table"].to_csv(
                        os.path.join(table_folder, self.scan_running_data["current_folder"]) + ".csv")
                    return
        self.calculateCurrentStep()
        self.scan_params_widget.updateCurrentParamValue()
        # self.DelayedMeasurementPlottingTimer.start()
        self.startDelayedMeasurementPlotting()
        # self.signals.updateFromScanner.emit()
        # print(self.scan_data)
        self.cycleTimer.start()

    def calculateEta(self):
        eta_formula = self.eta_formula_line.getValue()
        for param in self.scan_data["eta_dependencies"]:
            eta_formula = eta_formula.replace(param,str(self.globals["scan_running_table"].loc[self.scan_running_data["current_meas_number"],param]))
        eta = eval(eta_formula)
        # print("eta=",eta)
        self.globals["scan_running_table"].ix[self.scan_running_data["current_meas_number"], "eta"] = eta

    def calculateNewF0s(self):
        main_param_name = self.scan_params["main"]["Name"]
        new_f0s = []
        for main_param_value in self.scan_params["main"]["Seq"]:
            # data from last sidebands measurement for paticular paramter value
            data = self.scan_running_table[self.scan_running_table[main_param_name] == main_param_value][-len(self.scan_data["algorithm0_seq"]):]
            # params_values = {}
            # eta_plus_formula = self.eta_formula_line.getValue()
            # eta_minus_formula = self.eta_formula_line.getValue()
            # for param in self.scan_data["eta_dependencies"]:
            #     eta_plus_formula = eta_plus_formula.replace(param,str(data[data["slope"] == "+"][param].mean()))
            #     eta_minus_formula = eta_minus_formula.replace(param, str(data[data["slope"] == "-"][param].mean()))
            eta_plus = data[data["slope"] == "+"]["eta"].mean()
            eta_minus = data[data["slope"] == "-"]["eta"].mean()
            # eta_plus = eval(eta_plus_formula)
            # eta_minus = eval(eta_minus_formula)
            # print("eta+, eta-", eta_plus, eta_minus)
            if pd.isna(eta_plus) or pd.isna(eta_minus): # one can not calculate error signal
                new_f0s.append(data["f0"].iloc[0])
            else:
                error = eta_plus - eta_minus
                print("Error", error)
                f0 = data["f0"].iloc[0] + error*self.scan_data["feedback_gain"]*data["sigma"].iloc[0]/2
                new_f0s.append(f0)

        self.scan_running_data["f0s"].append(new_f0s)
        return

    def stopScan(self,stop_btn_text='Stop',is_scan_interrupted=False,**argd):
        print('stopScan')
        self.cycleTimer.stop()
        # self.signals.scanFinished.emit() # can be used to set valuues as they were before scan
        self.scan_running_data["on_scan"] = False
        self.scan_running_data["scan_interrupted"] = is_scan_interrupted
        self.globals["scan_running_data"].update({"on_scan":False})
        self.stop_btn.setText(stop_btn_text)
        self.scan_btn.setText('New scan')
        # self.scan_interrupted = is_scan_interrupted

    def stopBtnPressed(self):
        print('stopBtnPressed')
        if self.scan_running_data["on_scan"]:
            self.stopScan(stop_btn_text='Continue', is_scan_interrupted=True)
        elif self.scan_running_data["scan_interrupted"]: # to continue previously statred scan
            self.startScan()
            print('Scan restarted')

    def launchMeasurementWindow(self,n_start=0):
        self.meas_windows_counter +=1
        window = MeasurementWindow(parent=self, globals=self.globals, signals=self.signals,
                                   window_n=self.meas_windows_counter,n_start=n_start,y_params=self.scan_data["fit_params"])
        window.windowed = 2
        window.show()

    def startDelayedMeasurementPlotting(self):
        self.DelayedMeasurementPlottingTimer.stop()
        self.signals.updateMeasurementPlot.emit(self.meas_windows_counter,self.scan_running_data["current_meas_number"],False)

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
            self.color_bank = ["g","r","b","m"]

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
            # self.axes.legend(all_data.columns)
            # self.axes.plot(median_data,'o',mfc='None')
            # for i in range(len(yss)):
            #     # print(yss[i])
            #     self.axes.plot(xs, yss[i], '.', label=params[i],markersize=2)
            # self.axes.set_xlim(*self.x_lims)
            # if len(median_data) == 0:
            #     y_up_lim = 1
            # else:
            #     y_up_lim = np.max(np.max(median_data))*1.2
            # self.axes.set_ylim(0,y_up_lim)
            # self.axes.set_xlabel(self.x_label)
            # self.axes.set_ylabel(self.y_label)
            self.draw()

        def update_plot_eta(self,data,main_param_name):
            self.axes.cla()
            main_param_values = list(set(data[main_param_name]))
            d = data[data["slope"]=="+"]
            colors_plus = [self.color_bank[main_param_values.index(x)] for x in d[main_param_name]]
            self.axes.scatter(list(d.index),d["eta"],color=colors_plus,marker="+")
            d = data[data["slope"] == "-"]
            colors_minus = [self.color_bank[main_param_values.index(x)] for x in d[main_param_name]]
            self.axes.scatter(list(d.index), d["eta"], color=colors_minus, marker="_")
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

    def __init__(self, parent=None, signals=None, globals=None, window_n=0,y_params=['Wr_x1'],n_start=0):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.parent = parent
        self.globals = globals
        self.signals = signals
        self.window_n = window_n
        self.n_start = n_start
        self.finished = False
        self.figure_file_name = None
        # self.p0_change_timer = QTimer()
        # self.p0_change_timer.setInterval(1000)
        # self.p0_change_timer.timeout.connect(self.p0LineChanged)
        self.setWindowTitle("Measurement %i"%self.window_n)



        self.main_layout = QVBoxLayout()
        self.menu_layout = QHBoxLayout()
        self.save_btn = MyPushButton(name="Save",handler=self.saveClicked)
        self.menu_layout.addWidget(self.save_btn)
        # self.save_as_btn = MyPushButton(name="Save as",handler=self.saveAsClicked)
        # self.menu_layout.addWidget(self.save_as_btn)
        self.main_layout.addLayout(self.menu_layout)
        freq_plot_layout = QHBoxLayout()
        self.freq_plot_widget = self.MyMplCanvas(parent=self,x_label="cycle, n",y_label="freq",title=self.globals["scan_running_data"]["current_folder"])
        freq_plot_layout.addWidget(self.freq_plot_widget)
        # self.plot_widget.compute_initial_figure(self.xs,self.yss)
        self.adev_plot_widget = self.MyMplCanvas(parent=self,x_label="cycle, n",y_label="adev",title=self.globals["scan_running_data"]["current_folder"])
        freq_plot_layout.addWidget(self.adev_plot_widget)
        self.main_layout.addLayout(freq_plot_layout)
        self.eta_plot_widget = self.MyMplCanvas(parent=self,x_label="shot, n",y_label="eta",title="")
        self.main_layout.addWidget(self.eta_plot_widget)
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

    def saveFigure(self,f_name):
        print("Plot will be saved at ", f_name)
        self.plot_widget.fig.savefig(f_name)

    def updatePlot(self,window_n,current_shot,finished=False):
        # print("UpdatePlot", current_shot, " finished=",finished)
        if self.window_n != window_n:
            return
        freq_data = self.globals["scan_running_table"][["n_cycle",self.parent.scan_params["main"]["Name"],"f0"]]
        freq_data = freq_data.pivot_table(index="n_cycle",columns=self.parent.scan_params["main"]["Name"],values="f0")
        self.freq_plot_widget.update_figure_new(freq_data,[])
        eta_data = self.globals["scan_running_table"][[self.parent.scan_params["main"]["Name"],"slope","eta"]]
        self.eta_plot_widget.update_plot_eta(eta_data,main_param_name=self.parent.scan_params["main"]["Name"])
        # data = self.parent.globals["scan_running_table"][self.n_start:current_shot]
        # self.all_data_to_plot = data[[self.x_param]+[param for param in self.y_params if param in data.columns]].set_index(self.x_param)
        # self.median_data_to_plot = self.all_data_to_plot.groupby(self.x_param).median()
        # self.median_data_error = self.all_data_to_plot.groupby(self.x_param).std()
        # self.plot_widget.update_figure_new(self.all_data_to_plot, self.median_data_to_plot)
        # if finished:
        #     self.fit_function = self.parent.fit_function
        #     self.fit_function_name = self.parent.fit_function_name
        #     if self.fit_function:
        #         self.drawFit()
        #         fig_folder = os.path.join(self.parent.scan_running_data["day_folder"],"Figures")
        #         try:
        #             os.mkdir(fig_folder)
        #         except FileExistsError:
        #             pass
        #
        #         self.figure_file_name = os.path.join(fig_folder,self.parent.scan_running_data["folder_to_save"]+".png")
        #         self.saveFigure(self.figure_file_name)

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

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    mainWindow = ScannerLockWidget(config_file="config.json")
    mainWindow.show()
    sys.exit(app.exec_())
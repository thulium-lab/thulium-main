import os, time, datetime, json, shutil, traceback, sys
import numpy as np
from PyQt5.QtWidgets import (QApplication, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel, QPushButton, QWidget,
                             QSpinBox, QCheckBox, QMessageBox, QProgressBar)
from DigitalPulses.scanParameters import SingleScanParameter, AllScanParameters, MeasurementFolderClass

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

class Scanner(QWidget):

    def __init__(self, globals=None, all_updates_methods=None, signals=None, parent=None):
        super(Scanner, self).__init__()
        self.parent = parent
        self.globals = globals
        self.signals = signals
        self.all_updates_methods = all_updates_methods  # needed to apply changes while scanning
        # subprogramms
        self.scan_parameters = AllScanParameters(globals=globals,parent=self)
        self.meas_folder1 = MeasurementFolderClass(globals=globals,parent=self)

        self.add_points_flag = False    # whether add points if meas_folder exists or not
        self.notes = ''     # textfield to save notes
        self.current_meas_number = 0
        self.on_scan = False
        self.scan_interrupted = False
        self.number_of_shots = 5        # per parameter to average
        self.current_shot_number = -1
        self.single_meas_folder = ''    # folder with pictures
        self.loadConfig()
        self.progressBar = QProgressBar(self)

        self.initUI()
        self.setMinimumWidth(1000)

        self.signals.scanCycleFinished.connect(self.cycleFinished)
        # add variable to global namespace
        self.updateGlobals()

        # for tests (OLD)
        # self.timer = QTimer(self)
        # self.timer.setInterval(1000)
        # self.timer.timeout.connect(self.cycleFinished)

    def loadConfig(self):
        print('loadConfigScanner from ',os.path.join(data_directory, scanner_config_file))
        try:
            with open(os.path.join(data_directory, scanner_config_file), 'r') as f:
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
        hor3.addStretch(0.5)
        number_of_shots_box = QSpinBox()
        number_of_shots_box.setMinimum(0)
        number_of_shots_box.setMaximum(100)
        number_of_shots_box.setValue(self.number_of_shots)
        number_of_shots_box.valueChanged.connect(self.numberOfShotsChanged)
        hor3.addWidget(number_of_shots_box)

        hor3.addWidget(QLabel('Shots'))
        hor3.addStretch(0.5)

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

        self.progressBar.setMinimum(0)
        main_layout.addWidget(self.progressBar)

        console_text = '\n'.join([getsource(usfuncs.__dict__[item]).split(':')[0][4:] for item in dir(usfuncs) if item[0]!='_' and item not in ['np']])
        self.console = pyqtgraph.console.ConsoleWidget(namespace={'np':np,'usfuncs':usfuncs}, text=console_text)
        # self.console.ma
        main_layout.addWidget(self.console)
        # notes_box = QTextEdit(self.notes)
        # notes_box.textChanged.connect(self.notesChanged)
        # notes_box.setMaximumHeight(200)
        # main_layout.addWidget(notes_box)

        self.setLayout(main_layout)

    def addPointsChanged(self, new_value):
        print('addPointsChanged')
        self.add_points_flag = new_value
        self.saveConfig('add_points_flag')

    def numberOfShotsChanged(self, new_value):
        print('numberOfShotsChanged')
        self.number_of_shots = new_value
        self.globals['number_of_shots'] = new_value
        self.saveConfig('number_of_shots')

    def stopBtnPressed(self):
        print('stopBtnPressed')
        if self.on_scan:
            self.stopScan(stop_btn_text='Continue', is_scan_interrupted=True)
        elif self.scan_interrupted: # to continue previously statred scan
            self.startScan()
            print('Scan restarted')

    def scanBtnPressed(self):
        print('scanBtnPressed')
        if not self.on_scan:        # then start should be started
            # check equal length of params in each group
            is_ok = self.scan_parameters.checkLength()
            if not is_ok:
                return -1
            self.current_shot_number = -1
            changed_index = self.scan_parameters.updateIndexes(start=True)
            self.globals['current_measurement_folder'] = self.meas_folder1.day_folder.strip() + '/' + self.meas_folder1.name.strip()
            # if folder already exists and add_points_flag isn't risen
            if os.path.isdir(self.globals['current_measurement_folder']) and not self.add_points_flag:
                # remove all directory
                print('Removing directory')
                shutil.rmtree(self.globals['current_measurement_folder'])
                os.mkdir(self.globals['current_measurement_folder'])    # create new measurement folder
            elif not os.path.isdir(self.globals['current_measurement_folder']):
                os.mkdir(self.globals['current_measurement_folder'])    # create new measurement folder
            print('Data folder: ',self.globals['current_measurement_folder'])
            # self.globals['DAQ'].stop()
            # time.sleep(4)
            self.writeMeasConfig()
            self.updateParamAndSend(changed_index)
            self.updateSingleMeasFolder()
            self.startScan()
            # below are few tries with solving saving image bug
            # sthrd = threading.Thread(target=self.addFirstFolder)
            # sthrd.start()
            # self.globals['image_stack'].append(self.globals['current_data_folder'] + '/' + '0_0.png')
            print('Scan started at ',datetime.datetime.now().time())

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
        self.single_meas_folder = self.scan_parameters.getSingleFolderName()+single_folder_suffix
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

    def cycleFinished(self, number=None):
        """called when cycle is finished"""
        print(number, 'cycleFinished at',datetime.datetime.now().time())
        if not self.on_scan:
            return
        # add image_name for saving image
        # self.globals['image_stack'].append(
        #     self.globals['current_data_folder'] + '/' + '%i_0.png' % self.current_shot_number)
        # self.signals.imageProcessed.emit("%i %i" % (self.current_shot_number,self.scan_parameters.current_indexs[0]))
        if self.current_shot_number < self.number_of_shots - 1: # same shots to average
            self.current_shot_number += 1
            self.progressBar.setValue(self.scan_parameters.current_indexs[0] +
                                      self.current_shot_number / self.number_of_shots)
            self.globals['image_stack'].append(
                self.globals['current_data_folder'] + '/' + '%i_0.png' % self.current_shot_number)
            return 0

        self.current_shot_number = -1 # new parameter will be launched
        # self.globals['image_stack'].append(
        #     self.globals['current_data_folder'] + '/' + '%i_0.png' % self.current_shot_number)
        changed_index = self.scan_parameters.updateIndexes() # for nested scans
        # if changed_index != 0:
        #     self.signals.singleScanFinished.emit()
        if changed_index > 0:
            # we proceed to the next outer parameter
            self.signals.singleScanFinished.emit()
            self.scan_parameters.updateAdditionalName()     # update additional name
            self.meas_folder1.current_meas_number += 1      # increment meas folder number
            self.meas_folder1.gui.updateMeasFolder()
            # os.mkdir()    # create new measurement folder
            self.globals['current_measurement_folder'] = self.meas_folder1.day_folder.strip() + '/' + self.meas_folder1.name.strip()
            print(os.makedirs(self.globals['current_measurement_folder'], exist_ok=True))
            self.writeMeasConfig()

        self.updateParamAndSend(changed_index) # update parameter on scan

        if self.on_scan:
            self.updateSingleMeasFolder()
            self.globals['image_stack'].append(self.globals['current_data_folder'] + '/' + '-1_0.png')

    def updateParamAndSend(self,changed_index):
        """Updates scanning parameter and sends it to the module from which this parameter"""
        print('updateParamAndSend')
        # self.globals['DAQ'].stop()
        try:
            self.progressBar.setValue(self.scan_parameters.current_indexs[0]+
                                      self.current_shot_number/self.number_of_shots)
        except Exception as e:
            pass
        params_to_send = self.scan_parameters.getParamsToSend()
        print('Scanning parameters: ',params_to_send)
        # update parameters by calling update methods of subprogramm
        is_Ok = True    # now it's not used but may be later
        if self.all_updates_methods != None:
            for name, params in params_to_send.items():
                res_of_update = self.all_updates_methods[name](param_dict=params)
                if res_of_update == -1:
                    # if smth wrong
                    QMessageBox.warning(self, 'Message', "Couldn't change %s parameters\nScan is stopped"%(name), QMessageBox.Yes)
                    self.stopScan(stop_btn_text='Continue',is_scan_interrupted=True)
                    is_Ok = False
                    break

        # time.sleep(0.1)
        # self.globals['DAQ'].run()

        if changed_index == -1:
            self.stopScan(stop_btn_text='Fihished')

    def stopScan(self,stop_btn_text='Stop',is_scan_interrupted=False,**argd):
        print('stopScan')
        self.on_scan = False
        self.stop_btn.setText(stop_btn_text)
        self.scan_btn.setText('New scan')
        self.scan_interrupted = is_scan_interrupted


    def startScan(self,**argd):
        if self.scan_parameters.active_params_list:
            group = self.scan_parameters.active_params_list[0]
            if group:
                self.progressBar.setMaximum(len(group[0].param_list)-1)
        self.scan_interrupted = False
        self.stop_btn.setText('Stop')
        self.scan_btn.setText('On scan!')
        self.on_scan = True
        # print('scan_starteeeed')
        print(self.globals['active_params_list'])
        self.updateSingleMeasFolder()
        self.globals['image_stack'] = []
        self.globals['image_stack'].append(self.globals['current_data_folder'] + '/' + '-1_0.png')
        self.signals.scanStarted.emit()

    def notesChanged(self):
        print('notesChanged')
        self.notes = self.sender().toPlainText()
        # print(repr(self.notes))
        self.saveConfig('notes')



if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    mainWindow = Scanner()
    mainWindow.show()
    sys.exit(app.exec_())
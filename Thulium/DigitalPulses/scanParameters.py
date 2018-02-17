import os
import matplotlib
matplotlib.use('Qt5Agg',force=True)

from PyQt5.QtWidgets import (QApplication, QMenu, QGridLayout, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QWidget, QComboBox, QCheckBox, QFileDialog, QMessageBox,QTableWidget,
                             QTableWidgetItem,QHeaderView)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import QSize
import json
#import time
import re
from numpy import *
from itertools import chain
import sympy as sp
from sympy.parsing.sympy_parser import parse_expr

scan_params_str = 'scan_params'
data_directory = 'D:\!Data'
scan_folder_data_str = 'scan_folder_data'
SCAN_FINISHED = -1

class SingleScanParameter():
    is_active = False
    name = ('',)  # tuple of name i.e. ('pulse','1 stage cooling',..)
    short_name = ''
    nesting = 0  # indicate at which layer of nesting it is
    param_list = []
    current_index = 0
    current_value = 0

    def __init__(self, param_dict=None):
        """param_dict - dictionary of params from storage, if None - default attributes"""
        if type(param_dict) == type({}):
            for key, value in param_dict.items():
                try:
                    setattr(self, key, value)
                except AttributeError:
                    print('Error while loading key',key)
        elif param_dict:
            QMessageBox.warning(None, 'Message', "param_dict in SingelScanParamer is not a dictionary", QMessageBox.Ok)
        else:
            print('Creating default singleScanParameter')

    @property
    def length(self):
        """length of param_list without taking into account isActive"""
        return len(self.param_list)


class AllScanParameters():
    all_params_list = []
    active_params_list = [[]]
    current_indexs = []
    current_values = []

    @property
    def full_nesting(self):
        return len(self.all_params_list) - 1

    def __init__(self,globals=None,parent=None):
        """Creates empty container, function load will be called while loading config in parent"""
        self.globals = globals

    def addParameter(self, parameter):
        if parameter.nesting > self.full_nesting:
            self.all_params_list.append([])
        self.all_params_list[parameter.nesting].append(parameter)

    def load(self,parameters_dict_list=[]):
        print('load all scan parameters')
        assert type(parameters_dict_list)==type([]), 'parameters_dict_list is not a list of parameters'
        if parameters_dict_list == []:
            # if there no save parameters
            self.addParameter(SingleScanParameter())
            return 0
        for parameter_dict in parameters_dict_list:
            # print(parameter_dict)
            new_parameter = SingleScanParameter(parameter_dict)
            self.addParameter(new_parameter)
        self.updateActiveParameters()
        self.updateIndexes(start=True)
        self.updateAdditionalName()
        # print(self.active_params_list)

    def updateIndexes(self,start=False):
        print('updateIndexes')
        """update current_indexes and return last updated index number to construct params_to_send
        if returned -1 then scan should be finished
        checkLength  should be called before to construct self.active_params_list"""
        if start:
            self.current_indexs = [0] * len(self.active_params_list)
            for group in self.active_params_list:
                for param in group:
                    param.current_value = param.param_list[0]
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
            return SCAN_FINISHED

    def updateCurrentValues(self):
        # print('updateCurrentValues')
        # print(self.active_params_list)
        # print(self.current_indexs)
        for i,group in enumerate(self.active_params_list):
            for param in group:
                param.current_value = param.param_list[self.current_indexs[i]]

    def updateAdditionalName(self):
        # print('updateAdditionalName')
        # self.updateActiveParameters()
        # self.updateCurrentValues()
        res = ' '.join([param.short_name + '=' + str(int(param.current_value) if (param.current_value).is_integer() else param.current_value) for param in
                        list(chain.from_iterable(self.all_params_list)) if param.nesting > 0 and param.is_active])
        self.globals['additional_scan_param_name'] = res
        # print(res)

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

    class scanUI(QWidget):

        scan_grid_elems = {'menu': 0, 'short': 1, 'index': 2, 'line': 3,'is_active':4, 'current': 5, 'del': 6, 'add': 7}

        def __init__(self,data=None,parent=None):
            super().__init__()
            self.data=data
            self.parent=parent
            self.initUI()

        def initUI(self):
            layout = QVBoxLayout()
            top_layout = QHBoxLayout()

            top_layout.addWidget(QLabel('Scan parameters'))
            add_level_btn = QPushButton('Add level')
            add_level_btn.clicked.connect(self.addLevel)
            top_layout.addWidget(add_level_btn)

            layout.addLayout(top_layout)
            grid = QGridLayout()
            row = 1
            for i, param_level in enumerate(self.data.all_params_list):
                print(param_level)
                for j, param in enumerate(param_level):
                    param.nesting=i
                    ch_box = QCheckBox()
                    ch_box.setChecked(param.is_active)
                    ch_box.stateChanged.connect(self.isActiveChanged)
                    grid.addWidget(ch_box, row, self.scan_grid_elems['is_active'])

                    menu_btn = QPushButton(str(param.name) if len(param.name) == 0 else param.name[-1])
                    param_menu = QMenu(menu_btn)
                    param_menu.aboutToShow.connect(self.updateMenu)
                    # self.generateParamMenu(param_menu, self.all_scan_params) - not used now
                    menu_btn.setMenu(param_menu)
                    menu_btn.setToolTip('->'.join(param.name))
                    grid.addWidget(menu_btn, row, self.scan_grid_elems['menu'])

                    param_shortname = QLineEdit(param.short_name)
                    param_shortname.setMaximumWidth(50)
                    param_shortname.editingFinished.connect(self.paramShortNameChanged)
                    grid.addWidget(param_shortname, row, self.scan_grid_elems['short'])

                    grid.addWidget(QLabel(str(i)), row, self.scan_grid_elems['index'])

                    param_line = QLineEdit(' '.join([str(int(num) if (num).is_integer() else num) for num in param.param_list]))
                    param_line.editingFinished.connect(self.paramLineChanged)
                    grid.addWidget(param_line, row, self.scan_grid_elems['line'])

                    label = QLabel('-')
                    label.setMaximumWidth(30)
                    grid.addWidget(label, row, self.scan_grid_elems['current'])

                    if not (i == 0 and j == 0):
                        del_btn = QPushButton('Del')
                        del_btn.clicked.connect(self.delScanParam)
                        grid.addWidget(del_btn, row, self.scan_grid_elems['del'])
                    else:
                        grid.addWidget(QLabel(''), row, self.scan_grid_elems['del'])
                    add_btn = QPushButton('Add')
                    add_btn.clicked.connect(self.addScanParam)
                    grid.addWidget(add_btn, row, self.scan_grid_elems['add'])
                    row += 1

            # grid.addWidget(menu_btn)
            layout.addLayout(grid)
            self.grid = grid
            self.setLayout(layout)
            self.saveToConfig()
            print('after')

        def scanRedraw(self):
            QWidget().setLayout(self.layout())
            self.initUI()
            # self.saveConfig('scan_params')

        def addLevel(self):
            # do not update config because parameter is empty. It will be updated
            print('addLevel')
            new_param = SingleScanParameter()
            new_param.nesting = self.data.full_nesting + 1
            self.data.addParameter(new_param)
            self.scanRedraw()

        def isActiveChanged(self,new_value):
            print('isActiveChanged-scanParameters')
            changed_parameter = self.getChangedParameter()
            changed_parameter.is_active = new_value
            self.saveToConfig()

        def updateMenu(self):
            """updates dropout menu for particular scan parameter"""
            print('updateAllScanParams')
            # print(self.data.globals)
            self.sender().clear()
            self.generateParamMenu(self.sender(), self.data.globals[scan_params_str])

        def generateParamMenu(self, parent, data):
            """generates menu for parameters, parent - PushButton to which this menu will be attached, data - dictionary
            of available parameters"""
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
            """handles change in scan parameter (shoosing particular on from dropdown menu"""
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
            # par - which paramenter button is presed
            par = a.parent()
            changed_parameter = self.getChangedParameter(par)
            changed_parameter.name = tuple(name)
            # set name of the button only very last parameter name
            par.setText(name[-1])
            self.saveToConfig()

        def paramShortNameChanged(self):
            print('paramShortNameChanged')
            changed_parameter = self.getChangedParameter()
            changed_parameter.short_name = self.sender().text()
            self.saveToConfig()

        def paramLineChanged(self):
            print('paramLineChanged')
            s = self.sender().text()
            arr = [float(elem) for elem in re.findall('(-?\d+\.?\d*)', s)]
            changed_parameter = self.getChangedParameter()
            changed_parameter.param_list=arr
            self.saveToConfig()
            self.sender().setText(' '.join([str(int(num) if (num).is_integer() else num) for num in arr]))

        def delScanParam(self):
            print('delScanParam')
            changed_parameter = self.getChangedParameter()
            for param_group in self.data.all_params_list:
                if changed_parameter in param_group:
                    param_group.remove(changed_parameter)
                    if len(param_group) == 0:
                        self.data.all_params_list.remove(param_group)
            self.scanRedraw()
            self.saveToConfig()

        def addScanParam(self):
            print("addScanParam")
            changed_parameter = self.getChangedParameter()
            for param_group in self.data.all_params_list:
                if changed_parameter in param_group:
                    param_group.insert(param_group.index(changed_parameter)+1,SingleScanParameter())
            self.scanRedraw()

        def getChangedParameter(self,caller=None):
            """caller is needed for extracting changed parameter when parameter menu button is pressed"""
            if caller==None:
                caller = self.sender()
            print('getParamNumber')
            index = self.grid.indexOf(caller)
            row, column, cols, rows = self.grid.getItemPosition(index)
            return list(chain.from_iterable(self.data.all_params_list))[row - 1]

        def redrawCurrentValues(self):
            """only draws current values, they are updated in updateIndex"""
            # print('redrawCurrentValues')
            itter = 0
            for group in self.data.all_params_list:
                for param in group:
                    lbl = self.grid.itemAt(itter*len(self.scan_grid_elems) + self.scan_grid_elems['current']).widget()
                    if param.is_active:
                        num =param.current_value
                        lbl.setText(str(int(num) if (num).is_integer() else num))
                    else:
                        lbl.setText('-') # '-' - default value if parameter is not active
                    lbl.repaint()
                    itter +=1

        def saveToConfig(self):
            """simultaneousely update global parameter additional_scan_param_name"""
            print('saveToConfig')
            res = []
            self.data.updateActiveParameters()
            self.data.updateIndexes(start=True)
            self.data.updateAdditionalName()
            for param in list(chain.from_iterable(self.data.all_params_list)):
                res.append({key:getattr(param,key) for key in dir(param) if not callable(key) and not key.startswith('_')})
                # if param.nesting > 0 and param.is_active:
                #     additional_scan_param_name_arr.append(param.short_name +'=' +)
            self.parent.saveConfig(scan_params_str,changed_value=res)
            # print(json.dumps(res))



class MeasurementFolderClass():
    day_folder = ''
    current_type = None
    all_types = ['CL','FB','T', 'LT']
    other_params = ''
    name = ''
    current_meas_number = 0

    def __init__(self, globals=globals,parent=None):
        self.globals = globals
        # self.gui = self.folderUI(data=self,parent=parent)

    def load(self, param_dict=None):
        print('load measurement folder data')
        # print(param_dict)
        if param_dict:
            for key, value in param_dict.items():
                try:
                    setattr(self, key, value)
                except AttributeError:
                    print('Error in key=',key)

    class folderUI(QWidget):

        def __init__(self,data=None,parent=None):
            super().__init__()
            self.data=data
            self.parent=parent
            self.N_params=10
            self.initUI()

        def initUI(self):
            main_layout = QVBoxLayout()
            # main_layout.setSpacing(5)
            hor1 = QHBoxLayout()

            self.day_box = QLineEdit(os.path.basename(self.data.day_folder))
            hor1.addWidget(self.day_box)

            day_folder = QPushButton('Day')
            day_folder.clicked.connect(self.dayBtnPressed)
            hor1.addWidget(day_folder)

            hor1.addWidget(QLabel('Meas. type'))

            self.meas_type_box = QComboBox()
            self.meas_type_box.addItems(self.data.all_types)
            self.meas_type_box.setCurrentText(self.data.current_type)
            self.meas_type_box.currentTextChanged.connect(self.measTypeChanged)
            hor1.addWidget(self.meas_type_box)

            # hor1.addWidget(QLabel('other params'))
            #
            # other_params_box = QLineEdit(self.data.other_params)
            # other_params_box.editingFinished.connect(self.otherParamsChanged)
            # hor1.addWidget(other_params_box)

            main_layout.addLayout(hor1)

            self.param_table = QTableWidget(2,self.N_params)
            self.param_table.setVerticalHeaderLabels(['param','value'])
            self.param_table.setMaximumHeight(80)
            for i,s in enumerate(self.data.other_params.split()):
                if '=' not in s:
                    self.param_table.setItem(0, i, QTableWidgetItem(s))
                else:
                    self.param_table.setItem(0, i, QTableWidgetItem(s.split('=')[0]))
                    self.param_table.setItem(1, i, QTableWidgetItem(s.split('=')[1]))
            self.param_table.horizontalHeader().hide()
            # param_table.setItem(0,0,QTableWidgetItem('param'))
            # param_table.setItem(1, 0, QTableWidgetItem('value'))

            main_layout.addWidget(self.param_table)

            hor2 = QHBoxLayout()

            hor2.addWidget(QLabel('Folder'))

            # self.meas_folder_box = QLineEdit(self.data.name)
            # self.updateMeasFolder()
            # self.meas_folder_box.editingFinished.connect(self.measFolderChanged)
            self.meas_folder_box = QLabel(self.data.name)
            self.meas_folder_box.setStyleSheet("QLabel { background-color : white}")
            self.meas_folder_box.setFont(QFont("Arial",14))
            hor2.addWidget(self.meas_folder_box)
            hor2.addStretch(1)

            new_btn = QPushButton('New')
            new_btn.clicked.connect(self.newBtnPressed)
            hor2.addWidget(new_btn)

            open_btn = QPushButton('Open')
            open_btn.clicked.connect(self.openBtnPressed)
            hor2.addWidget(open_btn)

            main_layout.addLayout(hor2)

            self.setLayout(main_layout)

        def dayBtnPressed(self):
            print("dayBtnPressed")
            filet = str(QFileDialog.getExistingDirectory(self, "Select Directory", directory=data_directory))
            if filet:
                # print(filet)
                self.data.day_folder = filet
                self.day_box.setText(os.path.basename(self.data.day_folder))
                self.saveToConfig('day_folder')

        def measTypeChanged(self, new_value):
            print('measTypeChanged')
            self.data.current_type = new_value
            self.updateMeasFolder()
            self.saveToConfig('current_type')
            # print(self.data.current_type)

        # def otherParamsChanged(self):
        #     print('otherParamsChanged')
        #     self.data.other_params = self.sender().text()
        #     self.updateMeasFolder()
        #     self.saveToConfig('other_params')

        def updateMeasFolder(self):
            print('updateMeasFolder')
            params_str = ''
            for i in range(self.N_params):
                p_item = self.param_table.item(0,i)
                if p_item == None:
                    continue
                else:
                    params_str += ' ' + p_item.text()
                    v_item = self.param_table.item(1,i)
                    if v_item != None:
                        params_str += '=' + v_item.text()
            print(params_str)
            self.data.other_params = params_str.strip()
            self.data.name = "%02i %s %s" % (self.data.current_meas_number, self.data.current_type, self.data.other_params)

            if 'additional_scan_param_name' in self.data.globals:
                print('in update meas folder globals', self.data.globals['additional_scan_param_name'])
                self.data.name += ' ' + self.data.globals['additional_scan_param_name']
            print('-'*10, self.data.name)
            self.meas_folder_box.setText(self.data.name)
            self.meas_folder_box.repaint()

        def measFolderChanged(self):
            print('measFolderChanged')
            self.data.name = self.sender().text()
            # maybe update self.other params

        def newBtnPressed(self):
            print('newBtnPressed')
            drs = os.listdir(self.data.day_folder)
            last_index = 0
            for d in drs:
                n_folder = d.split(' ')[0]
                # if d[:2].isdigit():
                #     n = int(d[:2])
                if n_folder.isdigit():
                    n = int(n_folder)
                    print(n)
                    if n > last_index:
                        last_index = n
            self.data.current_meas_number = last_index + 1
            self.updateMeasFolder()
            self.saveToConfig('other_params')
            # self.

        def openBtnPressed(self):
            print('openBtnPressed')
            filet = str(QFileDialog.getExistingDirectory(None, "Select Directory",
                                                         directory=os.path.join(data_directory, self.data.day_folder)))
            if filet:
                print(filet)
                self.data.name = os.path.basename(filet)
                self.meas_folder_box.setText(self.data.name)
                # maybe update self.other params

        def saveToConfig(self,param=None):
            print('saveToConfig')
            res = {}
            for param in dir(self.data):
                if not callable(param) and not param.startswith('_') and param not in ['folderUI','globals','load','gui']:
                    # print(param)
                    res[param] = getattr(self.data,param)
            self.parent.saveConfig(scan_folder_data_str,changed_value=res)
            # print(res)
            print(json.dumps(res))

if __name__=='__main__':
    param_dict = {'is_active': True, 'name': ("Pulses", "2 stage cooling", "Green", "delay"), 'short_name': 'green_delay',
                  'nesting': 0,
                  'param_list': [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 6.22], 'current_index': 0, 'length':4}
    param_dict2 = {'is_active': False, 'name': ("Pulses", "2 stage cooling", "Green", "length"), 'short_name': 'green_length',
                  'nesting': 0,
                  'param_list': [11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 16.22], 'current_index': 0, 'length': 4}
    a = SingleScanParameter(param_dict)
    b = SingleScanParameter(param_dict2)

    print(a.name)
    print(b.name)
    print(a.length)

    globals = {'single_meas_folder': '', 'on_scan': False, 'scan_params': {'Pulses': {'1 stage cooling': {'Blue': ['delay', 'length'], 'nn': ['delay', 'length'], 'Green': ['delay', 'length'], 'Zeeman': ['delay', 'length'], 'group': ['delay', 'length'], 'pp': ['delay', 'length', 'l']}, '2 stage cooling': {'group': ['delay', 'length'], 'Green': ['delay', 'length'], 'Magnetic field': ['delay', 'length']}}}, 'Signals': {'Pulses': {}}, 'meas_folder': '00 LT a=10 b=3', 'current_shot_number': 0, 'Pulses': {'digital_channels': ['8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24', '25', '26', '27', '28', '29', '30'], 't_first': 1000.0, 'pulse_output': {'12': [(0, 1), (1100.0, 0), (1110.0, 0)], '11': [(0.0, 1), (1000.0, 0), (1110.0, 0)], '9': [(0.0, 1), (1000.0, 0), (1110.0, 0)], '10': [(0.0, 1), (1100.0, 0), (1110.0, 0)], 'A0': [(0, 0), (1110.0, 0)]}, 'analog_channels': ['A0', 'A1', 'A2', 'A3']}}
    all_scan = AllScanParameters(globals=globals)
    all_scan.addParameter(a)
    all_scan.addParameter(b)
    print(all_scan.all_params_list)
    # ["Pulses", "2 stage cooling", "Green", "delay"], [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 6.22]]


    import sys

    app = QApplication(sys.argv)
    mainWindow = all_scan.scanUI(all_scan)
    mainWindow.show()
    sys.exit(app.exec_())
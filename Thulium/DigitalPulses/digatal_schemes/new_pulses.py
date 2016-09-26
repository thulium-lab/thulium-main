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
                             QGridLayout, QVBoxLayout, QHBoxLayout, QSizePolicy,
                             QLabel, QLineEdit, QPushButton, QWidget, QComboBox,QRadioButton, QSpinBox, QCheckBox, QTabWidget, QFileDialog,QMessageBox, QDoubleSpinBox)
import pyqtgraph as pg

digital_pulses_folder = 'digatal_schemes'
config_scheme_file = 'config_scheme'
pulse_name_suffix = '.pls'









class pulseScheme():

    def __init__(self,parent=None,available_channels=[]):

        self.parent = parent
        self.available_channels = available_channels
        self.active_channels = {}
        self.all_schemes = {}
        self.config={}
        self.current_scheme = None
        self.current_groups = []
        self.output = {}
        self.load()
        self.gui = self.pulseSchemeQt(data=self)

    class pulseSchemeQt(QWidget):
        def __init__(self,data=None):
            self.data = data
            super().__init__()
            self.initUI()

        def initUI(self):
            self.main_box = QVBoxLayout(self)
            topbox = QHBoxLayout(self)

            topbox.addWidget(QLabel('Scheme'))

            self.scheme_combo_box = QComboBox()
            self.scheme_combo_box.addItems(self.data.all_schemes.keys())
            self.scheme_combo_box.setCurrentText(self.data.current_scheme)
            self.scheme_combo_box.currentTextChanged.connect(self.data.schemeChanged)
            topbox.addWidget(self.scheme_combo_box)

            self.add_group_button = QPushButton('Add group')
            self.add_group_button.clicked.connect(self.data.addGroup)
            topbox.addWidget(self.add_group_button)

            self.save_button = QPushButton('Save')
            self.save_button.clicked.connect(self.data.saveScheme)
            topbox.addWidget(self.save_button)

            self.save_as_button = QPushButton('Save as')
            self.save_as_button.clicked.connect(self.data.saveAsScheme)
            topbox.addWidget(self.save_as_button)

            self.main_box.addLayout(topbox)

            self.hor_box = QHBoxLayout(self)

            # self.channel_box = self.channelBoxWidget()
            # self.hor_box.addWidget(self.channel_box)
            # self.hor_box.addLayout(self.ch_grid)

            self.tabbox = QTabWidget()
            self.tabbox.setMovable(True)
            # self.current_scheme = self.scheme_combo_box.currentText()
            print('Current scheme: ', self.data.current_scheme)
            print(self.data.current_groups)
            for group in self.data.current_groups:
                print(self.tabbox)
                group.gui = group.pulseGroupQt(group)
                tab = group.gui
                # tab.updateReferences()
                try:
                    self.tabbox.addTab(tab, group.name)
                except Exception as e:
                    print(e)
                    raise e
                print('after')
            # tab1 = pulse_group(self)
            print('Now2')
            self.hor_box.addWidget(self.tabbox)
            self.main_box.addLayout(self.hor_box)
            # self.channels_vbox
            self.setLayout(self.main_box)

        def channelBoxWidget(self):
            print('construct channel_box')
            box = QWidget()
            grid = QGridLayout(box)
            # print('Now', self.ch_grid)
            # self.ch_grid = QGridLayout()
            for i, channel in enumerate(sorted(self.data.active_channels)):
                grid.addWidget(QLabel(channel), i, 0)
                alwais_on = QCheckBox()
                if self.data.active_channels[channel] == 'On':
                    alwais_on.setChecked(True)
                grid.addWidget(alwais_on, i, 1)
                alwais_off = QCheckBox()
                if self.data.active_channels[channel] == 'Off':
                    alwais_on.setChecked(True)
                grid.addWidget(alwais_off, i, 2)
            box.setLayout(grid)
            return box

        def schemeRedraw(self):
            print('schemeRedraw')
            self.tabbox.clear()
            # self.data.current_scheme = self.scheme_combo_box.currentText()
            print('Current scheme: ', self.data.current_scheme)
            print(self.data.current_groups)
            for group in self.data.current_groups:
                print(self.tabbox)
                tab = group.gui
                # tab.updateReferences()
                try:
                    self.tabbox.addTab(tab, group.name)
                except Exception as e:
                    print(e)
                    raise e
                print('after')
            # QWidget().setLayout(self.layout())
            # self.initUI()

    def load(self):
        print('loadSchemes')
        if not os.path.exists(digital_pulses_folder):
            print('create folder ', digital_pulses_folder)
            os.mkdir(digital_pulses_folder)
        files = os.listdir(digital_pulses_folder)
        if len(files) != 0:
            for fname in files:
                if fname.startswith('config'):
                    with open(os.path.join(digital_pulses_folder, fname), 'rb') as f:
                        print('config_load')
                        self.config = pickle.load(f)

                if fname.endswith(pulse_name_suffix):
                    with open(os.path.join(digital_pulses_folder, fname), 'rb') as f:
                        print('here')
                        self.all_schemes[fname[:fname.find(pulse_name_suffix)]] = pickle.load(f)

            # if not os.path.exists(os.path.join(digital_pulses_folder, config_scheme_file)):
            #     config = {}
            # else:
            #     with open(os.path.join(digital_pulses_folder, config_scheme_file), 'rb') as f:
            #         print('here-there')
            #         config = pickle.load(f)
            #         if type(config) != type(dict()):
            #             print('smth rong with config file')
            #             config = {}
        if 'current_scheme' in self.config:
            self.current_scheme = self.config['current_scheme']
        elif len(self.all_schemes):
            self.current_scheme = list(self.all_schemes.keys())[0]
        else:
            self.all_schemes['Default']=[pulseGroup(scheme=self)]
            self.current_scheme = 'Default'
        self.current_groups = self.all_schemes[self.current_scheme]
        if 'available_channels' in self.config:
            self.available_channels = self.config['available_channels']

    def schemeChanged(self, new_scheme):
        print('schemeChanged')
        self.current_scheme = new_scheme
        self.current_groups = self.all_schemes[self.current_scheme]
        self.gui.schemeRedraw()

    def addGroup(self):
        print('addGroup')
        new_group = pulseGroup(scheme=self)
        self.current_groups.append(new_group)
        print('Now')
        self.gui.schemeRedraw()

    def saveScheme(self):
        print('saveScheme')
        if not os.path.exists(digital_pulses_folder):
            print('create folder')
            os.mkdir(digital_pulses_folder)
        # print(self.schemes[self.current_scheme][0].__dict__)
        print(os.path.join(digital_pulses_folder,self.current_scheme+pulse_name_suffix))
        with open(os.path.join(digital_pulses_folder,self.current_scheme+pulse_name_suffix), 'wb') as f:
            # print(self.current_groups[0].__dict__)
            pickle.dump(self.current_groups,f)

    def saveAsScheme(self):
        print('saveAsScheme')
        if not os.path.exists(digital_pulses_folder):
            print('create folder')
            os.mkdir(digital_pulses_folder)
        fname = QFileDialog.getSaveFileName(self.gui,directory=digital_pulses_folder)[0]
        if not fname.endswith(pulse_name_suffix):
            fname += pulse_name_suffix
        with open(fname, 'wb') as f:
            pickle.dump(self.current_groups,f)
        fname = os.path.basename(fname)
        fname = fname[:fname.find(pulse_name_suffix)]
        self.all_schemes[fname] = deepcopy(self.current_groups)
        self.current_scheme = fname
        self.current_groups = self.all_schemes[self.current_scheme]
        self.gui.redraw()

    def deleteGroup(self,group):
        print("deleteGroup")
        # group_names = [group.name for group in self.current_groups]
        # print(group_name, group_names.index(group_name))
        self.current_groups.remove(group)
        self.gui.schemeRedraw()
    
    def changeInGroup(self):
        print('changeInGroup')

class pulseGroup():

    def __init__(self,scheme=None,name='Default', edge=0, delay=0, length=10, is_active=False, reference=None,pulses=[]):
        self.scheme = scheme
        # if scheme.changeInGroup == None:
        #     scheme.changeInGroup = lambda : print('Try to scheme.changeInGroup\n',self.__dict__)
        # self.scheme.changeInGroup = scheme.changeInGroup # mehtod which is called whent smth changed in pulses ore groups to update all pulses
        self.name = name
        self.edge = edge
        self.variables = {'delay':delay, 'length':length}
        self.is_active = is_active
        self.reference = reference
        self.pulses = pulses
        if len(pulses) == 0:
            self.pulses.append(IndividualPulse())
        # self.pulses.append(IndividualPulse(as_group=False,delay=10,edge=1,is_active=True,length=100,name='Blue'))
        # self.gui = self.pulseGroupQt(data=self)

    class pulseGroupQt(QWidget):

        def __init__(self, data=None):
            self.channels = [str(i) for i in range(10)]
            self.n_decimals = 2
            self.data = data
            super().__init__()
            self.initUI()

        def initUI(self):
            main_box = QVBoxLayout(self)

            topbox = QHBoxLayout(self)

            topbox.addWidget(QLabel('Reference:'))

            self.ref_channel_combo_box = QComboBox()
            self.ref_channel_combo_box.addItem('0')
            # self.ref_channel_combo_box.addItems(
            #     [group.name for group in self.data.scheme.current_groups])
            self.ref_channel_combo_box.addItems(['2','3'])
            self.ref_channel_combo_box.setCurrentText(self.data.reference)
            self.ref_channel_combo_box.currentIndexChanged.connect(self.data.groupReferenceChanged)
            topbox.addWidget(self.ref_channel_combo_box)

            self.add_pulse_btn = QPushButton('Add pulse')
            self.add_pulse_btn.clicked.connect(self.data.addPulse)
            topbox.addWidget(self.add_pulse_btn)

            self.del_group_btn = QPushButton('Del Group')
            self.del_group_btn.clicked.connect(self.data.deleteGroup)
            topbox.addWidget(self.del_group_btn)
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
            group_name.returnPressed.connect(self.data.groupNameChanged)
            self.grid_layout.addWidget(group_name, self.group_row, self.columns.index('Name'))

            group_edge = QComboBox()
            group_edge.addItems(self.edges)
            group_edge.setCurrentIndex(self.data.edge)
            group_edge.currentIndexChanged.connect(self.data.edgeChanged)
            self.grid_layout.addWidget(group_edge, self.group_row, self.columns.index('Edge'))

            group_delay = QDoubleSpinBox()
            group_delay.setDecimals(self.n_decimals)
            group_delay.setMaximum(10000)
            group_delay.setMinimum(-10000)
            group_delay.setValue(self.data.variables['delay'])
            group_delay.valueChanged.connect(self.data.delayChanged)
            self.grid_layout.addWidget(group_delay, self.group_row, self.columns.index('Delay'))

            group_length = QDoubleSpinBox()
            group_length.setDecimals(self.n_decimals)
            group_length.setMaximum(10000)
            group_length.setMinimum(-10000)
            group_length.setValue(self.data.variables['length'])
            group_length.valueChanged.connect(self.data.lengthChanged)
            self.grid_layout.addWidget(group_length, self.group_row, self.columns.index('Length'))

            group_is_active = QCheckBox()
            group_is_active.setChecked(self.data.is_active)
            group_is_active.stateChanged.connect(self.data.isActiveChanged)
            self.grid_layout.addWidget(group_is_active, self.group_row, self.columns.index('Active'))
            # add individual pulse data
            for i, pulse in enumerate(self.data.pulses):
                # print('pulse',i)
                pulse_row = i + 2

                del_button = QPushButton('Del')
                del_button.setMaximumWidth(40)
                del_button.clicked.connect(self.data.deletePulse)
                self.grid_layout.addWidget(del_button, pulse_row, self.columns.index('Del'))

                pulse_channel = QComboBox()
                # pulse_channel.addItems(self.data.scheme.all_channels)
                pulse_channel.addItems(self.channels)
                pulse_channel.setCurrentText(getattr(pulse, 'channel', '0'))
                pulse_channel.currentTextChanged.connect(self.data.pulseChannelChanged)
                self.grid_layout.addWidget(pulse_channel, pulse_row, self.columns.index('Channel'))

                pulse_name = QLineEdit(pulse.name)
                pulse_name.returnPressed.connect(self.data.pulseNameChanged)
                self.grid_layout.addWidget(pulse_name, pulse_row, self.columns.index('Name'))

                pulse_edge = QComboBox()
                pulse_edge.addItems(self.edges)
                pulse_edge.setCurrentIndex(pulse.edge)
                pulse_edge.currentIndexChanged.connect(self.data.edgeChanged)
                self.grid_layout.addWidget(pulse_edge, pulse_row, self.columns.index('Edge'))

                pulse_delay = QDoubleSpinBox()
                pulse_delay.setDecimals(self.n_decimals)
                pulse_delay.setMaximum(10000)
                pulse_delay.setMinimum(-10000)
                pulse_delay.setValue(pulse.variables['delay'])
                pulse_delay.valueChanged.connect(self.data.delayChanged)
                self.grid_layout.addWidget(pulse_delay, pulse_row, self.columns.index('Delay'))

                pulse_length = QDoubleSpinBox()
                pulse_length.setDecimals(self.n_decimals)
                pulse_length.setMaximum(10000)
                pulse_length.setMinimum(-10000)
                pulse_length.setValue(pulse.variables['length'])
                pulse_length.valueChanged.connect(self.data.lengthChanged)
                self.grid_layout.addWidget(pulse_length, pulse_row, self.columns.index('Length'))

                pulse_is_active = QCheckBox()
                pulse_is_active.setChecked(pulse.is_active)
                pulse_is_active.stateChanged.connect(self.data.isActiveChanged)
                self.grid_layout.addWidget(pulse_is_active, pulse_row, self.columns.index('Active'))

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

        def delayChanged(self, new_delay):
            print('delayChangedaaaa')
            print(self.sender())

        def redraw(self):
            QWidget().setLayout(self.layout())
            self.initUI()

        def getNewText(self):
            return self.sender().text()

    def __getstate__(self):
        print('__getstate__')
        print({k:v for k,v in self.__dict__.items() if  k not in ['gui']})
        return {k:v for k,v in self.__dict__.items() if  k not in ['gui']}

    def addPulse(self):
        print('addPulse')
        self.pulses.append(IndividualPulse())
        self.gui.redraw()
        self.scheme.changeInGroup() # call for parent method

    def deletePulse(self):
        print('deletePulse')
        # send to gui programm sender() to get back index of pulse to delete
        quit_msg = "Are you sure you want to delete this pulse?"
        reply = QMessageBox.question(self.gui, 'Message',
                                     quit_msg, QMessageBox.Yes, QMessageBox.No)
        print('hee')
        if reply == QMessageBox.Yes:
            print('Delete')
            pulse_number = self.gui.getPulseNumber()
            self.pulses.pop(pulse_number)
            self.gui.redraw()
            self.scheme.changeInGroup() # call for parent method

    def deleteGroup(self):
        print('deleteGroup')
        quit_msg = "Are you sure you want to delete this pulse group?"
        reply = QMessageBox.question(self.gui, 'Message',
                                     quit_msg, QMessageBox.Yes, QMessageBox.No)

        if reply == QMessageBox.Yes:
            print('Delete')
            self.scheme.deleteGroup(self)

    def pulseChannelChanged(self, new_channel):
        print('pulseChannelChanged')
        pulse_number = self.gui.getPulseNumber()
        self.pulses[pulse_number].channel = new_channel
        # self.gui.redraw()
        self.scheme.changeInGroup() # call for parent method

    def pulseNameChanged(self):
        print('pulseNameChanged')
        # there is no need to recalculate pulses if only name has changed
        pulse_number = self.gui.getPulseNumber()
        self.pulses[pulse_number].name = self.gui.getNewText()#self.gui.sender().text()

    def edgeChanged(self,new_edge):
        print('edgeChanged')
        pulse_number = self.gui.getPulseNumber()
        if pulse_number == -1:
            # group edge was changed
            self.edge = new_edge
        else:
            self.pulses[pulse_number].edge = new_edge
        self.scheme.changeInGroup() # call for parent method

    def isActiveChanged(self,new_is_active):
        print('isActiveChanged')
        pulse_number = self.gui.getPulseNumber()
        if pulse_number == -1:
            # group edge was changed
            self.is_active = new_is_active
        else:
            self.pulses[pulse_number].is_active = new_is_active
        self.scheme.changeInGroup() # call for parent method

    def delayChanged(self,new_delay):
        print('delayChanged')
        pulse_number = self.gui.getPulseNumber()
        print('here')
        if pulse_number == -1:
            # group edge was changed
            self.variables['delay'] = new_delay
        else:
            self.pulses[pulse_number].variables['delay'] = new_delay
        self.scheme.changeInGroup() # call for parent method

    def lengthChanged(self,new_length):
        print('lengthChanged')
        pulse_number = self.gui.getPulseNumber()
        if pulse_number == -1:
            # group edge was changed
            self.variables['length'] = new_length
        else:
            self.pulses[pulse_number].variables['length'] = new_length
        self.scheme.changeInGroup() # call for parent method

    def groupNameChanged(self):
        print('groupNameChanged')
        self.name = self.gui.getNewText()
        # update scheme becaus tab name and references has to be changed
        # self.scheme.updateScheme()

    def groupReferenceChanged(self, new_reference):
        print('groupReferenceChanged')
        # Посмотреть, можно ли просто использовать новое имя
        self.reference = new_reference
        self.scheme.changeInGroup()

    def analogGonfig(self):
        print('analogConfig')

class IndividualPulse():
    def __init__(self, group = None,name='',channel = '0', edge = 0, delay = 0, length=0,is_active=False):
        self.name = name   # name of the pulse
        # self.group = group # group of pulses it belongs to
        self.channel = channel # physical channel of the signal (or may be name in dictionary)
        self.edge = edge # start the pulse from group's t_start=0 or t_end=1
        self.variables = {'delay':delay,'length':length}  # for easy scanning
        self.is_active = is_active
    def getPoints(self):
        pass

class AnalogPulse(IndividualPulse):
    def __init__(self,type='Points'):
        super().__init__()
        self.type = type
        self.formula = '' # iether string of points if type Point ore string of formula if type Formula
        # self.timeStep # to define timestap if type=='Formula'


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    p = pulseScheme()
    # print(p.__dict__)
    # mainWindow = digital_pulses()

    p.gui.show()
    sys.exit(app.exec_())
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
                             QLabel, QLineEdit, QPushButton, QWidget, QComboBox,QRadioButton, QSpinBox, QCheckBox, QTabWidget, QFileDialog)

digital_pulses_folder = 'digatal_schemes'
config_scheme_file = 'config_scheme'
class digital_pulses(QWidget):
    # can be done as QWidget
    def __init__(self):
        self.loadSchemes()  # schemes with saved groups and pulses
        groups = []  # list of all pulse_groups
        super().__init__()
        if len(self.schemes) == 0:
            self.schemes['Default']=[pulse_group(name='first'),pulse_group(name='qqq')]
            self.schemes['Default1'] = [pulse_group(),pulse_group(name='dfg')]
        self.initUI()

    def initUI(self):

        vbox = QVBoxLayout(self)

        topbox = QHBoxLayout(self)
        self.scheme_lbl = QLabel('Scheme')
        topbox.addWidget(self.scheme_lbl)

        self.scheme_combo_box = QComboBox()
        self.scheme_combo_box.addItems(self.schemes.keys())
        if self.current_scheme:
            self.scheme_combo_box.setCurrentText(self.current_scheme)
        self.scheme_combo_box.currentTextChanged.connect(self.updateScheme)
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

        vbox.addLayout(topbox)


        self.tabbox = QTabWidget()
        self.tabbox.setMovable(True)
        self.current_scheme = self.scheme_combo_box.currentText()
        print(self.current_scheme)
        for group in self.schemes[self.current_scheme]:
            tab = group.PulseGroupWidget(parent=self, data=group)
            tab.updateReferences()
            self.tabbox.addTab(tab, group.name)
        # tab1 = pulse_group(self)

        vbox.addWidget(self.tabbox)
        self.setLayout(vbox)
        print(self.children())
        # few buttons like save, add_scheme (to add current version of the scheme) and so on
        # self.current_scheme  # set_current_scheme (may be from last session)
        # self.pulses_tabs = QTabWidget()  # initialize tab widget with tabs for pulse_groups
        # for p_group in current_scheme:
        #     self.pulses_tabs.addTab(p_group.get_tab(SMTH), p_group.name)
            # probably here i have to return widget or smth
    def addGroup(self):
        print('addGroup')
        new_group = pulse_group(self)
        self.schemes[self.current_scheme].append(new_group)
        # self.tabbox.addTab(new_group,new_group.name)
        # self.tabbox.setCurrentWidget(new_group)
        # self.show()
        self.updateScheme()

    def updateScheme(self):
        print('updateScheme')
        self.tabbox.clear()
        self.current_scheme = self.scheme_combo_box.currentText()
        for group in self.schemes[self.current_scheme]:
            tab = group.PulseGroupWidget(parent=self, data=group)
            # tab.updateReferences()
            self.tabbox.addTab(tab, group.name)
        self.updateConfig()

    def updateConfig(self):
        print('updateConfig')
        if not os.path.exists(os.path.join(digital_pulses_folder, config_scheme_file)):
            config = {}
        else:
            with open(os.path.join(digital_pulses_folder, config_scheme_file), 'rb') as f:
                print('here-there')
                config = pickle.load(f)
                if type(config) != type(dict()):
                    print('smth rong with config file')
                    config = {}
        config['current_scheme'] = self.current_scheme
        with open(os.path.join(digital_pulses_folder, config_scheme_file), 'wb') as f:
            pickle.dump(config,f)

    def saveScheme(self):
        print('saveScheme')
        if not os.path.exists(digital_pulses_folder):
            print('create folder')
            os.mkdir(digital_pulses_folder)
        print(self.schemes[self.current_scheme][0].__dict__)
        with open(os.path.join(digital_pulses_folder,self.current_scheme), 'wb') as f:
            pickle.dump(self.schemes[self.current_scheme],f)

    def saveAsScheme(self):
        print('saveAsScheme')
        if not os.path.exists(digital_pulses_folder):
            print('create folder')
            os.mkdir(digital_pulses_folder)
        fname = QFileDialog.getSaveFileName(self,directory=digital_pulses_folder)[0]
        with open(fname, 'wb') as f:
            pickle.dump(self.schemes[self.current_scheme],f)
        QWidget().setLayout(self.layout())
        fname = os.path.basename(fname)
        self.schemes[fname] = deepcopy(self.schemes[self.current_scheme])
        self.current_scheme = fname
        print('lll')
        self.initUI()

    def loadSchemes(self):
        print('loadSchemes')
        self.schemes = {}
        self.current_scheme = None
        if not os.path.exists(digital_pulses_folder):
            print('create folder')
            os.mkdir(digital_pulses_folder)
        files = os.listdir(digital_pulses_folder)
        if len(files) != 0:
            for fname in files:
                if not fname.startswith('config'):
                    with open(os.path.join(digital_pulses_folder, fname), 'rb') as f:
                        print('here')
                        self.schemes[fname] = pickle.load(f)
            if not os.path.exists(os.path.join(digital_pulses_folder, config_scheme_file)):
                config = {}
            else:
                with open(os.path.join(digital_pulses_folder, config_scheme_file), 'rb') as f:
                    print('here-there')
                    config = pickle.load(f)
                    if type(config) != type(dict()):
                        print('smth rong with config file')
                        config = {}
            if 'current_scheme' in config.keys():
                self.current_scheme = config['current_scheme']
            else:
                self.current_scheme = None


class pulse_group():
    def __init__(self,parent=None,name='Default'):
        self.name = name
        self.edge=0
        self.delay = 10
        self.length = 100
        self.is_active = True
        self.ref = None
        self.pulses = []
        self.pulses.append(IndividualPulse(name='Green'))
        self.pulses.append(IndividualPulse(as_group=False,delay=10,edge=1,is_active=True,length=100,name='Blue',))
        # t_start  # absolute time of the beginning of the group
        # t_end  # absolute time of the end of the group

    class PulseGroupWidget(QWidget):
        def __init__(self,parent=None,data=None):
            self.parent = parent
            self.data = data
            super().__init__()
            self.initUI()

        def initUI(self):
            vbox = QVBoxLayout(self)
            topbox = QHBoxLayout(self)

            self.ref_channel_lbl = QLabel('Ref. channel:')
            topbox.addWidget(self.ref_channel_lbl)

            self.ref_channel_combo_box = QComboBox()
            self.ref_channel_combo_box.addItem('0')
            self.ref_channel_combo_box.addItems([group.name for group in self.parent.schemes[self.parent.current_scheme]])
            # print(self.data.__dict__)
            self.ref_channel_combo_box.setCurrentText(self.data.ref)
            self.ref_channel_combo_box.currentIndexChanged.connect(self.refChannelChanged)
            topbox.addWidget(self.ref_channel_combo_box)

            self.add_pulse_btn = QPushButton('Add pulse')
            self.add_pulse_btn.clicked.connect(self.add_pulse)
            topbox.addWidget(self.add_pulse_btn)
            # topbox.addWidget(self.name_lbl)
            # topbox.addWidget(self.name_line)
            # topbox.addWidget(self.edge_lbl)
            # topbox.addWidget(self.edge_combo_box)
            vbox.addLayout(topbox)
            self.columns = ['Del','As group','Name','Edge','Delay','Length','Active']
            self.edges = ['Begin', 'End']
            grid_layout = self.drawGrid()
            vbox.addLayout(grid_layout)
            self.setLayout(vbox)
            self.show

        def refChannelChanged(self):
            print('refChannelChanged')
            self.data.ref = self.ref_channel_combo_box.currentText()
            print(self.data.ref)
            # self.redrawGroup()

        def redrawGroup(self):
            QWidget().setLayout(self.layout())
            self.initUI()
            self.updateReferences()

        def add_pulse(self):
            self.data.pulses.append(IndividualPulse())
            self.redrawGroup()
            # self.draw_pulses()

        def drawGrid(self):
            grid_layout = QGridLayout()
            for i,name in enumerate(self.columns):
                grid_layout.addWidget(QLabel(name),1,i)
            j=0
            group_name = QLineEdit(self.data.name)
            group_name.editingFinished.connect(self.groupNameChanged)
            grid_layout.addWidget(group_name,j,self.columns.index('Name'))
            group_edge = QComboBox()
            group_edge.addItems(self.edges)
            group_edge.setCurrentIndex(self.data.edge)
            grid_layout.addWidget(group_edge,j,self.columns.index('Edge'))
            group_delay = QSpinBox()
            group_delay.setValue(self.data.delay)
            grid_layout.addWidget(group_delay, j, self.columns.index('Delay'))
            group_length = QSpinBox()
            group_length.setValue(self.data.length)
            grid_layout.addWidget(group_length, j, self.columns.index('Length'))
            group_is_active = QRadioButton()
            group_is_active.setChecked(self.data.is_active)
            grid_layout.addWidget(group_is_active, j, self.columns.index('Active'))

            for i,pulse in enumerate(self.data.pulses):
                print('pulse',i)
                j = i + 2
                del_button = QPushButton('Del')
                del_button.clicked.connect(self.delButtonClicked)
                grid_layout.addWidget(del_button,j,self.columns.index('Del'))
                pulse_as_group = QRadioButton()
                pulse_as_group.setChecked(pulse.as_group)
                grid_layout.addWidget(pulse_as_group,j,self.columns.index('As group'))
                pulse_name = QLineEdit(pulse.name)
                grid_layout.addWidget(pulse_name,j,self.columns.index('Name'))
                pulse_edge = QComboBox()
                pulse_edge.addItems(self.edges)
                pulse_edge.setCurrentIndex(pulse.edge)
                grid_layout.addWidget(pulse_edge,j,self.columns.index('Edge'))
                pulse_delay = QSpinBox()
                pulse_delay.setValue(pulse.delay)
                grid_layout.addWidget(pulse_delay,j,self.columns.index('Delay'))
                pulse_length = QSpinBox()
                pulse_length.setValue(pulse.length)
                grid_layout.addWidget(pulse_length,j,self.columns.index('Length'))
                pulse_is_active = QRadioButton()
                pulse_is_active.setChecked(pulse.is_active)
                grid_layout.addWidget(pulse_is_active,j,self.columns.index('Active'))
            return grid_layout

        def delButtonClicked(self):
            layout = self.layout()
            index = layout.children()[1].indexOf(self.sender())
            row, column, cols, rows = layout.children()[1].getItemPosition(index)
            print(row, column, cols, rows)
            self.data.pulses.pop(row-2)
            self.redrawGroup()

        def groupNameChanged(self):
            print('Here')
            print('new name', self.sender().text())
            self.data.name = self.sender().text()
            self.parent.updateScheme()

        def updateReferences(self):
            self.ref_channel_combo_box.clear()
            self.ref_channel_combo_box.addItem('0')
            self.ref_channel_combo_box.addItems([group.name for group in self.parent.schemes[self.parent.current_scheme]])
            self.ref_channel_combo_box.setCurrentText(self.data.ref)

class IndividualPulse():
    def __init__(self, name='', as_group=True,edge = 0, delay = 0, length=1,is_active=True):
        self.name = name  # physical channel of the signal (or may be name in dictionary)
        self.as_group = as_group  # replicate timing of the group
        self.edge = edge # start the pulse from group's t_start or t_end
        self.delay = delay  # delay compared to group t_start or t_end
        self.length = length
        self.is_active = is_active
        # t_start  # absolute time of the beginning of the pulse
    # length  # length of pulse_group (can be negative - how to handle?)
    # t_end  # absolute time of the end of the group
    # is_active  # is the pulse_group now active
    # attached_shutters  # list of attached shutters to particular this pulse - can be usefull when more then 1 shutter is needed


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    mainWindow = digital_pulses()

    mainWindow.show()
    sys.exit(app.exec_())
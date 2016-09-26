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

class digital_pulses(QWidget):
    # can be done as QWidget
    def __init__(self):
        self.active_channels = {}
        self.loadSchemes()  # schemes with saved groups and pulses
        groups = []  # list of all pulse_groups]
        self.output_data = {}
        super().__init__()
        if len(self.schemes) == 0:
            self.schemes['Default']=[pulse_group(name='first'),pulse_group(name='qqq')]
            self.schemes['Default10'] = [pulse_group(),pulse_group(name='dfg')]
        self.refChannels = [0]
        self.refChannels.extend([group.name for group in self.schemes[self.current_scheme]])
        print(self.refChannels)
        self.initUI()
        self.win = pg.GraphicsWindow(title="Three plot curves")
        self.win.resize(1000, 600)
        self.onAnyChange()
    def plotPulses(self):
        self.win.clear()
        for name in sorted(self.output_data):
            value = self.output_data[name]
            p = self.win.addPlot(title=name)
            xx = []
            yy = []
            for i,point in enumerate(value[1:]):
                if (not i==0) and (not i == (len(value[1:])-1)):
                    xx.append(point[0])
                    yy.append(not point[1])
                xx.append(point[0])
                yy.append(point[1])
            p.plot(xx,yy)
            self.win.nextRow()

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

        self.hor_box = QHBoxLayout(self)

        self.ch_grid = QGridLayout(self)
        self.hor_box.addLayout(self.ch_grid)

        self.tabbox = QTabWidget()
        self.tabbox.setMovable(True)
        self.current_scheme = self.scheme_combo_box.currentText()
        print('Current scheme: ', self.current_scheme)
        for group in self.schemes[self.current_scheme]:
            tab = group.PulseGroupWidget(parent=self, data=group)
            # tab.updateReferences()
            self.tabbox.addTab(tab, group.name)
        # tab1 = pulse_group(self)

        self.hor_box.addWidget(self.tabbox)
        vbox.addLayout(self.hor_box)
        # self.channels_vbox
        self.setLayout(vbox)
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
        self.onAnyChange()

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
            elif len(self.schemes):
                self.current_scheme = list(self.schemes.keys())[0]

    def pulseByName(self,name):
        group_names = [group.name for group in self.schemes[self.current_scheme]]
        return self.schemes[self.current_scheme][group_names.index(name)]

    def calculateOutputData(self):
        self.output_data = {}
        end_time = 0
        first_time = 0
        for pulse_group in self.schemes[self.current_scheme]:
            if pulse_group.is_active:
                for pulse in pulse_group.pulses:
                    if pulse.is_active:
                        if not pulse.channel in self.output_data.keys():
                            self.output_data[pulse.channel] = []
                        new_points = self.getPoints(pulse,pulse_group)
                        for point in new_points:
                            if point[0] not in [point[0] for point in self.output_data[pulse.channel]]:
                                self.output_data[pulse.channel].append(point)
                            else:
                                self.output_data[pulse.channel].remove((point[0],not point[1]))
                        # if new_points[-1][0] > end_time:
                        #     end_time = new_points[-1][0]

        for point_list in self.output_data.values():
            point_list.sort(key=lambda x: x[0])
            if point_list[0][0] != 0:
                point_list.insert(0,(0,0))
        for points in self.output_data.values():
            if points[-1][0] > end_time:
                end_time = points[-1][0]
            if first_time == 0:
                first_time = end_time
            if points[1][0] < first_time:
                first_time = points[1][0]
        for points in self.output_data.values():
            points.append((end_time+10,points[-1][1]))
            points.insert(1,(first_time - 100, points[0][1]))
        self.first_time = first_time
        self.end_time = end_time

    def getPoints(self,pulse, group):
        group_begin = group.delay + group.getReferencePoint(self)
        if not pulse.edge:
            if pulse.length == 0:
                return ((group_begin + pulse.delay,1),(group_begin + group.length,0))
            elif pulse.length > 0:
                return ((group_begin + pulse.delay,1),(group_begin +  pulse.delay + pulse.length,0))
            else:
                return ((group_begin +  pulse.delay,1),(group_begin + group.length + pulse.length,0))
        else:
            if pulse.length == 0:
                return ((group_begin + pulse.delay,1),(group_begin + group.length,0))
            elif pulse.length > 0:
                return ((group_begin + group.length + pulse.delay,1),(group_begin + group.length + pulse.delay + pulse.length,0))
            else:
                return ((group_begin + group.length + pulse.delay + pulse.length,1),(group_begin + group.length + pulse.delay,0))

    def onAnyChange(self):
        self.updateChannelPannel()
        self.calculateOutputData()
        # self.plotPulses()
        print(self.output_data)

    def updateChannelPannel(self):
        print('updateChannelPannel')
        flag_to_redraw = False
        channels_in_pulses = set()
        for pulse_group in self.schemes[self.current_scheme]:
                for pulse in pulse_group.pulses:
                        channels_in_pulses.add(pulse.channel)
                        if pulse.channel not in self.active_channels:
                            self.active_channels[pulse.channel] = 'StandBy'
                            flag_to_redraw = True
        to_remove = []
        for key in self.active_channels:
            if key not in channels_in_pulses:
                to_remove.append(key)
        for key in to_remove:
            self.active_channels.pop(key)
            flag_to_redraw = True
        print(self.active_channels)
        if not flag_to_redraw:
            self.showChannelPannel()
        else:
            QWidget().setLayout(self.layout())
            self.initUI()

    def showChannelPannel(self):
        print('Now',self.ch_grid)
        # self.ch_grid = QGridLayout()
        for i,channel in enumerate(sorted(self.active_channels)):
            self.ch_grid.addWidget(QLabel(channel),i,0)
            alwais_on = QCheckBox()
            if self.active_channels[channel] == 'On':
                alwais_on.setChecked(True)
            self.ch_grid.addWidget(alwais_on, i, 1)
            alwais_off = QCheckBox()
            if self.active_channels[channel] == 'Off':
                alwais_on.setChecked(True)
            self.ch_grid.addWidget(alwais_off, i, 2)
        # self.initUI()


    def deleteGroup(self, group_name):
        print("deleteGroup")
        group_names = [group.name for group in self.schemes[self.current_scheme]]
        # print(group_name, group_names.index(group_name))
        self.schemes[self.current_scheme].pop(group_names.index(group_name))
        self.updateScheme()

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
        self.pulses.append(IndividualPulse(as_group=False,delay=10,edge=1,is_active=True,length=100,name='Blue'))

        # t_start  # absolute time of the beginning of the group
        # t_end  # absolute time of the end of the group
    def getReferencePoint(self,scheme):
        if self.ref == '0':
            return 0
        else:
            predecessor = scheme.pulseByName(self.ref)
            return self.edge * predecessor.length + predecessor.getReferencePoint(scheme)

    class PulseGroupWidget(QWidget):
        def __init__(self,parent=None,data=None):
            self.parent = parent
            self.data = data
            self.channels = [str(i) for i in range(10)]
            self.n_decimals = 2
            super().__init__()
            self.initUI()

        def initUI(self):
            vbox = QVBoxLayout(self)
            topbox = QHBoxLayout(self)

            ref_channel_lbl = QLabel('Ref. channel:')
            topbox.addWidget(ref_channel_lbl)

            self.ref_channel_combo_box = QComboBox()
            self.ref_channel_combo_box.addItem('0')
            self.ref_channel_combo_box.addItems([group.name for group in self.parent.schemes[self.parent.current_scheme]])
            self.ref_channel_combo_box.setCurrentText(self.data.ref)
            self.ref_channel_combo_box.currentIndexChanged.connect(self.refChannelChanged)
            topbox.addWidget(self.ref_channel_combo_box)

            self.add_pulse_btn = QPushButton('Add pulse')
            self.add_pulse_btn.clicked.connect(self.add_pulse)
            topbox.addWidget(self.add_pulse_btn)

            self.del_group_btn = QPushButton('Del Group')
            self.del_group_btn.clicked.connect(self.deleteGroup)
            topbox.addWidget(self.del_group_btn)
            vbox.addLayout(topbox)

            self.columns = ['Del','Channel','Name','Edge','Delay','Length','Active']
            self.edges = ['Begin', 'End']
            self.grid_layout = self.drawGrid()
            vbox.addLayout(self.grid_layout)
            self.setLayout(vbox)
            self.show

        def deleteGroup(self):
            print('deleteGroup')
            quit_msg = "Are you sure you want to delete this pulse group?"
            reply = QMessageBox.question(self, 'Message',
                                               quit_msg, QMessageBox.Yes, QMessageBox.No)

            if reply == QMessageBox.Yes:
                self.parent.deleteGroup(self.data.name)

        def refChannelChanged(self):
            print('refChannelChanged')
            self.data.ref = self.ref_channel_combo_box.currentText()
            self.parent.onAnyChange()
            # print(self.data.__dict__)
            # self.redrawGroup()

        def redrawGroup(self):
            # the way i found to redraw all layout
            print('redrawGroup')
            QWidget().setLayout(self.layout())
            self.initUI()
            # self.updateReferences()

        def add_pulse(self):
            print('addPulse')
            self.data.pulses.append(IndividualPulse())
            self.redrawGroup()
            self.parent.onAnyChange()
            # self.draw_pulses()

        def drawGrid(self):
            print('drawGrid')
            grid_layout = QGridLayout()

            # add column names
            label_row = 1
            for i,name in enumerate(self.columns):
                grid_layout.addWidget(QLabel(name),label_row,i)

            # add pulse_group data
            group_row=0
            self.group_row = group_row
            group_name = QLineEdit(self.data.name)
            group_name.returnPressed.connect(self.groupNameChanged)
            grid_layout.addWidget(group_name,group_row,self.columns.index('Name'))

            group_edge = QComboBox()
            group_edge.addItems(self.edges)
            group_edge.setCurrentIndex(self.data.edge)
            group_edge.currentIndexChanged.connect(self.edgeChanged)
            grid_layout.addWidget(group_edge,group_row,self.columns.index('Edge'))

            group_delay = QDoubleSpinBox()
            group_delay.setDecimals(self.n_decimals)
            group_delay.setMaximum(10000)
            group_delay.setMinimum(-10000)
            group_delay.setValue(self.data.delay)
            group_delay.valueChanged.connect(self.delayChanged)
            grid_layout.addWidget(group_delay, group_row, self.columns.index('Delay'))

            group_length = QDoubleSpinBox()
            group_length.setDecimals(self.n_decimals)
            group_length.setMaximum(10000)
            group_length.setMinimum(-10000)
            group_length.setValue(self.data.length)
            group_length.valueChanged.connect(self.lengthChanged)
            grid_layout.addWidget(group_length, group_row, self.columns.index('Length'))

            group_is_active = QCheckBox()
            group_is_active.setChecked(self.data.is_active)
            group_is_active.stateChanged.connect(self.isActiveChanged)
            grid_layout.addWidget(group_is_active, group_row, self.columns.index('Active'))
            # add individual pulse data
            for i,pulse in enumerate(self.data.pulses):
                # print('pulse',i)
                pulse_row = i + 2

                del_button = QPushButton('Del')
                del_button.setMaximumWidth(40)
                del_button.clicked.connect(self.delButtonClicked)
                grid_layout.addWidget(del_button,pulse_row,self.columns.index('Del'))

                # pulse_as_group = QRadioButton()
                # pulse_as_group.setChecked(pulse.as_group)
                # grid_layout.addWidget(pulse_as_group,pulse_row,self.columns.index('As group'))
                pulse_channel = QComboBox()
                pulse_channel.addItems(self.channels)
                pulse_channel.setCurrentText(getattr(pulse,'channel','0'))
                pulse_channel.currentTextChanged.connect(self.pulseChannelChanged)
                grid_layout.addWidget(pulse_channel,pulse_row,self.columns.index('Channel'))

                pulse_name = QLineEdit(pulse.name)
                pulse_name.returnPressed.connect(self.pulseNameChanged)
                grid_layout.addWidget(pulse_name,pulse_row,self.columns.index('Name'))

                pulse_edge = QComboBox()
                pulse_edge.addItems(self.edges)
                pulse_edge.setCurrentIndex(pulse.edge)
                pulse_edge.currentIndexChanged.connect(self.edgeChanged)
                grid_layout.addWidget(pulse_edge,pulse_row,self.columns.index('Edge'))

                pulse_delay = QDoubleSpinBox()
                pulse_delay.setDecimals(self.n_decimals)
                pulse_delay.setMaximum(10000)
                pulse_delay.setMinimum(-10000)
                pulse_delay.setValue(pulse.delay)
                pulse_delay.valueChanged.connect(self.delayChanged)
                grid_layout.addWidget(pulse_delay,pulse_row,self.columns.index('Delay'))

                pulse_length = QDoubleSpinBox()
                pulse_length.setDecimals(self.n_decimals)
                pulse_length.setMaximum(10000)
                pulse_length.setMinimum(-10000)
                pulse_length.setValue(pulse.length)
                pulse_length.valueChanged.connect(self.lengthChanged)
                grid_layout.addWidget(pulse_length,pulse_row,self.columns.index('Length'))

                pulse_is_active = QCheckBox()
                pulse_is_active.setChecked(pulse.is_active)
                pulse_is_active.stateChanged.connect(self.isActiveChanged)
                grid_layout.addWidget(pulse_is_active,pulse_row,self.columns.index('Active'))

            return grid_layout

        def delButtonClicked(self):
            # layout = self.layout()
            print('delButtonClicked')
            index = self.grid_layout.indexOf(self.sender())
            row, column, cols, rows = self.grid_layout.getItemPosition(index)
            # print(row, column, cols, rows)
            self.data.pulses.pop(row-2)
            self.redrawGroup()
            self.parent.onAnyChange()

        def groupNameChanged(self):
            print('groupNameChanged')
            # print('new name', self.sender().text())
            self.data.name = self.sender().text()
            self.parent.updateScheme()

        # def updateReferences(self):
        #     self.ref_channel_combo_box.clear()
        #     self.ref_channel_combo_box.addItem('0')
        #     self.ref_channel_combo_box.addItems([group.name for group in self.parent.schemes[self.parent.current_scheme]])
        #     self.ref_channel_combo_box.setCurrentText(self.data.ref)

        def edgeChanged(self, new_index):
            print('edgeChanged')
            index = self.grid_layout.indexOf(self.sender())
            row, column, cols, rows = self.grid_layout.getItemPosition(index)
            # print(row,column,new_index)
            if row == self.group_row:
                # group edge has been changed
                self.data.edge = new_index
            else:
                # individual pulse edge has been changed
                self.data.pulses[row-2].edge = new_index
            self.parent.onAnyChange()

        def delayChanged(self,new_value):
            print('delayChanged')
            index = self.grid_layout.indexOf(self.sender())
            row, column, cols, rows = self.grid_layout.getItemPosition(index)
            # print(row,column,new_value)
            if row == self.group_row:
                # group edge has been changed
                self.data.delay = new_value
            else:
                # individual pulse edge has been changed
                self.data.pulses[row-2].delay = new_value
            self.parent.onAnyChange()

        def lengthChanged(self,new_value):
            print('lengthChanged')
            index = self.grid_layout.indexOf(self.sender())
            row, column, cols, rows = self.grid_layout.getItemPosition(index)
            # print(row,column,new_value)
            if row == self.group_row:
                # group edge has been changed
                self.data.length = new_value
            else:
                # individual pulse edge has been changed
                self.data.pulses[row-2].length = new_value
            self.parent.onAnyChange()

        def isActiveChanged(self,new_value):
            print('isActiveChanged')
            index = self.grid_layout.indexOf(self.sender())
            row, column, cols, rows = self.grid_layout.getItemPosition(index)
            # print(row,column,new_value)
            if row == self.group_row:
                # group edge has been changed
                self.data.is_active = new_value
            else:
                # individual pulse edge has been changed
                self.data.pulses[row-2].is_active = new_value
            self.parent.onAnyChange()

        def pulseChannelChanged(self,new_value):
            print('pulseChannelChanged')
            index = self.grid_layout.indexOf(self.sender())
            row, column, cols, rows = self.grid_layout.getItemPosition(index)
            # print(row, column, new_value)
            self.data.pulses[row - 2].channel = new_value
            self.parent.onAnyChange()

        def pulseNameChanged(self):
            print('pulseNameChanged')
            index = self.grid_layout.indexOf(self.sender())
            row, column, cols, rows = self.grid_layout.getItemPosition(index)
            # print(row, column, self.sender().text())
            self.data.pulses[row - 2].name = self.sender().text()
            self.parent.onAnyChange()


class IndividualPulse():
    def __init__(self, name='',channel = 0, as_group=True,edge = 0, delay = 0, length=1,is_active=True):
        self.name = name  # physical channel of the signal (or may be name in dictionary)
        self.channel = str(channel)
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
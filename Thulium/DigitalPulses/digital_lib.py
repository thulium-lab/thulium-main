# from PyQt5.QtCore import QObject
import random
import numpy as np
import matplotlib
matplotlib.use('Qt5Agg',force=True)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from PyQt5.QtCore import (QLineF, QPointF, QRectF, Qt, QTimer)
from PyQt5.QtGui import (QBrush, QColor, QPainter)
from PyQt5.QtWidgets import (QApplication, QGraphicsView, QGraphicsScene, QGraphicsItem,
                             QGridLayout, QVBoxLayout, QHBoxLayout, QSizePolicy,
                             QLabel, QLineEdit, QPushButton, QWidget, QComboBox,QRadioButton, QSpinBox, QCheckBox)
# class digital_pulses(QWidget):
#     # can be done as QWidget
#     super().__init__()
#     self.initUI()
#     schemes = []  # schemes with saved groups and pulses
#     groups = []  # list of all pulse_groups
#
#     def initUI():
#         vbox = QVBoxLayout(self)
#         topbox = QVBoxLayout(self)
#
#         # few buttons like save, add_scheme (to add current version of the scheme) and so on
#         self.current_scheme  # set_current_scheme (may be from last session)
#         self.pulses_tabs = QTabWidget()  # initialize tab widget with tabs for pulse_groups
#         for p_group in current_scheme:
#             self.pulses_tabs.addTab(p_group.get_tab(SMTH), p_group.name)
#             # probably here i have to return widget or smth


class pulse_group(QWidget):
    def __init__(self):
        self.name = 'First'
        self.edge=0
        self.delay = 10
        self.length = 100
        self.is_active = True
        self.pulses = []
        self.pulses.append(IndividualPulse(name='Green'))
        self.pulses.append(IndividualPulse(as_group=False,delay=10,edge=1,is_active=True,length=100,name='Blue',))
        super().__init__()
        self.initUI()
        name = ''  # name of the group
        start_from_what = 0  # from wchich chennel or group to start - yet to figure out how to do this
        # 0 corresponds to the beggining of the period (start of the cooling)
        start_from_beggining_or_end = 0  # to start whether from the beginning or end of th start_from_what
        # 0 - beginning, 1 - end
        start_from_delay = 0  # delay
        length = 0  # length of pulse_group (can be negative - how to handle?)
        is_active = True  # is the pulse_group now active


    # t_start  # absolute time of the beginning of the group
    # t_end  # absolute time of the end of the group
    def initUI(self):
        vbox = QVBoxLayout(self)
        topbox = QHBoxLayout(self)
        # self.name_lbl = QLabel('Name:')
        # self.name_line = QLineEdit('')
        # self.name_line.setMaximumWidth(100)
        self.ref_channel_lbl = QLabel('Ref. channel:')
        self.ref_channel_combo_box = QComboBox()
        self.ref_channel_combo_box.addItems(['1','20000'])
        self.ref_channel_combo_box.setMaximumWidth(100)
        # self.edge_lbl = QLabel('Edge')
        # self.edge_combo_box = QComboBox()
        # self.edge_combo_box.addItems(['Begin','End'])
        self.add_pulse_btn = QPushButton('Add pulse')
        self.add_pulse_btn.clicked.connect(self.add_pulse)
        # topbox.addWidget(self.name_lbl)
        # topbox.addWidget(self.name_line)
        topbox.addWidget(self.ref_channel_lbl)
        topbox.addWidget(self.ref_channel_combo_box)
        # topbox.addWidget(self.edge_lbl)
        # topbox.addWidget(self.edge_combo_box)
        topbox.addWidget(self.add_pulse_btn)
        vbox.addLayout(topbox)
        self.columns = ['Del','As group','Name','Edge','Delay','Length','Active']
        self.edges = ['Begin', 'End']
        grid_layout = self.drawGrid()
        vbox.addLayout(grid_layout)
        self.setLayout(vbox)
        self.show
    def add_pulse(self):
        self.pulses.append(IndividualPulse())
        print(self.children())
        print(self.layout())
        QWidget().setLayout(self.layout())
        self.initUI()
        # self.draw_pulses()
    def drawGrid(self):
        grid_layout = QGridLayout()
        for i,name in enumerate(self.columns):
            grid_layout.addWidget(QLabel(name),1,i)
        j=0
        group_name = QLineEdit(self.name)
        grid_layout.addWidget(group_name,j,self.columns.index('Name'))
        group_edge = QComboBox()
        group_edge.addItems(self.edges)
        group_edge.setCurrentIndex(self.edge)
        grid_layout.addWidget(group_edge,j,self.columns.index('Edge'))
        group_delay = QSpinBox()
        group_delay.setValue(self.delay)
        grid_layout.addWidget(group_delay, j, self.columns.index('Delay'))
        group_length = QSpinBox()
        group_length.setValue(self.length)
        grid_layout.addWidget(group_length, j, self.columns.index('Length'))
        group_is_active = QRadioButton()
        group_is_active.setChecked(self.is_active)
        grid_layout.addWidget(group_is_active, j, self.columns.index('Active'))

        for i,pulse in enumerate(self.pulses):
            print('pulse',i)
            j = i + 2
            del_button = QPushButton('Del')
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
    # def get_tab(parent):
        # the part how to show pulse group with pyqt, maybe one would need additional class
        # main_vbox = VBOX
        # group_hbox = HBOX


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
    mainWindow = pulse_group()

    mainWindow.show()
    sys.exit(app.exec_())
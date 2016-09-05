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
                             QLabel, QLineEdit, QPushButton, QWidget, QComboBox,QRadioButton)
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
        pulses = []

    # t_start  # absolute time of the beginning of the group
    # t_end  # absolute time of the end of the group
    def initUI(self):
        vbox = QVBoxLayout(self)
        topbox = QHBoxLayout(self)
        self.name_lbl = QLabel('Name:')
        self.name_line = QLineEdit('')
        self.name_line.setMaximumWidth(100)
        self.ref_channel_lbl = QLabel('Ref. channel:')
        self.ref_channel_combo_box = QComboBox()
        self.ref_channel_combo_box.addItems(['1','20000'])
        self.ref_channel_combo_box.setMaximumWidth(100)
        topbox.addWidget(self.name_lbl)
        topbox.addWidget(self.name_line)
        topbox.addWidget(self.ref_channel_lbl)
        topbox.addWidget(self.ref_channel_combo_box)
        vbox.addLayout(topbox)
    # def get_tab(parent):
        # the part how to show pulse group with pyqt, maybe one would need additional class
        # main_vbox = VBOX
        # group_hbox = HBOX


# class individual_pulse():
#     channel  # physical channel of the signal (or may be name in dictionary)
#     the_same_as_group  # replicate timing of the group
#     from_begin_or_end  # start the pulse from group's t_start or t_end
#     delay  # delay compared to group t_start or t_end
#     t_start  # absolute time of the beginning of the pulse
#     length  # length of pulse_group (can be negative - how to handle?)
#     t_end  # absolute time of the end of the group
#     is_active  # is the pulse_group now active
#     attached_shutters  # list of attached shutters to particular this pulse - can be usefull when more then 1 shutter is needed


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    mainWindow = pulse_group()

    mainWindow.show()
    sys.exit(app.exec_())
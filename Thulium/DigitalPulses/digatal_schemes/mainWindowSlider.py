# from PyQt5.QtCore import QObject
import os, sys
import pickle
import random
import numpy as np
sys.path.append(r'D:\Dropbox\Python\Thulium\Camera')
sys.path.append(r'D:\Dropbox\Python\Thulium\DigitalPulses')
sys.path.append(r'D:\Dropbox\Python\Thulium\Device controll')
sys.path.append(r'D:\Dropbox\Python\Thulium\Device controll\WavelengthMeter')
import matplotlib
matplotlib.use('Qt5Agg',force=True)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from copy import deepcopy

from PyQt5.QtCore import (QLineF, QPointF, QRectF, Qt, QTimer)
from PyQt5.QtGui import (QBrush, QColor, QPainter)
from PyQt5.QtWidgets import (QApplication, QGraphicsView, QGraphicsScene, QGraphicsItem, QMenu, QAction,
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
from PyQt5.QtCore import (QLineF, QPointF, QRectF, Qt, QTimer,QObject,pyqtSignal)
from PyQt5.QtGui import (QBrush, QColor, QPainter)
from PyQt5.QtWidgets import (QApplication, QGraphicsView, QGraphicsScene, QGraphicsItem, QMenu, QAction, QMdiArea,QMdiSubWindow,
                             QMenu, QAction, QScrollArea, QFrame,QDesktopWidget,QSplitter,
                             QGridLayout, QVBoxLayout, QHBoxLayout, QSizePolicy,QMainWindow, QDialog,QTextEdit,
                             QLabel, QLineEdit, QPushButton, QWidget, QComboBox,QRadioButton, QSpinBox, QCheckBox, QTabWidget, QFileDialog,QMessageBox, QDoubleSpinBox)

from Pulses import PulseScheme, PulseGroup,IndividualPulse,AnalogPulse
from scanner import Scanner
from PlotPulse import PlotPulse
from bgnd_runner import Bgnd_Thread
from display_widget import DisplayWidget
from device_lib import connectArduino
from WMeter import WMMain,WMChannel
import arduinoShutters
import threading
import time
vertical_splitting = 0.7
horizontal_splitting = 0.6




class OurSignals(QObject):
    # here all possible signals which can be used in our programm
    anyPulseChange = pyqtSignal()  # to handle any change in pulse scheme - probably for displaying pulses
    newImageRead = pyqtSignal()     # emits when new image is read from image_folder
    scanCycleFinished = pyqtSignal(int)    # emits by DAQ when every cycle is finished - needed for proper scanning and data acquisition


class MainWindow(QMainWindow):
    count = 0
    signals = OurSignals()
    image_folder = r'Z:\Camera'

    def __init__(self, parent = None):
        super(MainWindow, self).__init__(parent)
        # self.showFullScreen()
        self.all_updates_methods = {}
        # self.slots_to_bound={}
        self.globals = {}
        self.globals['image'] = None
        self.globals['image_updated'] = False
        # self.arduino = connectArduino()

        self.bgnd_image_handler = Bgnd_Thread(globals = self.globals, signals = self.signals,
                                              image_folder=self.image_folder)
        self.bgnd_image_handler.start()
        # self.wm = WMMain(arduino=arduinoShutters.ArduinoShutters(device=self.arduino))
        # self.wm.load()
        self.widgets = {}
        self.default_widgets_names=['Scanner','PulseScheme']
        self.screenSize = QDesktopWidget().availableGeometry()
        self.initUI()

    def initUI(self):
        self.widgets['Scanner']=Scanner(parent=self,globals=self.globals,
                                        all_updates_methods=self.all_updates_methods,
                                        signals=self.signals)
        # self.slots_to_bound['cycleFinished'].connect(self.widgets['Scanner'].cycleFinished)
        # self.triggerCycle.connect(self.widgets['Scanner'].cycleFinished)
        self.widgets['Pulses']=PulseScheme(parent=self,globals=self.globals,signals=self.signals)
        self.widgets['PulsePlot']=PlotPulse(parent=self,globals=self.globals)
        self.widgets['CamView'] = DisplayWidget(parent=self, globals=self.globals, signals=self.signals)
        # self.widgets['WavelengthMeter'] = self.wm.WMWidget(data=self.wm)
        self.all_updates_methods['Pulses']=self.widgets['Pulses'].getUpdateMethod()
        hor_splitter = QSplitter(Qt.Horizontal)
        hor_splitter.setSizes([26, 74])

        self.setCentralWidget(hor_splitter)
        ver_splitter = QSplitter(Qt.Vertical)


        ver_splitter.addWidget(self.widgets['Scanner'])
        ver_splitter.addWidget(self.widgets['PulsePlot'])
        hor_splitter.addWidget(ver_splitter)
        hor_splitter.addWidget(self.widgets['Pulses'])

        self.setFixedWidth(self.screenSize.width())
        # self.widgets['WavelengthMeter'].show()
        self.widgets['CamView'].show()

        print('self_globals',self.globals)

    def addSubProgramm(self):
        pass

    def windowaction(self, q):
        print("triggered")

        if q.text() == "New":
            MainWindow.count = MainWindow.count+1
            sub = QMdiSubWindow()
            sub.setWidget(QTextEdit())
            sub.setWindowTitle("subwindow"+str(MainWindow.count))
            self.mdi.addSubWindow(sub)
            sub.show()

        if q.text() == "cascade":
          self.mdi.cascadeSubWindows()

        if q.text() == "Tiled":
          self.mdi.tileSubWindows()

def main():
    app = QApplication(sys.argv)
    ex = MainWindow()
    ex.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

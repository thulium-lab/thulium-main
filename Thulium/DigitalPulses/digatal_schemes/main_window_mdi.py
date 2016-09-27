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
from PyQt5.QtCore import (QLineF, QPointF, QRectF, Qt, QTimer)
from PyQt5.QtGui import (QBrush, QColor, QPainter)
from PyQt5.QtWidgets import (QApplication, QGraphicsView, QGraphicsScene, QGraphicsItem, QMenu, QAction, QMdiArea,QMdiSubWindow,
                             QMenu, QAction, QScrollArea, QFrame,QDesktopWidget,
                             QGridLayout, QVBoxLayout, QHBoxLayout, QSizePolicy,QMainWindow, QDialog,QTextEdit,
                             QLabel, QLineEdit, QPushButton, QWidget, QComboBox,QRadioButton, QSpinBox, QCheckBox, QTabWidget, QFileDialog,QMessageBox, QDoubleSpinBox)

from Pulses import PulseScheme, PulseGroup,IndividualPulse,AnalogPulse
from Scanner import Scanner

vertical_splitting = 0.7
horizontal_splitting = 0.6
class MainWindow(QMainWindow):
    count = 0

    def __init__(self, parent = None):
        super(MainWindow, self).__init__(parent)

        # self.resize(QDesktopWidget().availableGeometry(self).size())
        # self.size(QDesktopWidget().availableGeometry(self).size())
        self.resize(1500,700)
        self.mdi = QMdiArea()
        self.setCentralWidget(self.mdi)
        # self.showFullScreen()
        self.all_updates_methods = {}
        self.globals = {}
        self.widgets = {}
        self.default_widgets_names=['Scanner','PulseScheme']
        self.initUI()

    def initUI(self):
        bar = self.menuBar()
        file = bar.addMenu("File")
        file.addAction("New")
        file.addAction("cascade")
        file.addAction("Tiled")
        file.triggered[QAction].connect(self.windowaction)
        self.setWindowTitle("MDI demo")
        self.mdi.tileSubWindows()
        # self.mdi.setViewMode(QMdiArea.TabbedView)
        self.screenSize = QDesktopWidget().availableGeometry()
        print(self.screenSize)
        self.setGeometry(self.screenSize)

        # this->setFixedSize(QSize(screenSize.width * 0.7f, screenSize.height * 0.7f));
        MainWindow.count = MainWindow.count + 1
        sub = QMdiSubWindow()
        self.widgets['Scanner']=Scanner(globals=self.globals,all_updates_methods=self.all_updates_methods)
        sub.setWidget(self.widgets['Scanner'])
        self.mdi.addSubWindow(sub)

        MainWindow.count = MainWindow.count + 1
        sub = QMdiSubWindow()
        self.widgets['Pulses']=PulseScheme(globals=self.globals)
        sub.setWidget(self.widgets['Pulses'])
        self.all_updates_methods['Pulses']=self.widgets['Pulses'].getUpdateMethod()
        sub.setWindowTitle("Pulses")
        # sub.setOption(QMdiSubWindow.RubberBandResize, True)
        # sub.setTabPo
        # sub.adjustSize()
        # sub.show()
        # sub.updateGeometry()


        # sub.setOption(QMdiSubWindow.RubberBandResize, True)

        # sub.setMaximumWidth(500)

        self.mdi.addSubWindow(sub)
        sub.setWindowTitle("Scan")

        # sub.show()
        print('self_globals',self.globals)
        # self.adjustSize()
        # print(self.mdi.subWindowList())
        # print(self.mdi)
        # self.mdi.subWindowList()[0].setGeometry(self.screenSize.left() + (1 - vertical_splitting) * self.screenSize.right(),
        #                 self.screenSize.top() + (1 - horizontal_splitting) * self.screenSize.bottom(),
        #                 self.screenSize.right(),
        #                 self.screenSize.bottom())
        # self.mdi.subWindowList()[1].setGeometry(self.screenSize.left(),
        #                 self.screenSize.top(),
        #                 (1 - vertical_splitting) * self.screenSize.right(),
        #                 (1 - horizontal_splitting) * self.screenSize.bottom())
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

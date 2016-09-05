

from PySide import QtCore, QtGui
from pyqtgraph import PlotWidget, ImageView, ImageItem, GraphicsLayoutWidget
# from gageStruc import *
import numpy as np
import time
import UTILS_QT
# import NI_thread_qt
from savedata import saver

class rabi(QtGui.QWidget):
    def __init__(self, parent=None, gage = None, d= None, s =None, NI = None, fpga = None):

        QtGui.QWidget.__init__(self, parent)
        self.initGUI()
        self.gage = gage
        self.d = d
        self.NI = NI
        self.s = s
        self.fpga = fpga


    def initGUI(self):
        self.plot = rabi_plot()
        self.controls = rabi_controls()
        layout = QtGui.QHBoxLayout()
        layout.addWidget(self.plot)
        layout.addWidget(self.controls)
        self.setLayout(layout)
        self.inicons()

    def inicons(self):
        self.controls.startcontrols.startBtn.clicked.connect(self.rabistart)


    def rabistart(self):

        # prepare all instruments
        #self.setDTG()
        self.setSMIQ()
        self.setFPGA()
        #self.setGAGE()
        self.start()

    def setDTG(self):
        pass
        # see in the matlab code

    def setSMIQ(self):

        f = self.controls.rabicontrols.F()
        p = self.controls.rabicontrols.P()
        self.s.CW(f,p)

    def setGAGE(self):
        pass
        # see in the matlab code
        # Acquire from trigger or during the first time in the sequence
        # So, acquire since the first
    def setFPGA(self):
        pass

class rabi_plot(QtGui.QWidget):
    def __init__(self, parent=None, gage = None, d= None, s =None, NI = None):

        QtGui.QWidget.__init__(self, parent)
        self.initGUI()

    def initGUI(self):

        self.p_upper = PlotWidget()
        self.p_lower = PlotWidget()
        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.p_upper)
        layout.addWidget(self.p_lower)
        self.setLayout(layout)
        self.p1 = self.p_upper.getPlotItem()
        self.p2 = self.p_lower.getPlotItem()
        self.p1.addLegend()
        self.p1data = self.p1.plot([0],pen = 'r', name = 'averaged')
        self.p2data = self.p1.plot([0],pen = 'g', name = 'instant')
        self.p1.setLabel('bottom','Time','ns')
        self.p2.setLabel('bottom','Freq','kHz')
        self.p_upper.setTitle('Rabi raw data')
        self.p_lower.setTitle('Rabi FFT')

class rabi_controls(QtGui.QWidget):
    def __init__(self, parent=None, gage = None, d= None, s =None, NI = None):

        QtGui.QWidget.__init__(self, parent)
        self.initGUI()

    def initGUI(self):

        vbox = QtGui.QVBoxLayout()
        self.gagecontrols = UTILS_QT.acqboardcontrols()
        self.plotcontrols = UTILS_QT.plotcontrols()
        self.startcontrols = UTILS_QT.startstopbtn()

        self.rabicontrols = UTILS_QT.rabiControls()


        vbox.addWidget(self.gagecontrols)
        vbox.addWidget(self.plotcontrols)
        vbox.addWidget(self.startcontrols)
        vbox.addWidget(self.rabicontrols)
        self.s = saver(category='rabi')
        vbox.addWidget(self.s)
        self.setLayout(vbox)
        self.setMaximumWidth(200)

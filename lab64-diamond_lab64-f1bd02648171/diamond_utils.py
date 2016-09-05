from PySide import QtCore, QtGui
from pyqtgraph import PlotWidget, ImageView, ImageItem, GraphicsLayoutWidget, PlotItem
import pyqtgraph as pg

import numpy as np
import time
import UTILS_QT
from savedata import saver

class pulses_gen(QtGui.QWidget):
    def __init__(self, parent=None, d= None, fpga = None, smb = None):
        QtGui.QWidget.__init__(self, parent)
        self.initGUI()
    def initGUI(self):
        pass

class pulses_gen(QtGui.QWidget):
    def __init__(self, parent=None, d= None, fpga = None, smb = None):
        QtGui.QWidget.__init__(self, parent)
        self.initGUI()
    def initGUI(self):
        pass

class pulses_2_commands():
    def __init__(self,pulsestable):
        pass

def set_signals(exc = False, mw = False, rf = False, mw_shift = False,
                count_en = False, ref_count_en = False, duration = 0):

    pass


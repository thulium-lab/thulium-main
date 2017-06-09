# -*- coding: utf-8 -*-
"""
This example demonstrates the use of pyqtgraph's dock widget system.

The dockarea system allows the design of user interfaces which can be rearranged by
the user at runtime. Docks can be moved, resized, stacked, and torn out of the main
window. This is similar in principle to the docking system built into Qt, but
offers a more deterministic dock placement API (in Qt it is very difficult to
programatically generate complex dock arrangements). Additionally, Qt's docks are
designed to be used as small panels around the outer edge of a window. Pyqtgraph's
docks were created with the notion that the entire window (or any portion of it)
would consist of dockable components.

"""



# import initExample ## Add path to library (just for examples; you do not need this)
from sympy.parsing.sympy_parser import parse_expr
from PyQt5.QtCore import (QLineF, QPointF, QRectF, Qt, QTimer)
from PyQt5.QtGui import (QBrush, QColor, QPainter)
from PyQt5.QtWidgets import (QApplication, QGraphicsView, QGraphicsScene, QGraphicsItem, QMenu, QAction, QMdiArea,QMdiSubWindow,
                             QMenu, QAction, QScrollArea, QFrame,QDesktopWidget,QSplitter,
                             QGridLayout, QVBoxLayout, QHBoxLayout, QSizePolicy,QMainWindow, QDialog,QTextEdit,
                             QLabel, QLineEdit, QPushButton, QWidget, QComboBox,QRadioButton, QSpinBox, QCheckBox, QTabWidget, QFileDialog,QMessageBox, QDoubleSpinBox)


import os, sys
# sys.path.append(r'/Users/artemgolovizin/GitHub')
sys.path.append(r'D:\!Data')
from matplotlib.pyplot import imread
import pyqtgraph as pg
# from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph.console
import numpy as np

from pyqtgraph.dockarea import *
import thulium_python_lib.usefull_functions as usfuncs
import thulium_python_lib.image_processing_new as impr

pg.setConfigOptions(imageAxisOrder='row-major')

ds_dir = r'D:\!Data\2016_04_22\01 T no_ramp a=-6 f=363.9 b=0.8'
data = []
for d in os.listdir(ds_dir):
    d_dir  = os.path.join(ds_dir,d)
    if os.path.isdir(d_dir):
        x = imread(os.path.join(d_dir,os.listdir(d_dir)[0]))
        data.append(x)
data = np.array(data)

current_data_index = 0;
# app = QApplication([])
# win = QMainWindow()
#
# win.setCentralWidget(area)
# win.resize(1000,500)
# win.setWindowTitle('Dockarea')

class DisplayWidget(DockArea):
    def __init__(self,parent=None,globals=None,signals=None,**argd):
        self.globals = globals
        self.signals = signals
        self.parent = parent

        self.all_plot_data = {'N':[],'width':[]}
        self.do_fit1D_x = False
        self.do_fit1D_y = False
        self.do_fit2D = False
        self.n_sigmas = 3
        self.image_data_to_display = np.array([
            ('N',0, 0,0),
            ('Center',0 , 0,0),
            ("Width", 0, 0,0),
            ("N_small",0,0 , 0)
        ], dtype=[('Parameter', object), ('x', object), ('y', object), ('2D', object)])

        super(DisplayWidget, self).__init__(parent)
        self.initUI()
        self.iso = pg.IsocurveItem(pen='g')
        self.iso.setZValue(1000)
        self.show()
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.routine)
        # self.timer.start()

    def initUI(self):
        # self.area = DockArea()
        # self.setCentralWidget(self.area)
        self.resize(1000,500)
        self.setWindowTitle('Dockarea')
        self.d1 = Dock("Image", size=(500, 500))     ## give this dock the minimum possible size
        self.d2 = Dock("Number of atoms", size=(500,300))
        self.d3 = Dock("Image data", size=(200,500))
        self.d4 = Dock("Cloud width", size=(200,300))
        self.area.addDock(self.d1, 'left')      ## place d1 at left edge of dock area (it will fill the whole space since there are no other docks yet)
        self.area.addDock(self.d2, 'bottom', self.d1)## place d3 at bottom edge of d1
        self.area.addDock(self.d3, 'right',self.d1)     ## place d4 at right edge of dock area
        self.area.addDock(self.d4, 'right', self.d2)  ## place d5 at left edge of d1

        self.imv = pg.ImageView()
        self.imv.setColorMap(pg.ColorMap(np.array([ 0.  ,  0.25,  0.5 ,  0.75,  1.  ]), np.array([[  255, 255, 255, 255],       [  0,   0, 255, 255],       [  0,   0,   0, 255],       [255,   0,   0, 255],       [255, 255,   0, 255]], dtype=np.uint8)))
        self.imv.setImage(imread(r"D:\!Data\2016_04_22\01 T no_ramp a=-6 f=363.9 b=0.8\0ms\1_1.png"))
        self.d1.addWidget(self.imv)

        self.w2 = pg.PlotWidget()
        self.w2.addLegend()
        # self.w2.setYRange(0,100)
        self.curve11 = self.w2.plot(np.array([]),pen=(255,0,0),name='Nx')
        self.curve12 = self.w2.plot(np.array([]),pen=(0,255,0),name='Ny')
        self.curve13 = self.w2.plot(np.array([]),pen=(0,0,255),name='N')
        self.d2.addWidget(self.w2)

        self.w3 = pg.TableWidget()
        self.w3.setData(self.image_data_to_display)
        # self.w3 = pg.LayoutWidget()
        # self.w3.addWidget(QLabel('Parameter'), row=0, col=0)
        # self.w3.addWidget(QLabel('x'), row=0, col=1)
        # self.w3.addWidget(QLabel('y'), row=0, col=2)
        # self.w3.addWidget(QLabel('Center'), row=1, col=0)
        # self.w3.addWidget(QLabel('0'), row=1, col=1)
        # self.w3.addWidget(QLabel('0'), row=1, col=2)
        # self.w3.addWidget(QLabel('Width'), row=2, col=0)
        # self.w3.addWidget(QLabel('0'), row=2, col=1)
        # self.w3.addWidget(QLabel('0'), row=2, col=2)
        # self.w3.addWidget(QLabel('N'), row=3, col=0)
        # self.w3.addWidget(QLabel('0'), row=3, col=1)
        # self.w3.addWidget(QLabel('0'), row=3, col=2)
        self.d3.addWidget(self.w3)

        # self.w4 = pg.LayoutWidget()
        # self.w4.addWidget(QLabel('Var'), row=0, col=0)
        # self.w4.addWidget(QLabel('Show'), row=0, col=1)
        # self.w4.addWidget(QLabel('N'), row=1, col=0)
        # chb1 = QCheckBox()
        # chb1.setChecked(True)
        # # ch.stateChanged.connect(self.addPointsChanged)
        # self.w4.addWidget(chb1, row=1, col=1)
        # self.w4.addWidget(QLabel('sigma_x'), row=2, col=0)
        # chb2 = QCheckBox()
        # chb2.setChecked(True)
        # # ch.stateChanged.connect(self.addPointsChanged)
        # self.w4.addWidget(chb2, row=2, col=1)
        # self.w4.addWidget(QLabel('sigma_y'), row=3, col=0)
        # chb3 = QCheckBox()
        # chb3.setChecked(True)
        # # ch.stateChanged.connect(self.addPointsChanged)
        # self.w4.addWidget(chb3, row=3, col=1)
        # # self.w4.addStretch(1)
        self.w4 = pg.PlotWidget()
        # self.w2.setYRange(0,100)
        self.w4.addLegend(size=(5,20))
        self.curve21 = self.w4.plot(np.array([]), pen=(255, 0, 0),name="w_x1")
        self.curve22 = self.w4.plot(np.array([]), pen=(0, 255, 0),name="w_x2")
        self.curve23 = self.w4.plot(np.array([]), pen=(0, 0, 255),name="w_y1")
        self.curve24 = self.w4.plot(np.array([]), pen='y',name="w_y2")

        self.d4.addWidget(self.w4)
        self.signals.newImageRead.connect(self.routine)

    def routine(self):
        # global current_data_index
        # current_data_index = (current_data_index + 1) % len(data)
        new_data = self.process_image()
        self.update_image_info(new_data)
        # self.update_plot(new_data)
        # self.imv.setImage(new_data.image,autoLevels=False,autoHistogramRange=False,autoRange=False)
        # print(self.imv.getHistogramWidget().gradient.colorMap())
        self.imv.setImage(self.globals['image'],autoRange=False)#, autoLevels=False, autoHistogramRange=False, autoRange=False)

        self.imv.getHistogramWidget().setHistogramRange(0,100000)
        self.imv.getHistogramWidget().setLevels(0, 100000)

        self.updateIsocurve()

    def updateIsocurve(self):
        # global isoLine, iso,imv
        cur_data = pg.gaussianFilter(self.imv.getImageItem().image, (4, 4))
        self.iso.setParentItem(self.imv.getImageItem())
        self.iso.setData(cur_data)
        self.iso.setLevel(cur_data.max()/np.e)

    def process_image(self):
        # basic_data = impr.Image_Basics(data[current_data_index])
        basic_data = impr.Image_Basics(self.globals['image'])
        try:
            if self.do_fit1D_x:
                basic_data.fit1D_x = basic_data.fit_gaussian1D(0)
                print(basic_data.fit1D_x)
            if self.do_fit1D_y:
                basic_data.fit1D_y = basic_data.fit_gaussian1D(1)
            if self.do_fit2D:
                basic_data.fit2D = basic_data.fit_gaussian2D()
            # if self.do_fit1D_x and self.do_fit1D_y:
            #     basic_data.total_small = np.sum(basic_data.image[int(basic_data.fit1D_y[1]-self.n_sigmas*basic_data.fit1D_y[2]):int(basic_data.fit1D_y[1]+self.n_sigmas*basic_data.fit1D_y[2]),
            #                                  int(basic_data.fit1D_x[1]-self.n_sigmas*basic_data.fit1D_x[2]):int(basic_data.fit1D_x[1]+self.n_sigmas*basic_data.fit1D_x[2])])
        except RuntimeError:
            print("RuntimeError, couldn't find fit for image")
            basic_data.isgood = False
        return basic_data

    def update_image_info(self,data):
        if self.do_fit1D_x:
            self.image_data_to_display['x'] = np.array([*data.fit1D_x[:3],'-'],dtype=object)
        else:
            self.image_data_to_display['x'] = np.array(['-']*4, dtype=object)
        if self.do_fit1D_y:
            self.image_data_to_display['y'] = np.array([*data.fit1D_y[:3],'-'],dtype=object)
        else:
            self.image_data_to_display['y'] = np.array(['-'] * 4, dtype=object)
        if self.do_fit2D:
            self.image_data_to_display['2D'] = np.array([data.fit2D[0],"%.0f, %.0f"%(data.fit2D[2],data.fit2D[1]),
                                                         "%.0f, %.0f" %(data.fit2D[4],data.fit2D[3]),data.total_small],dtype=object)
        else:
            self.image_data_to_display['2D'] = np.array(['-'] * 4, dtype=object)
        self.w3.setData(self.image_data_to_display)

    def update_plot(self,data):
        if self.do_fit1D_x and self.do_fit1D_y and self.do_fit2D:
            self.all_plot_data['N'].append((data.fit1D_x[0],data.fit1D_y[0],data.fit2D[0]))
            self.all_plot_data['width'].append((data.fit1D_x[2], data.fit2D[4], data.fit1D_y[2], data.fit2D[3]))
            if len(self.all_plot_data['N']) > 20:
                points_to_show = 20
            else :
                points_to_show = len(self.all_plot_data['N'])
            # dataN = self.all_plot_data['N'][len(self.all_plot_data['N'])-points_to_show:len(self.all_plot_data['N'])]
            # dataN = np.array(self.all_plot_data['N'][-points_to_show:])
            dataN = np.array(self.all_plot_data['N'])
            # xx = np.arange(-points_to_show,0)+len(dataN)
            xx = np.arange(len(dataN))
            self.w2.setYRange(0,dataN.max())
            self.curve11.setData(xx,dataN[:,0])
            self.curve12.setData(xx, dataN[:, 1])
            self.curve13.setData(xx, dataN[:, 2])
            self.w2.setXRange(len(dataN)-points_to_show, len(dataN))
            # dataW = np.array(self.all_plot_data['width'][-points_to_show:])
            dataW = np.array(self.all_plot_data['width'])
            self.w4.setYRange(0, dataW.max())
            self.curve21.setData(xx, dataW[:, 0])
            self.curve22.setData(xx, dataW[:, 1])
            self.curve23.setData(xx, dataW[:, 2])
            self.curve24.setData(xx, dataW[:, 3])
            self.w4.setXRange(len(dataN) - points_to_show, len(dataN))

            # self.curve1.setData(range(len(self.all_plot_data['N'])-points_to_show,len(self.all_plot_data['N'])),
            #                 [x[0] for x in self.all_plot_data['N'][len(self.all_plot_data['N'])-points_to_show:len(self.all_plot_data['N'])]])
            # self.curve2.setData(range(len(self.all_plot_data['N']) - points_to_show, len(self.all_plot_data['N'])),
            #                     [x[1] for x in self.all_plot_data['N'][
            #                                    len(self.all_plot_data['N']) - points_to_show:len(
            #                                        self.all_plot_data['N'])]])
            # self.curve3.setData(range(len(self.all_plot_data['N']) - points_to_show, len(self.all_plot_data['N'])),
            #                     [x[2] for x in self.all_plot_data['N'][
            #                                    len(self.all_plot_data['N']) - points_to_show:len(
            #                                        self.all_plot_data['N'])]])
            # self.curve.setData(np.array([x[0] for x in self.all_plot_data['N']]))
## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    import sys
    # if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
    app = QApplication(sys.argv)
    ex = DisplayWidget()
    ex.show()
    sys.exit(app.exec_())
    # QApplication.instance().exec_()

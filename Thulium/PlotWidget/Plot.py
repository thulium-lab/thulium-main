__author__ = 'Vladimir'

from PySide import QtCore, QtGui
import matplotlib
matplotlib.use('Qt4Agg')
matplotlib.rcParams['backend.qt4']='PySide'
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
import numpy as np

class Plot(FigureCanvas):
    def __init__(self,parent=None,labels=('','')):
        self.fig = Figure()
        self.axes = self.fig.add_subplot(111)
        self.axes.set_xlabel(labels[0])
        self.axes.set_ylabel(labels[1])
        self.axes.set_autoscale_on(True)
        FigureCanvas.__init__(self, self.fig)
        FigureCanvas.setSizePolicy(self,
                                   QtGui.QSizePolicy.Expanding,
                                   QtGui.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        self.lines = {}
        self.setParent(parent)
        self.fig.hold(True)
        self.drawRequested = False
        self.image = None
    def setPointFormat(self,pf):
        self.pointFormat = pf
    def addPoint(self,x,y,lineLabel,plotParams={'marker':'+'}.copy()):
        l = self.lines.get(lineLabel,None)
        if l:
            xdata = np.append(l.get_xdata(),x)
            ydata = np.append(l.get_ydata(),y)
            l.set_data(xdata,ydata)
        else:
            if 'label' not in plotParams:
                plotParams['label'] = lineLabel
            l = Line2D(np.array([x]),np.array([y]),**plotParams)
            self.axes.add_line(l)
            self.lines[lineLabel] = l
            self.axes.legend()
        self.axes.relim()
        self.axes.autoscale_view()
        self.requestDraw()
    def requestDraw(self):
        if self.isVisible():
            self.draw()
            self.drawRequested = False
        else:
            self.drawRequested = True
    def showEvent(self, *args, **kwargs):
        super(Plot,self).showEvent(*args, **kwargs)
        if self.drawRequested:
            self.draw()
    @QtCore.Slot()
    def clearPlot(self,label):
        l = self.lines.get(label,None)
        if l:
            l.remove()
            del self.lines[label]
        self.axes.legend()
        self.requestDraw()
    @QtCore.Slot()
    def clear(self):
        self.lines.clear()
        self.axes.clear()
        self.axes.legend()
        self.image = None
        self.requestDraw()
    @QtCore.Slot()
    def imshow(self,data):
        if self.image is None:
            self.image = self.axes.imshow(data,interpolation='nearest')
        self.requestDraw()
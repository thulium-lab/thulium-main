__author__ = 'Vadim'

from PySide import QtCore, QtGui
from pyqtgraph import PlotWidget, ImageView, ImageItem, GraphicsLayoutWidget, PlotItem
import pyqtgraph as pg

import numpy as np
import time
import UTILS_QT
from savedata import saver

from Fiits import LorentzFit

class SSR(QtGui.QWidget):

    def __init__(self, parent=None, d= None, fpga = None, smiq = None):
        QtGui.QWidget.__init__(self, parent)
        self.initGUI()
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.mainloop)
        # self.gage = gage
        # self.d = d
        # self.NI = NI
        # self.smiq = smiq
        self.i = 0
        self.cw_spectrum_data_av = None
        self.int_spectrum_referenced = None
        self.spec2d = None
        self.dt = 100
        self.fpga = fpga
        self.data = None
        self.smiq = smiq


    def initGUI(self):

        self.plot = SSR_plot()
        self.controls = SSR_controls()
        layout = QtGui.QHBoxLayout()
        layout.addWidget(self.plot)
        layout.addWidget(self.controls)
        self.setLayout(layout)

        self.inicons()
        # connections

    def inicons(self):
        pass
        self.controls.startcontrols.startBtn.clicked.connect(self.startStopSSR)
        # # self.controls.savedata.clicked.connect(self.savedata)
        # self.controls.esrcontrols.plotcontrols.setBtn.clicked.connect(self.plotadjust)
        # self.controls.esrcontrols.plotcontrols.autoBtn.clicked.connect(self.plotauto)
        # self.controls.s.savebtn.clicked.connect(self.savedata)
        # self.controls.s.itemnumber.valueChanged.connect(self.restoredata)


    def startStopSSR(self):

        if self.timer.isActive():
            self.timer.stop()
            self.smiq.Off()
            self.fpga.run_sequence(programm=self.fpga.programm_exc_enable(),number_repeats=1)
            self.data = None
        else:

            self.setSMIQ()


            t_delay = self.controls.single_shot.lasdelay.value()
            t_mw = self.controls.single_shot.tmw.value()
            t_readout = self.controls.single_shot.readouts.value()
            N_cycles = self.controls.single_shot.numofreps.value()

            self.programm=self.fpga.programm_ssr(t_delay=t_delay,
                                                t_mw=t_mw,
                                                t_readout=t_readout,
                                                N_cycles= N_cycles
                                                )
            self.plot.psp.plotprograms(programm=self.programm)
            self.cycletime = (t_delay+t_mw+t_readout)*N_cycles

            self.timer.start(self.dt)

    def setSMIQ(self):

        f = self.controls.single_shot.F()*1e9
        p = self.controls.single_shot.P()
        print(f,p,'Hz, dbm:SMIQ')
        self.smiq.CW(f=f,power=p)
        self.smiq.On()
    def mainloop(self):


        self.fpga.run_sequence(
            programm=self.programm, number_repeats=100
        )
        data = self.fpga.data

        #newdata = #np.array(divmod(data[0],2**32)).reshape((1,2))
        #newdata = #np.append(newdata,np.diff(np.array([divmod(i,2**32) for i in data]),axis = 0)*1.0, axis = 0)
        newdata = np.diff(np.array([divmod(i,2**32) for i in data[:-1]]),axis = 0)*1.0
        # Kostil, since working not good with ends

        if self.data is not None:

            self.data = np.append(self.data,newdata,axis = 0)

        else:

            self.data = newdata

        times = np.arange(0,self.data.shape[0],1)*float(self.cycletime)
        if min(times) < 0:
            print(times, self.cycletime, self.data.shape)
        self.plotUpdate(times,self.data[:,0])

    def plotUpdate(self, times, data):

        if len(self.plot.data_plot.plots) == 0:
            self.plot.data_plot.addCurve(times,datay=data,name = 'av data', color='g')

        else:

            #self.plot.data_plot.updateSubplot(1,times,instant_data)
            self.plot.data_plot.updateSubplot(0,times*1e-9,data)

        self.plot.plot_histogramm(data)



class SSR_plot(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.initGUI()




    def initGUI(self):

        # scheme plot

        self.p_upper_l = PlotWidget()
        self.p_upper_r = PlotWidget()
        self.p_lower_l = PlotWidget()
        self.p_lower_r = PlotWidget()
        self.p_upper_r.setMaximumWidth(300)
        layout = QtGui.QVBoxLayout()

        upperlay = QtGui.QHBoxLayout()
        downlay = QtGui.QHBoxLayout()

        downlay.addWidget(self.p_lower_l)
        downlay.addWidget(self.p_lower_r)

        upperlay.addWidget(self.p_upper_l)
        upperlay.addWidget(self.p_upper_r)
        layout.addLayout(upperlay)
        layout.addLayout(downlay)
        self.setLayout(layout)

        # object oriented style using UTILS_QT.myplot()
        self.scheme_plot = UTILS_QT.myplot(self.p_lower_l,xlabel = ['time', 's'], ylabel =['',''],logmode=False)
        self.data_plot = UTILS_QT.myplot(self.p_upper_l,xlabel = ['time', 's'], ylabel = ['Signal','a.u.'],logmode=False)
        self.standErrorMeans = UTILS_QT.myplot(self.p_lower_r,xlabel= ['freq', 's'], ylabel = ['Relative signal',''],logmode=False)
        self.hist  = UTILS_QT.myplot(self.p_upper_r,xlabel= ['probability', 'a.u.'], ylabel = ['Counts','kcps'],logmode=False)
        self.hist.plots.append(self.p_upper_r.plot([0],[0],stepMode=True, fillLevel=0, brush=(0, 0, 255, 80)))
        self.hist.plots[0].rotate(-90)
        self.psp = UTILS_QT.pulses_scheme_plot(self.scheme_plot)

        self.p_upper_l.setTitle('Data')
        self.p_lower_l.setTitle('Pulses Scheme')
        self.p_lower_r.setTitle('Statistics')
        self.p_upper_r.setTitle('Histogram')

    def plot_histogramm(self,data):

        datay,datax = np.histogram(data,bins= 20)
        self.hist.updateSubplot(0,dataX = -datax[0:-1], dataY = datay)



class SSR_controls(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.initGUI()

    def initGUI(self):

        self.single_shot = UTILS_QT.SingleShotControls()
        vbox = QtGui.QVBoxLayout()

        self.plotcontrols = UTILS_QT.plotcontrols()
        self.startcontrols = UTILS_QT.startstopbtn()



        self.s = saver(category='SingleShot')
        # TODO make save on Dropbox or D:
        vbox.addWidget(self.single_shot)
        vbox.addWidget(self.startcontrols)
        vbox.addWidget(self.plotcontrols)

        vbox.addWidget(self.s)
        self.setLayout(vbox)
        self.setMaximumWidth(200)



    # all controls goes here

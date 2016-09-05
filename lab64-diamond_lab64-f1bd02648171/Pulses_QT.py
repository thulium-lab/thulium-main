from PySide import QtCore, QtGui
from pyqtgraph import PlotWidget, ImageView, ImageItem, GraphicsLayoutWidget
#from gageStruc import *
import numpy as np
import time
import UTILS_QT
#import NI_thread_qt
from savedata import saver

class Pulses(QtGui.QWidget):
    def __init__(self, parent=None, gage = None, d= None, s =None, NI = None, fpga = None):

        QtGui.QWidget.__init__(self, parent)
        self.initGUI()
        self.fpga = fpga
        self.gage = gage
        self.d = d
        self.NI = NI
        self.s = s
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.mainloop)
        self.dt = 100
        self.dict = {0:self.align,1:self.rabi,2:self.fid,3:self.rabi,4:self.rabi, 5:self.initial}
        self.data = None
        self.stop = False

    def initGUI(self):
        self.plot = PulsesPlot()
        self.controls = PulsesControls()
        layout = QtGui.QHBoxLayout()
        layout.addWidget(self.plot)
        layout.addWidget(self.controls)
        self.setLayout(layout)
        self.inicons()

    def inicons(self):
        self.controls.startcontrols.startBtn.clicked.connect(self.PulsesStartStop)
        self.controls.scheme.currentIndexChanged['QString'].connect(self.visibleWidget)
        self.controls.s.savebtn.clicked.connect(self.saveData)

    def restoredata(self):
        if self.controls.s.checkRestore.isChecked():


            data = self.controls.s.restore()
            if len(self.plot.data_plot.plots) < 2:
                self.plot.data_plot.addCurve(datax=data['times'],datay = data['data'],name='restored')

            else:
                # todo think about plotting of restored data
                pass

    def saveData(self):

        data = {}
        data['data'] = self.data
        data['times'] = self.times
        #data['timestart'] = self.t0
        data['comment'] = self.controls.s.commentsWindow.toPlainText()
        data['freq'] = self.controls.pulsescontrols.F()
        data['power'] = self.controls.pulsescontrols.P()
        self.controls.s.save(data=data)

    def visibleWidget(self, currentIndex):
        pass
        # self.controls.rabicontrols.hide()
        # self.controls.fidcontrols.hide()
        # self.controls.echocontrols.hide()
        # self.controls.dict_schemes[currentIndex].setVisible(True)

    def PulsesStartStop(self):

        if self.timer.isActive():
            self.timer.stop()
            self.s.Off()
            self.fpga.run_sequence(self.fpga.programm_exc_enable(),1)
            self.stop = True
            #self.data = None

        else:
        # prepare DTG
            self.data = None
            self.stop = False
            self.setDTG()
            self.setSMIQ()
            self.setGAGE()
            self.iterator = 1
            self.timer.start(self.dt)

    def align(self):

        times = np.arange(-self.controls.pulsescontrols.tfinish.value(),
                          self.controls.pulsescontrols.tfinish.value(),
                          self.controls.pulsescontrols.iterations.value())
        data = []
        texccoll = self.controls.pulsescontrols.readouts.value()
        self.controls.pulsescontrols.progress.setMaximum(times.shape[0])


        for i,t in enumerate(times):

            prog  = self.fpga.programm_align_exc_col(
                                        tau_exc=int(texccoll),
                                        tau_coll=int(texccoll),
                                        tau_shift= int(t),
                                        num_repeats=int(self.controls.pulsescontrols.numofreps.value()),
                                        )


            status,c,refc,col_signal,col_ref_signal = self.fpga.run_sequence(
                programm= prog,
                number_repeats=1,
            detectors=self.controls.startcontrols.acqType.currentIndex())

            if self.controls.startcontrols.acqType.currentIndex():
                data.append(col_signal)
            else:
                data.append(c)



            self.plot.psp.plotprograms(prog)
            QtCore.QCoreApplication.processEvents()

            self.controls.pulsescontrols.progress.setValue(i)
        return times,data
        # TODO make a skeleton of a pulses function general, maybe a class

    def initial(self):

        times = np.arange(0,
                          self.controls.pulsescontrols.tfinish.value(),
                          self.controls.pulsescontrols.iterations.value())
        data = []
        texccoll = self.controls.pulsescontrols.readouts.value()
        self.controls.pulsescontrols.progress.setMaximum(times.shape[0])


        for i,t in enumerate(times):

            prog  = self.fpga.programm_initialisation(
                                        tau_readout=int(texccoll),
                                        tau_delay= int(t),
                                        num_repeats=int(self.controls.pulsescontrols.numofreps.value()),
                                        )


            status,c,refc,col_signal,col_ref_signal = self.fpga.run_sequence(
                programm= prog,
                number_repeats=1,
            detectors=self.controls.startcontrols.acqType.currentIndex())

            if self.controls.startcontrols.acqType.currentIndex():
                data.append(col_signal*1.0/col_ref_signal)
            else:
                data.append(c*1.0/refc)



            self.plot.psp.plotprograms(prog)
            QtCore.QCoreApplication.processEvents()

            self.controls.pulsescontrols.progress.setValue(i)
        return times,data

    def rabi(self):



        times = np.arange(self.controls.pulsescontrols.dt.value(),
                          self.controls.pulsescontrols.tfinish.value(),
                          self.controls.pulsescontrols.iterations.value())

        data = []
        ref = [3000,1e6]
        self.controls.pulsescontrols.progress.setMaximum(times.shape[0])
        for i,t in enumerate(times):
            if not self.stop:
                programm=self.fpga.programm_rabi(
                                            tau_exc=int(3e5),
                                            tau_del=int(self.controls.pulsescontrols.tfinish.value()+3e3),
                                            tau_r= int(t),
                                            number_of_repeats=int(self.controls.pulsescontrols.numofreps.value()),
                                            t_signal = int(self.controls.pulsescontrols.readouts.value()),
                                            t_ref_delay=5*int(self.controls.pulsescontrols.readouts.value()),
                                            t_ref = ref[self.controls.startcontrols.acqType.currentIndex()]
                                            )

                status,c,refc,col_signal,col_ref_signal = self.fpga.run_sequence(
                    programm=programm,
                    number_repeats=1,
                    detectors=self.controls.startcontrols.acqType.currentIndex()
                )
                if self.controls.startcontrols.acqType.currentIndex():
                    if col_ref_signal != 0:
                        #data.append(col_ref_signal) # to see reference
                        #data.append(col_signal)
                        data.append(1.0*col_signal/col_ref_signal)
                    else:
                        data.append(1.0*col_signal)
                else:
                    if refc == 0:
                        data.append(1.0*c)
                    else:
                        data.append(1.0*c/refc)


                self.plot.psp.plotprograms(programm=programm)
                QtCore.QCoreApplication.processEvents()
                self.controls.pulsescontrols.progress.setValue(i)
        return times,data

    def fid(self):



        times = np.arange(self.controls.pulsescontrols.dt.value(),
                          self.controls.pulsescontrols.tfinish.value(),
                          self.controls.pulsescontrols.iterations.value())

        data = []
        self.controls.pulsescontrols.progress.setMaximum(times.shape[0])
        for i,t in enumerate(times):
            programm=self.fpga.programm_fid(
                                        tau_exc=int(3e4),
                                        tau_rest=int(self.controls.pulsescontrols.tfinish.value()+1.5e3),
                                        tau_fid= int(t),
                                        number_of_repeats=int(self.controls.pulsescontrols.numofreps.value()),
                                        t_signal = int(self.controls.pulsescontrols.readouts.value()),
                                        t_ref_delay=400,
                                        t_ref = 3000,
                                        tau_pi2= int(self.controls.pulsescontrols.pi_2.value()),
                                        tau_pi=int(self.controls.pulsescontrols.pi.value())
                                        )

            status,c,refc,col_signal,col_ref_signal = self.fpga.run_sequence(
                programm=programm,
                number_repeats=1)
            if refc == 0:
                data.append(0)
            else:
                data.append(1.0*c/refc)


            self.plot.psp.plotprograms(programm=programm)
            QtCore.QCoreApplication.processEvents()
            self.controls.pulsescontrols.progress.setValue(i)
        return times,data

    def mainloop(self):

        self.times,data = self.dict[self.controls.scheme.currentIndex()]()

        if self.data is None:
            self.data = np.array(data)
        else:
            self.data = ((self.iterator-1)*self.data + np.array(data))/self.iterator

        self.iterator += 1
#        self.plotUpdate(times,self.data)
        self.plotUpdate(self.times,data=self.data,instant_data=data)
        QtCore.QCoreApplication.processEvents()

    def setDTG(self):
        pass
        # see in the matlab code

    def setSMIQ(self):

        f = self.controls.pulsescontrols.F()*1e9
        p = self.controls.pulsescontrols.P()
        print f,p,'Hz, dbm:SMIQ'
        self.s.CW(f=f,power=p)
        self.s.On()

    def setGAGE(self):
        pass
        # see in the matlab code
        # Acquire from trigger or during the first time in the sequence
        # So, acquire since the first

    def plotUpdate(self,times,data,instant_data):

        times = np.array(times)*1e-9

        if len(self.plot.data_plot.plots) == 0:
            self.plot.data_plot.addCurve(times,datay=data,name = 'av data', color='g')
            #self.plot.data_plot.addCurve(times,datay=instant_data,name = 'inst data',color='r')
        else:

            #self.plot.data_plot.updateSubplot(1,times,instant_data)
            self.plot.data_plot.updateSubplot(0,times,data)

class PulsesPlot(QtGui.QWidget):
    def __init__(self, parent=None, gage = None, d= None, s =None, NI = None):

        QtGui.QWidget.__init__(self, parent)
        self.initGUI()

    def initGUI(self):

        self.p_upper = PlotWidget()
        self.p_lower_l = PlotWidget()
        self.p_lower_r = PlotWidget()
        layout = QtGui.QVBoxLayout()
        downlay = QtGui.QHBoxLayout()

        downlay.addWidget(self.p_lower_l)
        downlay.addWidget(self.p_lower_r)

        layout.addWidget(self.p_upper)
        layout.addLayout(downlay)
        self.setLayout(layout)

        # object oriented style using UTILS_QT.myplot()
        self.scheme_plot = UTILS_QT.myplot(self.p_upper,xlabel = ['time', 's'], ylabel =['',''],logmode=False)
        self.data_plot = UTILS_QT.myplot(self.p_lower_l,xlabel = ['time', 's'], ylabel = ['Signal','a.u.'],logmode=False)
        self.fft_data_plot = UTILS_QT.myplot(self.p_lower_r,xlabel= ['freq', 'Mhz'], ylabel = ['Relative signal',''],logmode=False)

        self.psp = UTILS_QT.pulses_scheme_plot(self.scheme_plot)

        # HARD coding style of plotting
        # self.p1 = self.p_upper.getPlotItem()
        # self.p2 = self.p_lowerl.getPlotItem()
        # self.p1.addLegend()
        # self.p1data = self.p1.plot([0],pen = 'r', name = 'averaged')
        # self.p2data = self.p1.plot([0],pen = 'g', name = 'instant')
        # self.p1.setLabel('bottom','Time','ns')
        # self.p2.setLabel('bottom','Freq','kHz')
        self.p_upper.setTitle('Pulse scheme')
        self.p_lower_l.setTitle('Pulses data')
        self.p_lower_r.setTitle('Pulses data FFT')

        #self.dataplot = self.data_plot.addCurve([0],[0])

class PulsesControls(QtGui.QWidget):
    def __init__(self, parent=None, gage = None, d= None, s =None, NI = None):

        QtGui.QWidget.__init__(self, parent)
        self.initGUI()

    def initGUI(self):

        vbox = QtGui.QVBoxLayout()
        self.gagecontrols = UTILS_QT.acqboardcontrols()
        self.plotcontrols = UTILS_QT.plotcontrols()
        self.startcontrols = UTILS_QT.startstopbtn()

        self.scheme = QtGui.QComboBox()
        self.scheme.addItems(['Align','Rabi','FID','Echo simple','Echo w 3Pi/2','Initialisation','Readout','T1'])

        vbox.addWidget(self.gagecontrols)
        vbox.addWidget(self.plotcontrols)
        vbox.addWidget(self.startcontrols)
        vbox.addWidget(self.scheme)

        self.rabicontrols = UTILS_QT.rabiControls()
        self.fidcontrols = UTILS_QT.fidControls()
        self.echocontrols = UTILS_QT.echoControls()
        self.pulsescontrols = UTILS_QT.pulsesControls()
        # self.dict_schemes = {
        #                      'Align':self.rabicontrols,
        #                      'Rabi':self.rabicontrols,
        #                      'FID': self.fidcontrols,
        #                      'Echo simple':self.echocontrols,
        #                      'Echo w 3Pi/2':self.echocontrols}

        self.dict_schemes = {
                             'Align':self.pulsescontrols,
                             'Rabi':self.pulsescontrols,
                             'FID': self.pulsescontrols,
                             'Echo simple':self.pulsescontrols,
                             'Echo w 3Pi/2':self.pulsescontrols}


        # vbox.addWidget(self.rabicontrols)
        # vbox.addWidget(self.fidcontrols)
        # vbox.addWidget(self.echocontrols)
        # self.fidcontrols.hide()
        # self.echocontrols.hide()
        vbox.addWidget(self.pulsescontrols)
        self.s = saver(category='Pulses')
        vbox.addWidget(self.s)
        self.setLayout(vbox)
        self.setMaximumWidth(200)


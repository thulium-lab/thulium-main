__author__ = 'Vadim Vorobyov'

from PySide import QtCore, QtGui
from pyqtgraph import PlotWidget, ImageView, ImageItem, GraphicsLayoutWidget, PlotItem
import pyqtgraph as pg
# from gageStruc import *
import numpy as np
import time
import UTILS_QT
from savedata import saver
# import NI_thread_qt
from Fiits import LorentzFit

class ESR(QtGui.QWidget):

    def __init__(self, gage, parent=None, d= None, NI = None, smiq = None, fpga = None):
        QtGui.QWidget.__init__(self, parent)
        self.initGUI()
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.mainloop)
        #self.gage = gage
        self.d = d
        #self.NI = NI
        self.smiq = smiq
        self.i = 0
        self.cw_spectrum_data_av = None
        self.int_spectrum_referenced = None
        self.spec2d = None
        self.dt = 100
        self.fpga = fpga
        self.fpga.run_sequence(self.fpga.programm_exc_enable(),1)

    def initGUI(self):

        self.plot = ESR_plot()
        self.controls = ESR_controls()
        layout = QtGui.QHBoxLayout()
        layout.addWidget(self.plot)
        layout.addWidget(self.controls)
        self.setLayout(layout)

        self.inicons()
        # connections

    def inicons(self):

        self.controls.esrcontrols.timercontrols.startBtn.clicked.connect(self.startstop)
        # self.controls.savedata.clicked.connect(self.savedata)
        self.controls.esrcontrols.plotcontrols.setBtn.clicked.connect(self.plotadjust)
        self.controls.esrcontrols.plotcontrols.autoBtn.clicked.connect(self.plotauto)
        self.controls.s.savebtn.clicked.connect(self.savedata)
        self.controls.s.itemnumber.valueChanged.connect(self.restoredata)


#### ESR core functions

    def startstop(self):
        print 'Button click'
        if self.timer.isActive():
            self.timer.stop()
            #self.d.Stop()
            self.smiq.CW()
            self.smiq.Off()
            self.fpga.run_sequence(
                programm=self.fpga.programm_exc_enable(),
                number_repeats=1
            )

        else:
            self.startESR()

        # TODO make threading in order not to freeze the process
        # TODO make saving of the data more accurate

    def startESR(self):

        self.fmin,self.fmax = self.controls.esrcontrols.F()
        self.plot.vLine5.setValue(self.fmin)
        self.plot.vLine6.setValue(self.fmax)
        self.fnum = self.controls.esrcontrols.Num()
        self.power = self.controls.esrcontrols.Power()
        #range = self.controls.gagecontrols.Range() for gage card or vova's

        df = (self.fmax - self.fmin) / (self.fnum)
        self.freqs = np.arange(self.fmin,self.fmax-0.5*df,df)
        #stat = self.setGage(channelRange=range)

        # #if stat < 0:
        #     print 'Error in gage', self.gage.status(stat)
        #     return
        # elif stat == 0:
        #     print ' Gage Ok!'
        # else:
        #     print 'Warning, check gage', self.gage.status(stat)

        #self.setDTG(self.controls.esrcontrols)
        self.setSMIQ()

        self.restartdata()
        self.time = QtCore.QTime()
        self.time.start()
        self.t0 = self.time.currentTime().toString('hh:mm:ss')
        print self.t0, 'time start'
        self.times = []
        self.timer.start(self.dt)   # 100 ms
        print 'Start ESR!'

    def restartdata(self):
        self.int_spectrum_referenced = None
        self.cw_spectrum_data_av = None
        self.spec2d = None
        self.i = 0

    def mainloop(self):
        # for two detectors ration referencing
        self.i+=1
        print self.i
        self.times.append(self.time.elapsed())

        #self.cw_spectrum_data = self.gage.getESR(self.fnum,self.i, self.NI)


        # t = 1e5
        # t_delay = 1e3
        # t_ref = 1e5

        t, t_delay = self.controls.esrcontrols.DurationDelay()
        t_ref = t
        numrep  = self.controls.esrcontrols.InternalRepeats()
        det_type = self.controls.esrcontrols.timercontrols.acqType.currentIndex()

        regime = self.controls.esrcontrols.regime.currentIndex()

        if not regime:

            status, c,rc,s,rs = self.fpga.run_sequence(
                programm= self.fpga.programm_esr(
                    t= t,
                    t_delay=t_delay,
                    t_ref = t_ref,
                    number_of_repeats = numrep,
                ),
                number_repeats=self.controls.esrcontrols.Num(),
                detectors = det_type
            )

        else:

            status, c,rc,s,rs = self.fpga.run_sequence(
                programm= self.fpga.programm_pulsed_esr(
                    tau_exc= self.controls.esrcontrols.readout.controldict["excitation"].valuebox.value(),
                    tau_delay=t_delay,
                    tau_pi=t,
                    t_signal=self.controls.esrcontrols.readout.controldict["detect"].valuebox.value(),
                    t_ref_delay=self.controls.esrcontrols.readout.controldict["refdelay"].valuebox.value(),
                    t_ref = self.controls.esrcontrols.readout.controldict["reference"].valuebox.value(),
                    num_repeats = numrep
                ),
                number_repeats=self.controls.esrcontrols.Num(),
                detectors = det_type
            )

            self.plot.psp.plotprograms(self.fpga.programm_pulsed_esr(
                    tau_exc= self.controls.esrcontrols.readout.controldict["excitation"].valuebox.value(),
                    tau_delay=t_delay,
                    tau_pi=t,
                    t_signal=self.controls.esrcontrols.readout.controldict["detect"].valuebox.value(),
                    t_ref_delay=self.controls.esrcontrols.readout.controldict["refdelay"].valuebox.value(),
                    t_ref = self.controls.esrcontrols.readout.controldict["reference"].valuebox.value(),
                    num_repeats = numrep
                ))
        # was before
        #
        # if det_type == 0:
        #     data  = self.fpga.data
        #     #print len(data)
        #     self.cw_spectrum_data = np.array(divmod(data[0],2**32)).reshape((1,2))
        #     self.cw_spectrum_data = np.append(self.cw_spectrum_data,
        #                                   np.diff(np.array([divmod(i,2**32) for i in data]),axis = 0)*1.0, axis = 0)
        # elif det_type == 1:
        #     data  = self.fpga.data
        #     data1 = self.fpga.data1
        #     self.cw_spectrum_data = np.array([data1[0],data[0]]).reshape((1,2))
        #     self.cw_spectrum_data = np.append(self.cw_spectrum_data,
        #                                   np.diff(np.array([data1,data]).T,axis = 0)*1.0, axis = 0)

        data = np.array(self.fpga.data).reshape((-1,7))
        print data.shape, 'shape of the data', numrep

        if det_type == 1:
            data_signal = data[0,0]
            data_refsignal = data[0,1]
            data_laser = data[0,2]
            data_reflaser = data[0,3]

            data_signal = np.append(data_signal, np.diff(data[:,0]))
            data_refsignal = np.append(data_refsignal,np.diff(data[:,1]))
            data_laser = np.append(data_laser,np.diff(data[:,2]))
            data_reflaser = np.append(data_reflaser,np.diff(data[:,3]))

            try:
                data_signal = 1.0*data_signal/data_laser
            except:
                print data_laser
            data_refsignal = 1.0*data_refsignal/data_reflaser

            self.cw_spectrum_data = data_signal/data_refsignal


        # if self.cw_spectrum_data_av is None:
        #     self.cw_spectrum_data_av = self.cw_spectrum_data
        # else:
        #     self.cw_spectrum_data_av = ((self.i-1) * self.cw_spectrum_data_av + self.cw_spectrum_data)/self.i
        #

        if self.int_spectrum_referenced is None:
            self.int_spectrum_referenced = self.cw_spectrum_data

        else:
            self.int_spectrum_referenced = ((self.i-1)*self.int_spectrum_referenced +
                                            self.cw_spectrum_data)/self.i
        try:
            current_ratio = self.cw_spectrum_data[:]
        except:
            current_ratio = self.cw_spectrum_data[:]

        plot2d = 'instant_with_flattening'

        if plot2d == 'averaged':
            if self.spec2d is None:
                self.spec2d = self.int_spectrum_referenced
            self.spec2d = np.vstack((self.spec2d,self.int_spectrum_referenced))
        elif plot2d == 'instant':
            if self.spec2d is None:
                self.spec2d = current_ratio
            self.spec2d = np.vstack((self.spec2d,current_ratio))
        elif plot2d == 'instant_with_flattening':
            # make shift all esr with equal maximum
            coeff = 1.0/max(current_ratio)
            current_ratio *=coeff
            if self.spec2d is None:
                self.spec2d = current_ratio
            self.spec2d = np.vstack((self.spec2d,current_ratio))

        self.updateplot()
        if self.update2d(self.i,1):
            #if self.i > 150:
            #    self.plot.view.setAspectLocked(False)
            self.update2dplot()
        return

    def mainloopSubstr(self):
        # for two detectors substraction referencing
        self.i+=1
        print self.i
        #self.cw_spectrum_data = self.gage.getESR(self.fnum,self.i, self.NI)




        if self.cw_spectrum_data_av is None:
            self.cw_spectrum_data_av = self.cw_spectrum_data
        else:
            self.cw_spectrum_data_av = ((self.i-1) * self.cw_spectrum_data_av + self.cw_spectrum_data)/self.i
        if self.AcqCfg.u32Mode == 1026:
            if self.int_spectrum_referenced is None:
                self.int_spectrum_referenced = self.cw_spectrum_data_av[:,0]-self.cw_spectrum_data_av[:,1]
            else:
                self.int_spectrum_referenced = (self.i-1)*self.int_spectrum_referenced +\
                                               (self.cw_spectrum_data_av[:,0]-self.cw_spectrum_data_av[:,1])/self.i
        current_ratio = self.cw_spectrum_data[:,0]-self.cw_spectrum_data[:,1]

        plot2d = 'instant'

        if plot2d == 'averaged':
            if self.spec2d is None:
                self.spec2d = self.int_spectrum_referenced
            self.spec2d = np.vstack((self.spec2d,self.int_spectrum_referenced))
        elif plot2d == 'instant':
            if self.spec2d is None:
                self.spec2d = current_ratio
            self.spec2d = np.vstack((self.spec2d,current_ratio))




        self.updateplot()
        if self.update2d(self.i,1):
            if self.i > 150:
                self.plot.view.setAspectLocked(False)
            self.update2dplot()
        return

    def mainloopBalanced(self):
        # balanced
        self.i+=1
        print self.i
        self.cw_spectrum_data = self.gage.getESR(self.fnum,self.i, self.NI)


        if self.cw_spectrum_data_av is None:
            self.cw_spectrum_data_av = self.cw_spectrum_data
        else:
            self.cw_spectrum_data_av = ((self.i-1) * self.cw_spectrum_data_av + self.cw_spectrum_data)/self.i
        if self.AcqCfg.u32Mode == 1026:
            if self.int_spectrum_referenced is None:
                self.int_spectrum_referenced = (self.cw_spectrum_data_av[:,0])
            else:
                self.int_spectrum_referenced = ((self.i-1)*self.int_spectrum_referenced +
                                                (self.cw_spectrum_data_av[:,0]))/self.i
        current_ratio = self.cw_spectrum_data[:,0]

        plot2d = 'instant'

        if plot2d == 'averaged':
            if self.spec2d is None:
                self.spec2d = self.int_spectrum_referenced
            self.spec2d = np.vstack((self.spec2d,self.int_spectrum_referenced))
        elif plot2d == 'instant':
            if self.spec2d is None:
                self.spec2d = current_ratio
            self.spec2d = np.vstack((self.spec2d,current_ratio))




        self.updateplot()
        if self.update2d(self.i,1):
            if self.i > 150:
                self.plot.view.setAspectLocked(False)
            self.update2dplot()
        return

#### Externally called functions

    def initESR(self, f, p, num, channelRange, funiform = True, sampleRate=None, esr = None):
        # function to initialize esr
        stat = self.setGage(num = num, channelRange=channelRange, sampleRate=sampleRate)
        if stat < 0:
            print 'Im out'
            return
        else:
            print ' Gage Ok!'

        self.setDTG(esr)
        self.setSMIQ(f,p,num, funiform=funiform)

    def initESR1(self, gage=None, esr=None, lockin=None, funiform = True):
        # updated version takes classes of controls instead of just variables
        # as arguments
        f1,f2 = esr.F()
        num = esr.Num()
        channelRange = gage.Range()
        sampleRate = gage.SampleRate()

        stat = self.setGage(num = num, channelRange=channelRange, sampleRate=sampleRate)
        self.gage.status(stat)

        if lockin.Enabled():
            print 'setting the NI'
            self.setNI(esr)

        self.setDTG(esr)
        self.setSMIQ(f=[f1,f2],p=esr.Power(),num=num, funiform=funiform, lockin =lockin)

    def getESR(self, mean=True, segsize = None, lockin = None,fnum = None):
        # function called after initialization
        # could be called in a loop, for time acquisition
        # if mean is True, means, average every segment, and pass to the CPU, otherwise, transfer raw data

        if fnum is None:
            return None, None


        if lockin is not None:
            if lockin.Enabled():
                nithread = NI_thread_qt.getData(ID=1,name='', counter=1,ni = self.NI)
                nithread.start()
        if mean:
            data = self.gage.getESR(fnum,1, self.NI)
        else:
            if segsize is not None:
                data = self.gage.getMultAcq(fnum,segsize,1,self.NI)
            else:
                segsize = self.m
                data = self.gage.getMultAcq(fnum,i=1,segsize=segsize,NI=self.NI)

        if lockin is not None:
            if lockin.Enabled():
                while nithread.isAlive():
                    time.sleep(0.1)
                return data, nithread.data
            else:
                return data, None
        else:
            return data, None

#### Instruments functions

    def setNI(self, esr):
        sampleRateNI = 10000
        acqTimeNI = esr.Num()*0.002
        self.NI.prepareAcq(rate= sampleRateNI, dwelltime= acqTimeNI)
        #here I want to create a thread which will wait for acquision, acquire and quit

    def stopNI(self):
        self.NI.killacqtask()

    def setGage(self, num = None, channelRange = None, sampleRate = None):

        if channelRange is None:
            channelRange = 1000

        self.AcqCfg = CsAqCfg()

        if sampleRate is None:
            self.AcqCfg.i64SampleRate = int(1e7)
        else:
            self.AcqCfg.i64SampleRate = int(sampleRate)
        self.AcqCfg.u32Size = sizeof(CsAqCfg)
        try:
            m = self.AcqCfg.i64SampleRate * float(self.controls.dwelltime.text()) * 1e-3  # Samples to acquire per point
        except:
            m = 0.1 *1e7 * 1e-3
        self.m = m
        if num is None:
            try:
                self.AcqCfg.u32SegmentCount = int(self.controls.numberoffreq.text())
            except:
                self.AcqCfg.u32SegmentCount = 400
                print 'make default numb of freq'
        else:
            self.AcqCfg.u32SegmentCount = int(num)


        self.AcqCfg.i64Depth = int(m)
        self.AcqCfg.u32Mode = 1026
        self.AcqCfg.i64TriggerTimeout = 30000000         #    %30s timeout
        self.AcqCfg.u32SampleSize = 2                   # TODO Check what is correct
        self.AcqCfg.i64SegmentSize = int(m)
        self.AcqCfg.u32ExtClk = 0
        self.AcqCfg.i64TriggerDelay = 0
        self.AcqCfg.i64TriggerHoldoff = 0

        self.CsTrCfg = CSTRIGGERCONFIG()
        self.CsTrCfg.u32Size = sizeof(CSTRIGGERCONFIG)
        self.CsTrCfg.i32Level = 25
        self.CsTrCfg.i32Source = -1
        self.CsTrCfg.u32ExtTriggerRange = 2000
        self.CsTrCfg.u32ExtCoupling = CS_COUPLING_DC
        self.CsTrCfg.u32Condition = CS_TRIG_COND_POS_SLOPE

        self.CsChCfg = CSCHCONFIG()
        self.CsChCfg.u32Size = sizeof(CSCHCONFIG)
        self.CsChCfg.u32InputRange = channelRange
        self.CsChCfg.u32Impedance = 50
        self.CsChCfg.i32DcOffset = 0#self.CsChCfg.u32InputRange/2
        self.CsChCfg.u32Filter = 1
        self.CsChCfg.u32Term = CS_COUPLING_DC

        # SET THE BOARD
        # Check Status
        status = self.gage.hllDll.CsGetStatus(self.gage.h)
        if status is not 0:
            print 'Error, board busy, stop other processe'
            if self.timer.isActive():
                self.time.stop()
            return -1
        else:
            print 'Board Ready for ESR'
        # gageSet (CsAqCfg, CsTrCfg, CsChCfg)
        stat = self.gage.gageSetESR(self.AcqCfg, self.CsTrCfg, self.CsChCfg)
        if stat > 0:
            return 1
        else:
            return -1

    def setDTG(self, esr):

        self.d.setESR(1,esr.Num(),1)
        self.d.Run()

    def setSMIQ(self, f=None,p=None, num = None, funiform = True, lockin=None):

        self.smiq.Off()
        self.smiq.CW()
        if lockin is None:
            self.smiq.FM()
        else:
            if lockin.Enabled():
                self.smiq.FM(fcentral=2.87e9, df=lockin.ModAmp(), modulationfreq=lockin.ModFreq()*1000, power=0)
            else:
                self.smiq.FM()

        if f is None:
            print self.fmin,self.fmax,self.power, self.fnum, 'listmode'
            self.smiq.listmode(self.fmin*1e9,self.fmax*1e9,self.power, self.fnum)
        else:
            if funiform:
                print f[0], f[1], p, num, 'listmode'
                self.smiq.listmode(f[0]*1e9, f[1]*1e9, p, num)
            else:
                print 'listmode non-uniform',f, p
                self.smiq.listmodeExplicit(f, p)

#### PLOT FUNCTIONS

    def update2d(self,i,n):
        if divmod(i,n)[1] == 0:
            return True
        else:
            return False

    def updateplot(self):
        #self.plot.p1.enableAutoRange()
        self.plot.p1data.setData(self.freqs[:],self.cw_spectrum_data[:])
        self.plot.p2data.setData(self.freqs[:],self.int_spectrum_referenced[:])

    def update2dplot(self):
        print 'plot 2d'
        self.plot.img.setImage(self.spec2d.T)
        f0 = self.controls.esrcontrols.F()[0]
        df = self.controls.esrcontrols.F()[1]-self.controls.esrcontrols.F()[0]
        self.plot.img.setRect(QtCore.QRectF(f0,0,df,self.spec2d.T.shape[1]))
        return

    def plotadjust(self):

        ymin,ymax = self.controls.esrcontrols.plotcontrols.YLim()
        if ymin is not None:
            self.plot.p1.setYRange(ymin,ymax)

    def plotauto(self):
        self.plot.p1.enableAutoRange()
        self.plot.p2.enableAutoRange()

    def savedata(self):
        print 'save Data'
        data = {}
        data['data2d'] = self.spec2d
        data['freq'] = [self.fmin, self.fmax]
        data['times'] = self.times
        data['timestart'] = self.t0
        data['comment'] = self.controls.s.commentsWindow.toPlainText()
        #data['sample rate'] = self.controls.gagecontrols.SampleRate()
        data['power'] = self.controls.esrcontrols.Power()
        self.controls.s.save(data=data)

    def restoredata(self):
        if self.controls.s.checkRestore.isChecked():
            data = self.controls.s.restore()
            try:
                self.plot.img.setImage(data['data2d'].T)
                f0 = data['freq'][0]
                df = data['freq'][1]-data['freq'][0]
                self.plot.img.setRect(QtCore.QRectF(f0,0,df,data['data2d'].shape[0]))
                time = data['times']
                time = np.array(time)
                time0 = QtCore.QTime.fromString(data['timestart'],"hh:mm:ss")
                time0ms = QtCore.QTime(0,0,0,0).msecsTo(time0)

                #times = [QtCore.QTime.fromString(t,"hh:mm:ss") for t in data['times']]
                #timesinms = [(t.second()*1000 + t.minute()*60000 + t.hour()*3600000) for t in times]

                b = np.ones((len(time)))

                self.plot.psdata.setData(x=time+time0ms,y=b)
            except:
                print 'no such file'

class ESR_plot(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.initGUI()

    def initGUI(self):
        self.plot = PlotWidget()
        self.sensorplot = PlotWidget()

        self.schemeplot = PlotWidget()
        self.scheme_plot = UTILS_QT.myplot(self.schemeplot,xlabel = ['time', 's'], ylabel =['',''],logmode=False)
        self.psp = UTILS_QT.pulses_scheme_plot(self.scheme_plot)


        date_axis = TimeAxisItem(orientation='bottom')
        #date_axis = pg.graphicsItems.DateAxisItem.DateAxisItem(orientation = 'bottom')
        self.sensorplot = PlotWidget(axisItems = {'bottom': date_axis})


        win = GraphicsLayoutWidget()
        win2 = PlotWidget()



        self.view = win.addViewBox(border = 'w', invertY = True)
        self.view.setAspectLocked(True)
        self.img = ImageItem()
        self.plotaxes = win2.getPlotItem()
        #self.view.addItem(self.img)
        #self.view.addItem(self.plotaxes)
        #self.view.


        data = np.random.normal(size=(1, 600, 600), loc=1024, scale=64).astype(np.uint16)
        self.img.setImage(data[0])
        self.plotaxes.getViewBox().addItem(self.img)


        # colormap
        pos = np.array([0., 1., 0.5, 0.25, 0.75])
        #pos2 = np.array([1.0,0.75,0.5,0.25,0.])
        pos2 = np.array([0.,0.25,0.5,0.75,1.0])
        color2 = np.array([[255,242,15,255], [245,124,15,255],[170,69,16,255],[91,50,0,255],[0,0,0,255]],dtype=np.ubyte)
        color = np.array([[0,255,255,255], [255,255,0,255], [0,0,0,255], (0, 0, 255, 255), (255, 0, 0, 255)], dtype=np.ubyte)
        cmap = pg.ColorMap(pos2, color2)
        lut = cmap.getLookupTable(0.0, 1.0, 256)
        self.img.setLookupTable(lut)
        #self.img.setLevels([-50,1])

        self.tw = QtGui.QTabWidget()
        self.tw.addTab(win2,'ESR data')
        self.tw.addTab(self.sensorplot,'B field')
        self.tw.addTab(self.schemeplot,'Scheme')

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.plot)
        #layout.addWidget(win2)
        layout.addWidget(self.tw)

        self.setLayout(layout)

        self.p1 = self.plot.getPlotItem()
        self.p2 = self.plot.getPlotItem()

        self.ps = self.sensorplot.getPlotItem()
        #self.p1.addLegend()
        self.p1data = self.p1.plot([0],pen = 'r')
        self.p2data = self.p1.plot([0],pen = 'g')
        self.psdata = self.ps.plot([],pen = 'w')
        self.ps.setLabel('left','Magnetic field', 'uT')

        self.vLine5 = pg.InfiniteLine(angle=90, movable=True)
        self.vLine6 = pg.InfiniteLine(angle=90, movable=True)
        self.plotaxes.addItem(self.vLine5, ignoreBounds=True)
        self.plotaxes.addItem(self.vLine6, ignoreBounds=True)

class TimeAxisItem(pg.AxisItem):

    def __init__(self, *args, **kwargs):
        super(TimeAxisItem,self).__init__(*args, **kwargs)

    def tickStrings(self, values, scale, spacing):
        # PySide's QTime() initialiser fails miserably and dismisses args/kwargs
        return [QtCore.QTime().addMSecs(value).toString('hh:mm:ss') for value in values]
        #return values

class ESR_controls(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.initGui()
    def initGui1(self):


        # init widgets
        self.fmin = QtGui.QLineEdit('2.86')
        self.fminl = QtGui.QLabel('Min f, GHz')
        hboxfmin = QtGui.QHBoxLayout()
        hboxfmin.addWidget(self.fminl)
        hboxfmin.addWidget(self.fmin)


        self.fmax = QtGui.QLineEdit('2.88')
        self.fmaxl = QtGui.QLabel('Max f, GHz')
        hboxfmax = QtGui.QHBoxLayout()
        hboxfmax.addWidget(self.fmaxl)
        hboxfmax.addWidget(self.fmax)


        self.dwelltime = QtGui.QLineEdit('1')
        self.dwelltimel = QtGui.QLabel('Dwell time, ms')
        hboxdt = QtGui.QHBoxLayout()
        hboxdt.addWidget(self.dwelltimel)
        hboxdt.addWidget(self.dwelltime)



        self.numberoffreq = QtGui.QLineEdit('400')
        self.numoffreqls = QtGui.QLabel('Number of freqs')
        hboxnf = QtGui.QHBoxLayout()
        hboxnf.addWidget(self.numoffreqls)
        hboxnf.addWidget(self.numberoffreq)

        self.power = QtGui.QLineEdit('0')
        self.powerl = QtGui.QLabel('MW power, db')

        hboxp = QtGui.QHBoxLayout()
        hboxp.addWidget(self.powerl)
        hboxp.addWidget(self.power)

        self.runBtn = QtGui.QPushButton('Run - Stop')
        self.savedata = QtGui.QPushButton('Save ...')

        self.commentl = QtGui.QLabel('Data comment')
        self.comment = QtGui.QTextEdit()

        self.ylim1 = QtGui.QLineEdit("")
        self.ylim2 = QtGui.QLineEdit("")
        self.yliml1 = QtGui.QLabel("ylim")
        self.setBtn = QtGui.QPushButton("Set")
        self.autoBtn = QtGui.QPushButton("Auto")

        limbox = QtGui.QHBoxLayout()
        limbox.addWidget(self.ylim1)
        limbox.addWidget(self.ylim2)
        limbox.addWidget(self.yliml1)
        limbox.addWidget(self.setBtn)
        limbox.addWidget(self.autoBtn)



        VBOX = QtGui.QVBoxLayout()
        VBOX.addLayout(hboxfmin)
        VBOX.addLayout(hboxfmax)
        VBOX.addLayout(hboxdt)
        VBOX.addLayout(hboxnf)
        VBOX.addLayout(hboxp)
        VBOX.addLayout(limbox)
        VBOX.addWidget(self.runBtn)
        VBOX.addWidget(self.savedata)
        VBOX.addWidget(self.commentl)
        VBOX.addWidget(self.comment)

        self.setLayout(VBOX)

        self.setMaximumWidth(200)

    def initGui(self):

        #self.gagecontrols = UTILS_QT.acqboardcontrols()
        self.esrcontrols = UTILS_QT.esrcontrols(addPlotControls=True, pulsesControls = True)

        self.s = saver(category = 'esr_data')



        self.vbox = QtGui.QVBoxLayout()
        self.vbox.addWidget(self.esrcontrols)
        #self.vbox.addWidget(self.gagecontrols)
        self.vbox.addWidget(self.s)
        self.setLayout(self.vbox)
        self.setMaximumWidth(200)

class sensor_esr_based():
    def __init__(self, plot):
        self.data = None
        self.plot = plot
        self.fit = LorentzFit(freqs = [], data = [])
        self.fs = np.array([])
        self.time = None

    def updatedata(self, newpeaceofdata):
        self.data = np.append(self.data,newpeaceofdata)

    def setdata(self,data):
        self.data = data

    def getfsall(self):
        fs = []
        for row in self.data:
            self.fit.updatedata(row)
            self.fit.findfit()
            fs.append(self.fit.f0)
        return fs

    def getnewfs(self):
        pass



    def plotme(self):
        self.plot.setData(self.time, self.fs)




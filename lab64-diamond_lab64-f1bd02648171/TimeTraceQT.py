__author__ = 'Vadim Vorobyov'


import numpy as np
#from GageControl import *
from pyqtgraph import PlotWidget
from PySide import QtCore, QtGui
from pyqtgraph import PlotWidget, ImageView, ImageItem, GraphicsLayoutWidget
import pyqtgraph as pg
import  UTILS_QT


#### Time Trace class for setting the CW measurements:
####
class timetrace(QtGui.QWidget):
    def __init__(self, parent=None, gage = None, d= None, fpga = None):

        QtGui.QWidget.__init__(self, parent)
        self.initGUI()
        self.maxpoints = 100
        self.timer = QtCore.QTimer()
        #self.timerext = QtCore.QTimer()
        self.timer.timeout.connect(self.runTTcycle)
        #self.timerext.timeout.connect(self.timer2timeoutrun)
        self.fpga = fpga
        self.data = np.zeros((3,self.maxpoints))
        self.instantdata = None
        self.n_step = 0
        self.d = d
        self.dt = 100 # this is the timer time step

    def initGUI(self):
        self.plot = timetraceplots()
        self.controls = timetracecontrols()
        #self.boardcontrols = acqboardcontrols()
        #self.tabs = QtGui.QTabWidget()

        #self.tabs.addTab(self.controls,'RunControl')
        #self.tabs.addTab(self.boardcontrols,'Acq Control')


        #self.tabs.setMaximumWidth(200)

        layout = QtGui.QHBoxLayout()
        layout.addWidget(self.plot)
        layout.addWidget(self.controls)
        self.setLayout(layout)
        self.initConn()

    def initConn(self):
        # actions connections
        self.controls.ttcontrols.timercontrols.startBtn.clicked.connect(self.runstoptimetrace)
        self.controls.ttcontrols.timercontrols.dt.valueChanged.connect(self.restartTimer)
        self.controls.ttcontrols.plotcontrols.setBtn.clicked.connect(self.plotadjust)
        self.controls.ttcontrols.plotcontrols.autoBtn.clicked.connect(self.plotauto)
        self.controls.gagecontrols.setBtn.clicked.connect(self.setGage)

    def setGage(self):
        self.gagenotinited = False
        rerun = False
        # if the time trace was running stop for a sec

        if self.timer.isActive():
            self.timer.stop()
            rerun = True

        samplerate = self.controls.gagecontrols.SampleRate()

        numOfSamples = self.controls.gagecontrols.NumberOfSamples()

        channelRange = self.controls.gagecontrols.Range()

        self.gage.InitCycle(
                sampleRate=samplerate,
                segmentSize=numOfSamples,
                numberOfSegments=1,
                channelRange=channelRange)

        if rerun:
            self.timer.start(self.dt)

    def runTTcycle(self):
        if self.controls.ttcontrols.rb1.isChecked():
            self.n_step+=1
            #data = self.gage.GetDataCycle()

            status, counts, refcounts, signal, refsignal = self.fpga.run_sequence(self.fpga.programm_timetrace)

            # new_val1 = np.mean(data[0])
            # new_val2 = np.mean(data[1])

            new_val1 = signal#np.mean(data[0])
            new_val2 = refsignal#np.mean(data[1])

            cur_data1 = self.data[1]
            cur_data2 = self.data[2]
            new_data1 = np.hstack((cur_data1[-self.maxpoints+1:], [new_val1]))
            new_data2 = np.hstack((cur_data2[-self.maxpoints+1:], [new_val2]))
            new_index = np.arange(self.n_step - len(new_data1) + 1,self.n_step + 0.01)
            self.data[0] = new_index
            self.data[1] = new_data1
            self.data[2] = new_data2



        # for samples
        # else:
        #     self.n_step+=1
        #     data = self.gage.GetDataCycle()
        #
        #     if self.instantdata is None:
        #         self.instantdata = np.zeros((3,data.shape[1]))
        #
        #     elif self.instantdata[0].shape[0] != data.shape[1]:
        #         self.instantdata = np.zeros((3,data.shape[1]))
        #
        #
        #     self.instantdata[0] = np.arange(data.shape[1])
        #     self.instantdata[1] = data[0]
        #     self.instantdata[2] = data[1]
        #
        #     if self.controls.ttcontrols.rb2.isChecked() and self.timer.isActive():
        #         self.timer.stop()
        self.updateplots()

    def restartTimer(self):
        self.dt = self.controls.ttcontrols.timercontrols.dT()
        if self.timer.isActive():
            print 'Stop'
            self.timer.stop()
            self.timer.start(self.dt)

    def externalstop(self):

        if self.timer.isActive():
            print 'Stop'
            self.timer.stop()

    def runstoptimetrace(self):

        self.dt = self.controls.ttcontrols.timercontrols.dT()

        if self.timer.isActive():
            print 'Stop'
            self.timer.stop()
            #self.d.Stop()
        else:
            #self.d.LaserOnOffStationary()
            #self.gage.GetInfo()

            #if self.gagenotinited:
                #self.gage.InitCycle()
                #self.setGage()
            #if self.gage.state == 'ESR':
                #self.setGage()


            print 'Starting timetrace....'
            if self.controls.ttcontrols.rb1.isChecked():
                self.timer.start(self.dt)
                print 'Live'
            elif self.controls.ttcontrols.rb2.isChecked():
                #self.timer.singleShot(0,self.runTTcycle)
                print 'Single shot, ommitted'
            elif self.controls.ttcontrols.rb3.isChecked():
                #self.timer.start(self.dt)
                print 'Repetitive Shot, ommited'

    def updateplots(self):


        multfactor = self.controls.ttcontrols.plotcontrols.MultFactor()

        if self.controls.ttcontrols.rb1.isChecked():
            self.plot.p1data.setData(self.data[0],self.data[1])
            self.plot.p2data.setData(self.data[0],self.data[2]*multfactor)
        else:
            self.plot.p1data.setData(self.instantdata[0],self.instantdata[1])
            self.plot.p2data.setData(self.instantdata[0],self.instantdata[2]*multfactor)

    def plotadjust(self):

        ymin,ymax = self.controls.ttcontrols.plotcontrols.YLim()
        if ymin is not None:
            self.plot.p1.setYRange(ymin,ymax)

    def plotauto(self):
        self.plot.p1.enableAutoRange()
        self.plot.p2.enableAutoRange()

    def collectionInitSimple(self, t = 1, controls = None):

        self.collectionInit(t= 1,
                            segmentSize=controls.NumberOfSamples(),
                            sampleRate=controls.SampleRate(),
                            channelRange=controls.Range())

    def collectionInit(self,t= 1, segmentSize = 1024, sampleRate = 10000000, channelRange = 10000):

        # Init GAGE PARAMETERS
        # Specify the time variable
        self.gage.InitCycle(segmentSize=segmentSize,
                                sampleRate=sampleRate,
                                channelRange=channelRange)

        self.times = np.arange(0,t,1)
        self.i2 = 0
        self.collectedCounts = np.array([])
        self.collectedCounts1 = np.array([])
        self.collectedCounts2 = np.array([])

    def startCollection(self):

        for t in self.times:
            newdata = self.gage.GetDataCycle()
            self.collectedCounts1 = newdata[0]
            self.collectedCounts2 = newdata[1]
            self.collectedCounts = newdata[0]-newdata[1] # For separate
            #self.collectedCounts = newdata[0] # Just for balanced detector

class timetraceplots(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.initGUI()

    def initGUI(self):
        self.plot = PlotWidget()
        layout = QtGui.QHBoxLayout()
        layout.addWidget(self.plot)
        self.setLayout(layout)
        self.p1 = self.plot.getPlotItem()
        self.p2 = self.plot.getPlotItem()
        self.p1.addLegend()
        self.p1data = self.p1.plot([0],pen = 'r',name = '   ch 1')
        self.p2data = self.p2.plot([0],pen = 'g', name = '  ch 2')
        self.vLine5 = pg.InfiniteLine(angle=90, movable=True)

        self.p1.addItem(self.vLine5, ignoreBounds=True)

class timetracecontrols(QtGui.QWidget):
    def __init__(self,parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.initGUI()
    def initGUI1(self):

        groupBox = QtGui.QGroupBox("Process control box")
        self.optionsbox = QtGui.QGroupBox("Options")
        self.rb1 = QtGui.QRadioButton("&Live timetrace")
        self.rb1.setChecked(True)
        self.rb2 = QtGui.QRadioButton("&Instant")
        self.rb3 = QtGui.QRadioButton("&Instant multiple")
        vertoptbox = QtGui.QVBoxLayout()
        vertoptbox.addWidget(self.rb1)
        vertoptbox.addWidget(self.rb2)
        vertoptbox.addWidget(self.rb3)
        self.optionsbox.setLayout(vertoptbox)


        self.startBtn = QtGui.QPushButton("&Start/Stop!")
        self.startBtn.setMinimumHeight(50)
        # self.xlim1 = QtGui.QLineEdit("")
        # self.xlim2 = QtGui.QLineEdit("")
        self.ylim1 = QtGui.QLineEdit("")
        self.ylim2 = QtGui.QLineEdit("")
        # self.xliml1 = QtGui.QLabel("xlim")
        self.yliml1 = QtGui.QLabel("ylim")
        self.setBtn = QtGui.QPushButton("Set")
        self.autoBtn = QtGui.QPushButton("Auto")
        self.setBtn.setMinimumHeight(50)
        self.autoBtn.setMinimumHeight(50)
        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.optionsbox)
        hbox = QtGui.QHBoxLayout()
        vbox.addLayout(hbox)
        vbox.addWidget(self.startBtn)
        self.plotLookOptions = QtGui.QGroupBox("Plot settings")
        #vplotoptbox1 = QtGui.QVBoxLayout()
#
        # hplotoptbox21 = QtGui.QHBoxLayout()
        hplotoptbox22 = QtGui.QHBoxLayout()
        hplotoptbox = QtGui.QHBoxLayout()


        # hplotoptbox21.addWidget(self.xliml1)
        # hplotoptbox21.addWidget(self.xlim1)
        # hplotoptbox21.addWidget(self.xlim2)

        hplotoptbox22.addWidget(self.yliml1)
        hplotoptbox22.addWidget(self.ylim1)
        hplotoptbox22.addWidget(self.ylim2)

        vplotoptbox2 = QtGui.QVBoxLayout()
        # vplotoptbox2.addLayout(hplotoptbox21)
        vplotoptbox2.addLayout(hplotoptbox22)

        setplotgoup = QtGui.QHBoxLayout()
        setplotgoup.addWidget(self.setBtn)
        setplotgoup.addWidget(self.autoBtn)

        vplotoptbox2.addLayout(setplotgoup)
        #vplotoptbox3 = QtGui.QVBoxLayout()
        #vplotoptbox3.addWidget(self.setBtn)
#        vplotoptbox3.addWidget(self.list)

        #hplotoptbox.addLayout(vplotoptbox1)
        hplotoptbox.addLayout(vplotoptbox2)

        self.multfactor = QtGui.QLineEdit('1')

        vbox.addWidget(self.multfactor)


        #hplotoptbox.addLayout(vplotoptbox3)
        #hplotoptbox.addWidget(self.autoBtn)
        self.plotLookOptions.setLayout(hplotoptbox)
        vbox.addWidget(self.plotLookOptions)


        self.windowLabel = QtGui.QLabel("Options1...")
        self.window_window = QtGui.QLineEdit("5...")
#        self.checkSameTab.setChecked(1)
        self.plotLookOptions = QtGui.QGroupBox("Other settings...")
        hplotoptbox = QtGui.QHBoxLayout()
        hplotoptbox.addWidget(self.windowLabel)
        hplotoptbox.addWidget(self.window_window)
        self.plotLookOptions.setLayout(hplotoptbox)
        vbox.addWidget(self.plotLookOptions)


        #vbox.addWidget(radio2)
        #vbox.addWidget(radio3)
        vbox.addStretch(1)
        groupBox.setLayout(vbox)
        vvbox = QtGui.QVBoxLayout()
        vvbox.addWidget(groupBox)
        vbox.addStretch(1)

        self.setLayout(vvbox)


        self.setMaximumWidth(200)

    def initGUI(self):

        self.ttcontrols = UTILS_QT.timetracecfg()
        self.gagecontrols = UTILS_QT.acqboardcontrols(setbtn=True)

        self.vbox = QtGui.QVBoxLayout()
        self.vbox.addWidget(self.ttcontrols)
        self.vbox.addWidget(self.gagecontrols)
        self.setLayout(self.vbox)
        self.setMaximumWidth(200)





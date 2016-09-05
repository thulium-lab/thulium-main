import time
from PySide import QtCore, QtGui
import numpy as np
from pyqtgraph import PlotWidget, ImageView, ImageItem, GraphicsLayoutWidget, PlotItem
import pyqtgraph as pg
class acqboardcontrols(QtGui.QWidget):
    def __init__(self, parent=None, setbtn = False, full = False):
        QtGui.QWidget.__init__(self, parent)
        self.setbtn = setbtn
        self.full = full
        self.initGUI()

    def initGUI(self):
        self.initWidgets()
        self.initLayout()

    def initWidgets(self):
        # initialize widgets
        self.coupling = QtGui.QComboBox()
        self.coupling.addItems(["DC","AC"])
        self.impedance = QtGui.QComboBox()
        self.impedance.addItems(["50","1e6"])
        self.lrate = QtGui.QLabel('Sample Rate')
        self.lnum = QtGui.QLabel('Sample Number')
        self.lpoints = QtGui.QLabel('Points in Alan')
        self.samplerate = QtGui.QLineEdit('10000000')
        self.samplenum = QtGui.QLineEdit('10000')
        self.range = QtGui.QComboBox()
        self.range.addItems(["5V","2V","1V","0.5V","0.2V","0.1V"])
        self.range.setCurrentIndex(3)
        self.rangelabel = QtGui.QLabel('Ch Range')

        # This could be added in to gui optionally
        self.trigger = QtGui.QComboBox()
        self.trigger.addItems(['No Trigger', 'Ext', 'Ch1', 'Ch2'])
        self.fft = QtGui.QCheckBox('Do FFT')
        self.coupling = QtGui.QComboBox()
        self.coupling.addItems(["DC","AC"])
        self.impedance = QtGui.QComboBox()
        self.impedance.addItems(["50","1e6"])
        self.setBtn = QtGui.QPushButton("Set")
        #self.pb = QtGui.QProgressBar()

    def initLayout(self):

        group = QtGui.QGroupBox('Gage Settings')
        self.VBOX = QtGui.QVBoxLayout()

        # RANGE
        self.rangebox = QtGui.QHBoxLayout()
        self.rangebox.addWidget(self.rangelabel)
        self.rangebox.addWidget(self.range)

        # RATE
        self.hbox = QtGui.QHBoxLayout()
        self.hbox.addWidget(self.lrate)
        self.hbox.addWidget(self.samplerate)

        # SAMPLE NUM
        self.hbox2 = QtGui.QHBoxLayout()
        self.hbox2.addWidget(self.lnum)
        self.hbox2.addWidget(self.samplenum)

        self.VBOX.addLayout(self.hbox)
        self.VBOX.addLayout(self.hbox2)

        self.VBOX.addLayout(self.rangebox)

        # self.trigtohbox = QtGui.QHBoxLayout()
        # self.trigtolabel = QtGui.QLabel("Trig T/O")
        # self.trigtimeout = QtGui.QLineEdit("1000")
        # self.trigtohbox.addWidget(self.trigtolabel)
        # self.trigtohbox.addWidget(self.trigtimeout)

        if self.setbtn:
            self.VBOX.addWidget(self.setBtn)

        if self.full:
            self.VBOX.addWidget(self.trigger)
            self.VBOX.addWidget(self.fft)
            self.VBOX.addWidget(self.coupling)
            self.VBOX.addWidget(self.impedance)

        self.VBOX.addStretch(1)
        group.setLayout(self.VBOX)
        self.vvbox = QtGui.QVBoxLayout()
        self.vvbox.addWidget(group)
        self.vvbox.addStretch(1)
        self.setLayout(self.vvbox)
        self.setMaximumWidth(200)

    def SampleRate(self):
        # returns the sample rate specified
        try:
            samplerate = int(self.samplerate.text())
            self.samplerate.setStyleSheet("""QLineEdit { background-color: white; color: black }""")
        except:
            samplerate = 10000000
            self.samplerate.setStyleSheet("""QLineEdit { background-color: pink; color: black }""")

        return samplerate

    def NumberOfSamples(self):
        try:
            numOfSamples = int(self.samplenum.text())
            self.samplenum.setStyleSheet("""QLineEdit { background-color: white; color: black }""")
        except:
            numOfSamples = 1024
            self.samplenum.setStyleSheet("""QLineEdit { background-color: pink; color: black }""")

        return numOfSamples

    def Range(self):

        ranges = np.array([5000,2000,1000,500,200,100])*2
        channelRange = ranges[self.range.currentIndex()]
        return channelRange

class esrcontrols(QtGui.QWidget):
    def __init__(self, parent=None, index=None, addPlotControls = True, fmin = None,fmax = None, pulsesControls = False):
        QtGui.QWidget.__init__(self, parent)
        self.index = index
        self.addPlotControls = addPlotControls
        self.f1 = fmin
        self.f2 = fmax
        self.initGUI()

    def initGUI(self):
        self.initWidgets()

    def initWidgets(self):

        self.esrbox = QtGui.QGroupBox()
        self.esrlay = QtGui.QVBoxLayout()

        # init widgets
        if self.f1 is not None:
            self.fmin = QtGui.QLineEdit(str(self.f1))
        else:
            self.fmin = QtGui.QLineEdit('2.86')
        self.fminl = QtGui.QLabel('Min f, GHz')
        hboxfmin = QtGui.QHBoxLayout()
        hboxfmin.addWidget(self.fminl)
        hboxfmin.addWidget(self.fmin)


        if self.f2 is not None:
            self.fmax = QtGui.QLineEdit(str(self.f2))
        else:
            self.fmax = QtGui.QLineEdit('2.88')

        self.fmaxl = QtGui.QLabel('Max f, GHz')
        hboxfmax = QtGui.QHBoxLayout()
        hboxfmax.addWidget(self.fmaxl)
        hboxfmax.addWidget(self.fmax)


        self.numberoffreq = QtGui.QLineEdit('400')
        self.numoffreqls = QtGui.QLabel('Number of freqs')
        hboxnf = QtGui.QHBoxLayout()
        hboxnf.addWidget(self.numoffreqls)
        hboxnf.addWidget(self.numberoffreq)

        # pulses settings

        self.duration = QtGui.QLineEdit('1e5')

        self.delay = QtGui.QLineEdit('1e3')


        self.intrepetsnum = QtGui.QSpinBox()
        self.intrepetsnum.setMaximum(10000)
        self.intrepetsnum.setValue(10)

        self.durationL = QtGui.QLabel('Pulse duration, ns')

        self.delayL = QtGui.QLabel('Delay duration, ns')

        self.intrepetsnumL = QtGui.QLabel('Internal rep num')

        self.regime = QtGui.QComboBox()
        self.regime.addItems(['CW','Pulsed'])



        hvoxp1 = QtGui.QHBoxLayout()
        hvoxp1.addWidget(self.durationL)
        hvoxp1.addWidget(self.duration)

        hvoxp2 = QtGui.QHBoxLayout()
        hvoxp2.addWidget(self.delayL)
        hvoxp2.addWidget(self.delay)

        hvoxp3 = QtGui.QHBoxLayout()
        hvoxp3.addWidget(self.intrepetsnumL)
        hvoxp3.addWidget(self.intrepetsnum)

        self.readout = readoutcontrols()

        vboxpulses = QtGui.QVBoxLayout()
        vboxpulses.addLayout(hvoxp1)
        vboxpulses.addLayout(hvoxp2)
        vboxpulses.addLayout(hvoxp3)
        vboxpulses.addWidget(self.readout)

        vboxpulses.addWidget(self.regime)

        self.esrlay.addLayout(vboxpulses)
        self.power = QtGui.QLineEdit('0')
        self.powerl = QtGui.QLabel('MW power, db')
        hboxp = QtGui.QHBoxLayout()
        hboxp.addWidget(self.powerl)
        hboxp.addWidget(self.power)

        self.esrlay.addLayout(hboxfmin)
        self.esrlay.addLayout(hboxfmax)
        self.esrlay.addLayout(hboxnf)
        self.esrlay.addLayout(hboxp)
        self.esrbox.setLayout(self.esrlay)

        if self.addPlotControls:
            self.plotcontrols = plotcontrols()
            self.esrlay.addWidget(self.plotcontrols)

        self.timercontrols = startstopbtn()
        self.esrlay.addWidget(self.timercontrols)

        self.esrlay.addStretch(1)
        self.setLayout(self.esrlay)

    def F(self):
        try:
            fmin = float(self.fmin.text())
            fmax = float(self.fmax.text())

            self.fmin.setStyleSheet("""QLineEdit { background-color: white; color: black }""")
            self.fmax.setStyleSheet("""QLineEdit { background-color: white; color: black }""")

        except:
            self.fmin.setStyleSheet("""QLineEdit { background-color: pink; color: red }""")
            self.fmax.setStyleSheet("""QLineEdit { background-color: pink; color: red }""")
            return None,None
        return fmin,fmax

    def Num(self):
        try:
            num = int(self.numberoffreq.text())
            self.numberoffreq.setStyleSheet("""QLineEdit { background-color: white; color: black }""")

        except:
            self.numberoffreq.setStyleSheet("""QLineEdit { background-color: pink; color: red }""")
            return 400
        return num

    def Power(self):
        try:
            num = float(self.power.text())
            self.power.setStyleSheet("""QLineEdit { background-color: white; color: black }""")

        except:
            self.power.setStyleSheet("""QLineEdit { background-color: pink; color: red }""")
            return -30

        return min(num,0)

    def DurationDelay(self):
        try:
            dur = float(self.duration.text())
            delay = float(self.delay.text())
            self.duration.setStyleSheet("""QLineEdit { background-color: white; color: black }""")
            self.delay.setStyleSheet("""QLineEdit { background-color: white; color: black }""")

        except:
            self.duration.setStyleSheet("""QLineEdit { background-color: pink; color: red }""")
            self.delay.setStyleSheet("""QLineEdit { background-color: pink; color: red }""")
            return 0
        return dur,delay

    def InternalRepeats(self):

        try:
            rep = self.intrepetsnum.value()
        except:
            return 10

        return rep

class timetracecfg(QtGui.QWidget):
    def __init__(self, parent=None, addPlotControls=True):
        QtGui.QWidget.__init__(self, parent)
        self.addPlotControls = addPlotControls
        self.initGUI()

    def initGUI(self):

        # Regime of the acquisition
        #groupBox = QtGui.QGroupBox("Process control box")
        regimebox = QtGui.QGroupBox("Regime")
        self.rb1 = QtGui.QRadioButton("&Live timetrace")
        self.rb1.setChecked(True)
        self.rb2 = QtGui.QRadioButton("&Instant")
        self.rb3 = QtGui.QRadioButton("&Instant multiple")
        #self.startBtn = QtGui.QPushButton("&Start/Stop!")
        #self.startBtn.setMinimumHeight(50)

        vbox = QtGui.QVBoxLayout()

        vertoptbox = QtGui.QVBoxLayout()
        vertoptbox.addWidget(self.rb1)
        vertoptbox.addWidget(self.rb2)
        vertoptbox.addWidget(self.rb3)

        regimebox.setLayout(vertoptbox)
        vbox.addWidget(regimebox)

        if self.addPlotControls:
            self.plotcontrols = plotcontrols()

        vbox.addWidget(self.plotcontrols)
        #vbox.addWidget(self.startBtn)
        self.timercontrols = startstopbtn()
        vbox.addWidget(self.timercontrols)

        self.mwfreq  = QtGui.QLineEdit('2.87')
        self.mwpower = QtGui.QLineEdit('-20') # the amplifier is on again be careful
        self.flabel = QtGui.QLabel('freq, GHz')
        self.plabel = QtGui.QLabel('power, dbm')
        self.mwon = QtGui.QPushButton('MW on/off')

        h1 = QtGui.QHBoxLayout()
        h2 = QtGui.QHBoxLayout()
        h1.addWidget(self.flabel)
        h1.addWidget(self.mwfreq)
        h2.addWidget(self.plabel)
        h2.addWidget(self.mwpower)
        vbox.addLayout(h1)
        vbox.addLayout(h2)
        vbox.addWidget(self.mwon)


        vbox.addStretch(1)
        self.setLayout(vbox)
        self.setMaximumWidth(200)

    def MultFactor(self):
        try:
            mu = float(self.multfactor.text())
            self.multfactor.setStyleSheet("""QLineEdit { background-color: white; color: black }""")
        except:
            mu = 1
            self.multfactor.setStyleSheet("""QLineEdit { background-color: pink; color: black }""")

        return mu

    def MWfreq(self):
        try:
            freq = float(self.mwfreq.text())*1e9
            self.mwfreq.setStyleSheet("""QLineEdit { background-color: white; color: black }""")
        except:
            self.mwfreq.setStyleSheet("""QLineEdit { background-color: pink; color: red }""")
            return None
        return freq
    def MWpower(self):
        try:
            power = float(self.mwpower.text())
            self.mwpower.setStyleSheet("""QLineEdit { background-color: white; color: black }""")
        except:
            self.mwpower.setStyleSheet("""QLineEdit { background-color: pink; color: red }""")
            return None
        return power

    def YLim(self):

        try:
            ymin = float(self.ylim1.text())
            ymax = float(self.ylim2.text())

            self.ylim1.setStyleSheet("""QLineEdit { background-color: white; color: black }""")
            self.ylim2.setStyleSheet("""QLineEdit { background-color: white; color: black }""")

        except:
            self.ylim1.setStyleSheet("""QLineEdit { background-color: pink; color: red }""")
            self.ylim2.setStyleSheet("""QLineEdit { background-color: pink; color: red }""")
            return None,None
        return ymin,ymax

class plotcontrols(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.initGUI()
        self.initLayout()

    def initGUI(self):

        self.ylim1 = QtGui.QLineEdit("")
        self.ylim2 = QtGui.QLineEdit("")
        # self.xliml1 = QtGui.QLabel("xlim")
        self.yliml1 = QtGui.QLabel("ylim")
        self.setBtn = QtGui.QPushButton("Set")
        self.autoBtn = QtGui.QPushButton("Auto")
        self.setBtn.setMinimumHeight(50)
        self.autoBtn.setMinimumHeight(50)
        self.plotLookOptions = QtGui.QGroupBox("Plot settings")
        self.multfactorl = QtGui.QLabel('xCh2')
        self.multfactor = QtGui.QLineEdit('1')

    def initLayout(self):
        vbox = QtGui.QVBoxLayout()

        limbox = QtGui.QHBoxLayout()

        limbox.addWidget(self.yliml1)
        limbox.addWidget(self.ylim1)
        limbox.addWidget(self.ylim2)

        vbox.addLayout(limbox)

        setbtnbox = QtGui.QHBoxLayout()
        setbtnbox.addWidget(self.setBtn)
        setbtnbox.addWidget(self.autoBtn)

        vbox.addLayout(setbtnbox)

        multfactorbox = QtGui.QHBoxLayout()
        multfactorbox.addWidget(self.multfactorl)
        multfactorbox.addWidget(self.multfactor)
        vbox.addLayout(multfactorbox)
        vbox.addStretch(1)

        self.plotLookOptions.setLayout(vbox)

        vvbox = QtGui.QVBoxLayout()
        vvbox.addWidget(self.plotLookOptions)
        vvbox.addStretch(1)
        self.setLayout(vvbox)
        self.setMaximumWidth(200)

    def MultFactor(self):
        try:
            mu = float(self.multfactor.text())
            self.multfactor.setStyleSheet("""QLineEdit { background-color: white; color: black }""")
        except:
            mu = 1
            self.multfactor.setStyleSheet("""QLineEdit { background-color: pink; color: black }""")

        return mu

    def YLim(self):

        try:
            ymin = float(self.ylim1.text())
            ymax = float(self.ylim2.text())

            self.ylim1.setStyleSheet("""QLineEdit { background-color: white; color: black }""")
            self.ylim2.setStyleSheet("""QLineEdit { background-color: white; color: black }""")

        except:
            self.ylim1.setStyleSheet("""QLineEdit { background-color: pink; color: red }""")
            self.ylim2.setStyleSheet("""QLineEdit { background-color: pink; color: red }""")
            return None,None
        return ymin,ymax

class startstopbtn(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.initGUI()
    def initGUI(self):

        self.startBtn = QtGui.QPushButton("&Start/Stop!")
        self.startBtn.setMinimumHeight(50)
        self.dt = QtGui.QSpinBox()

        self.dt.setMaximum(10000)
        self.dt.setMinimum(1)
        self.dt.setValue(100)

        self.dt.setMaximumWidth(50)
        self.timeout = QtGui.QSpinBox()
        self.timeout.setMinimum(-1)
        self.timeout.setMaximum(100)
        self.timeout.setValue(-1)
        self.timeout.setMaximumWidth(50)

        timebox = QtGui.QVBoxLayout()
        timebox.addWidget(self.dt)
        timebox.addWidget(self.timeout)

        self.hbox = QtGui.QHBoxLayout()
        self.hbox.addLayout(timebox)
        self.hbox.addWidget(self.startBtn)

        self.acqType = QtGui.QComboBox()
        self.acqType.addItems(['APDs','Photo Detectors'])

        vbox = QtGui.QVBoxLayout()
        vbox.addLayout(self.hbox)
        vbox.addWidget(self.acqType)

        self.setLayout(vbox)
        self.setMaximumWidth(200)


    def TO(self):
        try:
            mu = int(self.timeout.text())
            self.timeout.setStyleSheet("""QLineEdit { background-color: white; color: black }""")
        except:
            mu = -1
            self.timeout.setStyleSheet("""QLineEdit { background-color: pink; color: black }""")

        return mu

    def dT(self):
        try:
            mu = self.dt.value()

        except:
            mu = 100

        return mu

class lockincontrols(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.initGUI()
    def initGUI(self):

        self.lockin = QtGui.QGroupBox('LockIn')
        self.checkLI = QtGui.QCheckBox('Enabled')
        self.fmodl = QtGui.QLabel('Fmod, kHz')
        self.dfl = QtGui.QLabel('Amplitude, kHz')
        self.fmod = QtGui.QSpinBox()
        self.fmod.setMaximum(100)
        self.fmod.setValue(50)
        self.df = QtGui.QSpinBox()
        self.df.setValue(100)
        self.df.setMaximum(1000)

        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.checkLI)
        hbox1 = QtGui.QHBoxLayout()
        hbox1.addWidget(self.fmodl)
        hbox1.addWidget(self.fmod)
        vbox.addLayout(hbox1)
        hbox2 = QtGui.QHBoxLayout()
        hbox2.addWidget(self.dfl)
        hbox2.addWidget(self.df)
        vbox.addLayout(hbox2)
        vbox.addStretch(1)
        self.lockin.setLayout(vbox)


        VBOX = QtGui.QVBoxLayout()
        VBOX.addWidget(self.lockin)
        self.setLayout(VBOX)
        self.setMaximumWidth(200)

    def Enabled(self):

        return self.checkLI.isChecked()

    def ModAmp(self):

        return self.df.value()

    def ModFreq(self):

        return self.fmod.value()

class rabiControls(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.initGUI()

    def initGUI(self):


        box = QtGui.QGroupBox('Rabi')
        vbox = QtGui.QVBoxLayout()

        #self.runbtn = QtGui.QPushButton('Run')
        #TODO think about class of start button

        self.dt = QtGui.QSpinBox()
        self.dtl = QtGui.QLabel('T min, ns')
        self.dt.setMaximum(10000)
        self.dt.setValue(100)
        h = QtGui.QHBoxLayout()
        h.addWidget(self.dtl)
        h.addWidget(self.dt)

        self.tfinishl = QtGui.QLabel('T max, ns')
        self.tfinish = QtGui.QSpinBox()
        self.tfinish.setMaximum(1000000)
        self.tfinish.setValue(2000)
        h1 = QtGui.QHBoxLayout()
        h1.addWidget(self.tfinishl)
        h1.addWidget(self.tfinish)


        self.iterationsl = QtGui.QLabel('T step, ns')
        self.iterations = QtGui.QSpinBox()
        self.iterations.setValue(25)
        self.iterations.setMaximum(10000)
        h2 = QtGui.QHBoxLayout()
        h2.addWidget(self.iterationsl)
        h2.addWidget(self.iterations)

        self.numofreps = QtGui.QSpinBox()
        self.numofreps.setMaximum(1000000)
        self.numofreps.setValue(10)
        self.numofrepsL = QtGui.QLabel('Repetitions')

        self.progress = QtGui.QProgressBar()
        self.readouts = QtGui.QSpinBox()
        self.readouts.setMaximum(1000000)
        self.readouts.setValue(300)
        self.readoutsL = QtGui.QLabel('ReadoutTime, ns')

        hh = []
        for i in range(10):
            hh.append(QtGui.QHBoxLayout())

        hh[0].addWidget(self.numofrepsL)
        hh[0].addWidget(self.numofreps)

        hh[1].addWidget(self.progress)
        hh[2].addWidget(self.readoutsL)
        hh[2].addWidget(self.readouts)


        self.freq = QtGui.QLineEdit('2.87')
        self.power = QtGui.QSpinBox()

        self.power.setMinimum(-50)
        self.power.setMaximum(0)

        h3 = QtGui.QHBoxLayout()

        h3.addWidget(self.freq)
        h3.addWidget(QtGui.QLabel('GHz,'))
        h3.addWidget(self.power)
        h3.addWidget(QtGui.QLabel('dbm'))

        vbox.addLayout(h)
        vbox.addLayout(h1)
        vbox.addLayout(h2)
        vbox.addLayout(h3)
        for i in range(10):
            vbox.addLayout(hh[i])


        vbox.addStretch(1)
        box.setLayout(vbox)
        vvbox = QtGui.QVBoxLayout()
        vvbox.addWidget(box)
        vvbox.addStretch(1)



        self.setLayout(vvbox)
        self.setMaximumWidth(200)


        # Dynamical constructed blocks
        # Save load seqs
        # Make iterations

    def F(self):
        try:
            num = float(self.freq.text())
            self.freq.setStyleSheet("""QLineEdit { background-color: white; color: black }""")

        except:
            self.freq.setStyleSheet("""QLineEdit { background-color: pink; color: red }""")
            return 0
        return num

    def P(self):
        try:
            num = self.power.value()
        except:
            print '!ERROR!'
            return 0
        return num

class pulsesControls(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.initGUI()

    def initGUI(self):


        box = QtGui.QGroupBox('Pulses')
        vbox = QtGui.QVBoxLayout()

        #self.runbtn = QtGui.QPushButton('Run')
        #TODO think about class of start button

        self.dt = QtGui.QSpinBox()
        self.dtl = QtGui.QLabel('T min, ns')
        self.dt.setMaximum(10000)
        self.dt.setValue(100)
        h = QtGui.QHBoxLayout()
        h.addWidget(self.dtl)
        h.addWidget(self.dt)

        self.tfinishl = QtGui.QLabel('T max, ns')
        self.tfinish = QtGui.QSpinBox()
        self.tfinish.setMaximum(10000000)
        self.tfinish.setValue(2000)
        h1 = QtGui.QHBoxLayout()
        h1.addWidget(self.tfinishl)
        h1.addWidget(self.tfinish)


        self.iterationsl = QtGui.QLabel('T step, ns')
        self.iterations = QtGui.QSpinBox()
        self.iterations.setValue(25)
        self.iterations.setMaximum(1000000)
        h2 = QtGui.QHBoxLayout()
        h2.addWidget(self.iterationsl)
        h2.addWidget(self.iterations)

        self.numofreps = QtGui.QSpinBox()
        self.numofreps.setMaximum(10000000)
        self.numofreps.setValue(10)
        self.numofrepsL = QtGui.QLabel('Repetitions')

        self.progress = QtGui.QProgressBar()
        self.readouts = QtGui.QSpinBox()
        self.readouts.setMaximum(1000000)
        self.readouts.setValue(300)
        self.readoutsL = QtGui.QLabel('ReadoutTime, ns')

        self.pi_2 = QtGui.QSpinBox()
        self.pi_2.setSingleStep(1)
        self.pi_2.setMaximum(10000)
        self.pi_2.setValue(100)


        self.pi = QtGui.QSpinBox()
        self.pi.setSingleStep(1)
        self.pi.setMaximum(10000)
        self.pi.setValue(200)

        self.pi32 = QtGui.QSpinBox()
        self.pi32.setSingleStep(1)
        self.pi32.setMaximum(10000)
        self.pi32.setValue(300)


        hh = []
        for i in range(10):
            hh.append(QtGui.QHBoxLayout())

        hh[0].addWidget(self.numofrepsL)
        hh[0].addWidget(self.numofreps)

        hh[1].addWidget(self.progress)
        hh[2].addWidget(self.readoutsL)
        hh[2].addWidget(self.readouts)

        hh[4].addWidget(self.pi_2)
        hh[4].addWidget(QtGui.QLabel('Pi/2, ns'))

        hh[5].addWidget(self.pi)
        hh[5].addWidget(QtGui.QLabel('Pi, ns'))

        hh[6].addWidget(self.pi32)
        hh[6].addWidget(QtGui.QLabel('3Pi/2, ns'))


        self.freq = QtGui.QLineEdit('2.87')
        self.power = QtGui.QSpinBox()

        self.power.setMinimum(-50)
        self.power.setMaximum(0)

        h3 = QtGui.QHBoxLayout()

        h3.addWidget(self.freq)
        h3.addWidget(QtGui.QLabel('GHz,'))
        h3.addWidget(self.power)
        h3.addWidget(QtGui.QLabel('dbm'))

        vbox.addLayout(h)
        vbox.addLayout(h1)
        vbox.addLayout(h2)
        vbox.addLayout(h3)
        for i in range(10):
            vbox.addLayout(hh[i])


        vbox.addStretch(1)
        box.setLayout(vbox)
        vvbox = QtGui.QVBoxLayout()
        vvbox.addWidget(box)
        vvbox.addStretch(1)



        self.setLayout(vvbox)
        self.setMaximumWidth(200)


        # Dynamical constructed blocks
        # Save load seqs
        # Make iterations

    def F(self):
        try:
            num = float(self.freq.text())
            self.freq.setStyleSheet("""QLineEdit { background-color: white; color: black }""")

        except:
            self.freq.setStyleSheet("""QLineEdit { background-color: pink; color: red }""")
            return 0
        return num

    def P(self):
        try:
            num = self.power.value()
        except:
            print '!ERROR!'
            return 0
        return num

class fidControls(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.initGUI()

    def initGUI(self):


        box = QtGui.QGroupBox('FID')
        vbox = QtGui.QVBoxLayout()

        #self.runbtn = QtGui.QPushButton('Run')
        #TODO think about class of start button

        self.dt = QtGui.QSpinBox()
        self.dtl = QtGui.QLabel('T min, ns')
        self.dt.setMaximum(10000)
        self.dt.setValue(100)
        h = QtGui.QHBoxLayout()
        h.addWidget(self.dtl)
        h.addWidget(self.dt)

        self.tfinishl = QtGui.QLabel('T max, ns')
        self.tfinish = QtGui.QSpinBox()
        self.tfinish.setMaximum(1000000)
        self.tfinish.setValue(20000)
        h1 = QtGui.QHBoxLayout()
        h1.addWidget(self.tfinishl)
        h1.addWidget(self.tfinish)


        self.iterationsl = QtGui.QLabel('T step')
        self.iterations = QtGui.QSpinBox()
        self.iterations.setValue(100)
        h2 = QtGui.QHBoxLayout()
        h2.addWidget(self.iterationsl)
        h2.addWidget(self.iterations)

        self.freq = QtGui.QLineEdit('2.87')
        self.pi_2 = QtGui.QSpinBox()
        self.pi_2.setSingleStep(1)
        self.pi_2.setMaximum(1000)
        self.pi_2.setValue(100)
        self.power = QtGui.QSpinBox()
        self.power.setSingleStep(0.1)
        self.power.setMinimum(-50)

        h3 = QtGui.QHBoxLayout()

        h3.addWidget(self.freq)
        h3.addWidget(QtGui.QLabel('GHz,'))
        h3.addWidget(self.power)
        h3.addWidget(QtGui.QLabel('dbm'))

        h4 = QtGui.QHBoxLayout()

        h4.addWidget(self.pi_2)
        h4.addWidget(QtGui.QLabel('Pi/2, ns'))

        vbox.addLayout(h)
        vbox.addLayout(h1)
        vbox.addLayout(h2)
        vbox.addLayout(h3)
        vbox.addLayout(h4)
        vbox.addStretch(1)
        box.setLayout(vbox)
        vvbox = QtGui.QVBoxLayout()
        vvbox.addWidget(box)
        vvbox.addStretch(1)

        self.setLayout(vvbox)
        self.setMaximumWidth(200)


        # Dynamical constructed blocks
        # Save load seqs
        # Make iterations

class echoControls(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.initGUI()

    def initGUI(self):


        box = QtGui.QGroupBox('Echo')
        vbox = QtGui.QVBoxLayout()

        #self.runbtn = QtGui.QPushButton('Run')
        #TODO think about class of start button

        self.dt = QtGui.QSpinBox()
        self.dtl = QtGui.QLabel('T min, ns')
        self.dt.setMaximum(10000)
        self.dt.setValue(100)
        h = QtGui.QHBoxLayout()
        h.addWidget(self.dtl)
        h.addWidget(self.dt)

        self.tfinishl = QtGui.QLabel('T max, ns')
        self.tfinish = QtGui.QSpinBox()
        self.tfinish.setMaximum(1000000)
        self.tfinish.setValue(20000)
        h1 = QtGui.QHBoxLayout()
        h1.addWidget(self.tfinishl)
        h1.addWidget(self.tfinish)


        self.iterationsl = QtGui.QLabel('T step')
        self.iterations = QtGui.QSpinBox()
        self.iterations.setValue(100)
        h2 = QtGui.QHBoxLayout()
        h2.addWidget(self.iterationsl)
        h2.addWidget(self.iterations)

        self.freq = QtGui.QLineEdit('2.87')
        self.pi_2 = QtGui.QSpinBox()
        self.pi_2.setSingleStep(1)
        self.pi_2.setMaximum(1000)
        self.pi_2.setValue(100)
        self.power = QtGui.QSpinBox()
        self.power.setSingleStep(0.1)
        self.power.setMinimum(-50)

        h3 = QtGui.QHBoxLayout()

        h3.addWidget(self.freq)
        h3.addWidget(QtGui.QLabel('GHz,'))
        h3.addWidget(self.power)
        h3.addWidget(QtGui.QLabel('dbm'))

        h4 = QtGui.QHBoxLayout()

        h4.addWidget(self.pi_2)
        h4.addWidget(QtGui.QLabel('Pi/2, ns'))

        vbox.addLayout(h)
        vbox.addLayout(h1)
        vbox.addLayout(h2)
        vbox.addLayout(h3)
        vbox.addLayout(h4)
        vbox.addStretch(1)
        box.setLayout(vbox)
        vvbox = QtGui.QVBoxLayout()
        vvbox.addWidget(box)
        vvbox.addStretch(1)

        self.setLayout(vvbox)
        self.setMaximumWidth(200)


        # Dynamical constructed blocks
        # Save load seqs
        # Make iterations

class myplot():
    def __init__(self, plotwidget, xlabel, ylabel, logmode=True, grid = True):
        self.pw = plotwidget
        self.pi = self.pw.getPlotItem()
        self.logmode = logmode
        self.grid = grid
        self.pi.setLogMode(x=self.logmode,y=self.logmode)
        self.pi.showGrid(x=self.grid,y=self.grid)
        self.plots = []
        self.legend = self.pi.addLegend()
        self.color = ['g','c' , 'b', 'r', 'm', 'w']
        self.pi.setLabel('bottom',xlabel[0],xlabel[1])
        self.pi.setLabel('left',ylabel[0],ylabel[1])
        self.pi.enableAutoRange(True)


    def randcolor(self):
        r = 0
        g = 0
        b = 0
        while r+g+b < 100:
            r = np.random.random_integers(0,255)
            g= np.random.random_integers(0,255)
            b = np.random.random_integers(0,255)
        color = (r,g,b)
        return color

    def addCurve(self, datax, datay, name, color = None, xlabel = None):
        #print 'myaddcurve'
        if self.legend is None:
            self.legend = self.pi.addLegend()
        if color is None:
            self.plots.append(self.pi.plot(datax,datay, pen=self.randcolor(), name = name))
        else:
            self.plots.append(self.pi.plot(datax,datay, pen=color, name = name))

        if xlabel is not None:
            self.pi.setLabel('bottom',xlabel[0],xlabel[1])

        #print len(self.plots)

    def updateSubplot(self,i=0,dataX = None, dataY = None):
        #print dataX
        if dataX is not None:
            if len(self.plots) > i:
                self.plots[i].setData(dataX, dataY)

    def clearall(self):
        try:
            for item in self.pi.listDataItems():
                self.pi.removeItem(item)
            self.legend.scene().removeItem(self.legend)
            self.legend = None
        except:
            pass
        self.plots = []

class PulsesPlot(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.initGUI()
    def initGUI(self):
        vbox = QtGui.QVBoxLayout()
        self.plot = PlotWidget()
        vbox.addWidget(self.plot)
        self.myplot = myplot(plotwidget=self.plot,xlabel = ['Time','s'],ylabel=['',''],logmode=False)
        self.psp = pulses_scheme_plot(self.myplot)
        self.setLayout(vbox)
        self.setMaximumHeight(350)
    def drawFromSequence(self, sequence,progress=None):
        # sequence of type seq = [
                                 # {"channels":["Laser"],"Duration":100}
                                    # ]
        # here just a simple sequence of blocks
        self.psp.plotBlocks(sequence, progress)

class DataPlot(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.initGUI()
    def initGUI(self):
        vbox = QtGui.QVBoxLayout()
        self.plot = PlotWidget()
        vbox.addWidget(self.plot)
        self.myplot = myplot(self.plot,xlabel = ['Time','s'],ylabel = ['Signal','a.u.'],logmode=False)
        self.setLayout(vbox)

class pulses_scheme_plot():
    def __init__(self, myplot):
        self.plot = myplot # here goes the object of myplot class
        self.channel_map = {0:['1', 'LASER'], 1:['2','RF'], 2:['3', 'MW','SMIQ_TRIG', 'NI_TRIG'], 3:['4', 'Detect','GAGE_TRIG'], 4:['5','Ref Detect','vfgtrig']}#, 5:['6', 'Ref Coll','MWTRIG'],}# 7:['8', 'trigger']}
        self.channel_list = ["Laser","RF","MW","Detect","RefDet"]
        k = 100
        self.channel_signal = [[],[],[],[],[]]
        for key in self.channel_map.items():
            self.plot.addCurve(np.arange(0,k),np.ones((k))*(5-key[0]),name = key[1][1], color = self.plot.color[key[0]])
    def plotfromblocks(self, blocks, sequence):
        pass

    def plotBlocks(self, blocks,progress = 0):
        self.channel_signal = [[],[],[],[],[],[]]
        curtime = 0
        for block in blocks:
            delay = block["duration"]
            print delay
            if hasattr(delay, "__iter__"):
                i = int(progress*delay.shape[0])
                delay = delay[i]
            channels = block["channels"]
            for i,ch in enumerate(self.channel_list):
                if ch in channels:
                    self.channel_signal[i].append([curtime,i+0.5])
                    if delay > 0:
                         self.channel_signal[i].append([curtime+delay,i+0.5])
                    else:
                         self.channel_signal[i].append([curtime+5,i+0.5])

                else:
                    self.channel_signal[i].append([curtime,i+0])
                    if delay > 0:
                        self.channel_signal[i].append([curtime+delay,i+0])
                    else:
                        self.channel_signal[i].append([curtime+5,i+0])
                    #print i

            curtime += delay

        for i in range(5):

            xdata = np.array(self.channel_signal[i]).T[0]*1e-9 # convert to ns
            ydata = np.array(self.channel_signal[i]).T[1]
            self.plot.updateSubplot(i,xdata,ydata)

    def plotprograms(self,programm):


        #print 'plottting'
        self.channel_signal = [[],[],[],[],[],[]]
        curtime = 0
        programmstr = [hex(p) for p in programm]
        for i,p in enumerate(programmstr):

            if p.startswith('0xc0') and p != '0xc0000015L':
                #print p
                channels = str(bin(programm[i]))
                try:
                    delay = (programm[i+1]-0x90000000)*12.5
                    #print delay

                except:
                    delay = -1

                for i in range(0,6):
                    if channels[-i-1] == '1':
                        self.channel_signal[i].append([curtime,i+0.5])
                        if delay > 0:
                            self.channel_signal[i].append([curtime+delay,i+0.5])
                        else:
                            self.channel_signal[i].append([curtime+5,i+0.5])

                    elif channels[-i-1] == '0':
                        self.channel_signal[i].append([curtime,i+0])
                        if delay > 0:
                            self.channel_signal[i].append([curtime+delay,i+0])
                        else:
                            self.channel_signal[i].append([curtime+5,i+0])
                    #print i

                curtime += delay

        for i in range(6):

            xdata = np.array(self.channel_signal[i]).T[0]*1e-9 # convert to ns
            ydata = np.array(self.channel_signal[i]).T[1]
            if i == 5:
                self.plot.updateSubplot(i-1,xdata,ydata)
            else:
                self.plot.updateSubplot(i,xdata,ydata)

class SingleShotControls(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.initGUI()

    def initGUI(self):

        box = QtGui.QGroupBox('Single Shot')
        vbox = QtGui.QVBoxLayout()

        #self.runbtn = QtGui.QPushButton('Run')
        #TODO think about class of start button

        # laser delay
        # MW freq
        # MW power
        # MW duration
        # Readout Laser duration
        # Laser duration
        # Reference + Laser duration
        # Binning number

        self.lasdelay = QtGui.QSpinBox()
        self.lasdelayL = QtGui.QLabel('Laser delay, ns')
        self.lasdelay.setMaximum(10000)
        self.lasdelay.setValue(100)
        h = QtGui.QHBoxLayout()
        h.addWidget(self.lasdelayL)
        h.addWidget(self.lasdelay)

        self.tmwL = QtGui.QLabel('T MW, ns')
        self.tmw = QtGui.QSpinBox()
        self.tmw.setMaximum(1000000)
        self.tmw.setValue(200)
        h1 = QtGui.QHBoxLayout()
        h1.addWidget(self.tmwL)
        h1.addWidget(self.tmw)


        self.iterationsl = QtGui.QLabel('Bining, ns')
        self.iterations = QtGui.QSpinBox()
        self.iterations.setValue(1)
        self.iterations.setMaximum(10000)
        h2 = QtGui.QHBoxLayout()
        h2.addWidget(self.iterationsl)
        h2.addWidget(self.iterations)

        self.numofreps = QtGui.QSpinBox()
        self.numofreps.setMaximum(1000000)
        self.numofreps.setValue(10)
        self.numofrepsL = QtGui.QLabel('N Cycles')

        self.progress = QtGui.QProgressBar()
        self.readouts = QtGui.QSpinBox()
        self.readouts.setMaximum(1000000)
        self.readouts.setValue(300)
        self.readoutsL = QtGui.QLabel('ReadoutTime, ns')

        hh = []
        for i in range(10):
            hh.append(QtGui.QHBoxLayout())

        hh[0].addWidget(self.numofrepsL)
        hh[0].addWidget(self.numofreps)

        hh[1].addWidget(self.progress)
        hh[2].addWidget(self.readoutsL)
        hh[2].addWidget(self.readouts)


        self.freq = QtGui.QLineEdit('2.87')
        self.power = QtGui.QSpinBox()

        self.power.setMinimum(-50)
        self.power.setMaximum(0)

        h3 = QtGui.QHBoxLayout()

        h3.addWidget(self.freq)
        h3.addWidget(QtGui.QLabel('GHz,'))
        h3.addWidget(self.power)
        h3.addWidget(QtGui.QLabel('dbm'))

        vbox.addLayout(h)
        vbox.addLayout(h1)
        vbox.addLayout(h2)
        vbox.addLayout(h3)
        for i in range(10):
            vbox.addLayout(hh[i])


        vbox.addStretch(1)
        box.setLayout(vbox)
        vvbox = QtGui.QVBoxLayout()
        vvbox.addWidget(box)
        vvbox.addStretch(1)



        self.setLayout(vvbox)
        self.setMaximumWidth(200)

    def F(self):
        try:
            num = float(self.freq.text())
            self.freq.setStyleSheet("""QLineEdit { background-color: white; color: black }""")

        except:
            self.freq.setStyleSheet("""QLineEdit { background-color: pink; color: red }""")
            return 0
        return num

    def P(self):
        try:
            num = self.power.value()
        except:
            print '!ERROR!'
            return 0
        return num

class readoutcontrols(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.initGUI()

    def initGUI(self):

        vbox = QtGui.QVBoxLayout()
        box = QtGui.QGroupBox('Optical ReadOut')

        parameters = {"excitation": 1000000,
                      "delay": 1000,
                      "detect":1000000,
                      "reference": 1000000,
                      "refdelay": 500000}

        self.controldict = {}

        for key in parameters.keys():

            self.controldict[key] = parameter(name=key,defaultvalue=parameters[key])
            vbox.addWidget(self.controldict[key])

        vbox.addStretch(1)
        box.setLayout(vbox)
        vvbox = QtGui.QVBoxLayout()
        vvbox.addWidget(box)
        vvbox.addStretch(1)
        self.setLayout(vvbox)
        self.setMaximumWidth(200)

class parameter(QtGui.QWidget):
    def __init__(self, parent=None, name= 'name', defaultvalue = 0):
        QtGui.QWidget.__init__(self, parent)
        self.name = name
        self.value = defaultvalue
        self.initGUI()

    def initGUI(self):

        hbox = QtGui.QHBoxLayout()
        label = QtGui.QLabel(self.name)
        self.valuebox = QtGui.QSpinBox()
        self.valuebox.setMaximum(1000000000)
        self.valuebox.setValue(self.value)
        hbox.addWidget(label)
        hbox.addWidget(self.valuebox)
        hbox.addStretch(1)
        self.setLayout(hbox)
        self.setMaximumWidth(200)
        self.setMaximumHeight(30)

class PulsesDesigner(QtGui.QWidget):
    def __init__(self,parent = None, schemeplot= None,fpga = None):
        QtGui.QWidget.__init__(self, parent)

        self.fpga = fpga
        self.sequence = []
        # self.blocks = []
        # self.groups = []
        self.schemeplot = schemeplot
        self.initGUI()


    def initGUI(self):

        hbox = QtGui.QHBoxLayout()
        self.tabwidget = QtGui.QTabWidget()
        self.listview = QtGui.QListWidget()
        self.myvariables = VariablesWidget()
        self.myblocks = BlockWidget(listView=self.listview,pulsedesigner = self, tablevars=self.myvariables)
        self.mygroups = GroupsWidget(blocks=self.myblocks.blocks)
        self.mysequence = SequenceWidget()


        self.tabwidget.addTab(self.myblocks,'Blocks')
        self.tabwidget.addTab(self.mygroups,'Groups')
        self.tabwidget.addTab(self.mysequence,'Sequence')
        self.tabwidget.addTab(self.myvariables,'Variables')


        hbox.addWidget(self.tabwidget)
        hbox.addWidget(self.listview)

        self.setLayout(hbox)
        self.setMaximumHeight(350)

    def updatePulsesScheme(self, progress = None):

        self.sequence = [b.BLOCK for b in self.myblocks.blocks]
        self.schemeplot.drawFromSequence(self.sequence, progress)

    def getProgramm(self, i = None):

        programm = []
        programm.append(self.fpga.set_loops(self.mysequence.internalrepeats.value()))
        for b in [bl.BLOCK for bl in self.myblocks.blocks]:
            command = self.fpga.channels2command(b['channels'])
            delns = b['duration']
            if hasattr(delns, "__iter__"):
                if i is not None:
                     delns = delns[i]
                else:
                    delns = 1000
            else:
                pass

            delay = self.fpga.delayFromNS(delns)
            programm.append(command)
            programm.append(delay)
        programm.append(0x20000001)
        programm.append(self.fpga.finish())

        #print programm
        return programm

class BlockWidget(QtGui.QWidget):
    def __init__(self,parent = None, listView= None, pulsedesigner = None, tablevars = None):
        QtGui.QWidget.__init__(self, parent)
        self.listView = listView
        self.pulsedesigner = pulsedesigner
        self.tablevars = tablevars
        self.blocks = []
        self.initGUI()
        self.initConn()

    def initGUI(self):

        hbox = QtGui.QHBoxLayout()

        self.createbtn = QtGui.QPushButton('New')
        self.delbtn = QtGui.QPushButton('Delete')
        #self.openbtn = QtGui.QPushButton('Open')

        hbox.addWidget(self.createbtn)
        hbox.addWidget(self.delbtn)
        #hbox.addWidget(self.openbtn)

        vbox = QtGui.QVBoxLayout()
        vbox.addLayout(hbox)

        self.stacked = QtGui.QStackedWidget()
        vbox.addWidget(self.stacked)

        self.setLayout(vbox)
        self.setMaximumHeight(350)

    def initConn(self):

        self.createbtn.clicked.connect(self.createBlk)
        self.delbtn.clicked.connect(self.deleteBlk)
        self.listView.currentRowChanged.connect(self.blockDisplay)

    def blockDisplay(self,i):

        self.stacked.setCurrentIndex(i)

    def createBlk(self):

        blocknumer = len(self.blocks)
        curblock = SingleBlock(pulsedesigner=self.pulsedesigner, tablevars=self.tablevars)
        self.listView.addItem(QtGui.QListWidgetItem('block'+str(blocknumer)))
        self.blocks.append(curblock)
        self.stacked.addWidget(curblock)
        self.blockDisplay(blocknumer)

    def deleteBlk(self):

        blocknumer = self.listView.currentRow() # selectedIndexes()
        del(self.blocks[blocknumer])
        self.stacked.removeWidget(self.stacked.widget(blocknumer))
        self.listView.clear()
        for i,b in enumerate(self.blocks):
            self.listView.addItem(QtGui.QListWidgetItem('block'+str(i)))
        if len(self.blocks) > 0:
            self.blockDisplay(blocknumer-1)
            self.pulsedesigner.updatePulsesScheme(progress = 0 )

    def clearAll(self):

        while self.stacked.count() > 0:
            self.stacked.removeWidget(self.stacked.widget(0))

        self.blocks = []
        self.listView.clear()
        time.sleep(0.01)



class SingleBlock(QtGui.QWidget):
    def __init__(self,parent = None,pulsedesigner = None,tablevars = None):
        QtGui.QWidget.__init__(self, parent)
        self.pulsedesigner = pulsedesigner
        self.tablevars = tablevars
        self.BLOCK = {"channels":[],"duration":0,"setstart":False,"starttime":0}
        self.initGUI()
        self.initConn()

    def initGUI(self):

        vbox = QtGui.QVBoxLayout()

        label = QtGui.QLabel('Channels:')

        self.laserbox = QtGui.QCheckBox('Laser')
        self.rfbox = QtGui.QCheckBox('RF')
        self.mwbox = QtGui.QCheckBox('MW')
        self.detectbox = QtGui.QCheckBox('Detect')
        self.refdetectbox = QtGui.QCheckBox('Ref Det')

        self.chboxdict = {"Laser":self.laserbox,"RF":self.rfbox,
                          "MW":self.mwbox,"Detect":self.detectbox,
                          "RefDet":self.refdetectbox}


        hbox = QtGui.QHBoxLayout()
        self.starttime = QtGui.QCheckBox('Set Start Time')

        hbox.addWidget(self.starttime)
        self.tstart = QtGui.QLineEdit('0')
        label4= QtGui.QLabel("T Start, ns")
        hbox.addWidget(label4)
        hbox.addWidget(self.tstart)
        label3 = QtGui.QLabel("Duration, ns")
        self.duration = QtGui.QLineEdit('300')
        hbox.addWidget(label3)
        hbox.addWidget(self.duration)


        label2 = QtGui.QLabel('Timing')
        vbox.addWidget(label2)
        vbox.addLayout(hbox)

        vbox.addWidget(label)
        vbox.addWidget(self.laserbox)
        vbox.addWidget(self.rfbox)
        vbox.addWidget(self.mwbox)
        vbox.addWidget(self.detectbox)
        vbox.addWidget(self.refdetectbox)
        self.slide = QtGui.QSlider(QtCore.Qt.Horizontal)
        vbox.addWidget(self.slide)

        #vbox.addWidget(self.startFromLast)

        vbox.addStretch(1)
        self.setLayout(vbox)

    def initConn(self):
        self.duration.textEdited.connect(self.updateBlock)
        self.starttime.stateChanged.connect(self.updateBlock)
        self.laserbox.stateChanged.connect(self.updateBlock)
        self.rfbox.stateChanged.connect(self.updateBlock)
        self.mwbox.stateChanged.connect(self.updateBlock)
        self.detectbox.stateChanged.connect(self.updateBlock)
        self.refdetectbox.stateChanged.connect(self.updateBlock)
        self.tstart.textEdited.connect(self.updateBlock)
        self.slide.valueChanged.connect(self.updateBlock)

    def updateBlock(self):

        channels = []
        for key in self.chboxdict.keys():
            if self.chboxdict[key].isChecked():
                channels.append(key)

        self.BLOCK["channels"] = channels
        self.BLOCK["duration"] = getvalue(self.duration, tablevars=self.tablevars.vartable)
        self.BLOCK["setstart"] = self.starttime.isChecked()
        if self.starttime.isChecked():
            self.BLOCK["starttime"] = getvalue(self.tstart)
        else:
            self.BLOCK["starttime"] = 0
        #print self.BLOCK
        self.pulsedesigner.updatePulsesScheme(progress=self.slide.value()*0.01)
        #print self.slide.value()

class GroupsWidget(QtGui.QWidget):
    def __init__(self,parent = None, blocks = None):
        QtGui.QWidget.__init__(self, parent)
        self.blocks = blocks
        self.groups = []
        self.initGUI()
        self.initConn()
    def initGUI(self):
        self.createbtn = QtGui.QPushButton('Create')
        self.stacked = QtGui.QStackedWidget()


        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.createbtn)
        vbox.addWidget(self.stacked)
        self.setLayout(vbox)

    def initConn(self):

        self.createbtn.clicked.connect(self.createGr)

    def createGr(self):
        newgroup = Group(allblocks=self.blocks)
        self.groups.append(newgroup)
        self.stacked.addWidget(newgroup)
        self.stacked.setCurrentIndex(len(self.groups)-1)




class Group(QtGui.QWidget):
    def __init__(self,parent = None, allblocks = None):
        QtGui.QWidget.__init__(self, parent)
        self.blocks = []
        self.allblocks = allblocks
        self.initGUI()
        self.initConn()
    def initGUI(self):

        vbox = QtGui.QVBoxLayout()
        self.blocklist = QtGui.QListWidget()
        for i,b in enumerate(self.allblocks):
            self.blocklist.addItem(QtGui.QListWidgetItem("block"+str(i)))
        vbox.addWidget(self.blocklist)
        self.numrepeats = QtGui.QSpinBox()
        self.numrepeats.setValue(1)
        self.numrepeats.setMaximum(10000)
        label = QtGui.QLabel('Repeats')
        vbox.addWidget(label)
        vbox.addWidget(self.numrepeats)
        self.setLayout(vbox)

    def initConn(self):
        pass


class SequenceWidget(QtGui.QWidget):
    def __init__(self,parent = None):
        QtGui.QWidget.__init__(self, parent)
        self.blocks = {}
        self.groups = {}
        self.initGUI()
    def initGUI(self):
        vbox = QtGui.QVBoxLayout()
        self.detectors = QtGui.QComboBox()
        self.detectors.addItems(['APDs','Photo Detectors'])
        self.detectors.setCurrentIndex(1)
        self.internalrepeats = QtGui.QSpinBox()
        self.internalrepeats.setValue(2)
        self.internalrepeats.setMaximum(100000)
        self.label = QtGui.QLabel('Number of internal repeats')
        vbox.addWidget(self.internalrepeats)
        vbox.addWidget(self.label)
        vbox.addWidget(self.detectors)
        self.setLayout(vbox)


class VariablesWidget(QtGui.QWidget):
    def __init__(self,parent = None):
        QtGui.QWidget.__init__(self, parent)
        #self.variables = {}
        self.initGUI()
        self.initConn()
    def initGUI(self):
        hbox = QtGui.QHBoxLayout()

        self.plusbtn  = QtGui.QPushButton('+')
        self.delbtn = QtGui.QPushButton('-')
        hbox.addWidget(self.plusbtn)
        hbox.addWidget(self.delbtn)

        self.vartable = QtGui.QTableWidget(0,5)
        header = self.vartable.horizontalHeader()
        header.setResizeMode(QtGui.QHeaderView.Stretch)
        self.vartable.setHorizontalHeaderLabels(("Name","Value","Stop","Number","By Iterator"))

        self.vartable.insertRow(0)
        self.vartable.insertRow(1)
        self.vartable.insertRow(2)
        self.vartable.insertRow(3)

        self.vartable.setItem(0,0,QtGui.QTableWidgetItem('f_mw'))
        self.vartable.setItem(1,0,QtGui.QTableWidgetItem('f_rf'))
        self.vartable.setItem(2,0,QtGui.QTableWidgetItem('p_mw'))
        self.vartable.setItem(3,0,QtGui.QTableWidgetItem('p_rf'))

        self.vartable.setItem(0,1,QtGui.QTableWidgetItem('2.87e9'))
        self.vartable.setItem(1,1,QtGui.QTableWidgetItem('5e6'))
        self.vartable.setItem(2,1,QtGui.QTableWidgetItem('-30'))
        self.vartable.setItem(3,1,QtGui.QTableWidgetItem('-30'))

        vbox = QtGui.QVBoxLayout()
        vbox.addLayout(hbox)
        vbox.addWidget(self.vartable)
        self.setLayout(vbox)

    def initConn(self):

        self.plusbtn.clicked.connect(self.addVar)
        self.delbtn.clicked.connect(self.delVar)
        self.vartable.cellChanged.connect(self.findSweeps)

    def addVar(self):

        currow = self.vartable.rowCount()
        self.vartable.insertRow(currow)

    def delVar(self):

        try:
            if self.vartable.selectedIndexes()[0].row() > 3:
                self.vartable.removeRow(self.vartable.selectedIndexes()[0].row())
        except:
            pass

    def findSweeps(self):

        start = None
        stop = None
        step = None

        self.vars = {}

        for i in range(self.vartable.rowCount()):
            try:
                stop = float(self.vartable.item(i,2).text())
                start = float(self.vartable.item(i,1).text())
                step = (stop - start) / float(self.vartable.item(i,3).text())
                self.sweep = {'name':self.vartable.item(i,0).text(),
                              'values':np.arange(start,stop,step)}
                print self.sweep
            except:
                try:
                    self.vars[self.vartable.item(i,0).text()] = float(self.vartable.item(i,1).text())
                except:
                    pass

    def seqType(self):
        try:
            if self.sweep['name'] == 'f_rf':
                return 0
            elif self.sweep['name'] == 'f_mw':
                return 1
            else:
                return 2
        except:
            return 2

    def variables(self):
        vars = {}
        for i in range(self.vartable.rowCount()):
            try:
                name = self.vartable.item(i,0).text()
                try:
                    initialvalue = self.vartable.item(i,1).text()
                except:
                    initialvalue = ""

                try:
                    stopvalue = self.vartable.item(i,2).text()
                except:
                    stopvalue = ""

                try:
                    number = self.vartable.item(i,3).text()
                except:
                    number = ""

                try:
                    byiterator = self.vartable.item(i,4).text()
                except:
                    byiterator = ""

                vars[name] = {'initialvalue': initialvalue,
                              'stopvalue': stopvalue,
                              'number': number,
                              'byiterator': byiterator}

            except:
                pass
        return vars

    def updateVars(self, variables):

        for i in range(self.vartable.rowCount()):
            self.vartable.removeRow(0)
        for i,var in enumerate(variables.keys()):
            self.vartable.insertRow(self.vartable.rowCount())
            self.vartable.setItem(i,0,QtGui.QTableWidgetItem(var))

            try:
                self.vartable.setItem(i,1,QtGui.QTableWidgetItem(variables[var]['initialvalue']))
            except:
                pass
            try:
                self.vartable.setItem(i,2,QtGui.QTableWidgetItem(variables[var]['stopvalue']))
                self.vartable.setItem(i,3,QtGui.QTableWidgetItem(variables[var]['number']))
                self.vartable.setItem(i,4,QtGui.QTableWidgetItem(variables[var]['byiterator']))
            except:
                pass

def getvalue(qlineedit,tablevars = None):
    try:
        num = float(qlineedit.text())
        qlineedit.setStyleSheet("""QLineEdit { background-color: white; color: black }""")

    except:

        if tablevars is not None:
            n = tablevars.rowCount()
            var = []
            for i in range(n):
                if qlineedit.text() == tablevars.item(i,0).text():
                    try:
                        a =int(tablevars.item(i,1).text())
                        b =int(tablevars.item(i,2).text())
                        c = float(tablevars.item(i,3).text())
                        print a,b,c
                        num = np.arange(a,b,(b-a)/c)
                    except:
                        num = int(tablevars.item(i,1).text())

                    return num
            qlineedit.setStyleSheet("""QLineEdit { background-color: pink; color: red }""")
            return None

        else:
            qlineedit.setStyleSheet("""QLineEdit { background-color: pink; color: red }""")
            return None

    return num



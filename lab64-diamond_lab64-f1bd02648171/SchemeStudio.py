import sys
#from tryGage import gagescope

from NuclearReadout import SSR

from TimeTraceQT import timetrace
from ESR_QT import *
# from Sensitivity_QT import *
from Rabi_QT import *
from Pulses_QT import Pulses
# from SRTAU_OPT import *
from PySide import QtCore, QtGui
# import matplotlib
# import os
# import fnmatch
# import codecs
import pickle
class SchemeStudio(QtGui.QWidget):
    def __init__(self,parent = None, rf = None, smiq= None, fpga = None):
        super(SchemeStudio, self).__init__()
        self.initGUI()
        self.rf = rf
        self.smiq = smiq
        self.fpga = fpga

    def initGUI(self):

        self.tabs = {}
        self.names = []
        grid = QtGui.QGridLayout()

# main tabs
        self.tw = QtGui.QTabWidget()
        self.tw.setTabsClosable(True)
        menubox = QtGui.QHBoxLayout()
        self.opbtn = QtGui.QPushButton('Open')
        self.desbtn = QtGui.QPushButton('Create')
        self.savebtn = QtGui.QPushButton('Save')

        menubox.addWidget(self.opbtn)
        menubox.addWidget(self.desbtn)
        menubox.addWidget(self.savebtn)

        grid.addLayout(menubox,0,1,1,1)
        grid.addWidget(self.tw,1,1,1,1)

        self.setGeometry(100, 100, 1000, 600)
        self.setLayout(grid)
        self.desbtn.clicked.connect(self.addScheme)
        self.opbtn.clicked.connect(self.openScheme)
        self.savebtn.clicked.connect(self.saveScheme)

    def openScheme(self):

        file = QtGui.QFileDialog.getOpenFileName(self,
                                                 'Open scheme',
                                                 'C:\\Users\\Alexey\\PycharmProjects\\Diamond\\Schemes')

    def saveScheme(self):

        file = QtGui.QFileDialog.getSaveFileName(self,
                                                 'Save scheme',
                                                 'C:\\Users\\Alexey\\PycharmProjects\\Diamond\\Schemes')



    def addScheme(self, name=None):

        if name is None:
            name = self.askName()

        if name not in self.names:
            self.names.append(name)
            self.tabs[name] = Scheme(name = name, fpga=  self.fpga, rf = self.rf, smiq = self.smiq)
            self.tw.addTab(self.tabs[name],name)
        else:
            self.error('The name already exist, please enter again')

    def askName(self):
        text, ok = QtGui.QInputDialog.getText(self, 'New scheme',
            'Enter scheme name:')

        if ok:
            return str(text)

    def askFile(self):

        filepath= QtGui.QFileDialog.getOpenFileName(self, 'Open scheme', 'C:\\Users\\Alexey\\PycharmProjects\\Diamond\\Schemes')
        return filepath

    def error(self,string):
        error = QtGui.QErrorMessage()
        error.showMessage(string)
        error.exec_()

    def closeEvent(self, *args, **kwargs):
        print "Closing pm"
        #self.gage.free()


    def openScheme(self):

        file = QtGui.QFileDialog.getOpenFileName(self,
                                                 'Open scheme',
                                                 'C:\\Users\\Alexey\\PycharmProjects\\Diamond\\Schemes')

        try:
            data= pickle.load(file = open(file[0],'rb'))
        except:
            print 'loading failed'
        print 'scheme info: ', data

        if data['name'] in self.names:
            print 'Schemewith such name: '+data['name'] + ' already opened - changing the name!'
            name = data['name']+'_'
        else:
            name = data['name']
        self.addScheme(name = name)
        self.tabs[name].unzipScheme(data)




    def saveScheme(self):

        file = QtGui.QFileDialog.getSaveFileName(self,
                                                 'Save scheme',
                                                 'C:\\Users\\Alexey\\PycharmProjects\\Diamond\\Schemes\\sch')
        #print file[0],open(file[0],'wb')
        dict = {}
        dict['name'] = self.tw.currentWidget().name
        dict['blocks'] = [b.BLOCK for b in self.tw.currentWidget().pulsesmanager.myblocks.blocks]
        dict['variables'] = self.tw.currentWidget().pulsesmanager.myvariables.variables()
        print dict['name']
        print dict['variables']
        pickle.dump(obj=dict,file=open(file[0],'wb'))


class Scheme(QtGui.QWidget):

    def __init__(self,parent = None, name = None, fpga = None, rf = None, smiq = None, zipedScheme = None, gage = None, dtg = None, NI = None, esr = None):
        QtGui.QWidget.__init__(self, parent)
        self.name = name
        self.rf = rf
        self.d = dtg
        self.smiq = smiq
        self.esr = esr
        self.gage = gage
        self.fpga = fpga
        self.NI = NI
        self.initGUI()
        self.initConn()
        self.timer = QtCore.QTimer()
        self.data = None
        self.timer.timeout.connect(self.mainloop)
        self.dt = 100

    def initGUI(self):

        vbox = QtGui.QVBoxLayout()
        self.schemeplot = UTILS_QT.PulsesPlot()
        self.pb = QtGui.QProgressBar()
        self.pulsesmanager = UTILS_QT.PulsesDesigner(schemeplot = self.schemeplot,
                                                     fpga = self.fpga)
        self.plot = UTILS_QT.DataPlot()
        self.saver = saver(category = self.name)
        #self.fitmanager = UTILS_QT.FitDesigner()

        hbox = QtGui.QHBoxLayout()
        hbox1 = QtGui.QHBoxLayout()

        hvbox1 = QtGui.QVBoxLayout()
        hvbox1.addWidget(self.schemeplot)

        hhbox = QtGui.QHBoxLayout()
        self.startBtn = QtGui.QPushButton('Start')

        hhbox.addWidget(self.pb)
        hhbox.addWidget(self.startBtn)
        hvbox1.addLayout(hhbox)

        hvbox2 = QtGui.QVBoxLayout()
        hvbox2.addWidget(self.pulsesmanager)
        hbox.addLayout(hvbox1)
        hbox.addLayout(hvbox2)

        h1vbox1 = QtGui.QVBoxLayout()
        h1vbox1.addWidget(self.plot)


        h1vbox2 = QtGui.QVBoxLayout()
        h1vbox2.addWidget(self.saver)
        #h1vbox2.addWidget(self.fitmanager)

        hbox1.addLayout(h1vbox1)
        hbox1.addLayout(h1vbox2)

        vbox.addLayout(hbox)
        vbox.addLayout(hbox1)

        self.setLayout(vbox)

    def initConn(self):
        self.startBtn.clicked.connect(self.startStop)

    def startStop(self):

        if self.timer.isActive():
            self.timer.stop()
            self.smiq.Off()
            self.rf.Off()
            self.stop = True

        else:
            self.stop = False
            self.sequencetype = self.pulsesmanager.myvariables.seqType()
            self.setGEN()

            if self.sequencetype < 2:
                self.programm = self.pulsesmanager.getProgramm()
            self.currIter = 0
            self.data = None
            self.plot.myplot.clearall()
            self.int_spectrum_referenced = None
            self.cw_spectrum_data = None
            self.cw_spectrum_data_av = None
            self.timer.start(self.dt)

    def setGEN(self):
        if self.sequencetype == 0:
            freqs = self.pulsesmanager.myvariables.sweep['values']
            p_rf = np.ones(freqs.shape)*self.pulsesmanager.myvariables.vars['p_rf']
            self.rf.On()
            self.rf.List(freqs= freqs, powers = p_rf)

            f_mw = self.pulsesmanager.myvariables.vars['f_mw']
            p_mw = self.pulsesmanager.myvariables.vars['p_mw']
            self.smiq.CW(f=f_mw, power=p_mw)
            self.smiq.On()

        if self.sequencetype == 1:

            freqs = self.pulsesmanager.myvariables.sweep['values']
            freqstart = freqs[0]
            freqfinish = freqs[-1]
            numbval = freqs.shape[0]
            p_rf = self.pulsesmanager.myvariables.vars['p_rf']
            f_rf = self.pulsesmanager.myvariables.vars['f_rf']
            self.rf.CW(f=f_rf,p=p_rf)

            self.smiq.listmode(startfreq=freqstart,
                               endfreq=freqfinish,
                               numbval=numbval,
                               power = self.pulsesmanager.myvariables.vars['p_mw'])

        if self.sequencetype == 2:

            p_rf = self.pulsesmanager.myvariables.vars['p_rf']
            f_rf = self.pulsesmanager.myvariables.vars['f_rf']
            f_mw = self.pulsesmanager.myvariables.vars['f_mw']
            p_mw = self.pulsesmanager.myvariables.vars['p_mw']
            self.smiq.CW(f=f_mw, power=p_mw)
            self.smiq.On()
            self.rf.CW(f=f_rf,p=p_rf)

    def mainloop(self):
        if self.sequencetype == 0:
            self.runrfsweep(self.programm)
        elif self.sequencetype == 1:
            self.runmwsweep(self.programm)

        else:
            self.runtimeparametersweep()

    def runrfsweep(self,programm):
        self.currIter +=1
        freqs = self.pulsesmanager.myvariables.sweep['values']
        data = np.zeros(freqs.shape[0])
        self.pb.setMaximum(freqs.shape[0])


        for i,f in enumerate(freqs):

            if self.stop:
                break
            self.pb.setValue(i)
            status,c,refc,col_signal,col_ref_signal= self.fpga.run_sequence(programm=programm,
                               number_repeats=1,detectors=self.pulsesmanager.mysequence.detectors.currentIndex())
            self.rf.Trigger()

            if self.pulsesmanager.mysequence.detectors.currentIndex():
                if col_ref_signal != 0:
                    data[i]= 1.0*col_signal/col_ref_signal
                else:
                    data[i]= 1.0*col_signal
            else:
                if refc == 0:
                    data[i]= (1.0*c)
                else:
                    data[i]= (1.0*c/refc)
            QtCore.QCoreApplication.processEvents()

        # if self.data is not None:
        #     for i,d in enumerate(data):
        #         if d == 0:
        #             data[i] = self.data[i]

        # for case of stop not to affect acquired averaged data
        if not self.stop:

            if self.data is None:
                self.data = data
            else:
                self.data = (self.data*(self.currIter-1) + data)/self.currIter



            if len(self.plot.myplot.plots) == 0:

                self.plot.myplot.addCurve(datax = freqs, datay = self.data, name = 'rf sweep', xlabel = ['RF freq','Hz'])
            else:
                self.plot.myplot.updateSubplot(i = 0, dataX = freqs, dataY = self.data)

    def runmwsweep(self, programm):

        self.currIter +=1
        freqs = self.pulsesmanager.myvariables.sweep['values']
        data = np.zeros(freqs.shape)
        num_repeats = self.pulsesmanager.mysequence.internalrepeats.value()
        det_type = self.pulsesmanager.mysequence.detectors.currentIndex()
        progpre = [self.fpga.set_loops(num_repeats),0xC0000015,self.fpga.delayFromNS(1000)]
        programmnew = []
        for p in progpre:
            programmnew.append(p)
        for p in programm:
            programmnew.append(p)

        programmnew[-2] = 0x20000004
        print [hex(p) for p in programmnew]

        status,c,refc,col_signal,col_ref_signal = self.fpga.run_sequence(
            programm=programmnew,
            number_repeats=freqs.shape[0],
            detectors=self.pulsesmanager.mysequence.detectors.currentIndex())

        # extracting of data from fpga FIFO

        if det_type == 0:
            data  = self.fpga.data
            #print len(data)
            self.cw_spectrum_data = np.array(divmod(data[0],2**32)).reshape((1,2))
            self.cw_spectrum_data = np.append(self.cw_spectrum_data,
                                          np.diff(np.array([divmod(i,2**32) for i in data]),axis = 0)*1.0, axis = 0)
        elif det_type == 1:
            data = np.array(self.fpga.data).reshape((-1,7))
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

            # self.cw_spectrum_data = np.array([data1[0],data[0]]).reshape((1,2))
            # self.cw_spectrum_data = np.append(self.cw_spectrum_data,
            #                               np.diff(np.array([data1,data]).T,axis = 0)*1.0, axis = 0)

        # averaging :
        # 1. current iteration
        # if self.cw_spectrum_data_av is None:
        #     self.cw_spectrum_data_av = self.cw_spectrum_data
        # else:
        #     self.cw_spectrum_data_av = ((self.currIter-1) * self.cw_spectrum_data_av + self.cw_spectrum_data)/self.currIter


        # 2. averaged over iterations

        # if self.int_spectrum_referenced is None:
        #     try:
        #         self.int_spectrum_referenced = (self.cw_spectrum_data_av[:,0])/self.cw_spectrum_data_av[:,1]
        #     except:
        #         self.int_spectrum_referenced = self.cw_spectrum_data_av[:,0] * 0
        # else:
        #     self.int_spectrum_referenced = ((self.currIter-1)*self.int_spectrum_referenced +
        #                                     (self.cw_spectrum_data_av[:,0])/self.cw_spectrum_data_av[:,1])/self.currIter


        if self.int_spectrum_referenced is None:
            self.int_spectrum_referenced = self.cw_spectrum_data

        else:
            self.int_spectrum_referenced = ((self.currIter-1)*self.int_spectrum_referenced +
                                            self.cw_spectrum_data)/self.currIter
        # try:
        #     current_ratio = self.cw_spectrum_data[:]
        # except:
        #     current_ratio = self.cw_spectrum_data[:]


        # plotting
        if len(self.plot.myplot.plots) == 0:
            self.plot.myplot.addCurve(datax = freqs[:], datay = self.int_spectrum_referenced[:], name = 'mw sweep', xlabel = ['MW freq','Hz'])
        else:
            self.plot.myplot.updateSubplot(i = 0, dataX = freqs[:], dataY = self.int_spectrum_referenced[:])

    def runtimeparametersweep(self):
        self.currIter +=1
        taus = self.pulsesmanager.myvariables.sweep['values']
        data = np.zeros(taus.shape)
        self.pb.setMaximum(taus.shape[0]-1)


        for i,t in enumerate(taus):

            programm = self.pulsesmanager.getProgramm(i=i)

            self.schemeplot.psp.plotprograms(programm)

            self.pb.setValue(i)
            status,c,refc,col_signal,col_ref_signal= self.fpga.run_sequence(programm=programm,
                               number_repeats=1,detectors=self.pulsesmanager.mysequence.detectors.currentIndex())


            if self.pulsesmanager.mysequence.detectors.currentIndex():
                if col_ref_signal != 0:
                    data[i]= 1.0*col_signal/col_ref_signal
                else:
                    data[i]= 1.0*col_signal
            else:
                if refc == 0:
                    data[i]= (1.0*c)
                else:
                    data[i]= (1.0*c/refc)
            QtCore.QCoreApplication.processEvents()

        if self.data is None:
            self.data = data
        else:
            self.data = (self.data*(self.currIter-1) + data)/self.currIter

        if len(self.plot.myplot.plots) == 0:
            self.plot.myplot.addCurve(datax = taus, datay = self.data, name = 'rf sweep', xlabel = ['RF freq','Hz'])
        else:
            self.plot.myplot.updateSubplot(i = 0, dataX = taus, dataY = self.data)


    def unzipScheme(self,data):

        # blocks

        blocks = data['blocks']
        self.pulsesmanager.myblocks.clearAll()
        print len(self.pulsesmanager.myblocks.blocks), 'NUMbeR OF BLOCKS AFTER CLEAR'
        for i,b in enumerate(blocks):
            print i, 'th BLOCK',b
            self.pulsesmanager.myblocks.createBlk()
            for key in b['channels']:
                self.pulsesmanager.myblocks.blocks[i].chboxdict[key].setChecked(True)
            self.pulsesmanager.myblocks.blocks[i].BLOCK = b
            try:
                self.pulsesmanager.myblocks.blocks[i].duration.setText(b['variables']['duration'])
            except:
                try:
                    self.pulsesmanager.myblocks.blocks[i].duration.setText(str(float(b['duration'])))
                except:
                    try:
                        self.pulsesmanager.myblocks.blocks[i].duration.setText(str(float(b['duration'][0])))
                    except:
                        self.pulsesmanager.myblocks.blocks[i].duration.setText(str(305))

        # variables

        variables = data['variables']

        self.pulsesmanager.myvariables.updateVars(variables)





def main():
    app = QtGui.QApplication(sys.argv)
    form = SchemeStudio()
    form.show()
    ret = app.exec_()
    sys.exit(ret)

#main()



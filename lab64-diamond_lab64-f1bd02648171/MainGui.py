__author__ = 'Vadim Vorobyov'
import sys
#from tryGage import gagescope

# from NuclearReadout import SSR

# from TimeTraceQT import timetrace
# from ESR_QT import *
# from Sensitivity_QT import *
# from Rabi_QT import *
# from Pulses_QT import Pulses
# from SchemeStudio import SchemeStudio
# from SRTAU_OPT import *
from PySide import QtCore, QtGui
import matplotlib
import os
import fnmatch
import codecs

# from PY_NI_FPGA import Fpga
# from SR_RF_GEN import generator
# from tryGage import gagescope
# from DTG_QT import  DTG
# from NIDAQ_QT import nidaqmx
# from SMIQ_QT import SMIQ

class MainProgramm(QtGui.QWidget):
    def __init__(self, parent=None):
        super(MainProgramm, self).__init__()

        self.gage = None#gagescope()
        self.d = None#DTG()
        self.NI = None#nidaqmx()

        self.fpga = None#Fpga()
        self.rf = None#generator()

        # self.gage.GetInfo()
        # self.gage.InitCycle()
        self.smiq = None#SMIQ()
        self.initUI()
        #self.fpga.run_sequence(self.fpga.programm_exc_enable())


    def initUI(self):
        self.tabs = []
        grid = QtGui.QGridLayout()

# main tabs

        self.tw = QtGui.QTabWidget()
        grid.addWidget(self.tw,0,1,2,1)

        #1st tab - timetrace


        self.timetrace = timetrace(gage=self.gage, d = self.d, fpga = self.fpga)
        self.tw.addTab(self.timetrace,'TimeTrace')

        # 2nd tab ESR
        self.esr = ESR(gage = self.gage, d = self.d, NI= self.NI, smiq = self.smiq, fpga = self.fpga)
        self.tw.addTab(self.esr,'ESR')

        # 3 rd tab sensitivity

                # self.sensor = sensor(gage = self.gage, d = self.d, NI = self.NI, smiq = self.smiq, timetrace=self.timetrace, esr=self.esr)
                # self.tw.addTab(self.sensor,'MW Acquisition')


        # 4th tab Optical Acquisition

                # self.tauopt = srtauopt(gage = self.gage)
                # self.tw.addTab(self.tauopt,'Optical Acquisition')

        # 5th tab Rabi
        #self.rabi = rabi(gage = self.gage, d = self.d, NI = self.NI, s = self.smiq)
        #self.tw.addTab(self.rabi,'Rabi')


        # 6th tab SSR

        self.ssr =  SSR(fpga=self.fpga,
                        smiq=self.smiq)
        self.tw.addTab(self.ssr,'Nuclear Readout')

        # 7th tab SSR

        self.pulses =  Pulses(s=self.smiq,fpga = self.fpga)
        self.tw.addTab(self.pulses,'Pulses')

        # 8th tab

        self.pm = SchemeStudio(fpga= self.fpga, smiq = self.smiq, rf = self.rf)
        self.tw.addTab(self.pm, 'Schemes Studio')


# EVENTS
#         self.tw.blockSignals(True)
#         self.tw.currentChanged.connect(timetrace.externalstop)
#         self.tw.blockSignals(False)

# GEOMETRY
        self.setGeometry(100, 100, 1000, 600)
        self.setLayout(grid)


    def closeEvent(self, *args, **kwargs):
        print("Closing")
        #self.gage.free()

def main():
    app = QtGui.QApplication(sys.argv)
    form = MainProgramm()
    form.show()
    ret = app.exec_()
    sys.exit(ret)

main()


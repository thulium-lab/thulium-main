try:
    from .device_lib import LANDevice
except:
    from device_lib import LANDevice

from Lib import *
from PyQt5.QtCore import (Qt,)
from PyQt5.QtGui import (QDoubleValidator)
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QAction,QMenuBar,
                             QLabel, QLineEdit, QPushButton)
import json

SCAN_PARAMS_STR = 'available_scan_params'
NAME_IN_SCAN_PARAMS = 'SRS_clock'

class SRS_LAN(LANDevice):
    identification_names = ['Stanford Research Systems', 'SG382','s/n001915']
    timeout = 1
    ip = '192.168.1.245'
    port = 5025

    def setFreq(self,freq):
        status,readout = self.write(b'FREQ %f MHz\r' %(freq))
        print(status, readout)

    def setAmpl(self,ampl):
        status,readout = self.write(b'AMPR %f\r' %(ampl))
        print(status, readout)

    def getFreq(self):
        return self.write_read(b'FREQ? MHz\r')

    def getAmpl(self):
        return self.write_read(b'AMPR?\r')

class SRSGenerator(QWidget):
    def __init__(self,parent=None,globals=None,signals=None,config_file='config.json'):
        super().__init__()
        self.parent = parent
        self.globals = globals
        self.signals = signals
        self.config_file = config_file
        self.freq_center = 417500
        self.freq_offset = 0.0
        self.ampl = 0.0
        self.load()
        self.srs = SRS_LAN() #SRS_COM(self.config.get('port',''))
        self.setWindowTitle('SRS_clock')
        self.initUI()
        self.setMaximumWidth(500)
        self.sendScanParams()
        if self.signals:
            self.signals.updateFromScanner.connect(self.updateFromScanner)
            self.signals.scanFinished.connect(self.scanFinishedHandler)

    def load(self):
        print('load SRS_clock', end='\t')
        with open(self.config_file, 'r') as f:
            print('config_load')
            config = json.load(f)
        # print(config)
        self.__dict__.update(config['SRS_clock'])

    def save(self,dict_to_save):
        print('save SRS_clock')
        self.constructData()
        with open(self.config_file, 'r') as f:
            print('SRS_clock config_load_before_saving')
            all_config = json.load(f)
        config = all_config['SRS_clock']
        for key in config:
            config[key] = self.__dict__[key]
        with open(self.config_file, 'w') as f:
            print('config_save')
            json.dump(all_config, f)

    def constructData(self):
        self.freq_center = self.f_c_line.getValue()
        self.freq_offset = self.f_o_line.getValue()
        self.ampl = self.amp_line.getValue()

    def initUI(self):
        self.menuBar = QMenuBar(self)
        fileMenu = self.menuBar.addMenu('&File')
        save = QAction('&Save', self)
        save.triggered.connect(self.save)
        fileMenu.addAction(save)
        layout = QHBoxLayout()

        l1= QVBoxLayout()
        l1.addStretch(0.5)

        restor_btn = QPushButton('Restore')
        restor_btn.clicked.connect(self.restore)
        l1.addWidget(restor_btn)

        l1.addWidget(QLabel('Center freq, kHz'))
        self.f_c_line = MyDoubleBox(validator=QDoubleValidator(10000,500000,3),value=self.freq_center, text_changed_handler=self.changeFrequency)
        l1.addWidget(self.f_c_line)

        l1.addWidget(QLabel('Offset freq, kHz'))
        self.f_o_line = MyDoubleBox(validator=QDoubleValidator(-10000,10000,3),value=self.freq_offset, text_changed_handler=self.changeFrequency)
        l1.addWidget(self.f_o_line)

        l1.addWidget(QLabel('Amp, dBm'))
        self.amp_line = MyDoubleBox(validator=QDoubleValidator(-40,7,2),value=self.ampl,text_changed_handler=self.changeAmplitude)
        l1.addWidget(self.amp_line)
        l1.addStretch(.5)
        layout.addLayout(l1)

        layout.addWidget(self.srs.BasicWidget(data=self.srs, parent=self,connect=True))

        self.setLayout(layout)

    def changeFrequency(self):
        print('SRS_clock - changeFrequency')
        try:
            freq = (self.f_o_line.getValue() + self.f_c_line.getValue())/1e3 # devide by 1e3 since SRS takes MHz as input
            # print(freq)
            if 1<freq<500:
                self.srs.setFreq(freq)
        except ValueError:
            print('SRS_clock - Frequency input is not a float')

    def changeAmplitude(self):
        print('SRS_clock - changeAmplitude')
        try:
            ampl = self.amp_line.getValue()
            # print(ampl)
            self.srs.setAmpl(ampl)
        except ValueError:
            print('SRS_clock - Amplitude input is not a float')

    def restore(self):
        status, freq = self.srs.getFreq()
        freq = round((float(freq.strip().strip('0'))*1e3),3)
        self.f_c_line.setValue(str(freq))
        self.f_o_line.setValue('0.0')
        status, ampl = self.srs.getAmpl()
        self.amp_line.setValue(ampl.strip())

    def sendScanParams(self):
        params = ['freq_center','freq_offset','ampl']
        if self.globals != None:
            if SCAN_PARAMS_STR not in self.globals:
                self.globals[SCAN_PARAMS_STR] = {}
            self.globals[SCAN_PARAMS_STR][NAME_IN_SCAN_PARAMS] = params
        return

    def scanFinishedHandler(self):
        """Called when scan finished to set offset frequency to 0"""
        self.freq_offset = 0
        self.f_o_line.setValue(0)
        self.changeFrequency()

    def updateFromScanner(self, param_dict=None):
        # self.scanner = True
        current_shot = self.globals["scan_running_data"]["current_meas_number"]
        # print("update SRS frequency", current_shot)
        # print( self.globals["scan_running_table"].loc[current_shot, "f0"])
        for param, path in {**self.globals["scan_params"]["main"],
                            **self.globals["scan_params"]["low"]}.items():
            if path[0] == NAME_IN_SCAN_PARAMS and (current_shot == 0 or
                                         self.globals["scan_running_table"].loc[current_shot, param] !=
                                         self.globals["scan_running_table"].loc[current_shot - 1, param]):
                val = self.globals["scan_running_table"].loc[current_shot, param]
                print("SRS_clock - update from scanner - ", param, path,val)
                print(param, val)
                if path[1] == 'freq_center':
                    self.f_c_line.setValue(str(val))
                    self.changeFrequency()
                elif path[1] == 'freq_offset':
                    print("HERERERE")
                    self.f_o_line.setValue(str(val))
                    self.changeFrequency()
                elif path[1] == 'ampl':
                    self.amp_line.setValue(str(val))
                    self.changeAmplitude()


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    mainWindow = SRSGenerator()
    mainWindow.show()
    sys.exit(app.exec_())
import os, sys, json
from PyQt5.QtCore import (pyqtSignal, QTimer, QRect, Qt, )
from PyQt5.QtGui import (QIcon, QDoubleValidator, )
from PyQt5.QtWidgets import (QPushButton, QHBoxLayout, QVBoxLayout, QLineEdit, QComboBox, QDoubleSpinBox, QApplication,
                             QWidget, QLabel, QMenuBar, QAction, QFileDialog, QInputDialog,QSizePolicy,QScrollArea )

if __name__ == '__main__':
    from DAQ import AnalogInput as AI
else:
    from Devices.DAQ import AnalogInput as AI

class PMT(QWidget):
    def __init__(self, parent=None, globals=None, signals=None):
        super(PMT, self).__init__()
        self.globals = globals
        self.parent = parent
        self.signals = signals
        self.setWindowTitle('PMT')
        self.config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings\last.pmt')
        self.initUI()
        self.setMaximumWidth(500)
        self.sendScanParams()

    def load(self):
        try:
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        except json.decoder.JSONDecodeError:
            print('ERROR in reading ', self.config_file)
            return
        except FileNotFoundError:
            print('File not yet exist')
            return
        for key in self.config:
            self.__dict__[key] = self.config[key]

    def save(self, dict_to_save):
        self.globals['image_lower_left_corner'] = self.roi_center
        print('saveConfig')
        try:
            with open(self.config_file, 'r') as f:
                old_config = json.load(f)
        except json.decoder.JSONDecodeError:
            old_config = {}
        except FileNotFoundError:
            old_config = {}
            print('File not yet exist')
        with open(self.config_file, 'w') as f:
            try:
                json.dump(self.config,f)
            except: # find what error does it raise when cannot dump
                json.dump(old_config, f)
                QMessageBox.warning(None, 'Message', "can not dump config to json, old version will be saved",
                                    QMessageBox.Ok)


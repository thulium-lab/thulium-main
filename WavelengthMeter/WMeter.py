import matplotlib
matplotlib.use('Qt5Agg',force=True)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from copy import deepcopy

from PyQt5.QtCore import (QLineF, QPointF, QRectF, Qt, QTimer)
from PyQt5.QtGui import (QBrush, QColor, QPainter)
from PyQt5.QtWidgets import (QApplication, QGraphicsView, QGraphicsScene, QGraphicsItem, QMenu, QAction, QScrollArea,QFrame,
                             QGridLayout, QVBoxLayout, QHBoxLayout, QSizePolicy,QMainWindow, QDialog,QTextEdit,
                             QLabel, QLineEdit, QPushButton, QWidget, QComboBox,QRadioButton, QSpinBox, QCheckBox, QTabWidget, QFileDialog,QMessageBox, QDoubleSpinBox)

import numpy as np
import scipy.constants as ct

n_air = 1.0002926
class WMChannel:
    # Дописать часть про спектры
    def __init__(self, name='New',shutter_number=None, is_active=True):
        self.name = name
        self.shutter_number = shutter_number
        self.is_active = is_active
        self.wavelength = 1140 #in nm
        self.spectrum = [0,0]

    @property
    def frequency(self):
        return  ct.c * n_air / self.wavelength *1e-3

    class WMChannelGUI(QWidget):
        def __init__(self,parent=None,data=None):
            self.parent = parent
            self.data = data
            super().__init__(parent=self.parent)
            main_layout = QVBoxLayout()

            layout1 = QHBoxLayout()
            self.btn_w = QRadioButton('nm')
            self.btn_w.setChecked(True)
            self.btn_w.toggled.connect(self.setValueText)#(lambda:self.unitChange(self.btn_w))
            layout1.addWidget(self.btn_w)
            self.btn_f = QRadioButton('THz')
            self.btn_f.setChecked(False)
            self.btn_f.toggled.connect(self.setValueText)#(lambda: self.unitChange(self.btn_f))
            layout1.addWidget(self.btn_f)

            # implemented in main window
            # self.show_box = QCheckBox('Show')
            # self.show_box.setChecked(False)
            # self.show_box.stateChanged.connect(lambda:self.showSpectrum(self.show_box.checkState()))
            # layout1.addWidget(self.show_box)

            main_layout.addLayout(layout1)

            self.name_line = QLabel(self.data.name)
            main_layout.addWidget(self.name_line)

            self.value = QLabel()
            self.setValueText()
            main_layout.addWidget(self.value)
            self.setLayout(main_layout)

        def setValueText(self):
            if self.btn_w.isChecked():
                self.value.setText("%.5f nm"%self.data.wavelength)
            else:
                self.value.setText("%.5f THz"%self.data.frequency)

        def showSpectrum(self,b):
            print('Show spectrum',b)
            # pass to parent



class WMMain():
    channels = []

    current_index = 0
    active_channels_indexes = []
    mode = 'all' # another possibility 'single' in case if I'll add this option
    def __init__(self, arduino = None):
        # import wlm
        # self.wlm = wlm
        if arduino == None:
            # try to connect to arduino
            pass
        self.arduino = arduino

    def addChannel(self,name,shutter_number):
        new_channel = WMChannel(name,shutter_number)
        self.channels.append(new_channel)
        self.active_channels_indexes = [i for i in range(len(self.channels)) if self.channels[i].is_active]
        self.current_index = self.active_channels_indexes[-1]
        print('Current index',self.current_index)

    def delChannel(self,name):
        for channel in self.channels:
            if channel.name == name:
                self.channels.remove(channel)
                break
        self.active_channels_indexes = [i for i in range(len(self.channels)) if self.channels[i].is_active]
        self.current_index = self.active_channels_indexes[-1]

    class WMWidget(QWidget):
        def __init__(self, parent=None, data=None):
            self.parent = parent
            self.data = data
            super().__init__(parent=self.parent)
            main_layout = QVBoxLayout()

            menu_layout = QHBoxLayout()
            chan_btn = QPushButton('Channels')
            chan_menu = QMenu(chan_btn)
            chan_menu.aboutToShow.connect(self.updateChannelsMenu)
            chan_btn.setMenu(chan_menu)
            menu_layout.addWidget(chan_btn)

            main_layout.addLayout(menu_layout)


            self.channels_layout = QGridLayout()
            self.drawChannels()

            main_layout.addLayout(self.channels_layout)
            self.setLayout(main_layout)
            print('WLM_GUI created')
            self.timer = QTimer(self)
            self.timer.setInterval(1000)
            self.timer.timeout.connect(self.routine)
            self.timer.start()

        def routine(self):
            if self.data.mode != 'all':
                return 0
            self.data.current_index = self.data.active_channels_indexes[
                (self.data.active_channels_indexes.index(self.data.current_index) + 1)%len(self.data.active_channels_indexes)]
            # print(self.data.current_index)
            channel = self.data.channels[self.data.current_index]
            self.

        def drawChannels(self):
            # cleen up previous grid
            while self.channels_layout.count():
                item = self.channels_layout.takeAt(0)
                item.widget().deleteLater()
            active_channels = [channel for channel in self.data.channels if channel.is_active]
            for i,channel in enumerate(active_channels):
                print(i%2,i//2)
                self.channels_layout.addWidget(channel.WMChannelGUI(parent=self,data=channel),i//2,i%2)

        def updateChannelsMenu(self):
            # print('updateAllScanParams')
            # print(self.data.globals)
            channels_menu = self.sender()
            channels_menu.clear()
            for channel in self.data.channels:
                print(channel.name)
                m = channels_menu.addMenu(channel.name)
                text = 'hide' if channel.is_active else 'show'
                act = m.addAction(text)
                # act.triggered.connect(lambda:self.showHideChannel(channel))
                act.triggered.connect(self.showHideChannel)
                act = m.addAction('del')
                # act.triggered.connect(lambda:self.delChannel(channel))
                act.triggered.connect(self.delChannel)
            new_chan_act = channels_menu.addAction('new')
            new_chan_act.triggered.connect(lambda:self.NewChannelWidget(parent=self))


        def showHideChannel(self,channel):
            # channel.is_active = not channel.is_active
            name = self.sender().parent().title()
            for channel in self.data.channels:
                if channel.name == name:
                    channel.is_active = not channel.is_active
                    break
            self.drawChannels()

        def delChannel(self):
            # print(self.sender().parent().title())
            name = self.sender().parent().title()
            # ask for confirmation
            for channel in self.data.channels:
                if channel.name == name:
                    self.data.channels.remove(channel)
                    break
            self.drawChannels()
            # print('del ', channel.name)

        def addNewChannel(self,caller):
            if caller.exit_status:
                # a = self.NewChannelWidget(parent=self)
                new_name = caller.name.text()
                new_shutter_channel = caller.shutter_channel.value()
                new_channel = WMChannel(name=new_name,shutter_number=new_shutter_channel)
                self.data.channels.append(new_channel)
                print(new_name, new_shutter_channel)
                self.drawChannels()
            del caller


        class NewChannelWidget(QDialog):
            def __init__(self, parent=None, data=None):
                super().__init__(parent)
                self.parent = parent
                # self.data = data
                # self.initUI()
                main_layout = QVBoxLayout()

                line1 = QHBoxLayout()
                line1.addWidget(QLabel('Name'))
                self.name = QLineEdit()
                line1.addWidget(self.name)
                main_layout.addLayout(line1)

                line2 = QHBoxLayout()
                line2.addWidget(QLabel('Shutter_channel'))
                self.shutter_channel = QSpinBox()
                self.shutter_channel.setMaximum(18)
                self.shutter_channel.setMinimum(0)
                self.shutter_channel.setMinimumWidth(10)
                line2.addWidget(self.shutter_channel)
                # line1.addWidget(self.name)
                main_layout.addLayout(line2)

                ok_cancel = QHBoxLayout()
                ok_btn = QPushButton('Create')
                ok_btn.clicked.connect(self.createChannel)
                ok_cancel.addWidget(ok_btn)

                cancel_btn = QPushButton('Cancel')
                cancel_btn.clicked.connect(self.cancelPressed)
                ok_cancel.addWidget(cancel_btn)

                main_layout.addLayout(ok_cancel)
                self.setLayout(main_layout)
                self.show()

            def createChannel(self):
                self.exit_status = True
                # data_to_send = {'name':self.name, 'shutter_channel':self.shutter_channel}
                self.close()
                self.parent.addNewChannel(self)

            def cancelPressed(self):
                self.exit_status = False
                self.close()
                self.parent.addNewChannel(self)

if __name__ == '__main__':
    # config = {}
    # config['day_folder'] = '2016_10_10'
    # config['all_meas_type'] = ['CL', 'LT', 'FB', 'T']
    # config['current_meas_type'] = 'CL'
    # config['add_points_flag']=  False
    # config['notes'] = 'some note'
    # config['number_of_shots'] = 10
    # with open(scanner_config_file,'w') as f:
    #     json.dump(config,f)
    import sys
    app = QApplication(sys.argv)
    a = WMChannel(name='Green',shutter_number=2,is_active=True)
    a.wavelength = 530.7
    b = WMChannel(name='Blue', shutter_number=4,is_active=True)
    b.wavelength = 410.6
    aw =  WMMain()
    # aw.channels.append(a)
    # aw.channels.append(b)
    aw.addChannel(name='Green',shutter_number=2)
    aw.addChannel(name='Blue', shutter_number=4)
    mainWindow = aw.WMWidget(data=aw)
    mainWindow.show()
    sys.exit(app.exec_())
import os, json, ctypes, sys, inspect, time
import pyqtgraph as pg
import numpy as np
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(os.path.dirname(currentdir))
sys.path.insert(0,parentdir)
# sys.path.append('..')
from Devices.WavelengthMeter import wlm
from Devices import arduinoShutters
# import wlm
# import arduinoShutters
#
from PyQt5.QtCore import (QTimer, pyqtSignal, Qt)
from PyQt5.QtGui import (QColor, QFont, QIcon)
from PyQt5.QtWidgets import (QApplication, QMenu, QColorDialog, QGridLayout, QVBoxLayout, QHBoxLayout, QDialog, QLabel,
                             QLineEdit, QPushButton, QWidget, QRadioButton, QSpinBox, QCheckBox, QButtonGroup,
                             QErrorMessage)
import datetime
import socket
HOST, PORT = "192.168.1.59", 9999
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

n_air = 1.0002926
cicle_counter = 0
folder = 'Devices\WavelengthMeter'
myAppID = u'LPI.WMWIndow' # arbitrary string
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myAppID)
waitTime = pyqtSignal()

class WMChannel:
    # Дописать часть про спектры
    def __init__(self, name='New', shutter_number=None, is_active=True, color=QColor(0,0,0)):
        self.name = name
        self.shutter_number = shutter_number
        self.is_active = is_active
        self.wavelength = 1140  # in nm
        self.amplitudes = (0,0)
        self.spectrum = [[], []]
        self.unit = 'nm' # alternative THz
        self.color = color
        self.show_spectrum = True
        self.frequency = 1
        self.single = False

    # @property
    # def frequency(self):
    #     return ct.c / n_air / self.wavelength * 1e-3

    class WMChannelGUI(QWidget):
        def __init__(self, parent=None, data=None):
            self.parent = parent
            self.data = data
            super().__init__(parent=self.parent)
            main_layout = QVBoxLayout()

            layout1 = QHBoxLayout()
            self.btn_w = QRadioButton('nm')
            self.btn_w.setChecked(self.data.unit == 'nm')
            self.btn_w.toggled.connect(self.unitChanged)  # (lambda:self.unitChange(self.btn_w))
            layout1.addWidget(self.btn_w)
            self.btn_f = QRadioButton('THz')
            self.btn_f.setChecked(self.data.unit != 'nm')
            # self.btn_f.toggled.connect(self.unitChanged)  # (lambda: self.unitChange(self.btn_f))
            layout1.addWidget(self.btn_f)
            self.show_sp_chbx = QCheckBox('Show')
            self.show_sp_chbx.setChecked(self.data.show_spectrum)
            self.show_sp_chbx.toggled.connect(self.showSpectrum)
            layout1.addWidget(self.show_sp_chbx)

            self.col_btn = QPushButton()
            self.col_btn.setMinimumWidth(25)
            self.col_btn.setMaximumWidth(25)
            # print('background-color: rgb(%i,%i,%i)' % self.data.color.getRgb()[:3])
            # self.col_btn.setStyleSheet('background-color: rgb(%i,%i,%i)' % self.data.color.getRgb()[:3])
            self.col_btn.setStyleSheet("QWidget { background-color: %s }"% self.data.color.name())
            self.col_btn.clicked.connect(self.changeColor)
            layout1.addWidget(self.col_btn)
            # implemented in main window
            # self.show_box = QCheckBox('Show')
            # self.show_box.setChecked(False)
            # self.show_box.stateChanged.connect(lambda:self.showSpectrum(self.show_box.checkState()))
            # layout1.addWidget(self.show_box)
            self.single_check_box = QCheckBox(text='Single')
            self.single_check_box.setChecked(self.data.single)
            self.single_check_box.toggled.connect(self.setSingle)
            layout1.addWidget(self.single_check_box)
            layout1.addStretch(1)

            main_layout.addLayout(layout1)

            self.name_line = QLabel(self.data.name)
            self.name_line.setFont(QFont("Times", 20, QFont.Bold))
            self.name_line.setStyleSheet("QWidget { color: %s }"% self.data.color.name())
            main_layout.addWidget(self.name_line)

            self.value = QLabel()
            self.value.setFont(QFont("Times",40))#,QFont.Bold
            self.setValueText()
            self.value.setStyleSheet("QWidget { color: %s }"% self.data.color.name())
            main_layout.addWidget(self.value)
            self.setLayout(main_layout)
            # print('Min Width ', self.width())

        def changeColor(self):
            col = QColorDialog.getColor()
            if col.isValid():
                self.data.color = col#.setStyleSheet("QWidget { background-color: %s }"% col.name())
            self.parent.data.save()

        def unitChanged(self):
            if self.btn_w.isChecked():
                self.data.unit = 'nm'
            else:
                self.data.unit = 'THz'
            self.parent.data.save()

        def setValueText(self):
            if self.data.wavelength == -3:
                self.value.setText('LOW')
                return
            elif self.data.wavelength == -4:
                self.value.setText('HIGH')
                return
            if self.data.unit == 'nm':
                self.value.setText("%.6f nm" % self.data.wavelength)
            else:
                self.value.setText("%.6f THz" % self.data.frequency)

        def showSpectrum(self, b):
            # print('Show spectrum', b)
            self.data.show_spectrum = b
            self.parent.data.save()
            # pass to parent

        def setSingle(self,b):
            self.data.single = b
            self.parent.updateSingleChannel(self.data.name, self.data.single)
            # self.parent.data.save()

class WMMain():
    channels = []
    N_SHOTS_MAX = 10
    N_SHOTS_MIN = 2
    EXCEPTABLE_WAVELENGTH_ERROR = 0.01 #nm
    current_index = 0
    active_channels_indexes = []
    single_index = 0
    mode = 'all'  # another possibility 'single' in case if I'll add this option
    n_channels = 2
    timer_interval = 500

    def __init__(self, arduino=None):
        self.wavemeter = wlm.WavelengthMeter()
        self.load()
        self.arduino = arduinoShutters.Arduino(port=self.config.get('port',''))
        self.arduino.n_lines = 1
        self.arduino.n_chars_in_string = 1000
        self.a = 1
        self.b = 0
        self.loadCalib()
        self.calibrate(force=True)
        # if arduino == None:
        #     # try to connect to arduino
        #     pass
        # self.arduino = arduino

    def loadCalib(self, filename='WM_calib.json'):
        filename = os.path.join(folder, filename)
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                self.calibData = data
        except Exception as e:
            self.calibData = {'Clock': 0, 'GreenX2': 0, 'Green': 0, 'time': 0}
        return

    def saveCalib(self, filename='WM_calib.json'):
        filename = os.path.join(folder, filename)
        with open(filename, 'w') as f:
            json.dump(self.calibData, f)
        return

    def getFreq(self, omega):
        return self.a*omega + self.b

    def calibrate(self, force=False):
        if datetime.datetime.now().timestamp() - self.calibData['time'] < 600 and not force:
            return -1
        if self.calibData['Clock'] == 0 or self.calibData['GreenX2'] == 0 or self.calibData['Green'] == 0:
            return 1
        if (self.calibData['Clock'] + self.calibData['GreenX2'] - 2*self.calibData['Green']) == 0:
            return 1
        a = (262954938.269213 + 2*426.7607) / (self.calibData['Clock'] + self.calibData['GreenX2'] - 2*self.calibData['Green']) / 1e6
        b = a * (self.calibData['GreenX2'] - 2*self.calibData['Green'])
        if abs(a-1) > 1e-7:
            # print('#WM check that all lasers are locked')
            return 2
        ans = -1
        if abs(b) > 100e-6:
            # print('#WM consider recalibrating the wavemeter')
            ans = 0
        self.a = a
        self.b = b
        print('#WM recalibrated successfully')
        if not force:
            self.calibData['time'] = datetime.datetime.now().timestamp()
            self.saveCalib()
        return ans

    def save(self):
        # print('Save')
        data_to_save = {}
        data_to_save['n_channels'] = self.n_channels
        data_to_save['timer_interval'] = self.timer_interval
        data_to_save['channels'] = []
        for channel in self.channels:
            d = {}
            # print(channel.__dict__)
            for attr in channel.__dict__:
                # if not callable(getattr(channel,attr)):
                if attr not in ['spectrum','save','color']:
                    d[attr] = getattr(channel,attr)
                if attr == 'color':
                    d[attr] = getattr(channel,attr).getRgb()[:3]
            data_to_save['channels'].append(d)
        # print(data_to_save)
        with open(os.path.join(folder,'WM_config.json'),'w') as f:
            json.dump(data_to_save,f)

    def load(self,file_name='WM_config.json'):
        file_name = os.path.join(folder,file_name)
        with open(file_name,'r') as f:
            data = json.load(f)
        self.n_channels = data['n_channels']
        self.config = data
        if 'timer_interval' in data:
            self.timer_interval = data['timer_interval']
        for chan in data['channels']:#getattr(data,'channels',[]):
            # print(chan)
            new_chan = WMChannel()
            for attr in chan:
                if attr == 'color':
                    setattr(new_chan,'color',QColor(*chan['color']))
                else:
                    setattr(new_chan,attr,chan[attr])
            self.channels.append(new_chan)
        # print(data['channels'])
        self.active_channels_indexes = [i for i in range(len(self.channels)) if self.channels[i].is_active]
        self.current_index = self.active_channels_indexes[-1]
        print(self.config)

    def addChannel(self, name, shutter_number,color=QColor(0,0,0)):
        new_channel = WMChannel(name, shutter_number,color=color)
        self.channels.append(new_channel)
        self.active_channels_indexes = [i for i in range(len(self.channels)) if self.channels[i].is_active]
        self.current_index = self.active_channels_indexes[-1]

    def delChannel(self, name):
        for channel in self.channels:
            if channel.name == name:
                self.channels.remove(channel)
                break
        self.active_channels_indexes = [i for i in range(len(self.channels)) if self.channels[i].is_active]
        self.current_index = self.active_channels_indexes[-1]
        # print('Delliting')
        # print(self.current_index)

    class WMWidget(QWidget):
        # handled = False # flag that value is written from wavemeter
        def __init__(self, parent=None, data=None, signals=None):
            self.parent = parent
            self.data = data
            self.signals = signals
            self.lastMessage = ''
            super().__init__(parent=self.parent)
            self.setWindowTitle('My WavelengthMeter')
            self.setWindowIcon(QIcon('icon.jpg'))
            self.plot_window1 = pg.PlotWidget(background='w')
            self.plot_window2 = pg.PlotWidget(background='w')
            self.read_data = []
            self.shotN = 0
            # self.plot_window.plot(range(10),range(10))

            main_layout = QVBoxLayout()

            menu_layout = QHBoxLayout()
            chan_btn = QPushButton('Channels')
            chan_menu = QMenu(chan_btn)
            chan_menu.aboutToShow.connect(self.updateChannelsMenu)
            chan_btn.setMenu(chan_menu)
            menu_layout.addWidget(chan_btn)

            n_channels_per_line = QSpinBox()
            n_channels_per_line.setMinimum(2)
            n_channels_per_line.setMaximum(10)
            n_channels_per_line.setValue(self.data.n_channels)
            n_channels_per_line.valueChanged.connect(self.nCannelsChanged)
            menu_layout.addWidget(n_channels_per_line)

            menu_layout.addWidget(QLabel('per line'))

            self.calibrateBox = QCheckBox("recalibrate")
            self.calibrateBox.setChecked(True)

            menu_layout.addStretch(1)

            menu_layout.addWidget(self.calibrateBox)

            timer_len = QSpinBox()
            timer_len.setMinimum(10)
            timer_len.setMaximum(10000)
            timer_len.setValue(self.data.timer_interval)
            timer_len.valueChanged.connect(self.temerIntervalChanged)
            menu_layout.addWidget(timer_len)

            menu_layout.addWidget(QLabel('msec'))
            # mode_group = QButtonGroup()
            # self.all_btn = QRadioButton('all')
            # self.all_btn.setChecked(self.data.mode=='all')
            # self.all_btn.toggled.connect(self.modeChanged)
            # mode_group.addButton(self.all_btn)
            # menu_layout.addWidget(self.all_btn)
            #
            # self.single_btn = QRadioButton('single')
            # self.single_btn.setChecked(self.data.mode != 'all')
            # self.single_btn.toggled.connect(self.modeChanged)
            # mode_group.addButton(self.single_btn)
            # menu_layout.addWidget(self.single_btn)
            #
            # single_menu_btn = QPushButton('Single ch.')
            # single_menu = QMenu(single_menu_btn)
            # single_menu.aboutToShow.connect(self.updateSingleMenu)
            # single_menu_btn.setMenu(single_menu)
            # menu_layout.addWidget(single_menu_btn)

            main_layout.addLayout(menu_layout)

            temp_layout = QHBoxLayout()


            plots_layout = QVBoxLayout()
            plots_layout.addWidget(self.plot_window1)
            plots_layout.addWidget(self.plot_window2)
            temp_layout.addLayout(plots_layout)

            self.arduinoWidget = self.data.arduino.Widget(parent=self, data=self.data.arduino)
            self.arduinoWidget.setMaximumWidth(250)
            temp_layout.addWidget(self.arduinoWidget)


            main_layout.addLayout(temp_layout)

            self.channels_layout = QGridLayout()
            self.drawChannels()

            main_layout.addLayout(self.channels_layout)
            self.setLayout(main_layout)

            self.window().setGeometry(1920, 1080, 1920, 1080)
            self.setWindowState(Qt.WindowMaximized)
            # print('WLM_GUI created')
            self.timer = QTimer(self)
            self.timer.setInterval(self.data.timer_interval)
            self.timer.timeout.connect(self.routine)
            self.timer.start()
            self.timer2 = QTimer(self)
            self.timer2.timeout.connect(self.checkWM)
            if self.signals:
                self.signals.arduinoReceived.connect(self.timer2.start)

        def save(self,dict_to_save):
            file_name = 'WM_config.json'
            file_name = os.path.join(folder, file_name)
            with open(file_name, 'r') as f:
                self.config = json.load(f)
            self.config.update(dict_to_save)
            print('new_config', self.config)
            with open(os.path.join(folder,'WM_config.json'), 'w') as f:
                json.dump(self.config, f)

        def temerIntervalChanged(self, new_val):
            self.data.timer_interval = new_val
            self.data.save()
            self.timer.stop()
            self.timer.setInterval(self.data.timer_interval)
            self.timer.start()

        def nCannelsChanged(self,new_val):
            self.data.n_channels = new_val
            self.data.save()

        def modeChanged(self):
            if self.sender().text() == 'all':
                self.single_btn.setChecked(not self.all_btn.isChecked())
            if self.sender().text() == 'single':
                self.all_btn.setChecked(not self.single_btn.isChecked())
            # print(self.sender().text(),self.sender().isChecked())
            self.data.mode = 'all' if self.all_btn.isChecked() else 'single'

        def updateSingleMenu(self):
            channels_menu = self.sender()
            channels_menu.clear()
            for channel in self.data.channels:
                # print(channel.name)
                act = channels_menu.addAction(channel.name)
                act.triggered.connect(self.updateSingleIndex)

        def updateSingleIndex(self):
            name = self.sender().text()
            # print('single ',name)
            for i, channel in enumerate(self.data.channels):
                if channel.name == name:
                    self.data.single_index = i
                    break
            # print('single index ', self.data.single_index)

        def updateSingleChannel(self,name,status):
            if not status:
                self.data.mode = 'all'
            else:
                self.data.mode = 'single'
                for i, channel in enumerate(self.data.channels):
                    if channel.name == name:
                        self.data.single_index = i
                    else:
                        channel.single = False
            self.data.save()

        def keyPressEvent(self, QKeyEvent):
            if QKeyEvent.key() == Qt.Key_F5 and self.shotN == 0 and self.signals:
                self.signals.shutterChange.emit(self.lastMessage)
            return

        def routine(self):
            # print('here')
            # global cicle_counter
            # cicle_counter += 1
            # print(self.data.arduino.connected)
            if not self.data.arduino.connected:
                return False
            self.timer.stop()
            # print("Cicle #",cicle_counter)
            # print(self.data.current_index)
            # print(self.data.active_channels_indexes)
            if self.data.mode == 'all':
                self.data.current_index = self.data.active_channels_indexes[
                (self.data.active_channels_indexes.index(self.data.current_index) + 1) % len(
                    self.data.active_channels_indexes)]
            else:
                self.data.current_index = self.data.single_index
            # print('current index ',self.data.current_index)
            arr_to_arduino = [(self.data.channels[i].shutter_number,int(i==self.data.current_index)) for i in range(len(self.data.channels))]
            # resp = self.data.arduino.setWMShutters(arr_to_arduino)
            message = 'WMShutters'
            for chan, state in arr_to_arduino:
                message += ' %i %i' % (chan, state)
            message += '!'
            # print(message)
            try:
                status, readout = self.data.arduino.write_read_com(message.encode())
            except Exception as e:
                print(e)
            # print(message, status, readout)
            # check resp
            time_per_shot = self.data.wavemeter.exposure
            # print('Time per shot ',time_per_shot)
            self.read_data = []
            read_success = False
            self.shotN = 0
            self.timer2.setInterval(time_per_shot)
            self.lastMessage = message
            self.timer2.start()
            # self.signals.shutterChange.emit(message)
            # self.cycleTimer.start()

        def checkWM(self):
            # print('checkWM')
            self.shotN += 1
            i = self.shotN
            try:
                wm_data = {'wavelength': self.data.wavemeter.wavelength,
                           'frequency': self.data.wavemeter.frequency,
                           'amplitudes': self.data.wavemeter.amplitudes,
                           'spectrum': self.data.wavemeter.spectrum,
                           'exposure': self.data.wavemeter.exposure
                           }
            except Exception as e:
                print(e)
                raise e
            # print(wm_data['wavelength'])
            self.read_data.append(wm_data)
            # print(wm_data['wavelength'])
            if (i > self.data.N_SHOTS_MIN and
                abs(wm_data['wavelength'] - self.read_data[-2]['wavelength']) <= self.data.EXCEPTABLE_WAVELENGTH_ERROR and
                abs(wm_data['wavelength'] - self.read_data[-2]['wavelength']) <= self.data.EXCEPTABLE_WAVELENGTH_ERROR and
                wm_data["exposure"] * i > 100 or
                i > self.data.N_SHOTS_MAX):
                self.timer2.stop()
                # print('Steady state reached; i=', i)
                # print(wm_data['wavelength'])
                read_success = True
                channel = self.data.channels[self.data.current_index]
                channel.wavelength = wm_data['wavelength']
                channel.frequency = wm_data['frequency']
                with open('freq_data_10_10.txt','a') as f:
                    f.write('%.10f %i %.10f\n' % (time.time(),self.data.current_index,channel.frequency))
                channel.amplitudes = wm_data['amplitudes']
                channel.spectrum = wm_data['spectrum']

                # remember for calibration
                self.data.calibData[channel.name] = channel.frequency
                if self.calibrateBox.isChecked():
                    colour = self.data.calibrate()
                    if colour > 0:
                        self.calibrateBox.setStyleSheet("color: red")
                    if colour < 0:
                        self.calibrateBox.setStyleSheet("color: black")
                    if colour == 0:
                        self.calibrateBox.setStyleSheet("color: green")
                    channel.frequency = self.data.getFreq(channel.frequency)
                # send to server data
                msg = 'WM %s %.2f %.7f\n'%(channel.name,datetime.datetime.now().timestamp(),channel.frequency)
                sock.sendto(bytes(msg, "utf-8"), (HOST, PORT))

                # self.signals.wvlChanged.emit(' '.join([str(channel.frequency) for channel in self.data.channels]))
                self.drawChannels()
                self.drawSpecta()
                self.timer.start()

        def drawSpecta(self):
            self.plot_window1.clear()
            self.plot_window2.clear()
            active_channels = [channel for channel in self.data.channels if (channel.is_active  and channel.show_spectrum)]
            for i, channel in enumerate(active_channels):
                spectr = channel.spectrum[0]
                # for spectr in channel.spectrum[:1]:
                if len(spectr):
                    # print(len(spectr))
                    self.plot_window1.plot(np.arange(1024),spectr[:1024],pen=pg.mkPen(color=channel.color,width=2))
                spectr = channel.spectrum[1]
                # for spectr in channel.spectrum[:1]:
                if len(spectr):
                    # print(len(spectr))
                    self.plot_window2.plot(np.arange(1024), spectr[:1024], pen=pg.mkPen(color=channel.color,width=6))

        def drawChannels(self):
            # cleen up previous grid
            while self.channels_layout.count():
                item = self.channels_layout.takeAt(0)
                item.widget().deleteLater()
            active_channels = [channel for channel in self.data.channels if channel.is_active]
            self.data.active_channels_indexes = [i for i,channel in enumerate(self.data.channels) if channel.is_active]
            # print(active_channels)
            # print('Frame ',self.frameGeometry().width())
            # print('widget', active_channels[0].width())
            for i, channel in enumerate(active_channels):
                # print(i % 2, i // 2)
                chan_widget = channel.WMChannelGUI(parent=self, data=channel)
                # print('Widget ', chan_widget.frameGeometry().width())
                self.channels_layout.addWidget(chan_widget, i // self.data.n_channels, i % self.data.n_channels)

        def updateChannelsMenu(self):
            # print('updateAllScanParams')
            # print(self.data.globals)
            channels_menu = self.sender()
            channels_menu.clear()
            for channel in self.data.channels:
                # print(channel.name)
                m = channels_menu.addMenu(channel.name)
                text = 'hide' if channel.is_active else 'show'
                act = m.addAction(text)
                # act.triggered.connect(lambda:self.showHideChannel(channel))
                act.triggered.connect(self.showHideChannel)
                act = m.addAction('del')
                # act.triggered.connect(lambda:self.delChannel(channel))
                act.triggered.connect(self.delChannel)
            new_chan_act = channels_menu.addAction('new')
            new_chan_act.triggered.connect(lambda: self.NewChannelWidget(parent=self))

        def showHideChannel(self, channel):
            # channel.is_active = not channel.is_active
            name = self.sender().parent().title()
            for channel in self.data.channels:
                if channel.name == name:
                    channel.is_active = not channel.is_active
                    break
            self.drawChannels()
            self.data.save()

        def delChannel(self):
            # print(self.sender().parent().title())
            name = self.sender().parent().title()
            self.data.delChannel(name)
            self.drawChannels()
            self.data.save()

        def addNewChannel(self, caller):
            if caller.exit_status:
                # a = self.NewChannelWidget(parent=self)
                new_name = caller.name.text()
                new_shutter_channel = caller.shutter_channel.value()
                self.data.addChannel(name=new_name, shutter_number=new_shutter_channel)
                # self.data.channels.append(new_channel)
                # print(new_name, new_shutter_channel)
                self.drawChannels()
            del caller
            self.data.save()

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

def connectArduino(response=''):
    # ports = list(serial.tools.list_ports.comports())
    for port in serial.tools.list_ports.comports():
        if port.description.startswith("USB-SERIAL CH340"):
            try:
                arduino = Serial(port.device, baudrate=57600, timeout=1)
            except SerialException as e:
                error = QErrorMessage()
                error.showMessage("Can't open port %s !" % port.device + e.__str__())
                error.exec_()
                return -1
            # here one can add checking response on command arduino.write(b'*IDN?'), know is somewhy doesn't work
            return arduino
    error = QErrorMessage()
    error.showMessage("Arduino is not connected!")
    error.exec_()
    return -1

if __name__ == '__main__':
    import sys
    from serial import Serial
    from serial import SerialException
    import serial.tools.list_ports
    folder = ''
    app = QApplication(sys.argv)
    # device = connectArduino()
    # if device != -1:
        # device = Serial('COM4',baudrate=57600,timeout=1)
    print('Here')
    # arduino = arduinoShutters.Arduino()
    print('Here')
    aw = WMMain()
    # aw.load()
    # aw.addChannel(name='Green', shutter_number=2, color=QColor(0,255,0))
    # aw.addChannel(name='Clock', shutter_number=1, color=QColor(255,170,0))
    # aw.addChannel(name='red', shutter_number=3)
    mainWindow = aw.WMWidget(data=aw)
    mainWindow.show()
    sys.exit(app.exec_())
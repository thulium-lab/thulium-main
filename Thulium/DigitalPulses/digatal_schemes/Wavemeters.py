from PyQt5.QtCore import (QLineF, QPointF, QRectF, Qt, QTimer)
from PyQt5.QtGui import (QBrush, QColor, QPainter)
from PyQt5.QtWidgets import (QApplication, QGraphicsView, QGraphicsScene, QGraphicsItem, QMenu, QAction, QScrollArea,QFrame,
                             QGridLayout, QVBoxLayout, QHBoxLayout, QSizePolicy,QMainWindow, QDialog,QTextEdit,
                             QLabel, QLineEdit, QPushButton, QWidget, QComboBox,QRadioButton, QSpinBox, QCheckBox, QTabWidget, QFileDialog,QMessageBox, QDoubleSpinBox)
# import pyqtgraph as pg
import sys

class Wavemeters():
    update_interval = 200 # ms
    always_on = False
    def __init__(self,channels = []):
        # connect to arduino
        # arduino - just a serial port
        # connect to wavemeter
        # wavemeter - is also a serial port
        self.list_of_channels = []
        self.current_index = 0
        if channels:
            self.load(channels)
        else:
            self.list_of_channels = [WavemeterChannel({'name':'1'}),WavemeterChannel({'name':'2'}),WavemeterChannel({'name':'3'})]
        self.gui = self.WavemeterWidget(data=self)

    def load(self,channels):
        print('wavemeters-load')
        for channel in channels:
            self.list_of_channels.append(WavemeterChannel(param_dict=channel))

    def addChannel(self):
        print('wavemeters-addChannel')

    def delChannel(self):
        print('wavemeters-delChannel')

    def readWavelength(self):
        print('wavemeters-readWavelength')
        # write querry and read an answer from wavemeter
        #self.wavemeter.write('')

        # parse read data to be of the form needed in WavemeterChannel.update
        data = None
        self.list_of_channels[self.current_index].update(data)

    def channelAlwaysOnChanged(self,channel_name, state):
        print('Wavemeters-channelAlwaysOnChanged')
        if not state:
            self.always_on = False
            return
        for i, chan in enumerate(self.list_of_channels):
            if chan.name == channel_name:
                print(i, 'True')
                self.current_index = i
            else:
                print(i, 'False')
                chan.always_on = False
        self.gui.drawGrid(new=False)

    class WavemeterWidget(QWidget):
        wms_in_row = 2
        def __init__(self,parent=None,data=None):
            self.parent = parent
            self.data = data
            super().__init__(parent=self.parent)

            self.initUI()
            self.show()
            self.timer = QTimer(self)
            self.timer.setInterval(self.data.update_interval)
            self.timer.timeout.connect(self.routine)
            self.timer.start(10000)


        def initUI(self):
            self.grid_layout = QGridLayout()
            self.drawGrid(new=True)
            self.setLayout(self.grid_layout)

        def routine(self):
            print('wavemeterWidget-routine')
            self.data.readWavelength()

        def drawGrid(self, new=True):
            print('drawGrid', new)
            if new:
                while self.grid_layout.count():
                    item = self.grid_layout.takeAt(0)
                    item.widget().deleteLater()
                for i, chan in enumerate(self.data.list_of_channels):
                    self.grid_layout.addWidget(chan.WavemeterChannelWidget(data=chan, parent=self),
                                               i // self.wms_in_row, i % self.wms_in_row)

            else:
                for i in range(self.grid_layout.count()):
                    chan_widget = self.grid_layout.itemAt(i).widget()# .takeAt(i)

                    print('repaint',chan_widget.data.always_on)
                    chan_widget.redraw()


class WavemeterChannel():
    name = 'new'
    shutter = None
    frequency = 100.0 # in THz
    wavelength = 0
    always_on = False
    measured_waveforms = []
    amplitude = 0
    database = None

    def __init__(self, param_dict = {}):
        if param_dict:
            for key, val in param_dict.items():
                self.__dict__[key] = val

    def update(self, data):
        """data should be a dictionary, which is constructed based on reply from wavemeter. it shoul be:
        {date: date,
         frequency: f # or wavelength: lambda,
         amplitude: a,
         measured_waveforms = [[],[]] # or smth like that}
        """
        print('WavemeterChannel-update')

        # self.wavelength = data['wavelength']
        # self.amplitude = data['amplitude']
        # self.measured_waveforms  =data['measured_waveforms']
        # if not self.database:
        #     self.writeToDB(date=data['date'])

    def writeToDB(self,date):
        # write to mongodb
        print('wavelengthChannel-writeToDB')

    class WavemeterChannelWidget(QWidget):
        def __init__(self,parent=None, data=None):
            self.parent = parent
            self.data = data
            # self.all_widgets = []
            super().__init__()
            self.initUI()
            self.show()

        def initUI(self):
            main_layout = QVBoxLayout()

            hor1 = QHBoxLayout()
            self.name_line = QLineEdit(self.data.name)
            self.name_line.returnPressed.connect(self.nameChanged)
            # self.all_widgets.append(self.name_line)
            hor1.addWidget(self.name_line)

            hor1.addWidget(QLabel('On'))
            self.on_check = QCheckBox()
            self.on_check.setChecked(self.data.always_on)
            self.on_check.stateChanged.connect(self.alwaysOnChanged)
            # self.all_widgets.append(on_check)
            hor1.addWidget(self.on_check)

            main_layout.addLayout(hor1)

            hor2 = QHBoxLayout()
            self.wavelength = QLabel()
            self.wavelength.setText("%.3f nm (air)" % (self.data.wavelength))
            # self.all_widgets.append(wavelength)
            hor2.addWidget(self.wavelength)

            self.freq = QLabel("%.3f THz" % (self.data.frequency))
            # self.all_widgets.append(freq)
            hor2.addWidget(self.freq)

            main_layout.addLayout(hor2)

            self.setLayout(main_layout)

        def nameChanged(self):
            print('wavelengthChannel-nameChanged')
            self.data.name = self.sender().text()

        def alwaysOnChanged(self,new_val):
            print('wavelengthChannel-alwaysOnChanged')
            self.data.always_on = bool(new_val)
            if self.parent:
                self.parent.data.channelAlwaysOnChanged(self.data.name, bool(new_val))

        def redraw(self):
            print('WavemeterChannelWidget-redraw')
            self.name_line.setText(self.data.name)
            self.on_check.setChecked(self.data.always_on)
            self.wavelength.setText("%.3f nm (air)" % (self.data.wavelength))
            self.freq.setText("%.3f THz" % (self.data.frequency))
            self.repaint()
if __name__ == '__main__':
    app = QApplication(sys.argv)
    wm = Wavemeters()
    # gu = wm.WavemeterWidget(data=wm)
    sys.exit(app.exec_())
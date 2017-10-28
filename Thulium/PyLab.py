import sys, ctypes, time, functools

from PyQt5.QtCore import (Qt, QObject, pyqtSignal)
from PyQt5.QtGui import (QIcon)
from PyQt5.QtWidgets import (QApplication, QMdiSubWindow, QDesktopWidget, QSplitter, QMainWindow, QTextEdit, QAction,
                             QMessageBox)

from DigitalPulses.Pulses import PulseScheme, PulseGroup, IndividualPulse, AnalogPulse
from DigitalPulses.scanner import Scanner
from DigitalPulses.PlotPulse import PlotPulse
from Camera.bgnd_runner import Bgnd_Thread
from DigitalPulses.display_widget import DisplayWidget
from Devices.arduinoShutters import Arduino
from Devices.WavelengthMeter import WMeter
from Devices.DDS import DDSWidget
from Devices.SRSgeneratorSG382 import SRSGenerator
from Devices.GWInstek import GPDwidget

from server import PyServer

vertical_splitting = 0.7
horizontal_splitting = 0.6

myAppID = u'LPI.MainScanWindow' # arbitrary string
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myAppID)


class OurSignals(QObject):
    # here all possible signals which can be used in our program
    anyPulseChange = pyqtSignal()  # to handle any change in pulse scheme - probably for displaying pulses
    newImageRead = pyqtSignal()     # emits when new image is read from image_folder
    newImage2Read = pyqtSignal()
    scanCycleFinished = pyqtSignal(int)    # emits by DAQ whenever a cycle is finished
    shutterChange = pyqtSignal(str)
    arduinoReceived = pyqtSignal() # WMeter can start averaging
    wvlChanged = pyqtSignal(str) # server can update wvl
    imageRendered = pyqtSignal() # server can update img


class MainWindow(QMainWindow):
    count = 0
    signals = OurSignals()
    globals = {}
    widgets = {}
    all_updates_methods = {}
    image_folder = r'Z:\Camera' # RamDisk http://www.radeonramdisk.com/software_downloads.php
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setWindowTitle('Pulses')
        self.setWindowIcon(QIcon('pulse.ico'))

        self.globals['image'] = None
        self.globals['image_updated'] = False
        self.globals['image_stack']=[]

        # self.arduino = connectArduino()
        self.arduino = Arduino(self.signals)
        # self.arduino.preCheck()
        # print('Arduino port', self.arduino.port)
        # res = self.arduino.connect()
        # print('Arduino connection',res)
        self.bgnd_image_handler = Bgnd_Thread(globals=self.globals, signals=self.signals,
                                              image_folder=self.image_folder)
        self.bgnd_image_handler.start()

        self.default_widgets_names=['Scanner','PulseScheme']
        self.screenSize = QDesktopWidget().availableGeometry()

        self.widgets['Scanner'] = Scanner(parent=self, globals=self.globals,
                                          all_updates_methods=self.all_updates_methods, signals=self.signals)
        self.widgets['Scanner'].windowed = 1
        # self.slots_to_bound['cycleFinished'].connect(self.widgets['Scanner'].cycleFinished)
        # self.triggerCycle.connect(self.widgets['Scanner'].cycleFinished)
        self.widgets['DDS'] = DDSWidget(parent=self, globals=self.globals, signals=self.signals)
        self.widgets['DDS'].windowed = 1

        self.widgets['CamView'] = DisplayWidget(parent=self, globals=self.globals, signals=self.signals)
        self.widgets['CamView'].windowed = 2
        self.widgets['Arduino'] = self.arduino.Widget(parent=self, data=self.arduino)
        self.widgets['Arduino'].windowed = 1
        self.widgets['Arduino'].connectBtnPressed()
        self.widgets['Pulses'] = PulseScheme(parent=self, globals=self.globals, signals=self.signals)
        self.widgets['Pulses'].windowed = 0
        self.widgets['PulsePlot'] = PlotPulse(parent=self, globals=self.globals, signals=self.signals)
        self.widgets['PulsePlot'].windowed = 0
        #self.widgets['ClockGenerator'] = SRSGenerator(parent=self,globals=self.globals)
        #self.widgets['ClockGenerator'].windowed = 1

        # comment these if you get problems
        self.widgets['GPD 3303'] = GPDwidget(parent=self, globals=self.globals)
        self.widgets['GPD 3303'].windowed = 1

        # self.wm = WMeter.WMMain(arduino=self.arduino)
        # self.wm.load()
        # self.widgets['WavelengthMeter'] = self.wm.WMWidget(data=self.wm, signals=self.signals)
        # self.widgets['WavelengthMeter'].windowed = 2

        self.all_updates_methods['Pulses'] = self.widgets['Pulses'].getUpdateMethod()
        self.all_updates_methods['DDS'] = self.widgets['DDS'].getUpdateMethod()
        #self.all_updates_methods['ClockGenerator'] = self.widgets['ClockGenerator'].getUpdateMethod()

        # and this
        self.all_updates_methods['GPD 3303'] = self.widgets['GPD 3303'].getUpdateMethod()

        self.server = PyServer(self, self.signals, self.globals)

        self.initUI()

    def initUI(self):
        bar = self.menuBar()
        openMenu = bar.addMenu('&Open')

        splitter = QSplitter(Qt.Vertical)
        # splitter.setSizes([50,50])
        self.setCentralWidget(splitter)

        for widget in self.widgets:
            if self.widgets[widget].windowed:
                if self.widgets[widget].windowed > 1:
                    self.widgets[widget].show()
                action = QAction("&" + widget, self)
                action.triggered.connect(functools.partial(self.focus, widget))# self.widgets[widget].show)
                openMenu.addAction(action)
            else:
                pass # splitter.addWidget(self.widgets[widget]) # might be wrong order
        splitter.addWidget(self.widgets['Pulses']) # explicitly state the order
        splitter.addWidget(self.widgets['PulsePlot'])

        # self.setFixedWidth(self.screenSize.width())
        # self.widgets['WavelengthMeter'].show()
        # self.widgets['CamView'].showFullScreen()

        print('self_globals',self.globals)
        self.server.start()

    def focus(self, widget):
        window = self.widgets[widget]
        window.show()
        window.setWindowState(window.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        window.activateWindow()

    def addSubProgramm(self):
        pass

    def windowaction(self, q):
        print("triggered")

        if q.text() == "New":
            MainWindow.count = MainWindow.count+1
            sub = QMdiSubWindow()
            sub.setWidget(QTextEdit())
            sub.setWindowTitle("subwindow"+str(MainWindow.count))
            self.mdi.addSubWindow(sub)
            sub.show()

        if q.text() == "cascade":
          self.mdi.cascadeSubWindows()

        if q.text() == "Tiled":
          self.mdi.tileSubWindows()

    def closeEvent(self, event, *args, **kwargs):
        message = "This action will close the entire program. Are you sure?"
        reply = QMessageBox.question(self, 'Warning', message, QMessageBox.Yes, QMessageBox.Cancel)
        if reply != QMessageBox.Yes:
            return event.ignore()
        self.bgnd_image_handler.stop()
        for widget in self.widgets:
            if self.widgets[widget].window:
                self.widgets[widget].hide()
        event.accept() # should be same as below
        # super(MainWindow, self).closeEvent(event, *args, **kwargs)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('pulse.ico'))
    ex = MainWindow()
    ex.show()
    sys.exit(app.exec_())

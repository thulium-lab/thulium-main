import sys, ctypes, time, functools,threading, json, datetime, requests
import socket
import pickle
import socketserver

from PyQt5.QtCore import (Qt, QObject, pyqtSignal, QSettings,)
from PyQt5.QtGui import (QIcon,)
from PyQt5.QtWidgets import (QApplication, QMdiSubWindow, QDesktopWidget, QSplitter, QMainWindow, QTextEdit, QAction,
                             QMessageBox,QDockWidget,QScrollArea,)

# from DigitalPulses.Pulses import PulseScheme, PulseGroup, IndividualPulse, AnalogPulse
# from DigitalPulses.scanner import Scanner
# from DigitalPulses.PlotPulse import PlotPulse
# from Camera.bgnd_runner import Bgnd_Thread
# from DigitalPulses.display_widget import DisplayWidget
# from Devices.arduinoShutters import Arduino
# from Devices.WavelengthMeter import WMeter
# from Devices.DDS import DDSWidget
# from Devices.SRSgeneratorSG382 import SRSGenerator
# from Devices.GWInstek import GPDwidget
#
#
# from server import PyServer
from PulseScheme import (PulseScheme, PlotPulse)
from Shutters import ShutterWidget
from Current import CurrentWidget
from Scanner_classic import ScannerWidget
from DisplayWindowNew import CameraWidget, DisplayWidget
from Digital import DigitalOutoutWidget
from DDS import DDSWidget
from AnalogIN import AnalogInWidget
from SRSgeneratorSG382 import SRSGenerator
from StepperMotors import  StepperWidget
from Scanner_lock import ScannerLockWidget


vertical_splitting = 0.7
horizontal_splitting = 0.6

myAppID = u'LPI.MainScanWindow' # arbitrary string
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myAppID)

CONFIG_FILE = 'config.json'

# HOST, PORT = "localhost", 9998
HOST,PORT = "192.168.1.227", 9998
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(.1)

class MyTCPHandler(socketserver.StreamRequestHandler):
    def handle(self):
        msg = self.rfile.readline().strip().decode('utf-8')
        try:
            task, data = msg.split(' ', maxsplit=1)
        except ValueError as e:
            task = msg
            data = ''

        if task != "analog_input":
            print("not DAQin should connect via UDP, not TCP")
            return

        print("received from DAQin",len(msg), time.perf_counter())
        try:
            data = json.loads(data)
        except json.JSONDecodeError as e:
            print(e)
            print(data[0:10])
            data = {}
            return
        print("analog_input. Read channels", data.keys())
        main_window_widget.globals["analog_input_data"] = data
        main_window_widget.signals.analogInputRecieved.emit('')

class MyUDPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        msg = self.request[0].strip().decode('utf-8')
        sender_socket = self.request[1]
        try:
            task, data = msg.split(' ', maxsplit=1)
        except ValueError as e:
            task = msg
            data = ''
        # try:
        #     data = json.loads(data)
        # except json.JSONDecodeError as e:
        #     data = {}
        # print('task:', task, ",data:", data)
        if task == "cicle_finished": # end of cicle
            print("Cycle %s finished at"%(data), time.perf_counter(),datetime.datetime.now())#datetime.datetime.now().time()
            main_window_widget.signals.singleScanFinished.emit(time.perf_counter())
            try:
                requests.get("http://192.168.1.59:2900/trigger", timeout=0.02)
            except Exception as e:
                print("failed to trigger SRS freq change")
        elif task == "analog_input": # reading of analog inputs:
            print("DAQin should connect via TCP")
            print("analog_input. Read channels", data.keys())
            main_window_widget.globals["analog_input_data"] = data
            main_window_widget.signals.analogInputRecieved.emit()
        elif task == "arduino_readings":
            main_window_widget.signals.readingsFromArduino.emit(data)
        elif task == "AvailableCOMs":
            main_window_widget.signals.serverComPortsUpdate.emit(data)
        else:
            print("Message from Server",task,data)


class OurSignals(QObject):
    # here all possible signals which can be used in our program
    anyPulseChange = pyqtSignal()  # to handle any change in pulse scheme - probably for displaying pulses
    newImageRead = pyqtSignal()     # emits when new image is read from image_folder
    newImage2Read = pyqtSignal()
    scanCycleFinished = pyqtSignal(int,float)    # emits by DAQ whenever a cycle is finished
    shutterChange = pyqtSignal(str)
    arduinoReceived = pyqtSignal() # WMeter can start averaging
    wvlChanged = pyqtSignal(str) # server can update wvl
    imageRendered = pyqtSignal() # server can update img
    scanStarted = pyqtSignal()
    imageProcessed = pyqtSignal(str)
    singleScanFinished = pyqtSignal(float)

    shutterChannelChangedSignal = pyqtSignal(str)  #not used now - all shutter processing in Shutters widget
    pulsesChanged = pyqtSignal(float,float)
    updateFromScanner = pyqtSignal()
    sendMessageToDeviceServer = pyqtSignal(str)
    analogInputRecieved = pyqtSignal(str)
    updateDigitalPlot = pyqtSignal(float,float)
    updateMeasurementPlot = pyqtSignal(int,int,bool)
    readingsFromArduino = pyqtSignal(str)
    serverComPortsUpdate = pyqtSignal(str)
    scanFinished = pyqtSignal()

class MainWindow(QMainWindow):
    count = 0
    signals = OurSignals()
    globals = {}
    widgets = {}
    all_updates_methods = {}
    image_folder = r'Z:\Camera' # RamDisk http://www.radeonramdisk.com/software_downloads.php
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setWindowTitle('Main')
        self.signals = OurSignals()
        self.globals['host_port'] = (HOST,PORT)
        # self.setWindowIcon(QIcon('pulse.ico'))

        self.screenSize = QDesktopWidget().availableGeometry()

        self.widgets['Pulses'] = PulseScheme(parent=self, globals=self.globals,
                                             signals=self.signals,config_file=CONFIG_FILE)
        self.widgets['Pulses'].windowed = 2
        self.widgets['Current'] = CurrentWidget(parent=self, globals=self.globals,
                                                signals=self.signals, config_file=CONFIG_FILE)
        self.widgets['Shutters'] = ShutterWidget(parent = self, globals=self.globals,
                                                 signals=self.signals,config_file=CONFIG_FILE)

        self.widgets['Scanner'] = ScannerWidget(parent=self, globals=self.globals,
                                                signals=self.signals,config_file=CONFIG_FILE)
        self.widgets['ScannerLock'] = ScannerLockWidget(parent=self, globals=self.globals,
                                                signals=self.signals, config_file=CONFIG_FILE)
        self.widgets['DDS'] = DDSWidget(parent=self, globals=self.globals,
                                        signals=self.signals,config_file=CONFIG_FILE)
        self.widgets['PulsePlot'] = PlotPulse(parent=self, globals=self.globals, signals=self.signals)
        self.widgets['PulsePlot'].windowed = 0

        # self.widgets["DisplayWidget"] = CameraWidget(parent=self, globals=self.globals, signals=self.signals,image_folder=r"\\ETHEREAL\Camera")
        self.widgets["DisplayWidget"] = DisplayWidget(parent=self, globals=self.globals, signals=self.signals,
                                                      config_file=CONFIG_FILE)
        self.widgets["DisplayWidget"].windowed = 2
        self.widgets["DisplayWidget"].show()

        self.widgets["DigitalOutput"] = DigitalOutoutWidget(parent=self, globals=self.globals, signals=self.signals,
                                                      config_file=CONFIG_FILE)

        self.widgets["AnalogIn"] = AnalogInWidget(parent=self, globals=self.globals, signals=self.signals,
                                                      config_file=CONFIG_FILE)
        self.widgets["SRS_clock"] = SRSGenerator(parent=self, globals=self.globals, signals=self.signals,
                                                      config_file=CONFIG_FILE)
        self.widgets["Steppers"] = StepperWidget(parent=self, globals=self.globals, signals=self.signals,
                                                 config_file=CONFIG_FILE)
        # self.widgets['ClockGenerator'] = SRSGenerator(parent=self,globals=self.globals)
        # self.widgets['ClockGenerator'].windowed = 1

        # # comment these if you get problems
        # self.widgets['GPD 3303'] = GPDwidget(parent=self, globals=self.globals, signals=self.signals)
        # self.widgets['GPD 3303'].windowed = 1

        # self.server = PyServer(self, self.signals, self.globals)
        self.widgets['Pulses'].constructPulseSequence()
        self.initUI()

    def initUI(self):
        # bar = self.menuBar()
        # openMenu = bar.addMenu('&Open')
        self.setCentralWidget(self.widgets['Pulses'])
        dock01 = QDockWidget('Scanner', self)
        dock01.setWidget(self.widgets['Scanner'])
        dock02 = QDockWidget('PulsePlot', self)
        dock02.setWidget(self.widgets['PulsePlot'])
        dock03 = QDockWidget('ScannerLock', self)
        dock03.setWidget(self.widgets['ScannerLock'])
        self.addDockWidget(Qt.RightDockWidgetArea, dock01)
        self.addDockWidget(Qt.RightDockWidgetArea, dock02)
        self.addDockWidget(Qt.RightDockWidgetArea, dock03)
        self.tabifyDockWidget(dock02, dock03)
        self.tabifyDockWidget(dock02, dock01)
        dock11 = QDockWidget('Shutters', self)
        dock11.setWidget(self.widgets['Shutters'])
        dock12 = QDockWidget('Current', self)
        dock12.setWidget(self.widgets['Current'])
        dock13 = QDockWidget('DDS', self)
        dock13.setWidget(self.widgets['DDS'])
        dock14 = QDockWidget('AnalogIn', self)
        dock14.setWidget(self.widgets['AnalogIn'])
        dock15 = QDockWidget("Steppers",self)
        dock15.setWidget(self.widgets["Steppers"])
        self.addDockWidget(Qt.BottomDockWidgetArea, dock11)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock12)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock13)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock14)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock15)
        self.tabifyDockWidget(dock12, dock11)
        self.tabifyDockWidget(dock12, dock13)
        self.tabifyDockWidget(dock13, dock14)
        self.tabifyDockWidget(dock14, dock15)
        dock20 = QDockWidget("SRS_clock",self)
        dock20.setWidget(self.widgets["SRS_clock"])
        self.addDockWidget(Qt.BottomDockWidgetArea,dock20)

        # dock13 = QDockWidget('DDS', self)
        # dock13.setWidget(self.widgets['DDS'])
        # self.addDockWidget(Qt.BottomDockWidgetArea, dock13)
        # self.tabifyDockWidget(dock11, dock13)  # the order is super important

        # dock21 = QDockWidget('DDS',self)
        # dock21.setWidget(self.widgets['DDS'])
        # self.addDockWidget(Qt.BottomDockWidgetArea,dock21)
        # dock1 = QDockWidget('PulsePlot', self)
        # dock1.setWidget(self.widgets['PulsePlot'])
        # dock2 = QDockWidget('scan', self)
        # dock2.setWidget(self.widgets['Scanner'])
        # self.addDockWidget(Qt.RightDockWidgetArea, dock2)
        # self.addDockWidget(Qt.RightDockWidgetArea, dock1)
        # self.tabifyDockWidget(dock2, dock1)
        # # w = QScrollArea()
        # # w.setWidget(self.widgets['DDS'])
        # # w.setMinimumHeight(200)
        # dock3 = QDockWidget('dds', self)
        # dock3.setWidget(self.widgets['DDS'])
        # self.addDockWidget(Qt.BottomDockWidgetArea, dock3)
        # dock4 = QDockWidget('ClockGenerator', self)
        # dock4.setWidget(self.widgets['ClockGenerator'])
        # self.addDockWidget(Qt.BottomDockWidgetArea, dock4)
        #
        # dock5 = QDockWidget('GWInstek', self)
        # dock5.setWidget(self.widgets['GPD 3303'])
        # self.addDockWidget(Qt.BottomDockWidgetArea, dock5)
        #
        # self.tabifyDockWidget(dock5,dock4)
        # self.setWindowState(Qt.WindowMaximized)
        # # self.setWindowState(Qt.WindowFullScreen)
        # for widget in self.widgets:
        #     if widget in ['Pulses','PulsePlot','Scanner','DDS','ClockGenerator','GPD 3303']:
        #         continue
        #     if self.widgets[widget].windowed:
        #         if self.widgets[widget].windowed > 1:
        #             self.widgets[widget].show()
        #         action = QAction("&" + widget, self)
        #         action.triggered.connect(functools.partial(self.focus, widget))# self.widgets[widget].show)
        #         openMenu.addAction(action)
        #     else:
        #         pass # splitter.addWidget(self.widgets[widget]) # might be wrong order
        # splitter.addWidget(self.widgets['Pulses']) # explicitly state the order
        # splitter.addWidget(self.widgets['PulsePlot'])

        # self.setFixedWidth(self.screenSize.width())
        # self.widgets['WavelengthMeter'].show()
        # self.widgets['CamView'].showFullScreen()

        # print('-MAIN - self_globals',self.globals)
        # self.server.start()
        print("PyLabDock loaded")

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
        self.saveState()
        sock.sendto(bytes("Finished", "utf-8"), self.globals["host_port"])
        # self.bgnd_image_handler.stop()
        for widget in self.widgets:
            if self.widgets[widget].window:
                self.widgets[widget].hide()
        event.accept() # should be same as below
        # super(MainWindow, self).closeEvent(event, *args, **kwargs)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('pulse.ico'))
    main_window_widget = MainWindow()
    main_window_widget.show()
    server = socketserver.UDPServer(("192.168.1.15", 9997), MyUDPHandler)
    server2 = socketserver.TCPServer(("192.168.1.15", 9996), MyTCPHandler)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread2 = threading.Thread(target=server2.serve_forever)
    server_thread.daemon = True
    server_thread2.daemon = True
    server_thread.start()
    server_thread2.start()
    print("UDP started at HOST, PORT", "192.168.1.15", 9997)
    print("TCP started at HOST, PORT", "192.168.1.15", 9996)
    # server.serve_forever()
    sys.exit(app.exec_())

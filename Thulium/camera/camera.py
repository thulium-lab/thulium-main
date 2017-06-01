import os, sys
import numpy as np
import pickle
from ctypes import *

from PyQt5.QtCore import (QLineF, QPointF, QRectF, Qt, QTimer, QCoreApplication, QSize, QBasicTimer,
                          QThread, pyqtSignal)
from PyQt5.QtGui import (QBrush, QColor, QPainter, QIcon, QPixmap)
from PyQt5.QtWidgets import (QApplication, QGraphicsView, QGraphicsScene, QGraphicsItem, QScrollArea, QFrame,
                             QGridLayout, QVBoxLayout, QHBoxLayout, QSizePolicy, QMainWindow, QDialog, QLabel,
                             QLineEdit, QPushButton, QWidget, QComboBox, QRadioButton, QSpinBox, QCheckBox,
                             QTabWidget, QFileDialog, QMessageBox, QDoubleSpinBox)
import pyqtgraph as pg

import time
import re
import png

from STT_CAM import Camera

class CameraWidget(QTabWidget):
    def __init__(self, globals={}, **kwargs):
        super().__init__(**kwargs)
        self.globals = globals
        self.indices = []
        self.initUI()
        return

    def initUI(self):
        self.setGeometry(100, 100, 1000, 700)
        for index in range(1):
            self.addTab(CamWidget(index, self.globals), "camera "+str(index))
            self.setTabToolTip(index, str(self.widget(index)))
        self.setWindowIcon(QIcon(os.path.dirname(__file__)+r'\icons\camera.png'))
        self.setWindowTitle('STT camera viewer')
        self.show()
        
        return


class GetImageThread(QThread):
    def __init__(self, papa):
        super().__init__()
        self.widget = papa
        self.save = False
        self.filename = ""
        self.prepare=True
        self.gradChanged = True
        self.time = time.perf_counter()
        return
    def __del__(self):
        self.wait()
        return

    def getTime(self):
        oldTime = self.time
        self.time = time.perf_counter()
        return self.time - oldTime

    def run(self):
        if self.gradChanged:
            self.gradChange()
        if self.prepare:
            self.prepare = False
            return
        self.widget.camera.read()
        self.widget.trigger.emit()
        #if not self.save:
        #    return
        #png.from_array(self.camera.image, 'L;16').save(self.filename)
        return

    def gradChange(self):
        self.widget.plot.setLookupTable(self.widget.grad.getLookupTable(65536))
        pickle.dump(self.widget.grad.saveState(), open("grad.p", "wb"))
        self.gradChanged = False
        return


class CamWidget(QWidget):
    trigger = pyqtSignal()
    def __init__(self, index, globals={}, **kwargs):
        super().__init__(**kwargs)
        self.index = index
        self.globals=globals
        self.connected = False
        self.name = ""
        self.camera = None
        self.capture = False
        self.trig = 2
        self.plotArea = pg.GraphicsLayoutWidget(self)
        box = pg.ViewBox(lockAspect=1)
        self.plotArea.addItem(box)
        self.plot = pg.ImageItem()
        box.addItem(self.plot)
        self.grad = pg.GradientEditorItem()
        try:
            state = pickle.load(open("grad.p", "rb"))
        except:
            state = None
        if state:
            self.grad.restoreState(state)
        box.addItem(self.grad)
        self.timer = QTimer()
        self.timer.timeout.connect(self.sayCheese)
        self.time = time.perf_counter()

        self.trigger.connect(self.draw)
        self.trigType = None
        self.connectCamera()
        if self.connected:
            self.initUI()
            self.getImageThread = GetImageThread(self)
            self.getImageThread.start()
            self.grad.sigGradientChangeFinished.connect(self.gradChange)
        return

    def draw(self):
        return self.plot.setImage(np.array(self.camera.image), levels=(0, 65535))

    def __str__(self, **kwargs):
        return self.name

    def gradChange(self):
        self.getImageThread.gradChanged = True
        return

    def connectCamera(self):
        self.camera = Camera()
        self.trig = self.camera.trig.value-1
        if self.camera.getNumberCameras() <= self.index:
            return -1
        if self.camera.openCamera(self.index):
            return -1
        self.connected = True
        self.name = self.camera.name
        return 0

    def initUI(self, show=True):
        layout = QVBoxLayout()
        tools = QHBoxLayout()

        self.start = QPushButton('', self)
        self.start.setIcon(QIcon(os.path.dirname(__file__)+r'\icons\start.png'))
        self.start.setIconSize(QSize(18, 18))
        self.start.clicked.connect(self.toggleCapture)
        tools.addWidget(self.start)

        self.trigType = QComboBox(self)
        self.trigType.addItems(['external', 'program'])
        self.trigType.currentIndexChanged.connect(self.changeTrig)
        tools.addWidget(self.trigType)

        tools.addStretch(1)

        restart = QPushButton('', self)
        restart.setIcon(QIcon(os.path.dirname(__file__)+r'\icons\restart.png'))
        restart.setIconSize(QSize(18, 18))
        restart.clicked.connect(self.connectCamera)
        tools.addWidget(restart)

        layout.addItem(tools)
        layout.addWidget(self.plotArea)

        self.setLayout(layout)
        
        self.show()
        self.trigType.setCurrentIndex(self.trig)
        return

    def getTime(self):
        oldTime = self.time
        self.time = time.perf_counter()
        return self.time-oldTime

    def sayCheese(self):
        if self.camera.busy():
            return
        self.getImageThread.start()
        return

    def saveNext(self, save=False, filename=""):
        self.getImageThread.save = save
        self.getImageThread.filename = filename
        return

    def changeTrig(self, trig):
        self.camera.setTrig(trig+1)
        self.trig = self.camera.trig.value-1
        self.trigType.setCurrentIndex(self.trig)

    def toggleCapture(self):
        self.capture = not self.capture
        if self.capture:
            self.start.setIcon(QIcon(os.path.dirname(__file__)+r'\icons\stop.png'))
            # 10ms for external (making this less is not advisable due to CPU being useful for other processes
            # 100ms for program (10fps is enough - it's not a CS)
            dt = 10+90*self.trig
            self.camera.start()
            self.timer.start(dt)
        else:
            self.timer.stop()
            self.camera.stop()
            self.start.setIcon(QIcon(os.path.dirname(__file__)+r'\icons\start.png'))
        return


def main():
    app = QApplication(sys.argv)
    window = CameraWidget()
    sys.exit(app.exec_())
    return

if __name__ == '__main__':
    main()

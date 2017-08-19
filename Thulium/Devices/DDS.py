import os, sys, json, socket, ctypes

from PyQt5.QtCore import (pyqtSignal, QTimer, QRect)
from PyQt5.QtGui import (QIcon)
from PyQt5.QtWidgets import (QPushButton, QHBoxLayout, QVBoxLayout, QLineEdit, QComboBox, QDoubleSpinBox, QApplication,
                             QWidget, QLabel, QMenuBar, QAction, QFileDialog, QInputDialog)

folder = 'Devices\settings'
myAppID = u'LPI.DDS' # arbitrary string
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myAppID)
sizes = [10, 100, 60, 60, 60, 60, 80, 100, 60, 60, 60, 60, 60, 30]

# setChannel(2,blue probe,SingleTone,0,0,0,145.000000000000,0.000000000000,3.000000000000,2.000000000000,0.001000000000,
#            0.002000000000,100pulses.awf,4.000000000000,146.000000000000,1.000000000000,0,0,0,,1,1,1);
# 2 - channel number                self.index
# <string>, <mode>                  self.name, self.mode
# 0,0,0 - Gated?, ???, ???          ---
# 145, 0 - freq, amp                self.freq, self.amp
# 3, 2 - fall, rise                 self.fall, self.rise
# 1e-3, 2e-3 - upper, lower         self.upper, self.lower
# <string> - waveform               self.wForm
# 4 - length                        self.length
# 146, 1 - freq2, amp2              self.freq2, self.amp2
# 0,0,0 - mirror?, invert?, skip?   ---
# ,,1,1 - god know what             ---
# 1 - SwitchedOn?                   ---

class Line(QWidget):
    def __init__(self, parent,
                 data={'index': '15', 'name': 'not used', 'mode': 'SingleTone', 'freq': 140, 'freq2': 100, 'amp': 0,
                       'amp2': 0, 'wForm': '', 'length': 0, 'lower': 0, 'upper': 0, 'rise': 0, 'fall': 0}
                 ):
        super().__init__(parent)
        self.parent = parent
        self.name = QLineEdit(data['name'])
        self.name.editingFinished.connect(self.update)

        self.index = QComboBox()
        self.index.clear()
        self.index.addItems(map(str, range(16)))
        self.index.setCurrentText(str(data['index']))
        self.index.currentIndexChanged.connect(self.update)

        self.mode = QComboBox()
        self.mode.addItems(['SingleTone', 'FrequencyRamp', 'AmplitudeRamp', 'ArbitraryWaveModus'])
        self.mode.setCurrentText(data['mode'])
        self.mode.currentIndexChanged.connect(self.update)

        self.wForm = QComboBox()
        self.wForm.addItems([None, '100pulses.awf', 'gaussian.awf', 'mod_cos_1-0.86.awf',
                             'smoothed_linear_ramp_down.awf', 'squeeze_and_unsqueeze_0pi.awf',
                             'squeeze_and_unsqueeze_14over7pi.awf', 'squeeze_and_unsqueeze_1over7pi.awf',
                             'squeeze_and_unsqueeze_2over7pi.awf', 'squeeze_and_unsqueeze_3over7pi.awf',
                             'squeeze_and_unsqueeze_4over7pi.awf', 'squeeze_and_unsqueeze_5over7pi.awf',
                             'squeeze_and_unsqueeze_6over7pi.awf', 'squeeze_and_unsqueeze_7over7pi.awf',
                             'squeeze_and_unsqueeze_v2_0over5.awf', 'squeeze_and_unsqueeze_v2_10over5.awf',
                             'squeeze_and_unsqueeze_v2_1over5.awf', 'squeeze_and_unsqueeze_v2_2over5.awf',
                             'squeeze_and_unsqueeze_v2_3over5.awf', 'squeeze_and_unsqueeze_v2_4over5.awf',
                             'squeeze_and_unsqueeze_v2_5over5.awf', 'squeeze_and_unsqueeze_v2_6over5.awf',
                             'squeeze_and_unsqueeze_v2_7over5.awf', 'squeeze_and_unsqueeze_v2_8over5.awf',
                             'squeeze_and_unsqueeze_v2_9over5.awf', 'squeeze_and_unsqueeze_v3_0over5.awf',
                             'squeeze_and_unsqueeze_v3_1.6over5.awf', 'squeeze_and_unsqueeze_v3_10over5.awf',
                             'squeeze_and_unsqueeze_v3_3.3over5.awf', 'squeeze_and_unsqueeze_v3_5over5.awf',
                             'squeeze_and_unsqueeze_v3_6.6over5.awf', 'squeeze_and_unsqueeze_v3_8.3over5.awf',
                             'squeeze_and_unsqueeze_v4_0over5.awf', 'squeeze_and_unsqueeze_v4_10over5.awf',
                             'squeeze_and_unsqueeze_v4_5over5.awf', 'squeezeing.awf', 'squeezing_85pc.awf',
                             'squeezing_85pc_22p.awf', 'test.awf'])
        self.wForm.setCurrentText(data['wForm'])
        self.wForm.currentIndexChanged.connect(self.update)

        self.freq = QDoubleSpinBox()
        self.freq.setDecimals(2)
        self.freq.setMinimum(10)
        self.freq.setMaximum(1000)
        self.freq.setValue(data['freq'])
        self.freq.valueChanged.connect(self.update)

        self.freq2 = QDoubleSpinBox()
        self.freq2.setDecimals(2)
        self.freq2.setMinimum(10)
        self.freq2.setMaximum(1000)
        self.freq2.setValue(data['freq2'])
        self.freq2.valueChanged.connect(self.update)

        self.amp = QDoubleSpinBox()
        self.amp.setDecimals(2)
        self.amp.setMinimum(0)
        self.amp.setMaximum(10)
        self.amp.setValue(data['amp'])
        self.amp.valueChanged.connect(self.update)

        self.amp2 = QDoubleSpinBox()
        self.amp2.setDecimals(2)
        self.amp2.setMinimum(0)
        self.amp2.setMaximum(10)
        self.amp2.setValue(data['amp2'])
        self.amp2.valueChanged.connect(self.update)

        self.lower = QDoubleSpinBox()
        self.lower.setValue(data['lower'])
        self.lower.valueChanged.connect(self.update)
        self.upper = QDoubleSpinBox()
        self.upper.setValue(data['upper'])
        self.upper.valueChanged.connect(self.update)

        self.rise = QDoubleSpinBox()
        self.rise.setMinimum(0)
        self.rise.setValue(data['rise'])
        self.rise.valueChanged.connect(self.update)

        self.fall = QDoubleSpinBox()
        self.fall.setMinimum(0)
        self.fall.setValue(data['fall'])
        self.fall.valueChanged.connect(self.update)

        self.length = QDoubleSpinBox()
        self.length.setMinimum(0)
        self.length.setValue(data['length'])
        self.length.valueChanged.connect(self.update)

        self.delBtn = QPushButton('del')
        self.delBtn.clicked.connect(lambda: self.parent.delete(self))
        self.delBtn.setFixedWidth(30)

        self.update()

        self.initUI()

    def initUI(self):
        layout = QHBoxLayout()
        i = 0
        layout.addWidget(self.index, sizes[i])
        i += 1
        layout.addWidget(self.name, sizes[i])
        i += 1
        layout.addWidget(self.freq, sizes[i])
        i += 1
        layout.addWidget(self.amp, sizes[i])
        i += 1
        layout.addWidget(self.freq2, sizes[i])
        i += 1
        layout.addWidget(self.amp2, sizes[i])
        i += 1
        layout.addWidget(self.mode, sizes[i])
        i += 1
        layout.addWidget(self.wForm, sizes[i])
        i += 1
        layout.addWidget(self.lower, sizes[i])
        i += 1
        layout.addWidget(self.upper, sizes[i])
        i += 1
        layout.addWidget(self.rise, sizes[i])
        i += 1
        layout.addWidget(self.fall, sizes[i])
        i += 1
        layout.addWidget(self.length, sizes[i])
        i += 1
        layout.addWidget(self.delBtn, sizes[i])
        i += 1
        self.setLayout(layout)

    def update(self):
        if not self.parent.connected:
            return
        try:
            self.parent.dds.send(str(self).encode())
        except Exception as e:
            self.parent.connected = False
            print('disconnected from ' + self.parent.ip + '\n', e)

    def __call__(self):
        return {'index':self.index.currentText(), 'name':str(self.name.text()), 'mode':self.mode.currentText(),
                'freq':self.freq.value(), 'freq2':self.freq2.value(), 'amp':self.amp.value(), 'amp2':self.amp2.value(),
                'wForm':self.wForm.currentText(), 'length':self.length.value(), 'lower':self.lower.value(),
                'upper':self.upper.value(), 'rise':self.rise.value(), 'fall':self.fall.value()}

    def __str__(self):
        data = self.__call__()
        args = [data['index'], data['name'], data['mode'], 0, 0, 0, data['freq'], data['amp'], data['fall'],
                data['rise'], data['upper'], data['lower'], data['wForm'], data['length'], data['freq2'], data['amp2'],
                0, 0, 0, '', 1, 1, 1]
        return 'setChannel(' + ','.join(map(str, args)) + ');'


class DDSWidget(QWidget):
    def __init__(self, parent=None, globals={}, signals=None):
        super(DDSWidget, self).__init__()
        self.parent = parent
        self.signals = signals
        self.dds = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ip = '192.168.1.6'
        self.port = 2600
        self.connected = False
        try:
            self.dds.connect((self.ip, self.port))
            self.connected = True
        except Exception as e:
            print(e)

        self.lines = []
        self.load()

        self.menuBar = QMenuBar(self)

        self.initUI()

        self.autoSave = QTimer(self)
        self.autoSave.setInterval(500000)
        self.autoSave.timeout.connect(self.save)
        self.autoSave.start()


    def initUI(self):
        fileMenu = self.menuBar.addMenu('&File')
        connect = QAction('&Connect', self)
        connect.triggered.connect(self.connect)
        fileMenu.addAction(connect)
        load = QAction('&Load', self)
        load.triggered.connect(self.loadDialog)
        fileMenu.addAction(load)
        save = QAction('&Save', self)
        save.triggered.connect(self.saveDialog)
        fileMenu.addAction(save)

        self.setWindowTitle('DDS')
        self.setWindowIcon(QIcon('Devices\dds.jpg'))

        mainLayout = QVBoxLayout()
        mainLayout.addSpacing(20)

        fields = QHBoxLayout()
        i = 0
        fields.addWidget(QLabel('index'), sizes[i])
        i += 1
        fields.addWidget(QLabel('name'), sizes[i])
        i += 1
        fields.addWidget(QLabel('freq'), sizes[i])
        i += 1
        fields.addWidget(QLabel('amp'), sizes[i])
        i += 1
        fields.addWidget(QLabel('freq2'), sizes[i])
        i += 1
        fields.addWidget(QLabel('amp2'), sizes[i])
        i += 1
        fields.addWidget(QLabel('mode'), sizes[i])
        i += 1
        fields.addWidget(QLabel('wForm'), sizes[i])
        i += 1
        fields.addWidget(QLabel('lower'), sizes[i])
        i += 1
        fields.addWidget(QLabel('upper'), sizes[i])
        i += 1
        fields.addWidget(QLabel('rise'), sizes[i])
        i += 1
        fields.addWidget(QLabel('fall'), sizes[i])
        i += 1
        fields.addWidget(QLabel('length'), sizes[i])
        i += 1
        fields.addSpacing(sizes[i])
        i += 1
        mainLayout.addLayout(fields)

        for line in self.lines:
            mainLayout.addWidget(line)

        addLine = QPushButton('add line')
        addLine.clicked.connect(self.addLine)
        mainLayout.addWidget(addLine)

        mainLayout.addStretch()

        self.setLayout(mainLayout)

    def addLine(self):
        self.signals.wvlChanged.emit('hello there')
        self.lines.append(Line(self))
        self.layout().insertWidget(len(self.lines), self.lines[-1])
        self.save()
        return

    def delete(self, line):
        self.layout().removeWidget(line)
        line.deleteLater()
        self.lines.remove(line)
        self.save()
        return

    def connect(self):
        ip, ok = QInputDialog.getText(self, '(Re)connect', 'enter ip:', text=self.ip)
        if not ok:
            return
        if self.connected:
            self.connected = False
            self.dds.close()
        self.ip = ip
        try:
            self.dds.connect((self.ip, self.port))
            self.connected = True
        except Exception as e:
            print(e)
        for line in self.lines:
            line.update()
        return

    def loadDialog(self):
        fileName = QFileDialog.getOpenFileName(self, 'Load scheme', folder, filter='*.json')
        if fileName:
            self.load(fileName[0])
        return

    def load(self, name='last.json'):
        success = False
        try:
            with open(os.path.join(folder, name), 'r') as f:
                self.lines = [Line(parent=self, data=line) for line in json.load(f)]
            success = True
        except Exception as error:
            print(error)
        return success

    def saveDialog(self):
        fileName = QFileDialog.getSaveFileName(self, 'Save scheme', folder, filter='*.json')
        if fileName:
            self.save(fileName[0])
        return

    def save(self, name='last.json'):
        success = False
        try:
            with open(os.path.join(folder, name), 'w') as f:
                json.dump([line() for line in self.lines], f)
            success = True
        except Exception as error:
            print(error)
        return success

    def __del__(self):
        print('deleting')
        if self.connected:
            self.connected = False
            self.dds.close()

if __name__ == '__main__':
    folder = 'settings'
    app = QApplication(sys.argv)
    ex = DDSWidget()
    ex.show()
    sys.exit(app.exec_())

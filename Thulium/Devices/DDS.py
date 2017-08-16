import os, sys, json

from PyQt5.QtCore import (pyqtSignal)
from PyQt5.QtGui import (QIcon)
from PyQt5.QtWidgets import (QPushButton, QHBoxLayout, QVBoxLayout, QLineEdit, QComboBox, QDoubleSpinBox, QApplication,
                             QWidget, QLabel, QMenuBar, QAction, QFileDialog)

folder = 'Device\settings'


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
    def __init__(self, parent=None,
                 data={'index': '15', 'name': 'not used', 'mode': 'SingleTone', 'freq': 140, 'freq2': 100, 'amp': 0,
                       'amp2': 0, 'wForm': '', 'length': 0, 'lower': 0, 'upper': 0, 'rise': 0, 'fall': 0}
                 ):
        super().__init__(parent)
        self.name = QLineEdit(data['name'])
        self.name.editingFinished.connect(parent.save)

        self.index = QComboBox()
        self.index.clear()
        self.index.addItems(map(str, range(16)))
        self.index.setCurrentText(str(data['index']))
        self.index.currentIndexChanged.connect(lambda: parent.update(self))

        self.mode = QComboBox()
        self.mode.addItems(['SingleTone', 'FrequencyRamp', 'AmplitudeRamp', 'ArbitraryWaveModus'])
        self.mode.setCurrentText(data['mode'])
        self.mode.currentIndexChanged.connect(lambda: parent.update(self))

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
        self.wForm.currentIndexChanged.connect(lambda: parent.update(self))

        self.freq = QDoubleSpinBox()
        self.freq.setDecimals(2)
        self.freq.setMinimum(10)
        self.freq.setMaximum(1000)
        self.freq.setValue(data['freq'])
        self.freq.valueChanged.connect(lambda: parent.update(self))

        self.freq2 = QDoubleSpinBox()
        self.freq2.setDecimals(2)
        self.freq2.setMinimum(10)
        self.freq2.setMaximum(1000)
        self.freq2.setValue(data['freq2'])
        self.freq2.valueChanged.connect(lambda: parent.update(self))

        self.amp = QDoubleSpinBox()
        self.amp.setDecimals(2)
        self.amp.setMinimum(0)
        self.amp.setMaximum(10)
        self.amp.setValue(data['amp'])
        self.amp.valueChanged.connect(lambda: parent.update(self))

        self.amp2 = QDoubleSpinBox()
        self.amp2.setDecimals(2)
        self.amp2.setMinimum(0)
        self.amp2.setMaximum(10)
        self.amp2.setValue(data['amp2'])
        self.amp2.valueChanged.connect(lambda: parent.update(self))

        self.lower = QDoubleSpinBox()
        self.lower.setValue(data['lower'])
        self.lower.valueChanged.connect(lambda: parent.update(self))

        self.upper = QDoubleSpinBox()
        self.upper.setValue(data['upper'])
        self.upper.valueChanged.connect(lambda: parent.update(self))

        self.rise = QDoubleSpinBox()
        self.rise.setMinimum(0)
        self.rise.setValue(data['rise'])
        self.rise.valueChanged.connect(lambda: parent.update(self))

        self.fall = QDoubleSpinBox()
        self.fall.setMinimum(0)
        self.fall.setValue(data['fall'])
        self.fall.valueChanged.connect(lambda: parent.update(self))

        self.length = QDoubleSpinBox()
        self.length.setMinimum(0)
        self.length.setValue(data['length'])
        self.length.valueChanged.connect(lambda: parent.update(self))

        self.delBtn = QPushButton('del')
        self.delBtn.clicked.connect(lambda: parent.delete(self))

        print(self)

        self.initUI()

    def initUI(self):
        layout = QHBoxLayout()
        layout.addWidget(self.index)
        layout.addWidget(self.name)
        layout.addWidget(self.freq)
        layout.addWidget(self.amp)
        layout.addWidget(self.freq2)
        layout.addWidget(self.amp2)
        layout.addWidget(self.mode)
        layout.addWidget(self.wForm)
        layout.addWidget(self.lower)
        layout.addWidget(self.upper)
        layout.addWidget(self.rise)
        layout.addWidget(self.fall)
        layout.addWidget(self.length)
        layout.addWidget(self.delBtn)
        self.setLayout(layout)

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
        super().__init__(parent)
        self.lines = []
        self.load()
        self.menuBar = QMenuBar(self)
        self.initUI()

    def initUI(self):
        mainLayout = QVBoxLayout()

        fields = QHBoxLayout()
        fields.addWidget(QLabel('index'))
        fields.addWidget(QLabel('name'))
        fields.addWidget(QLabel('freq'))
        fields.addWidget(QLabel('amp'))
        fields.addWidget(QLabel('freq2'))
        fields.addWidget(QLabel('amp2'))
        fields.addWidget(QLabel('mode'))
        fields.addWidget(QLabel('wForm'))
        fields.addWidget(QLabel('lower'))
        fields.addWidget(QLabel('upper'))
        fields.addWidget(QLabel('rise'))
        fields.addWidget(QLabel('fall'))
        fields.addWidget(QLabel('length'))
        mainLayout.addLayout(fields)

        for line in self.lines:
            mainLayout.addWidget(line)

        addLine = QPushButton('add line')
        addLine.clicked.connect(self.addLine)
        mainLayout.addWidget(addLine)

        fileMenu = self.menuBar.addMenu('&File')
        load = QAction('&Load', self)
        load.triggered.connect(self.loadDialog)
        fileMenu.addAction(load)
        save = QAction('&Save', self)
        save.triggered.connect(self.saveDialog)
        fileMenu.addAction(save)

        self.setLayout(mainLayout)

    def addLine(self):
        self.lines.append(Line(parent=self))
        self.layout().insertWidget(len(self.lines), self.lines[-1])
        self.save()
        return

    def delete(self, line):
        self.layout().removeWidget(line)
        line.deleteLater()
        self.lines.remove(line)
        self.save()

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

    def update(self, line):
        self.save()
        print(line)
        return

if __name__ == '__main__':
    folder = 'settings'
    app = QApplication(sys.argv)
    ex = DDSWidget()
    ex.show()
    sys.exit(app.exec_())

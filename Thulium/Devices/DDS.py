import os, sys, json, socket, ctypes
from collections import OrderedDict

from PyQt5.QtCore import (pyqtSignal, QTimer, QRect, Qt, )
from PyQt5.QtGui import (QIcon, QDoubleValidator, )
from PyQt5.QtWidgets import (QPushButton, QHBoxLayout, QVBoxLayout, QLineEdit, QComboBox, QDoubleSpinBox, QApplication,
                             QWidget, QLabel, QMenuBar, QAction, QFileDialog, QInputDialog,QSizePolicy,QScrollArea )

# Changed the way DDS widget is constructed - now it is done based on an ordered dictionary. It is only when forming string to send to BeagleBone parameters are called by name (key).
# To add new parameter one should add entry to the LineDict, and then add this variable in __str__ method.
# !!! MyBox now returns value in string format
# Did not yet added nice field names (upper line)


folder = 'Devices\settings'
myAppID = u'LPI.DDS' # arbitrary string
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myAppID)
sizes = [10, 100, 60, 60, 60, 60, 80, 100, 60, 60, 60, 60, 60, 30]
wForm_list = [None, '100pulses.awf', 'gaussian.awf', 'mod_cos_1-0.86.awf',
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
              'squeezing_85pc_22p.awf', 'test.awf']
# LineDict form ('name of variable',[widget type, default, value,other parameters,width of the widget])
LineDict = OrderedDict([
    ('index',['CB','15',list(map(str, range(16))),10]),
    ('name',['LE','not used',120]),
    ('freq',['MB','140',60]),
    ('amp',['MB','0',60]),
    ('freq2',['MB','140',60]),
    ('amp2',['MB','1',60]),
    ('mode',['CB','SingleTone',['SingleTone', 'FrequencyRamp', 'AmplitudeRamp', 'ArbitraryWaveModus'],80]),
    ('lower',['MB','0',60]),
    ('upper',['MB','0',60]),
    ('rise',['MB','0',60]),
    ('fall',['MB','0',60]),
    ('ndl',['MB','0',30]),
    ('ndh',['MB','0',30]),
    ('osk',['MB','0',30]),
    ('length',['MB','0',60]),
    ('wForm',['CB','',wForm_list,100])
])
scan_params_str = 'scan_params'
name_in_scan_params = 'DDS'

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
# ,,1,1 - god knows what            ---
# 1 - SwitchedOn?                   ---

class MyBox(QLineEdit):
    def __init__(self, *args, **kwargs):
        super(MyBox, self).__init__(*args, **kwargs)
        self.setValidator(QDoubleValidator(10, 999, 6))

    def keyPressEvent(self, QKeyEvent):
        p = 0
        if QKeyEvent.key() == Qt.Key_Up:
            p = 1
        if QKeyEvent.key() == Qt.Key_Down:
            p = -1
        if p == 0:
            return super(MyBox, self).keyPressEvent(QKeyEvent)
        number = [x for x in self.text()]
        position = self.cursorPosition()
        pos = position - 1
        while p and pos >= 0:
            if ('0' < number[pos] < '9') or (number[pos] == '9' and p < 0) or (number[pos] == '0' and p > 0):
                number[pos] = chr(ord(number[pos]) + p)
                p = 0
            elif number[pos] == '9':
                number[pos] = '0'
            elif number[pos] == '0':
                number[pos] = '9'
            pos -= 1
        if p == 1:
            number = '1' + ''.join(number)
            position += 1
        self.setText(''.join(number))
        self.setCursorPosition(position)

    def value(self):
        return float(self.text())


autoSave = QTimer()
autoSave.setInterval(5000)



class Line(QWidget):

    def __init__(self, parent,data={}):
        super().__init__(parent)
        self.parent = parent
        layout = QHBoxLayout()
        self.data = data
        self.autoUpdate = QTimer()
        self.autoUpdate.setInterval(100)
        self.autoUpdate.timeout.connect(self.update)
        self.widgets = {}
        for key,val in LineDict.items():
            if val[0] == 'CB':
                # do a combo box widget
                w = QComboBox()
                w.setText = w.setCurrentText
                w.text = w.currentText
                w.clear()
                w.addItems(val[2])
                w.setCurrentText(data.get(key,val[1]))
                w.currentIndexChanged.connect(self.autoUpdate.start)
            elif val[0] == 'LE':
                w = QLineEdit(data.get(key,val[1]))
                # w.editingFinished.connect(self.autoUpdate.start)
                w.textChanged.connect(self.autoUpdate.start)
                w.textEdited.connect(self.textEdited)
            elif val[0] == 'MB':
                w = MyBox()
                w.setText(data.get(key,val[1]))
                w.textChanged.connect(self.autoUpdate.start)
                w.textEdited.connect(self.textEdited)
            self.widgets[key] = w
            layout.addWidget(w, val[-1])

        self.delBtn = QPushButton('del')
        self.delBtn.clicked.connect(lambda: self.parent.delete(self))
        self.delBtn.setFixedWidth(30)
        layout.addWidget(self.delBtn)
        # layout.addStretch(1)
        self.setLayout(layout)
        # self.setMinimumHeight(50)
        self.update()

        # self.initUI()

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
        # print(str(self))
        self.autoUpdate.stop()
        if self.parent and not self.parent.scanner:
            autoSave.start()
        if not self.parent.connected:
            print(str(self))
            return
        try:
            self.parent.dds.send(str(self).encode())
        except Exception as e:
            self.parent.connected = False
            print('disconnected from ' + self.parent.ip + '\n', e)

    def textEdited(self):
        if self.parent:
            self.parent.scanner = False
        self.autoUpdate.start()

    def __call__(self):
        self.data={}
        for key,val in LineDict.items():
            if val[0] == 'CB':# do a combo box widget
                self.data[key] = self.widgets[key].currentText()
            elif val[0] == 'LE':
                self.data[key] = self.widgets[key].text()
            elif val[0] == 'MB':
                self.data[key] = self.widgets[key].text()
        return self.data

    def __str__(self):
        data = self.__call__()
        args = [data['index'], data['name'], data['mode'], int(data['osk']), int(data['ndl']), int(data['ndh']),
                data['freq'], data['amp'], data['fall'], data['rise'], data['lower'], data['upper'], data['wForm'],
                data['length'], data['freq2'], data['amp2'], 0, 0, 0, '', 1, 1, 1]
        return 'setChannel(' + ','.join(map(str, args)) + ');'


class DDSWidget(QScrollArea):
    def __init__(self, parent=None, globals=None, signals=None):
        super(DDSWidget, self).__init__()
        self.parent = parent
        self.signals = signals
        self.globals = globals
        self.scanner = False
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
        # print(self.lines)

        self.menuBar = QMenuBar(self)

        self.initUI()
        self.setSizePolicy(QSizePolicy(QSizePolicy.Preferred,QSizePolicy.Preferred))
        autoSave.timeout.connect(self.save)
        # self.autoSave.start()


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
        main_widget = QWidget()
        mainLayout = QVBoxLayout()
        # mainLayout.addSpacing(10)

        fields = QHBoxLayout()
        # fields.addSpacing(15)
        for key,val in LineDict.items():
            fields.addWidget(QLabel(key))#, val[-1])
        # fields.addStretch(50)
        mainLayout.addLayout(fields)

        for line in self.lines:
            mainLayout.addWidget(line)

        addLine = QPushButton('add line')
        addLine.clicked.connect(self.addLine)
        mainLayout.addWidget(addLine)
        main_widget.setLayout(mainLayout)
        main_widget.setMaximumWidth(1400)
        self.setWidget(main_widget)
        self.setMinimumHeight(200)
        # mainLayout.addStretch()
        # self.setMinimumWidth(500)

        # self.setLayout(mainLayout)


    def addLine(self):
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
        else:
            print("can't open " + fileName)
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
        print('saving')
        autoSave.stop()
        success = False
        try:
            self.sendScanParams()
            with open(os.path.join(folder, name), 'w') as f:
                json.dump([line() for line in self.lines], f)
            success = True
        except Exception as error:
            print(error)
        return success

    def sendScanParams(self):
        params = {}
        for line in self.lines:
            data = line()
            key = data['index']
            params[key] = list(data.keys())
        if self.globals != None:
            if scan_params_str not in self.globals:
                self.globals[scan_params_str] = {}
            self.globals[scan_params_str][name_in_scan_params] = params
        return

    def getUpdateMethod(self):
        return self.updateFromScanner

    def updateFromScanner(self, param_dict=None):
        self.scanner = True
        try:
            for param,val in param_dict.items():
                index = param[0]
                field = param[1]
                for line in self.lines:
                    if line.widgets['index'].text() == index:
                        line.widgets[field].setText(str(val))
        except Exception as e:
            print("can't change from scanner: ", e)
            return -1
        return 0

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

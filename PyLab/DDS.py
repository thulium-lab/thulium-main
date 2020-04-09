import os, sys, json, socket, ctypes, re, datetime
import numpy as np
import sympy as sp
from sympy.utilities.lambdify import lambdify
from sympy.parsing.sympy_parser import parse_expr
from collections import OrderedDict

from PyQt5.QtCore import (pyqtSignal, QTimer, QRect, Qt, )
from PyQt5.QtGui import (QIcon, QDoubleValidator, )
from PyQt5.QtWidgets import (QPushButton, QHBoxLayout, QVBoxLayout, QLineEdit, QComboBox, QDoubleSpinBox, QApplication,
                             QWidget, QLabel, QMenuBar, QAction, QFileDialog, QInputDialog, QSizePolicy, QScrollArea )

# Changed the way DDS widget is constructed - now it is done based on an ordered dictionary.
# It is only when forming string to send to BeagleBone parameters are called by name (key).
# To add new parameter one should add entry to the LineDict, and then add this variable in __str__ method.
# !!! MyBox now returns value in string format
# Did not yet added nice field names (upper line)
from Lib import (MyComboBox, MyDoubleBox, MyIntBox, MyLineEdit, MyCheckBox, MyPushButton,
                 QDoubleValidator, QIntValidator)

# folder = 'Devices\settings'
folder = ''
myAppID = u'LPI.DDS'  # arbitrary string
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myAppID)
sizes = [10, 100, 60, 60, 60, 60, 80, 100, 60, 60, 60, 60, 60, 30]
wForm_list = [None, '100pulses.awf', 'gaussian.awf', 'mod_cos_1-0.86.awf']
# LineDict form ('name of variable',[widget type, default, value,other parameters,width of the widget])
# 'CB' - ComboBox, 'LE' - LineEdit, 'MB' - MyBox
freq_validator = QDoubleValidator(1, 500, 6)
ampl_validator = QDoubleValidator(0, 1, 2)
slope_validator = QDoubleValidator(0, 9, 5)
bit_validator = QIntValidator(0, 1)
LineDict = OrderedDict([
    ('index', ['CB', '15', list(map(str, range(16))), 10]),
    ('name', ['LE', 'not used', 120]),
    ('freq0', ['MDB', '140', freq_validator, 60]),
    ('amp0', ['MDB', '0', ampl_validator, 60]),
    ('freq1', ['MDB', '140', freq_validator, 60]),
    ('amp1', ['MDB', '1', ampl_validator, 60]),
    ('mode', ['CB', 'SingleTone',
              ['SingleTone', 'FrequencyRamp', 'PhaseAmpMode', 'FreqRampAmpRam', "FreqRampAntiRam",'AmpRamp'], 120]),
    ('lower', ['MDB', '0', freq_validator, 60]),
    ('upper', ['MDB', '0', freq_validator, 60]),
    ('rise', ['MDB', '0', slope_validator, 60]),
    ('fall', ['MDB', '0', slope_validator, 60]),
    ('ndl', ['MIB', '0', bit_validator, 30]),
    ('ndh', ['MIB', '0', bit_validator, 30]),
    ('osk', ['MIB', '0', bit_validator, 30]),
    ('length', ['MDB', '0', slope_validator, 60]),
    ('wForm', ['LE', '0', 100])
])
SCAN_PARAMS_STR = 'available_scan_params'
NAME_IN_SCAN_PARAMS = 'DDS'
DEBUG=True

# setChannel(2,blue probe,SingleTone,0,0,0,145.000000000000,0.000000000000,3.000000000000,2.000000000000,0.001000000000,
#            0.002000000000,100pulses.awf,4.000000000000,146.000000000000,1.000000000000,0,0,0,,1,1,1);
# 2 - channel number                self.index
# <string>, <mode>                  self.name, self.mode
# 0,0,0 - Gated?, ndl, ndh          no-dwell-low and no-dwell-high
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
        self.setValidator(QDoubleValidator(0, 999, 6))

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

    def __init__(self, parent, data={}):
        super().__init__(parent)
        self.parent = parent
        layout = QHBoxLayout()
        self.data = data
        self.autoUpdate = QTimer()
        self.autoUpdate.setInterval(100)
        self.autoUpdate.timeout.connect(self.update)
        self.widgets = {}
        for key,val in LineDict.items():
            # print(key,val)
            if val[0] == 'CB':
                # create a combo box widget
                w = MyComboBox(items=val[2], current_text=data.get(key,val[1]),
                               current_index_changed_handler=self.autoUpdate.start)
            elif val[0] == 'LE':
                w = MyLineEdit(name=data.get(key,val[1]),
                            text_changed_handler=self.autoUpdate.start,
                            text_edited_handler=self.textEdited)
            elif val[0] == 'MDB':
                w = MyDoubleBox(validator=val[2],value=data.get(key,val[1]),
                                    text_changed_handler=self.autoUpdate.start,
                                    text_edited_handler=self.textEdited)
            elif val[0] == 'MIB':
                w = MyIntBox(validator=val[2], value=data.get(key, val[1]),
                            text_changed_handler=self.autoUpdate.start,
                            text_edited_handler=self.textEdited)
            self.widgets[key] = w
            layout.addWidget(w, val[-1])
        self.delBtn = MyPushButton(name='del',handler=lambda: self.parent.delete(self),fixed_width=30)
        layout.addWidget(self.delBtn)
        # layout.addStretch(1)
        self.setLayout(layout)
        self.setMinimumHeight(10)
        self.update()

    def update(self):
        # print(str(self))
        self.autoUpdate.stop()
        if self.parent and not self.parent.scanner:
            autoSave.start()
        if not self.parent.connected:
            print(str(self))
            return
        print("Sending to DDS at ", datetime.datetime.now())
        try:
            self.parent.dds.send(str(self).encode())
        except Exception as e:
            self.parent.connected = False
            print('disconnected from ' + self.parent.ip + '\n', e)

        try:
            pass
            # received = str(self.parent.dds.recv(1024), "utf-8")
            # print('DDS says', received)
        except Exception as e:
            print('DDS ' + e)

        print("Received from DDS at ", datetime.datetime.now())

    def textEdited(self):
        if self.parent:
            self.parent.scanner = False
        self.autoUpdate.start()

    def __call__(self):
        # self.data={}
        for key,val in LineDict.items():
            if val[0] == 'CB':# do a combo box widget
                self.data[key] = self.widgets[key].currentText()
            elif val[0] == 'LE':
                self.data[key] = self.widgets[key].text()
            elif val[0] in ['MDB','MIB']:
                self.data[key] = self.widgets[key].text()
        # data['formula'] =
        return self.data

    def __str__(self):
        data = self.__call__()
        i = data['name'].find('<0')
        m = 1
        if i >= 0:
            m = float(data['name'][i+1:])
        m = min(m,1)
        m = max(m,0)
        if data['mode'] == 'SingleTone':
            points = ''
        elif data['mode'] == 'AmpRamp':
            n_points = 1024
            t_fall = float(data['fall'])
            t_low = float(data['length'])
            t_rise = float(data['rise'])
            a0 = min(max(float(data['amp0']),0),m)
            a1 = min(max(float(data['lower']),0),m)
            a2 = min(max(float(data['upper']), 0), m)
            t_tot = t_fall + t_low + t_rise
            n1 = int(t_fall/t_tot * (n_points-1))
            n2 = int(t_low/t_tot * (n_points-1))
            n3 = (n_points-1) - (n1 + n2)
            points_fall = [a0 + (a1-a0)*i/n1 for i in range(n1)]
            points_low = [a1]*n2
            points_rise = [a1 + (a2-a1)*i/n3 for i in range(n3)] + [a2]
            points = points_fall + points_low + points_rise
            # print("Every 40th point", points[::40])
            # args = [data['index'], data['name'], data['mode'], int(data['osk']),
            #         int(data['ndl']), int(data['ndh']), data['freq0'], data['amp0'],
            #         data['fall'], data['rise'], data['lower'], data['upper'], points,
            #         str(t_tot), data['freq1'], data['amp1'], 0, 0, 0, '', 1, 1, 1]
            # 'PhaseAmpMode' or 'FreqRampAmpRam'. For reverse trigger: 'FreqRampAntiRam'
            args = [data['index'], data['name'], 'PhaseAmpMode', int(data['osk']),
                    int(data['ndl']), int(data['ndh']), data['freq0'], data['amp0'],
                    0, 0, data['freq1'], data['freq1'], " ".join(["%.5f"%(x) for x in points]),
                    str(1e6*t_tot), data['freq1'], data['amp1'], 0, 0, 0, '', 1, 1, 1]
            return 'setChannel(' + ','.join(map(str, args)) + ');'
        else:
            sp_form = re.split("([+-/*()])", data['wForm'])
            sp_form = [s.strip() for s in sp_form]
            for i, s in enumerate(sp_form):
                if s in LineDict.keys():
                    sp_form[i] = str(data[s])
            formula = ''.join(sp_form)
            try:
                formula = parse_expr(formula)
                t = sp.symbols('t')
                func = np.vectorize(lambdify(t, formula, 'numpy'))
                xs = np.linspace(start=0, stop=float(data['length']), num=1024)
                ys = func(xs)
                points = ' '.join("{:.5f}".format(min(max(y,0),m)) for y in ys)
            except Exception as e:
                print("dds: bad formula")
                points = '0 0 0'
        data['amp0'] = str(min(max(float(data['amp0']),0),m))
        data['amp1'] = str(min(max(float(data['amp1']),0),m))
        args = [data['index'], data['name'], data['mode'], int(data['osk']),
                int(data['ndl']), int(data['ndh']), data['freq0'], data['amp0'],
                data['fall'], data['rise'], data['lower'], data['upper'], points,
                data['length'], data['freq1'], data['amp1'],0,0,0,'',1,1,1]
        return 'setChannel(' + ','.join(map(str, args)) + ');'

    def updateFromScanner(self,field,value):
        print("--line -- DDS -- update from scanner")
        self.widgets[field].setValue(str(value))
        self.update()

class DDSWidget(QScrollArea):

    def __init__(self, parent=None, globals=None, signals=None,config_file=None):
        super(DDSWidget, self).__init__()
        self.parent = parent
        self.signals = signals
        self.globals = globals
        self.scanner = False
        self.dds = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ip = '192.168.1.5'
        self.port = 2600
        self.connected = False
        try:
            self.dds.connect((self.ip, self.port))
            self.connected = True
        except Exception as e:
            print(e)

        self.lines = []
        self.mainWidget = QWidget()
        self.load()

        self.menuBar = QMenuBar(self)

        self.initUI()
        self.sendScanParams()
        self.setSizePolicy(QSizePolicy(QSizePolicy.Preferred,QSizePolicy.Preferred))
        autoSave.timeout.connect(self.save)
        if self.signals and self.signals.updateFromScanner:
            self.signals.updateFromScanner.connect(self.updateFromScanner)
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
        self.updateWidget()
        self.mainWidget.setMaximumWidth(1400)
        self.setMinimumHeight(200)
        self.setWidget(self.mainWidget)

    def updateWidget(self):
        mainLayout = QVBoxLayout(self)

        fields = QHBoxLayout()
        for key,val in LineDict.items():
            lbl = QLabel(key)
            lbl.setMinimumWidth(val[-1])
            fields.addWidget(lbl)#, val[-1])
        # fields.addStretch(50)
        mainLayout.addLayout(fields)

        for line in self.lines:
            mainLayout.addWidget(line)

        addLine = QPushButton('add line')
        addLine.clicked.connect(self.addLine)
        mainLayout.addWidget(addLine)
        self.mainWidget.setLayout(mainLayout)
        mainLayout.setSpacing(1)

        # mainLayout.addStretch()
        # self.setMinimumWidth(500)

        # self.setLayout(mainLayout)

    def addLine(self):
        self.lines.append(Line(self))
        # print(self.layout())
        self.mainWidget.layout().insertWidget(len(self.lines), self.lines[-1])
        self.save()
        return

    def delete(self, line):
        self.mainWidget.layout().removeWidget(line)
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
            self.dds = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
        return self.updateWidget()

    def load(self, name='last_new.json'):
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

    def save(self, name='last_new.json'):
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
            key = data['name']
            params[key] = list(data.keys())
        if self.globals != None:
            if SCAN_PARAMS_STR not in self.globals:
                self.globals[SCAN_PARAMS_STR] = {}
            self.globals[SCAN_PARAMS_STR][NAME_IN_SCAN_PARAMS] = params
        return

    def getUpdateMethod(self):
        return self.updateFromScanner

    def updateFromScanner(self):
        self.scanner = True
        current_shot = self.globals["scan_running_data"]["current_meas_number"]
        for param, path in {**self.globals["scan_params"]["main"],
                            **self.globals["scan_params"]["low"]}.items():
            if path[0] == "DDS" and (current_shot==0 or
                                        self.globals["scan_running_table"].loc[current_shot, param] != self.globals["scan_running_table"].loc[
                current_shot - 1, param]):
                if DEBUG: print("DDS - update from scanner - ", param, path)
                name = path[1]
                field = path[2]
                for line in self.lines:
                    if line.widgets['name'].text() == name:
                        print("DDS CHANNEL FOUND", field, self.globals["scan_running_table"].loc[current_shot, param])
                        line.updateFromScanner(field=field,value=self.globals["scan_running_table"].loc[current_shot, param])
                        break
        return 0

    def __del__(self):
        print('deleting')
        if self.connected:
            self.connected = False
            self.dds.close()

if __name__ == '__main__':
    # folder = 'settings'
    app = QApplication(sys.argv)
    ex = DDSWidget()
    ex.show()
    sys.exit(app.exec_())

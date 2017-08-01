from PyQt5.QtCore import (Qt, pyqtSignal)
from PyQt5.QtWidgets import (QGridLayout, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
                             QDoubleSpinBox, QApplication, QDialog, QDialogButtonBox, QCheckBox)


class Shutter():
    N_CHANNELS = 16

    def __init__(self,name=''):
        self.name = name
        self.channel = 0
        self.linked_digital_channels = []
        self.start_delay = 0
        self.stop_delay = 0
        self.always_on = False
        self.always_off = False

    def load(self, shutter_dict=None):
        print('shutter-load')

    class ShutterWidget(QDialog):
        fields = ['name', 'channels','start_delay','stop_delay','linked_pulses']
        def __init__(self,parent=None,data=None):
            super().__init__(parent)
            self.parent = parent
            self.data = data
            self.initUI()
            self.show()

        def initUI(self):
            main_layout = QVBoxLayout()
            self.grid_layout = QGridLayout()

            self.grid_layout.addWidget(QLabel('Name'),0,0)
            name_line = QLineEdit(self.data.name)
            name_line.returnPressed.connect(self.nameChanged)
            self.grid_layout.addWidget(name_line, 0, 1)

            self.grid_layout.addWidget(QLabel('Channel'),1,0)
            channel_box = QComboBox()
            channel_box.addItems([str(i) for i in range(self.data.N_CHANNELS)])
            channel_box.setCurrentIndex(self.data.channel)
            channel_box.currentIndexChanged.connect(self.channelChanged)
            self.grid_layout.addWidget(channel_box, 1, 1)

            self.grid_layout.addWidget(QLabel('Start delay'),2,0)
            start_delay_box = QDoubleSpinBox()
            start_delay_box.setDecimals(1)
            start_delay_box.setMinimum(-100)
            start_delay_box.setMaximum(100)
            start_delay_box.setValue(self.data.start_delay)
            start_delay_box.valueChanged.connect(self.startDelayChanged)
            self.grid_layout.addWidget(start_delay_box, 2,1)

            self.grid_layout.addWidget(QLabel('Stop delay'), 3, 0)
            stop_delay_box = QDoubleSpinBox()
            stop_delay_box.setDecimals(1)
            stop_delay_box.setMinimum(-100)
            stop_delay_box.setMaximum(100)
            stop_delay_box.setValue(self.data.stop_delay)
            stop_delay_box.valueChanged.connect(self.stopDelayChanged)
            self.grid_layout.addWidget(stop_delay_box, 3,1)

            self.alwaysOnChbx = QCheckBox('Always On')
            self.alwaysOnChbx.setChecked(self.data.always_on)
            self.grid_layout.addWidget(self.alwaysOnChbx, 4, 0)
            self.alwaysOnChbx.stateChanged.connect(lambda x: self.alwaysOnOffChanged('on',x))
            self.alwaysOffChbx = QCheckBox('Always Off')
            self.alwaysOffChbx.setChecked(self.data.always_off)
            self.grid_layout.addWidget(self.alwaysOffChbx, 4, 1)
            self.alwaysOffChbx.stateChanged.connect(lambda x: self.alwaysOnOffChanged('off',x))

            self.grid_layout.addWidget(QLabel('Linked pulses'), 5, 0)
            # self.grid_layout.addWidget(QLabel('First pulse\nSecond pulse\nthird'), 4, 1)
            self.grid_layout.addWidget(QLabel('\n'.join(self.data.linked_digital_channels)), 5, 1)
            main_layout.addLayout(self.grid_layout)

            buttons = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
                Qt.Horizontal, self)
            # buttons.
            buttons.accepted.connect(self.accept)
            buttons.rejected.connect(self.reject)
            main_layout.addWidget(buttons)
            self.setLayout(main_layout)

            print('finisht ShutterGUI')

        def alwaysOnOffChanged(self, btn,new_state):
            # print(btn, new_state)
            if btn=='on':
                self.data.always_on = bool(new_state)
                if new_state:
                    self.data.always_off = False
                    self.alwaysOffChbx.setChecked(False)
            if btn == 'off':
                self.data.always_off = bool(new_state)
                if new_state:
                    self.data.always_on = False
                    self.alwaysOnChbx.setChecked(False)

        def nameChanged(self):
            print('shutter-nameChanged')
            self.data.name = self.sender().text()

        def channelChanged(self,new_value):
            print('shutter-channelChanged')
            self.data.channel = int(new_value)

        def startDelayChanged(self,new_value):
            print('shutter-startDelayChanged')
            self.data.start_delay = new_value

        def stopDelayChanged(self,new_value):
            print('shutter-stopDelayChanged')
            self.data.stop_delay = new_value

if __name__ == '__main__':
    import sys
    # pulseGroup = PulseGroup
    app = QApplication(sys.argv)
    sh1 = Shutter()
    mainWindow = sh1.ShutterWidget(data=sh1)

    mainWindow.show()
    sys.exit(app.exec_())



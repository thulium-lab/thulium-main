from PyQt5.QtWidgets import (QApplication, QMenu, QColorDialog, QGridLayout, QVBoxLayout, QHBoxLayout, QDialog, QLabel,
                             QLineEdit, QPushButton, QWidget, QRadioButton, QSpinBox, QCheckBox, QButtonGroup,
                             QErrorMessage)
import sys

class BasicInstance:
    def __init__(self,name='',data={}):
        self.name = name
        self.data = data

        self.ui = self.Widget(data=self)

    class Widget(QWidget):
        def __init__(self,data=None,patent=None):
            super().__init__()
            self.data = data
            self.setLayout(QHBoxLayout())
            self.drawUI()

        def drawUI(self):
            print('draw')
            layout = self.layout()
            self.label_btn = QPushButton(self.data.name)
            self.label_btn.clicked.connect(lambda :self.ChangeInstance(parent=self))
            layout.addWidget(self.label_btn)

            for key, val in self.data.data.items():
                layout.addWidget(QLabel(key))
                l = QLineEdit(val)
                l.editingFinished.connect(lambda :self.dataChanged(key))
                layout.addWidget(l)
            # self.setLayout(layout)
            self.show()

        class ChangeInstance(QDialog):
            def __init__(self, parent=None):
                self.parent = parent
                super().__init__(parent)
                self.setLayout(QVBoxLayout())
                self.initUI()
                self.show()

            def initUI(self):
                layout = self.layout()
                self.name = QLineEdit(self.parent.data.name)
                layout.addWidget(self.name)
                self.keys = QLineEdit(' '.join(self.parent.data.data))
                layout.addWidget(self.keys)
                self.OkBtn = QPushButton('Ok')
                self.OkBtn.clicked.connect(self.okBtnPressed)
                layout.addWidget(self.OkBtn)
                # self.setLayout(layout)

            def okBtnPressed(self):
                print('okBtnPressed')
                self.parent.data.name = self.name.text()
                self.parent.data.data = {key:self.parent.data.data.get(key,'') for key in self.keys.text().strip().split()}
                self.parent.smthChanged()
                self.close()

        def smthChanged(self):
            # print('labelBtnClicked')
            # self.ChangeInstance(parent=self)
            while self.layout().count():
                item = self.layout().takeAt(0)
                item.widget().deleteLater()
            self.drawUI()

        def dataChanged(self,key):
            print(key,self.sender().text())
            self.data.data[key]=self.sender().text()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = BasicInstance('new',{'1':'sdf'})
    ex.ui.show()
    sys.exit(app.exec_())
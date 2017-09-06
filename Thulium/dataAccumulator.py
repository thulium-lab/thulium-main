from PyQt5.QtWidgets import (QApplication, QMenu, QColorDialog, QGridLayout, QVBoxLayout, QHBoxLayout, QDialog, QLabel,
                             QLineEdit, QPushButton, QWidget, QRadioButton, QSpinBox, QCheckBox, QButtonGroup,QTabWidget,
                             QErrorMessage,QMenuBar)
from PyQt5.QtCore import (Qt)
import sys,os, json

config_file = 'dataAcc_config.json'

class BasicInstance:
    def __init__(self,name='',data={'':''}):
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
            self.label_btn.setMaximumWidth(60)
            self.label_btn.setMaximumWidth(60)
            self.label_btn.clicked.connect(lambda :self.ChangeInstance(parent=self))
            layout.addWidget(self.label_btn)

            for key, val in sorted(self.data.data.items()):
                lbl = QLabel(key)
                lbl.setAlignment(Qt.AlignCenter)
                lbl.setMaximumWidth(20)
                lbl.setMinimumWidth(20)
                layout.addWidget(lbl)
                l = QLineEdit(val)
                l.editingFinished.connect(self.dataChanged)
                l.setMaximumWidth(40)
                l.setMinimumWidth(40)
                layout.addWidget(l)
            layout.setAlignment(Qt.AlignLeft)
            # layout.addStretch(1)
            # self.setLayout(layout)
            # self.show()

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
            self.parent().saveConfig()

        def dataChanged(self):
            layout = self.layout()
            i = layout.indexOf(self.sender())
            key = sorted(self.data.data)[i//2-1]
            print(key,self.sender().text())
            self.data.data[key]=self.sender().text()
            self.parent().saveConfig()

class DataPage(QWidget):
    def __init__(self,name,data,parent=None):
        self.parent = parent
        self.name = name
        self.data=[]
        for key in data:
            self.data.append(BasicInstance(name=key,data=data[key]))
        super().__init__()
        self.setLayout(QGridLayout())
        self.drawUI()
        self.show()

    def drawUI(self):
        # clear layout for further dwawing
        layout = self.layout()
        while layout.count():
            item = layout.takeAt(0)
            item.widget().deleteLater()
        for i,item in enumerate(self.data):
            print(i, item.name)
            layout.addWidget(item.Widget(data=item),i,0)
            delBtn = QPushButton('Del')
            delBtn.pressed.connect(self.delSubEntry)
            layout.addWidget(delBtn,i,1)
        addBtn = QPushButton('Add')
        addBtn.pressed.connect(self.addBtnPressed)
        layout.addWidget(addBtn,len(self.data),0)
        w = QWidget()
        w.setLayout(QVBoxLayout())
        w.layout().addStretch(1)
        layout.addWidget(w, len(self.data)+1, 0)

    def delSubEntry(self):
        print('delSubEntry')
        layout = self.layout()
        i = layout.indexOf(self.sender())//2
        # layout = self.layout()
        # item = layout.takeAt(2*i)
        # item.widget().deleteLater()
        # item = layout.takeAt(2*i)
        # item.widget().deleteLater()
        del self.data[i]
        self.drawUI()
        self.saveConfig()

    def saveConfig(self):
        # print(self.parent())
        self.parent.saveConfig()

    def addBtnPressed(self):
        print('addBtnPressed')
        self.data.append(BasicInstance())
        self.drawUI()

    def getDataToConfig(self):
        d = {}
        for item in self.data:
            d[item.name]=item.data
        return {self.name:d}

class DataAccumulator(QTabWidget):
    def __init__(self):
        self.pages = []
        self.load()
        # self.data = {'mag':{'HH':{'I':'12'},'AHH':{'B':'4'},'gf':{'I':'10'}}}
        super().__init__()
        self.initUI()

    def load(self):
        if not os.path.exists(config_file):
            print('create folder ', config_file)
            self.data = {}
            with open(config_file, 'w') as f:
                json.dump(self.data, f)
        else:
            with open(config_file, 'r') as f:
                print('config_load')
                self.data = json.load(f)

    def saveConfig(self):
        print('saveConfig')
        d = {}
        for i in range(self.count()):
            d.update(self.widget(i).getDataToConfig())
        print(d)
        with open(config_file, 'w') as f:
            json.dump(d, f)


    def initUI(self):
        # menu_bar = QMenuBar()
        # new_page_menu = QMenu('Pages')
        # menu_bar.addMenu(new_page_menu)
        # new_page_menu.addAction('New page')
        # self.layout().setMenuBar(menu_bar)
        for key in self.data:
            new_page = DataPage(name=key,data=self.data[key],parent=self)
            self.addTab(new_page,key)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    # ex = BasicInstance('new',{'1':'sdf'})
    ex = DataAccumulator()
    ex.show()
    sys.exit(app.exec_())
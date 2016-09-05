from PySide import QtCore, QtGui
import numpy as np
import time
import os
from hdfUtils import *
class saver(QtGui.QWidget):
    def __init__(self, parent=None, category = 'Sensitivity'):
        QtGui.QWidget.__init__(self, parent)
        self.category = category
        self.initUI()

    def initUI(self):

        self.VBOX = QtGui.QVBoxLayout()
        self.itemnumber = QtGui.QSpinBox()
        restore = QtGui.QHBoxLayout()
        restore.addWidget(self.itemnumber)
        self.checkRestore = QtGui.QCheckBox('Restore')
        restore.addWidget(self.checkRestore)
        self.VBOX.addLayout(restore)
        self.savebtn = QtGui.QPushButton('Save')
        self.savebtn.setMinimumHeight(50)
        self.VBOX.addWidget(self.savebtn)
        self.paramswindow = QtGui.QTextEdit('Loaded parameters...')
        self.paramswindow.setReadOnly(True)

        self.commentsWindow = QtGui.QTextEdit('Comments...')

        self.VBOX.addWidget(self.paramswindow)
        self.VBOX.addWidget(self.commentsWindow)

        self.setLayout(self.VBOX)


        self.setMaximumWidth(200)

    def restore(self):

        if os.path.exists(self.category):
            filename = str(self.itemnumber.value())
            fp = os.path.join(self.category, filename)

            if os.path.exists(fp+'.hdf5'):
                data = readhdf(fp)
                return data

            else:
                return None

        else:
            print 'Error, no files in this category'
            return None

    def save(self, data):

        if not os.path.exists(self.category):
            os.makedirs(self.category)

        i = 0
        while os.path.exists(os.path.join(self.category,str(i)+'.hdf5')):
            i+=1
        print i, 'filename'
        filename = str(i)
        fp = os.path.join(self.category, filename)
        writehdf(fp,data)









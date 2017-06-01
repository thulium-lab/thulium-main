from PyQt5.QtCore import (QLineF, QPointF, QRectF, Qt, QTimer,QObject,pyqtSignal,pyqtSlot)

class c1(QObject):
    sig1 = pyqtSignal()
    def emit(self):
        self.sig1.emit()

class c2():
    def __init__(self,signal):
        signal.connect(self.handle)
    def handle(self):
        print('Handled')


if __name__ == '__main__':
    i1 = c1()
    i2 = c2(i1.sig1)
    i1.emit()
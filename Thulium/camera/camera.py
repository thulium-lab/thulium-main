import os, sys
import numpy as np
import matplotlib
matplotlib.use('Qt5Agg', force=True)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from PyQt5.QtCore import (QLineF, QPointF, QRectF, Qt, QTimer)
from PyQt5.QtGui import (QBrush, QColor, QPainter)
from PyQt5.QtWidgets import (QApplication, QGraphicsView, QGraphicsScene, QGraphicsItem, QScrollArea, QFrame,
                             QGridLayout, QVBoxLayout, QHBoxLayout, QSizePolicy, QMainWindow, QDialog, QLabel,
                             QLineEdit, QPushButton, QWidget, QComboBox, QRadioButton, QSpinBox, QCheckBox,
                             QTabWidget, QFileDialog, QMessageBox, QDoubleSpinBox)

import time
import re

from Camera.STT_CAM import Camera


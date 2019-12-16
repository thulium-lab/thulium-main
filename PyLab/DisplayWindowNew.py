import os, sys, time, datetime, json, scipy.misc, threading, ctypes, math #png,
import re
import pyqtgraph as pg
import pyqtgraph.dockarea as da
import pyqtgraph.exporters
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
import pickle
import pymongo, datetime
from pymongo import MongoClient
# from bson.objectid import ObjectId

from matplotlib.pyplot import imread
from PyQt5.QtCore import (QTimer, Qt,QRect)
from PyQt5.QtGui import (QIcon, QFont,QTransform)
from PyQt5.QtWidgets import (QApplication, QDesktopWidget, QHBoxLayout, QLabel, QWidget, QSpinBox, QCheckBox,
                             QMessageBox,QVBoxLayout,QHeaderView, QPushButton,QComboBox, QLineEdit,QTableWidget,
                             QTableWidgetItem,QGridLayout,QDockWidget,QAction,QInputDialog,QTabWidget)

sys.path.append(r'D:\!Data')

import thulium_python_lib.usefull_functions as usfuncs
import thulium_python_lib.image_processing_new as impr
import  thulium_python_lib.fit_func_lib as fit_func_lib
myAppID = u'LPI.Camera' # arbitrary string
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myAppID)

pg.setConfigOptions(imageAxisOrder='row-major')

ds_dir = r'D:\!Data\2016_04_22\01 T no_ramp a=-6 f=363.9 b=0.8'

import socket
HOST, PORT = "192.168.1.59", 9999
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(0.01)

from collections import OrderedDict
from Lib import *
# from scipy.misc import imread
import imageio

def gaussian(x,N,x0,sigma, background):
    """Returns value of a 1D-gaussian with the given parameters"""
    return N / (sigma * np.sqrt(np.pi)) * np.exp(-(x - x0)**2/(sigma**2)) + background

CameraLineDict = OrderedDict([
    ('Channel',['MCB','D16',['D%i'%i for i in np.arange(8,32)],60]),
    ('Image number', ['MCB', '0', [str(i) for i in range(2)], 30]),
    ('do fits',['MChB',0,30]),
    ('subs bgnd',['MChB',0,30])
])

FIT_TABLE_PARAMS = ["N","Nr","X0","X0r","W","Wr","bgnd"]

CAMERA_TABLE_PARAMS = ["Exp","Gain","Binning","power,mW","width,um","delta,MHz"]

def calculateNrCoefficient(gain=100, exposure=300, power=2.7, width=2.27, delta = 0):
    angle = 1. / 225
    Isat = 0.18
    hw = 6.6 * 3 / 0.41 * 1e-11
    gamma = 10
    s1 = 2 * power / np.pi / width**2 / Isat
    rho = s1 / 2 / (1 + s1 + (2 * delta / gamma)**2)
    return 9.69 * 0.001 / 100 / exposure / 2.718281828 ** (3.85 / 1000 * gain) / gamma / hw / angle / rho


class ImageWidget(QWidget):

    def __init__(self,parent=None,globals=None,
                 config_file='cam_config.json',
                 image_name='image'):

        self.config_file = config_file  # where to save config
        self.image_name = image_name    # name of the image in parent.globals)
        self.parent = parent
        self.globals = globals
        self.config = {"do_fits":True,"subs_bgnd":True,"roi_size":[100,100],"roi_ll":[0,0],
                       "camera_params":[150,20,2,1,500,10],
                       "pixel_size":3,
                       "channel":"D16",
                       "image_number":"0",
                       "list_of_image":["0","1"]}
        super().__init__()
        # default. All theese will be downloaded from config file
        self.nAtoms = impr.N_atoms(gain=324, exposure=909, power=2.42, width=2.43, delta=7e6)
        self.realSize = impr.real_size

        self.load() # config loading
        self.initUI()

    def initUI(self):

        main_layout = QVBoxLayout()

        self.window = pg.GraphicsLayoutWidget()
        image_plot = self.window.addPlot()
        self.img = pg.ImageItem()
        self.img.setZValue(1)
        image_plot.addItem(self.img)
        self.image = np.zeros((200,200))
        # self.parent.globals[self.image_name] = imread(default_image).T #initialise picture
        self.img.setImage(self.image)
        self.roi = pg.ROI(self.config["roi_ll"], self.config["roi_size"], pen=pg.mkPen('g', width=1))  # , style=pg.QtCore.Qt.DotLine
        self.roi.addScaleHandle([1, 1], [0, 0])
        # self.roi.addScaleHandle([1, 0.5], [0, 1])
        image_plot.addItem(self.roi)
        self.roi.setZValue(100)
        self.hist = pg.HistogramLUTItem()
        self.hist.setImageItem(self.img)
        self.hist.setHistogramRange(0, 0.6)
        self.hist.setLevels(0, 0.6)
        self.hist.gradient.setColorMap(pg.ColorMap(np.array([0., 0.25, 0.5, 0.75, 1.]),
                                                   np.array([[255, 255, 255, 255], [0, 0, 255, 255],
                                                             [0, 0, 0, 255], [255, 0, 0, 255], [255, 255, 0, 255]],
                                                            dtype=np.uint8)))
        self.window.addItem(self.hist)
        self.img.setLookupTable(self.hist.getLookupTable(n=256))
        self.roi.sigRegionChangeFinished.connect(self.updateROI)
        main_layout.addWidget(self.window)

        chbx_layout = QHBoxLayout()  # basically config and info layout
        # self.image_number = MyComboBox()
        self.channel_box = MyComboBox(items=['D%i'%i for i in np.arange(8,32)],
                                      current_text=self.config["channel"],
                                      current_text_changed_handler=self.updateChannel,
                                      max_width=60)
        chbx_layout.addWidget(self.channel_box)
        chbx_layout.addWidget(QLabel("channel"))
        self.image_number_box = MyComboBox(items=self.config["list_of_image"],
                                      current_text=self.config["image_number"],
                                      current_text_changed_handler=self.updateImageNumber,
                                      max_width=60)
        chbx_layout.addWidget(self.image_number_box)
        chbx_layout.addWidget(QLabel("image number"))
        self.fit_chbx = MyCheckBox("do fits", is_checked=self.config["do_fits"],
                                   handler=lambda state: self.chbxClicked('do_fits', state))
        chbx_layout.addWidget(self.fit_chbx)

        self.bgnd_chbx = MyCheckBox("subs bgnd", is_checked=self.config["subs_bgnd"],
                                    handler=lambda state: self.chbxClicked("subs_bgnd", state))
        chbx_layout.addWidget(self.bgnd_chbx)

        main_layout.addLayout(chbx_layout)

        data_layout = QVBoxLayout()



        self.fit_table = QTableWidget(3, len(FIT_TABLE_PARAMS))
        self.fit_table.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)
        self.fit_table.horizontalHeader().setMinimumSectionSize(40)
        self.fit_table.setVerticalHeaderLabels(["p",'x', 'y'])
        font = QFont()
        font.setPointSize(20)
        self.fit_table.setFont(font)
        self.fit_table.setFixedHeight(120)
        # self.fit_table.cellEntered.connect(self.paramTableChanged)
        # print('other params in MeasFolder', self.data["other_params"])
        for i, param in enumerate(FIT_TABLE_PARAMS):
            self.fit_table.setItem(0, i, QTableWidgetItem(param))
            self.fit_table.setItem(1, i, QTableWidgetItem("-"))
            self.fit_table.setItem(2, i, QTableWidgetItem("-"))
        self.fit_table.horizontalHeader().hide()

        data_layout.addWidget(self.fit_table)

        self.camera_table = QTableWidget(2, len(CAMERA_TABLE_PARAMS))
        self.camera_table.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)
        self.camera_table.horizontalHeader().setMinimumSectionSize(40)
        self.camera_table.setVerticalHeaderLabels(['p', 'v'])
        self.camera_table.setFixedHeight(80)
        # self.fit_table.cellEntered.connect(self.paramTableChanged)
        # print('other params in MeasFolder', self.data["other_params"])
        for i, param in enumerate(CAMERA_TABLE_PARAMS):
            self.camera_table.setItem(0, i, QTableWidgetItem(param))
            if i < len(self.config["camera_params"]):
                v = self.config["camera_params"][i]
            else:
                v = "0"
            self.camera_table.setItem(1, i, QTableWidgetItem(v))
        self.camera_table.horizontalHeader().hide()
        self.camera_table.cellChanged.connect(self.cameraTableChanged)
        data_layout.addWidget(self.camera_table)

        main_layout.addLayout(data_layout)

        self.setLayout(main_layout)
        self.setMinimumHeight(500)
        self.setMaximumHeight(700)
        self.setMinimumWidth(500)

    def updateChannel(self,new_channel):
        self.config["channel"] = new_channel
        self.save_config()

    def updateImageNumber(self,new_number):
        self.config["image_number"] = new_number
        self.save_config()

    def updateListOfImage(self,new_list):
        self.config["list_of_image"] = new_list
        self.image_number_box.clear()  # delete all items from comboBox
        self.image_number_box.addItems(new_list)
        if self.config["image_number"] not in new_list:
            self.config["image_number"] = "0"
        self.image_number_box.setCurrentText(self.config["image_number"])
        self.save_config()

    def getNumberOfImages(self):
        return len(self.config["list_of_image"])

    def cameraTableChanged(self,row,col):
        print(row, col)
        self.config["camera_params"][col] = self.camera_table.item(row,col).text()
        self.save_config()

    def newCameraSettings(self): # not used now, but may increase spead
        self.nAtoms = impr.N_atoms(gain=int(self.gain.text()),
                                   exposure=int(self.exp.text()),
                                   power=float(self.power.text()),
                                   delta=float(self.delta.text())*1e6, width=2.43)
        self.realSize = impr.real_size(binning=int(self.binn.text()))
        return

    def load(self):
        try:
            with open(self.config_file,'r') as f:
                config = json.load(f)
        except json.decoder.JSONDecodeError:
            print('ERROR in reading ', self.config_file)
            return
        except FileNotFoundError:
            print('File not yet exist')
            return
        self.config.update(config["camera"])

    def save_config(self):
        try:
            with open(self.config_file, 'r') as f:
                old_config = json.load(f)
        except json.decoder.JSONDecodeError:
            old_config = {}
        except FileNotFoundError:
            old_config = {}
            print('File not yet exist')
        old_config["camera"].update(self.config)
        with open(self.config_file, 'w') as f:
            try:
                json.dump(old_config,f)
            except: # find what error does it raise when cannot dump
                json.dump(old_config, f)
                QMessageBox.warning(None, 'Message', "can not dump config to json, old version will be saved",
                                    QMessageBox.Ok)

    def updateROI(self):
        # print('updateRoi')
        self.roi_center = [int(self.roi.pos()[0]),int(self.roi.pos()[1])]
        self.roi_size = [int(self.roi.size()[0]),int(self.roi.size()[1])]
        self.config['roi_ll'] = self.roi_center
        self.config['roi_size'] = self.roi_size
        self.save_config()

    def chbxClicked(self,attribute,state):
        self.config[attribute] = bool(state)
        self.save_config()
        # print(attribute, state)

    def getCameraChannel(self):
        return self.config["channel"]

    def updateImage(self):
        # print("--imageWidget -- updateImage")
        # global current_data_index
        # check if row is still correct
        if (np.array(self.config["roi_ll"]) < 0).any() or not (np.array(self.config["roi_ll"])+np.array(self.config["roi_size"]) < self.parent.image.shape[::-1]).all():
            self.config["roi_ll"]=[0,0]
            self.config["roi_size"]=self.parent.image.shape[::-1]
            # print(self.roi_size,self.globals['image'].shape[::-1])
            self.roi.setPos(*self.config["roi_ll"])
            self.roi.setSize(self.config["roi_size"])

        self.roi_image = np.array(self.parent.image[self.config["roi_ll"][1]:self.config["roi_ll"][1]+self.config["roi_size"][1],
                                      self.config["roi_ll"][0]:self.config["roi_ll"][0]+self.config["roi_size"][0]])
        self.current_fit_data = []
        self.fit_status = True
        # print("befor do fits")
        # print(self.config)
        if self.config["do_fits"]:
            # print("ind do fits")
            # print(self.roi_image.shape)
            tot = np.sum(self.roi_image )
            # print(tot)
            # print(self.config["camera_params"])
            gain = float(self.config["camera_params"][CAMERA_TABLE_PARAMS.index("Gain")])
            exposure = float(self.config["camera_params"][CAMERA_TABLE_PARAMS.index("Exp")])
            power = float(self.config["camera_params"][CAMERA_TABLE_PARAMS.index("power,mW")])
            width = float(self.config["camera_params"][CAMERA_TABLE_PARAMS.index("width,um")])
            delta = float(self.config["camera_params"][CAMERA_TABLE_PARAMS.index("delta,MHz")])
            # print(gain,exposure,power,width,delta)
            norm_coeff = calculateNrCoefficient(gain=gain, exposure=exposure, power=power, width=width, delta=delta)
            # print(6)
            pixel_size = float(self.config["camera_params"][CAMERA_TABLE_PARAMS.index("Binning")])*self.config["pixel_size"]
            # print(norm_coeff,pixel_size)
            bgnds = []
            for i in [0,1]:
                try:
                    d = np.sum(self.roi_image,i)
                    # print(d)
                    # print(len(d),self.roi_image.shape)
                    popt,pcov = curve_fit(gaussian,np.arange(len(d)),d,p0=[tot,np.argmax(d),10,0])
                    # print(popt)
                    x0 = popt[1]+self.config["roi_ll"][i]
                    self.current_fit_data.extend([popt[0],popt[0]*norm_coeff,x0,x0*pixel_size,popt[2],
                                     popt[2]*pixel_size,popt[3]/self.roi_image.shape[i-1]])
                    bgnds.append(popt[-1]/self.roi_image.shape[i-1])
                except Exception as e:
                    print("can not find fit", i)
                    print(e)
                    self.current_fit_data.extend([0]*len(FIT_TABLE_PARAMS))
                    self.fit_status = False

            self.parent.data_table = self.parent.data_table.append(pd.Series(self.current_fit_data,index=self.parent.data_table.columns),ignore_index=True)
            # print("data_table",self.data_table)
            self.updateFitTable()

        # update image based on fits
        # print(1)
        if self.config["do_fits"] and self.config["subs_bgnd"] and self.fit_status:
            self.roi_image -= np.mean(bgnds)
            self.parent.image[self.config["roi_ll"][1]:self.config["roi_ll"][1] + self.config["roi_size"][1],
                    self.config["roi_ll"][0]:self.config["roi_ll"][0] + self.config["roi_size"][0]] = self.roi_image
        # show image
        # print(2)
        self.img.setImage(self.parent.image,autoRange=True, autoLevels=False,autoHistogramRange=False,autoDownsample=True)
        # print("finished updating")
        return self.fit_status

    def updateFitTable(self):
        for i, param in enumerate(FIT_TABLE_PARAMS):
            coeff = 1
            if param == "Nr":
                coeff = 1e-6
            self.fit_table.setItem(1, i, QTableWidgetItem("%.2f"%(self.current_fit_data[i]*coeff)))
            self.fit_table.setItem(2, i, QTableWidgetItem("%.2f"%(self.current_fit_data[i+len(FIT_TABLE_PARAMS)]*coeff)))

    def saveImage(self,image_name):
        print('Image %s saved at '%(image_name), datetime.datetime.now().time())
        imageio.imwrite(image_name,self.roi_image)

class PlotWidget(QWidget):

    def __init__(self,parent=None,config_file='cam_config.json',
                 chbx_config_name="plot0_chbx"):
        self.config_file = config_file  # where to save config
        self.parent = parent
        self.chbx_config_name=chbx_config_name
        super().__init__()
        self.config = {**{key+'_x':False for key in FIT_TABLE_PARAMS},**{key+'_y':False for key in FIT_TABLE_PARAMS}}
        self.config["n_points"]=200
        self.curves = {}
        self.load()
        self.initUI()

    def initUI(self):
        main_layout = QHBoxLayout()

        menu_layout = QVBoxLayout()
        self.chbx_layout = QGridLayout()
        for i,key in enumerate(FIT_TABLE_PARAMS):
            w1 = MyCheckBox(key+'_x',is_checked=self.config[key+'_x'],
                                   handler=self.chbxClicked)
            w2 = MyCheckBox(key + '_y', is_checked=self.config[key+'_y'],
                            handler=self.chbxClicked)
            self.chbx_layout.addWidget(w1, i, 0)
            self.chbx_layout.addWidget(w2, i, 1)

        self.chbx_layout.setContentsMargins(5, 2, 5, 2)
        menu_layout.addLayout(self.chbx_layout)
        menu_layout.addStretch(1)
        self.n_point_box = MyIntBox(value=self.config["n_points"],validator=QIntValidator(10,10000),
                     text_edited_handler=self.NpointsChanged,
                     text_changed_handler=self.NpointsChanged,
                                    max_width=30)
        menu_layout.addWidget(self.n_point_box)
        main_layout.addLayout(menu_layout)

        self.plot = pg.PlotWidget()
        self.createCurves()
        main_layout.addWidget(self.plot)
        self.setLayout(main_layout)

    def NpointsChanged(self):
        self.config["n_points"] = self.n_point_box.value()
        self.save_config()

    def createCurves(self):
        self.plot.addLegend()
        n_plots = np.sum([self.config[key] > 0 for key in self.config])
        i = 0
        for key in self.config:
            if key in ["n_points"]:
                continue
            if self.config[key]:  # this parameter is set to be displayed
                self.curves[key] = self.plot.plot(np.array([]), name=key, pen=(i, n_plots))
                i += 1

    def chbxClicked(self):
        # print("--plotWidget -- chbxClicked")
        for i,key in enumerate(FIT_TABLE_PARAMS):
            self.config[key+'_x'] = self.chbx_layout.itemAtPosition(i,0).widget().getValue()
            self.config[key+'_y'] = self.chbx_layout.itemAtPosition(i, 1).widget().getValue()
        for key in self.curves:
            self.plot.removeItem(self.curves[key])
        for item in self.plot.getPlotItem().legend.items:
            self.plot.getPlotItem().legend.removeItem(item)
        del self.plot.getPlotItem().legend
        self.plot.clear()
        # self.plot.getPlotItem().legend.items = []
        # print("legend items",self.plot.getPlotItem().legend.items)
        # del self.plot.getPlotItem().legend
        # self.plot.removeItem(self.plot.LegendItem())
        # for key in self.curves:
        #     del self.curves[key]
        self.curves = {}
        self.createCurves()
        self.save_config()

    def updatePlot(self):
        # print("--plotWidget -- updatePlot")
        # print(self.parent.data_table)
        for key in self.config:
            if key in ["n_points"]:
                continue
            # print(key,self.config[key])
            if self.config[key] and len(self.parent.data_table):  # this parameter is set to be displayed
                # print(key, "to plot")
                # print(self.parent.data_table[key+self.parent.camera_number])
                # print("points_to_show",self.parent.data_table[key+self.parent.camera_number][-self.config["n_points"]:])
                data = self.parent.data_table[key+self.parent.camera_number][-self.config["n_points"]:]
                xs = np.array(data.index)
                ys = data.values
                self.curves[key].setData(xs,ys)
                self.plot.setXRange(min(xs),max(xs))
                #

    def load(self):
        try:
            with open(self.config_file,'r') as f:
                config = json.load(f)
        except json.decoder.JSONDecodeError:
            print('ERROR in reading ', self.config_file)
            return
        except FileNotFoundError:
            print('File not yet exist')
            return
        self.config.update(config[self.chbx_config_name])

    def save_config(self):
        try:
            with open(self.config_file, 'r') as f:
                old_config = json.load(f)
        except json.decoder.JSONDecodeError:
            old_config = {}
        except FileNotFoundError:
            old_config = {}
            print('File not yet exist')
        old_config[self.chbx_config_name].update(self.config)
        with open(self.config_file, 'w') as f:
            try:
                json.dump(old_config,f)
            except: # find what error does it raise when cannot dump
                json.dump(old_config, f)
                QMessageBox.warning(None, 'Message', "can not dump config to json, old version will be saved",
                                    QMessageBox.Ok)

class CameraWidget(da.DockArea):

    def __init__(self,parent=None,globals=None,signals=None,config_file='cam_config.json',image_name='image',
                 camera_number="1",image_folder=r"Z:\CameraTop"):
        super(CameraWidget, self).__init__()
        self.parent = parent
        self.globals = globals
        self.signals = signals
        self.image_fodler = image_folder
        self.config_file = config_file
        self.camera_number = camera_number
        self.config = {}
        self.image_name = image_name
        self.load()
        self.data_table = pd.DataFrame(columns=[s +"_x" + self.camera_number for s in FIT_TABLE_PARAMS] +
                                               [s +"_y" + self.camera_number for s in FIT_TABLE_PARAMS], dtype=float)


        self.initUI()
        self.timer = QTimer()
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.cycleFinishedHandler)
        self.waitForImageTimer = QTimer()
        self.waitForImageTimer.setInterval(10)
        self.waitForImageTimer.timeout.connect(self.processImage)
        self.waitForFirstImageTimer = QTimer()
        self.waitForFirstImageTimer.setInterval(100)
        self.waitForFirstImageTimer.timeout.connect(self.startImageReadings)
        self.waitAfterScanStarted = QTimer()
        self.waitAfterScanStarted.setInterval(100)
        self.waitAfterScanStarted.timeout.connect(self.deleteAllImaged)

        # self.onScanStarted()
        # self.timer.start()
        if self.signals:
            self.signals.scanCycleFinished.connect(self.cycleFinishedHandler)
            self.signals.scanStarted.connect(self.onScanStarted)
            self.signals.pulsesChanged.connect(self.onPulsesChanged)
            # self.signals.scanCycleFinished.connect(self.cycleFinishedHandler)

    def initUI(self):
        self.setWindowTitle(self.image_name)
        # self.setWindowIcon(QIcon('DigitalPulses\display_image_icon.jpg'))
        # self.setWindowState(Qt.WindowMaximized)
        self.image_dock = da.Dock("Image")
        self.plot1_dock = da.Dock("Plot1")
        self.plot2_dock = da.Dock("Plot2")
        self.area.addDock(self.image_dock, 'top')
        self.area.addDock(self.plot1_dock,"bottom",self.image_dock)
        self.area.addDock(self.plot2_dock,"below",self.plot1_dock)

        self.image_widget = ImageWidget(parent=self,globals=self.globals,config_file=self.config_file,
                                        image_name=self.image_name)
        self.image_dock.addWidget(self.image_widget)
        self.plot1_widget = PlotWidget(parent=self,config_file=self.config_file,
                                       chbx_config_name="plot1_chbx")
        self.plot1_dock.addWidget(self.plot1_widget)
        self.plot2_widget = PlotWidget(parent=self, config_file=self.config_file,
                                       chbx_config_name="plot2_chbx")
        self.plot2_dock.addWidget(self.plot2_widget)

    def onPulsesChanged(self):
        camera_channel = self.image_widget.getCameraChannel()
        start_times = []
        if camera_channel in self.globals["pulses"]:
            print("Camera", self.camera_number, "pulse",self.globals["pulses"][camera_channel])
            for pulse in self.globals["pulses"][camera_channel]:
                if pulse[1] == 1: # start exposition
                    start_times.append(pulse[0])
            if self.image_widget.getNumberOfImages() != len(start_times):
                self.image_widget.updateListOfImage([str(i) for i in range(len(start_times))])
                self.number_of_images = len(start_times)
                self.waitForFirstImageTimer.setInterval(min(start_times))
                return
                columns = []
                for i in range(len(start_times)):
                    columns.extend(["C%s_%i_"%(self.camera_number,i) + s +"_x" for s in FIT_TABLE_PARAMS] +
                                               ["C%s_%i_"%(self.camera_number,i) + s +"_y" for s in FIT_TABLE_PARAMS])
                self.data_table = pd.DataFrame(columns=columns, dtype=float)

    def startImageReadings(self):
        self.waitForFirstImageTimer.stop()
        self.handled_images = 0
        print("New image should arrive", self.number_of_images)
        self.n_waits = 0
        self.waitForImageTimer.start()

    def onScanStarted(self):
        print("onScanStarted")#,self.data_table.columns
        self.waitForImageTimer.stop()
        if self.globals and "scan_running_table" in self.globals:
            for fit_param in self.data_table.columns:
                self.globals["scan_running_table"][fit_param] = 0.0
        self.waitAfterScanStarted.start()

    def deleteAllImaged(self):
        self.waitAfterScanStarted.stop()
        if self.camera_number == "0":
            print("camera - delite all images at",datetime.datetime.now())
        files = os.listdir(self.image_fodler)
        files = [f for f in files if f.endswith('png') or f.endswith('tiff')]
        for f in files:
            os.remove(os.path.join(self.image_fodler,f))

    def cycleFinishedHandler(self,finished_shot):
        # self.finished_shot = finished_shot
        # self.waitForFirstImageTimer.start()
        # old code
        if self.camera_number=="0":
            print("camera cycle_finished at", datetime.datetime.now())
        # print("camera - cycleFinishedHandeler")
        self.finished_shot = finished_shot
        self.n_waits = 0
        self.waitForImageTimer.start()

    # def processImage(self):
    #     self.waitForImageTimer.stop()
    #     files = os.listdir(self.image_fodler)
    #     files = [f for f in files if f.endswith('png') or f.endswith('tiff')]
    #     if files == []:
    #         # start timer to wait for image
    #         self.n_waits += 1
    #         self.waitForImageTimer.start()
    #         return
    #     else:
    #         # if self.camera_number == "0":
    #         #     print("camera image found at", datetime.datetime.now())
    #         last_handled = self.handled_images
    #         for i in range(self.handled_images,len(files)):
    #             f = files[i]
    #             try:
    #                 self.image = imageio.imread(os.path.join(self.image_fodler,f))
    #             except (PermissionError,IndexError):
    #                 self.n_waits += 1
    #                 self.waitForImageTimer.start()
    #                 self.handled_images = last_handled
    #                 return
    #             self.image = self.image / 2**16
    #             update_image_status = self.image_widget.updateImage()
    #             if update_image_status:
    #                 self.plot1_widget.updatePlot()
    #                 self.plot2_widget.updatePlot()
    #             last_handled = i
    #         self.handled_images = last_handled+1
    #         if self.handled_images == self.image_widget.getNumberOfImages():# all expected images are handled
    #             for f in files:
    #                 os.remove(os.path.join(self.image_fodler, f))
    #
    #         if self.globals and "scan_running_data" in self.globals and self.finished_shot>0:
    #             image_folder_name = os.path.join(self.globals["scan_running_data"]["day_folder"],
    #                                              self.globals["scan_running_data"]["folder_to_save"])
    #             meas_num = self.finished_shot
    #             if update_image_status:
    #                 # print(self.data_table.iloc[-1])
    #                 for fit_param in self.data_table.columns:
    #                     # print(meas_num,fit_param,self.data_table.iloc[-1][fit_param])
    #                     self.globals["scan_running_table"].at[meas_num,fit_param] = self.data_table.iloc[-1][fit_param]
    #                 # print(self.globals["scan_running_table"])
    #             # print(self.globals["scan_running_table"],self.globals["scan_params"])
    #             image_name = "cam"+self.camera_number + "_"
    #             image_name += '_'.join(["%s=%f"%(key,self.globals["scan_running_table"].loc[int(meas_num),key])
    #                                   for key in self.globals["scan_params"]["low"]])
    #             image_name += '_shot_n=%i.png'%self.globals["scan_running_table"].loc[int(meas_num),"shot_n"]
    #             image_name = os.path.join(image_folder_name,image_name)
    #             self.image_widget.saveImage(image_name)
    #     # for f in files:
    #     #     os.remove(os.path.join(self.image_fodler,f))

    def processImage(self):
        self.waitForImageTimer.stop()
        files = os.listdir(self.image_fodler)
        files = [f for f in files if f.endswith('png') or f.endswith('tiff')]
        if files == []:
            # start timer to wait for image
            self.n_waits += 1
            self.waitForImageTimer.start()
            return
        else:
            if self.camera_number == "0":
                print("camera image found at", datetime.datetime.now())
            f = files[-1]
            try:
                self.image = imageio.imread(os.path.join(self.image_fodler,f))
            except (PermissionError,IndexError):
                self.n_waits += 1
                self.waitForImageTimer.start()
                return
            self.image = self.image / 2**16
            update_image_status = self.image_widget.updateImage()
            if update_image_status:
                self.plot1_widget.updatePlot()
                self.plot2_widget.updatePlot()

            if self.globals and "scan_running_data" in self.globals and self.finished_shot>0:
                image_folder_name = os.path.join(self.globals["scan_running_data"]["day_folder"],
                                                 self.globals["scan_running_data"]["folder_to_save"])
                meas_num = self.finished_shot
                if update_image_status:
                    # print(self.data_table.iloc[-1])
                    for fit_param in self.data_table.columns:
                        # print(meas_num,fit_param,self.data_table.iloc[-1][fit_param])
                        self.globals["scan_running_table"].at[meas_num,fit_param] = self.data_table.iloc[-1][fit_param]
                    # print(self.globals["scan_running_table"])
                # print(self.globals["scan_running_table"],self.globals["scan_params"])
                image_name = "cam"+self.camera_number + "_"
                image_name += '_'.join(["%s=%f"%(key,self.globals["scan_running_table"].loc[int(meas_num),key])
                                      for key in self.globals["scan_params"]["low"]])
                image_name += '_shot_n=%i.png'%self.globals["scan_running_table"].loc[int(meas_num),"shot_n"]
                image_name = os.path.join(image_folder_name,image_name)
                self.image_widget.saveImage(image_name)
        for f in files:
            os.remove(os.path.join(self.image_fodler,f))

    def load(self):
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
        except json.decoder.JSONDecodeError:
            print('ERROR in reading ', self.config_file)
            return
        except FileNotFoundError:
            print('File not yet exist')
            return
        self.config.update(config)

    def save_config(self):
        try:
            with open(self.config_file, 'r') as f:
                old_config = json.load(f)
        except json.decoder.JSONDecodeError:
            old_config = {}
        except FileNotFoundError:
            old_config = {}
            print('File not yet exist')
        old_config.update(self.config)
        with open(self.config_file, 'w') as f:
            try:
                json.dump(old_config, f)
            except:  # find what error does it raise when cannot dump
                json.dump(old_config, f)
                QMessageBox.warning(None, 'Message', "can not dump config to json, old version will be saved",
                                    QMessageBox.Ok)

class SingleAnalogInDisplayWidget(QTabWidget):#da.DockArea

    class AnalogMain(QWidget):

        def __init__(self, parent=None, globals=None, signals=None,):
            super().__init__(parent)
            self.globals = globals
            self.signals = signals
            self.parent = parent
            self.initUI()

        def initUI(self):
            main_layout = QVBoxLayout()

            hor_layout = QHBoxLayout()
            self.channel_box = MyComboBox(items=self.parent.getAvailableChannels(),
                                          current_text=self.parent.channel,
                                          current_text_changed_handler=self.channelChanged, max_width=100
                                          )
            hor_layout.addWidget(self.channel_box)
            self.pulse_box = MyIntBox(validator=QIntValidator(0,9),value=self.parent.pulse,
                                      text_edited_handler=self.pulseChanged,
                                      text_changed_handler=self.pulseChanged)
            hor_layout.addWidget(self.pulse_box)
            self.active_box = MyCheckBox(is_checked=self.parent.is_active,handler=self.isActiveChanged)
            hor_layout.addWidget(self.active_box)
            hor_layout.addWidget(QLabel("is_active"))
            hor_layout.addStretch(1)
            save_btn = MyPushButton(name="Save",handler=self.parent.saveChannel)
            hor_layout.addWidget(save_btn)
            del_btn = MyPushButton(name="Delete",handler=self.parent.delChannel)
            hor_layout.addWidget(del_btn)
            add_btn = MyPushButton(name="add new channel", handler=self.parent.addChannel)
            hor_layout.addWidget(add_btn)

            main_layout.addLayout(hor_layout)

            self.plot = pg.PlotWidget()
            self.curve = self.plot.plot(np.array([]))
            main_layout.addWidget(self.plot)
            main_layout.addWidget(QLabel("Parameters, 'data' is reading array"))
            self.param_line = MyLineEdit(name=self.getParamLineFromParams(),
                                         editing_finished_handler=self.paramLineChanged)
            main_layout.addWidget(self.param_line)
            main_layout.addWidget(QLabel("Fit function"))
            self.fit_func_line = MyLineEdit(name=self.parent.fit_func_str,
                                         editing_finished_handler=self.fitFuncLineChanged)
            main_layout.addWidget(self.fit_func_line)

            self.setLayout(main_layout)
            self.setMaximumWidth(500)
            self.setMaximumHeight(400)

        def isActiveChanged(self):
            self.parent.is_active = self.active_box.getValue()

        def pulseChanged(self):
            self.parent.pulse = self.pulse_box.getValue()

        def channelChanged(self,new_channel):
            print('--analogMain - channelChanged', new_channel)
            self.parent.channel = new_channel

        def getParamLineFromParams(self):
            """generates parameters line based on dictionary of param:{'value':value,'to_plot':bool}
            if value is None, than param is to be determined from fit, else value is str to execute"""
            pl = []
            for param, data in self.parent.params.items():
                if data["value"] != None:
                    pl.append("%s=%s"%(param,data["value"]))
                else:
                    pl.append(param)
            return ', '.join(pl)

        def paramLineChanged(self):
            param_dict = {}
            for line in self.param_line.text().split(','):
                line = line.strip()
                if '=' not in line: # param value get from fit
                    param = line
                    value = None
                else:
                    param,value = map(str.strip,line.split('='))
                    if value == '': # if somewhy there is nothing after =, than param to get from fit
                        value = None
                if param in self.parent.params:
                    to_plot = self.parent.params[param]["to_plot"]
                else:
                    to_plot = False
                param_dict[param] = {"value":value,"to_plot":to_plot}
            self.parent.params = param_dict

        def fitFuncLineChanged(self):
            new_fit_func_line = self.fit_func_line.text()
            # do here validation of correctness
            self.parent.fit_func_str = new_fit_func_line

        def plotData(self,arr):
            xs = np.arange(len(arr))
            self.curve.setData(xs,arr)

    class AnalogPlot(QWidget):

        def __init__(self, parent=None, globals=None, signals=None,):
            super().__init__(parent)
            self.globals = globals
            self.signals = signals
            self.parent = parent
            self.chbx_widgets = []
            self.curves = {}
            self.initUI()

        def initUI(self):
            main_layout = QHBoxLayout()

            self.menu_layout = QVBoxLayout()
            for param, data in self.parent.params.items():
                w = MyCheckBox(param, is_checked=data["to_plot"],max_width=100,
                               handler=self.chbxChanged)
                self.chbx_widgets.append(w)
                self.menu_layout.addWidget(w)
            self.n_point_box = MyIntBox(value=self.parent.n_points, validator=QIntValidator(10, 10000),
                                        text_edited_handler=self.NpointsChanged,
                                        text_changed_handler=self.NpointsChanged,
                                        max_width=30)
            self.menu_layout.addWidget(self.n_point_box)
            main_layout.addLayout(self.menu_layout)

            self.plot = pg.PlotWidget()
            self.createCurves()
            main_layout.addWidget(self.plot)
            self.setLayout(main_layout)

        def chbxChanged(self):
            for w in self.chbx_widgets:
                self.parent.params[w.name]["to_plot"] = w.isChecked()
            for key in self.curves:
                self.plot.removeItem(self.curves[key])
            for item in self.plot.getPlotItem().legend.items:
                self.plot.getPlotItem().legend.removeItem(item)
            del self.plot.getPlotItem().legend
            self.plot.clear()
            self.curves = {}
            self.createCurves()

        def updateChbx(self):
            chbx_to_del = [w for w in self.chbx_widgets if w.name not in self.parent.params]
            for w in chbx_to_del:
                self.chbx_widgets.remove(w)
                self.menu_layout.removeWidget(w)
                w.deleteLater()
            for param,data in self.parent.params.items():
                if param not in [w.name for w in self.chbx_widgets]:
                    w = MyCheckBox(param, is_checked=data["to_plot"], max_width=100,
                                   handler=self.chbxChanged)
                    self.chbx_widgets.append(w)
                    self.menu_layout.insertWidget(0,w)

        def NpointsChanged(self):
            self.parent.n_points = self.n_point_box.value()

        def createCurves(self):
            self.plot.addLegend()
            n_plots = np.sum([w.isChecked() for w in self.chbx_widgets])
            i = 0
            for w in self.chbx_widgets:
                if w.isChecked():
                    key = w.name
                    self.curves[key] = self.plot.plot(np.array([]), name=key, pen=(i, n_plots))
                    i += 1

        def updatePlot(self):
            # print("--plotWidget -- updatePlot")
            for key in self.parent.params:
                if self.parent.params[key]["to_plot"] and len(self.parent.data_table):  # this parameter is set to be displayed
                    data = self.parent.data_table[key][-self.parent.n_points:]
                    xs = np.array(data.index)
                    ys = data.values
                    self.curves[key].setData(xs, ys)

    def __init__(self, parent=None, globals=None, signals=None,
                 data = {}):
        super(SingleAnalogInDisplayWidget, self).__init__()
        self.parent = parent
        self.globals = globals
        self.signals = signals
        self.data = {"channel":"I0", "pulse":0,
                         "params":{"a":{"value":"np.mean(data)","to_plot":True}},
                         "fit_func":"",
                        "is_active":True,
                         "n_points":200}
        self.data.update(data)
        self.data_table = pd.DataFrame(columns=list(self.data["params"]))
        self.main_widget = self.AnalogMain(parent=self,globals=self.globals,signals=self.signals)
        self.plot_widget = self.AnalogPlot(parent=self, globals=self.globals, signals=self.signals)
        self.initUI()
        if self.signals:
            self.signals.analogInputRecieved.connect(self.processInputDataNew)
            self.signals.scanStarted.connect(self.onScanStarted)
        self.couter = 0
        self.timer = QTimer()
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.timerTry)
        # self.timer.start()

    @property
    def channel(self):
        return self.data["channel"]
    @channel.setter
    def channel(self,new_str):
        self.data["channel"] = new_str

    @property
    def pulse(self):
        return self.data["pulse"]
    @pulse.setter
    def pulse(self,new_value):
        self.data["pulse"] = new_value

    @property
    def params(self):
        return self.data["params"]
    @params.setter
    def params(self, new_params):
        for param in self.data_table.columns:
            if param not in new_params:
                del self.data_table[param]
        for param in new_params:
            if param not in self.data_table.columns:
                self.data_table[param] = 0
        self.data["params"] = new_params
        self.plot_widget.updateChbx()
        self.plot_widget.updatePlot()

    @property
    def fit_func_str(self):
        return self.data["fit_func"]
    @fit_func_str.setter
    def fit_func_str(self, new_str):
        self.data["fit_func"] = new_str
        self.saveConfig()

    @property
    def n_points(self):
        return self.data["n_points"]
    @n_points.setter
    def n_points(self, new_val):
        self.data["n_points"] = new_val
        self.plot_widget.updatePlot()

    @property
    def is_active(self):
        return self.data["is_active"]
    @is_active.setter
    def is_active(self,new_val):
        self.data["is_active"]=new_val

    def initUI(self):
        self.addTab(self.main_widget,'Main')
        self.addTab(self.plot_widget,'Plot')
        # self.main_dock = da.Dock("Main")
        # self.plot_dock = da.Dock("Plot")
        # self.area.addDock(self.main_dock, 'top')
        # self.area.addDock(self.plot_dock, "below", self.main_dock)
        # self.main_dock.addWidget(self.main_widget)
        # self.plot_dock.addWidget(self.plot_widget)
        self.setMaximumHeight(500)
        self.setMinimumWidth(500)
        # self.area.setMinimumWidth(500)


    def getAvailableChannels(self):
        return self.parent.available_channels

    def delChannel(self):
        if self.parent:
            self.parent.delChannel(self)

    def addChannel(self):
        if self.parent:
            self.parent.addChannel(self)

    def saveChannel(self):
        print(self.data)
        if self.parent:
            self.parent.saveClicked()

    def timerTry(self):
        self.timer.stop()
        self.processInputData("I1 1 " + ' '.join(map(str,np.arange(10)+self.couter)))
        self.couter += 1
        self.timer.start()

    def constructGlobalParamName(self,param):
        return "_".join([self.channel,str(self.pulse),param])

    def onScanStarted(self):
        print("onScanStarted",self.data_table.columns)
        if self.globals and "scan_running_table" in self.globals:
            for fit_param in self.data_table.columns:
                self.globals["scan_running_table"][self.constructGlobalParamName(fit_param)] = 0.0
        # self.waitAfterScanStarted.start()

    def processInputData(self,data):
        """older version, excepts data as string input"""
        data = data.split(' ')
        if len(data) < 3:
            print("Something wrong with analog input massege")
            return
        channel, pulse, *data = data
        if channel == self.channel and pulse == str(self.pulse):
            print("Handling imput data", self.channel,self.pulse)
            try:
                data = np.array(list(map(float,data)))
            except:
                print("Can not convert data array to ndarray")
                return
            self.main_widget.plotData(data)
            columns = []
            new_vals = []
            if self.is_active and self.globals and "scan_running_data" in self.globals and self.globals["scan_running_data"]["on_scan"]:
                save_to_main_table = True
                current_meas_number = self.globals and self.globals["scan_running_data"]["current_meas_number"]
            else:
                save_to_main_table = False
            for param, conf in self.params.items():
                columns.append(param)
                val = eval(conf["value"])
                new_vals.append(val)
                if save_to_main_table:
                    self.globals["scan_running_table"].ix[current_meas_number,self.constructGlobalParamName(param)]=val
            self.data_table = self.data_table.append(pd.Series(new_vals,index=columns),ignore_index=True)
            self.plot_widget.updatePlot()
            # add data to table in globals

    def processInputDataNew(self, s=''):
        """newer version, analog input data stored in globals"""
        if self.globals and "analog_input_data" in self.globals:
            name = self.channel
            n = int(self.pulse)
            if name in self.globals["analog_input_data"]:
                data = self.globals["analog_input_data"][name]
                print(name, n, len(data))
                if len(data) <= n:
                    return
                data = [x/2**14 for x in data[n]]
                self.main_widget.plotData(data)
                columns = []
                new_vals = []
                if self.is_active and self.globals and "scan_running_data" in self.globals and self.globals["scan_running_data"][
                    "on_scan"]:
                    save_to_main_table = True
                    current_meas_number = self.globals and self.globals["scan_running_data"]["current_meas_number"]
                else:
                    save_to_main_table = False
                for param, conf in self.params.items():
                    columns.append(param)
                    val = eval(conf["value"])
                    new_vals.append(val)
                    if save_to_main_table:
                        self.globals["scan_running_table"].ix[
                            current_meas_number, self.constructGlobalParamName(param)] = val
                self.data_table = self.data_table.append(pd.Series(new_vals, index=columns), ignore_index=True)
                self.plot_widget.updatePlot()

class AllAnalogInDisplayWidget(da.DockArea):

    def __init__(self, parent=None, globals=None, signals=None,config_file=None):
        super(AllAnalogInDisplayWidget, self).__init__()
        self.parent = parent
        self.globals = globals
        self.signals = signals
        self.config_file = config_file
        self.available_channels = [ "I0", "I1", "I2", "I3" ]
        self.data = []
        self.load()
        self.widgets = []
        self.initUI()

    def initUI(self):
        # fileMenu = self.menuBar.addMenu('&File')
        # save = QAction('&Save', self)
        # save.triggered.connect(self.saveClicked)
        # fileMenu.addAction(save)
        for d in self.data:
            w = SingleAnalogInDisplayWidget(parent=self,globals=self.globals,signals=self.signals,data=d)
            self.widgets.append(w)
            dock = da.Dock(d["channel"],"below")
            dock.addWidget(w)
            self.area.addDock(dock)

    def load(self):
        print('load analogInDisplayWidget', end='\t')
        with open(self.config_file, 'r') as f:
            # if DEBUG: print('config_load')
            config = json.load(f)
        # print(config)
        self.__dict__.update(config['AnalogInDisplay'])

    def saveClicked(self):
        print('save analogInDisplayWidget')
        self.data = self.constructData()
        with open(self.config_file, 'r') as f:
            # if DEBUG: print('config_load_before_saving')
            all_config = json.load(f)
        config = all_config['AnalogInDisplay']
        for key in config:
            config[key] = self.__dict__[key]
        with open(self.config_file, 'w') as f:
            # if DEBUG: print('config_save')
            json.dump(all_config, f)

    def constructData(self):
        return [w.data for w in self.widgets]

    def delChannel(self,channel):
        print("--AllAnalogInDisplayWidget - Deleting widget is not implemented")

    def addChannel(self,channel):
        new_channel, ok_pressed = QInputDialog.getItem(self, "Choose new channel",
                                                          "Type:", self.available_channels,
                                                          0, False)
        if ok_pressed:
            print("Add new analog input widget for channel", new_channel)
            w = SingleAnalogInDisplayWidget(parent=self, globals=self.globals, signals=self.signals,
                                            data={"channel":new_channel})
            self.widgets.append(w)
            dock = da.Dock(new_channel,"below")
            dock.addWidget(w)
            self.area.addDock(dock)

class DisplayWidget(da.DockArea):

    def __init__(self, parent=None, globals=None, signals=None, config_file=None,**kwargs):
        super(DisplayWidget, self).__init__(parent)
        self.globals = globals
        self.signals = signals
        self.parent = parent
        self.config_file = config_file
        self.screen_size = QDesktopWidget().screenGeometry()
        self.config = {"camera_main":{"config_file":'cam_main_config.json',
                                        "camera_number":"0",
                                        "image_folder":r"\\ETHEREAL\Camera"},
                       "camera_top": {"config_file": 'cam_top_config.json',
                                       "camera_number": "1",
                                       "image_folder": r"\\ETHEREAL\Camera2"}
                       }
        self.load()
        self.camera_main = CameraWidget(parent=self,globals=self.globals,signals=self.signals,
                                        **self.config["camera_main"],image_folder= r"\\ETHEREAL\Camera")
        self.camera_top = CameraWidget(parent=self, globals=self.globals, signals=self.signals,
                                        **self.config["camera_top"],image_folder= r"\\ETHEREAL\Camera2")
        dock01 = da.Dock('Main camera', self)
        dock01.addWidget(self.camera_main)
        dock02 = da.Dock('Top camera', self)
        dock02.addWidget(self.camera_top)
        self.area.addDock(dock01,"left")
        self.area.addDock(dock02,"right",dock01)
        self.setWindowTitle('Display widget')

        dock03 = da.Dock('Analog inputs', self)
        dock03.addWidget(AllAnalogInDisplayWidget(parent=self, globals=self.globals, signals=self.signals,
                                                  config_file=self.config_file))
        self.area.addDock(dock03, "right",dock02)

        # self.area.tabify
        self.resize(self.screen_size.width(), self.screen_size.height())
        self.setWindowState(Qt.WindowMaximized)
        self.show()


    def load(self):
        print('load DisplayWidget config', end='\t')
        with open(self.config_file, 'r') as f:
            config = json.load(f)
        # print(config)
        self.__dict__.update(config['DisplayWidget'])


## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    import sys
    # if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
    app = QApplication(sys.argv)
    # ex = DisplayWidget()
    ex = CameraWidget()
    ex.show()
    sys.exit(app.exec_())

    # QApplication.instance().exec_()

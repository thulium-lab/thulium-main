import os, sys, time, datetime, json, scipy.misc, threading, ctypes
import re
import pyqtgraph as pg
import pyqtgraph.dockarea as da
import pyqtgraph.exporters
import numpy as np
from scipy.optimize import curve_fit
import pickle
import pymongo, datetime
from pymongo import MongoClient
from bson.objectid import ObjectId

from matplotlib.pyplot import imread
from PyQt5.QtCore import (QTimer, Qt,QRect)
from PyQt5.QtGui import (QIcon, QFont,QTransform)
from PyQt5.QtWidgets import (QApplication, QDesktopWidget, QHBoxLayout, QLabel, QWidget, QSpinBox, QCheckBox,
                             QMessageBox,QVBoxLayout,QHeaderView, QPushButton,QComboBox, QLineEdit)

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

class CameraWidget(QWidget):

    def __init__(self,parent=None,
                 config_file='cam_config.json',
                 image_name='image',
                 default_image=r"DigitalPulses\default_camera.tiff",
                 image_stack_name='image_stack'):

        self.config_file = config_file  # where to save config
        self.image_name = image_name    # name of the image in parent.globals
        self.image_stack_name = image_stack_name    # name of image stack in parent globals (array of filenames to save)
        self.parent = parent
        self.config = {}
        super().__init__()
        # default. All theese will be downloaded from config file
        self.do_fit1D_x = True
        self.do_fit1D_y = True
        self.do_fit2D = False
        self.subs_bgnd = True
        self.n_sigmas = 3
        self.roi_center = [200, 200]
        self.roi_size = [100, 100]

        # image data to show in table
        self.image_data_to_display = np.array([
            ('N',0, 0,0),
            ("X0", 0, 0,0),
            ('W',0,0,0)
        ], dtype=[(' ', object), ('x', object), ('y', object), ('2D', object)])

        self.load() # config loading

        main_layout = QHBoxLayout()

        self.win = pg.GraphicsLayoutWidget()
        p1 = self.win.addPlot()
        self.img = pg.ImageItem()
        self.img.setZValue(1)
        p1.addItem(self.img)
        self.parent.globals[self.image_name] = imread(default_image).T #initialise picture
        self.img.setImage(self.parent.globals[self.image_name])
        self.roi = pg.ROI(self.roi_center, self.roi_size, pen=pg.mkPen('g', width=1))  # , style=pg.QtCore.Qt.DotLine
        self.roi.addScaleHandle([1, 1], [0, 0])
        # self.roi.addScaleHandle([1, 0.5], [0, 1])
        p1.addItem(self.roi)
        self.roi.setZValue(100)
        self.hist = pg.HistogramLUTItem()
        self.hist.setImageItem(self.img)
        self.hist.setHistogramRange(0, 0.6)
        self.hist.setLevels(0, 0.6)
        self.hist.gradient.setColorMap(pg.ColorMap(np.array([0., 0.25, 0.5, 0.75, 1.]),
                                                   np.array([[255, 255, 255, 255], [0, 0, 255, 255],
                                                             [0, 0, 0, 255], [255, 0, 0, 255], [255, 255, 0, 255]],
                                                            dtype=np.uint8)))
        self.win.addItem(self.hist)
        self.img.setLookupTable(self.hist.getLookupTable(n=256))
        self.roi.sigRegionChangeFinished.connect(self.updateROI)
        main_layout.addWidget(self.win)

        chbx_layout = QVBoxLayout() # basically config and info layout
        chbx_layout.addWidget(QLabel('fit1D_x'))
        self.fit1D_x_chbx = QCheckBox()
        self.fit1D_x_chbx.setChecked(self.do_fit1D_x)
        self.fit1D_x_chbx.stateChanged.connect(lambda state: self.chbxClicked('do_fit1D_x', state))
        chbx_layout.addWidget(self.fit1D_x_chbx)

        chbx_layout.addWidget(QLabel('fit1D_y'))
        self.fit1D_y_chbx = QCheckBox()
        self.fit1D_y_chbx.setChecked(self.do_fit1D_y)
        self.fit1D_y_chbx.stateChanged.connect(lambda state: self.chbxClicked('do_fit1D_y', state))
        chbx_layout.addWidget(self.fit1D_y_chbx)

        chbx_layout.addWidget(QLabel('fit2D'))
        self.fit2D_chbx = QCheckBox()
        self.fit2D_chbx.setChecked(self.do_fit2D)
        self.fit2D_chbx.stateChanged.connect(lambda state: self.chbxClicked('do_fit2D', state))
        chbx_layout.addWidget(self.fit2D_chbx)

        chbx_layout.addWidget(QLabel('substract background'))
        self.fit2D_chbx = QCheckBox()
        self.fit2D_chbx.setChecked(self.subs_bgnd)
        self.fit2D_chbx.stateChanged.connect(lambda state: self.chbxClicked('subs_bgnd', state))
        chbx_layout.addWidget(self.fit2D_chbx)

        self.w3 = pg.TableWidget()
        self.w3.setFont(QFont('Arial', 12))
        self.w3.setData(self.image_data_to_display)
        chbx_layout.addWidget(self.w3)
        self.w3.horizontalHeader().setDefaultSectionSize(40)
        self.w3.verticalHeader().setDefaultSectionSize(30)
        self.w3.horizontalHeader().setResizeMode(QHeaderView.Fixed)
        self.w3.verticalHeader().setResizeMode(QHeaderView.Fixed)

        chbx_layout.addStretch(1)
        main_layout.addLayout(chbx_layout)
        self.setLayout(main_layout)

        # self.iso = pg.IsocurveItem(pen='g')
        # self.iso.setZValue(1000)
        # self.iso.setParentItem(self.img)
    def load(self):
        try:
            with open(self.config_file,'r') as f:
                self.config = json.load(f)
        except json.decoder.JSONDecodeError:
            print('ERROR in reading ', self.config_file)
            return
        except FileNotFoundError:
            print('File not yet exist')
            return
        for key in self.config:
            self.__dict__[key] = self.config[key]

    def save_config(self):
        try:
            with open(self.config_file, 'r') as f:
                old_config = json.load(f)
        except json.decoder.JSONDecodeError:
            old_config = {}
        except FileNotFoundError:
            old_config = {}
            print('File not yet exist')
        with open(self.config_file, 'w') as f:
            try:
                json.dump(self.config,f)
            except: # find what error does it raise when cannot dump
                json.dump(old_config, f)
                QMessageBox.warning(None, 'Message', "can not dump config to json, old version will be saved",
                                    QMessageBox.Ok)

    def updateROI(self):
        # print('updateRoi')
        self.roi_center = [int(self.roi.pos()[0]),int(self.roi.pos()[1])]
        self.roi_size = [int(self.roi.size()[0]),int(self.roi.size()[1])]
        # self.w5.cellChanged.disconnect(self.roiTableChanged)
        # self.w5.setData(self.getROITableData())
        # self.w5.cellChanged.connect(self.roiTableChanged)
        self.config['roi_center'] = self.roi_center
        self.config['roi_size'] = self.roi_size
        self.save_config()

    def chbxClicked(self,attribute,state):
        self.__dict__[attribute] = bool(state)
        self.config[attribute] = bool(state)
        self.save_config()
        # print(attribute, state)

    def getROITableData(self):
        # not used now
        return np.array([
            ('ll corner',*self.roi_center),
            ('Size',*self.roi_size),
        ], dtype=[(' ', object), ('x', object), ('y', object)])

    def roiTableChanged(self,row,column):
        "Not used now"
        new_val = int(self.w5.item(row,column).data(0))
        column -= 1
        if row ==0: #
            self.roi_center[column] = new_val
            self.roi.setPos(*self.roi_center)
        elif row == 1:
            self.roi_size[column] = new_val
            self.roi.setSize(self.roi_size)
        self.config['roi_center'] = self.roi_center
        self.config['roi_size'] = self.roi_size
        self.save_config()

    def updateIsocurve(self):
        # #old
        # cur_data = pg.gaussianFilter(self.imv.getImageItem().image, (4, 4))
        # self.iso.setParentItem(self.imv.getImageItem())
        cur_data = pg.gaussianFilter(self.img.image, (4, 4))
        # self.iso.setParentItem(self.img)
        self.iso.setData(cur_data) # this line takes too much process time
        self.iso.setLevel(cur_data.max()/np.e)
        self.iso.setZValue(1000)

    def data_processing(self):
        # here all image analysis is performed
        self.process_image(self.new_data) # pprocess image - may be this and below should be done in thread, because fits take time
        self.update_image_info(self.new_data)
        # self.updateIsocurve() # takes too much process time, 'Go To' for details
        print('Finished %s data processing at '%(self.image_name), datetime.datetime.now().time())

    def process_image(self,basic_data):
        if self.do_fit1D_x:
            try:
                basic_data.fit1D_x = basic_data.fit_gaussian1D(0)
            except RuntimeError:
                print("RuntimeError, couldn't find 1D_x fit for image")
                basic_data.isgood = False
        if self.do_fit1D_y:
            try:
                basic_data.fit1D_y = basic_data.fit_gaussian1D(1)
            except RuntimeError:
                print("RuntimeError, couldn't find 1D_y fit for image")
                basic_data.isgood = False
        if self.do_fit2D and ('fit1D_x' in basic_data.__dict__ and 'fit1D_y' in basic_data.__dict__):
            try:
                basic_data.fit2D = basic_data.fit_gaussian2D()
            except RuntimeError:
                print("RuntimeError, couldn't find 2D fit for image")
                basic_data.isgood = False
            basic_data.total_small = np.sum(basic_data.image[int(basic_data.fit1D_y[1]-self.n_sigmas*basic_data.fit1D_y[2]):int(basic_data.fit1D_y[1]+self.n_sigmas*basic_data.fit1D_y[2]),
                                             int(basic_data.fit1D_x[1]-self.n_sigmas*basic_data.fit1D_x[2]):int(basic_data.fit1D_x[1]+self.n_sigmas*basic_data.fit1D_x[2])])

    def update_image_info(self,data):
        if 'fit1D_x' in data.__dict__:
            self.image_data_to_display['x'] = np.array([int(data.fit1D_x[0]+0.5),int(data.fit1D_x[1]+0.5)+int(self.roi.pos()[0]),int(data.fit1D_x[2]+0.5)],dtype=object)
        else:
            self.image_data_to_display['x'] = np.array(['-']*3, dtype=object)
        if 'fit1D_y' in data.__dict__:
            self.image_data_to_display['y'] = np.array([int(data.fit1D_y[0]+0.5),int(data.fit1D_y[1]+0.5)+int(self.roi.pos()[1]),int(data.fit1D_y[2]+0.5)],dtype=object)
        else:
            self.image_data_to_display['y'] = np.array(['-'] * 3, dtype=object)
        if'fit2D' in data.__dict__:
            self.image_data_to_display['2D'] = np.array([data.fit2D[0],"%.0f, %.0f"%(data.fit2D[2]+self.roi.pos()[0],data.fit2D[1]+self.roi.pos()[1]),
                                                         "%.0f, %.0f" %(data.fit2D[4],data.fit2D[3])],dtype=object)
        else:
            self.image_data_to_display['2D'] = np.array(['-'] * 3, dtype=object)
        # print(self.image_data_to_display)
        # self.w3.clear()
        self.w3.setData(self.image_data_to_display)

    def updateImage(self):
        # global current_data_index
        # check if row is still correct
        if (np.array(self.roi_center) < 0).any() or not (np.array(self.roi_center)+np.array(self.roi_size) < self.parent.globals[self.image_name].shape[::-1]).all():
            self.roi_center=[0,0]
            self.roi_size=self.parent.globals[self.image_name].shape[::-1]
            # print(self.roi_size,self.globals['image'].shape[::-1])
            self.roi.setPos(*self.roi_center)
            self.roi.setSize(self.roi_size)
        # construct image bounds  by roi
        self.image_bounds = [(0 if 0>self.roi_center[1]>self.parent.globals[self.image_name].shape[0] else self.roi_center[1],
                            self.parent.globals[self.image_name].shape[0] if (self.roi_center[1] + self.roi_size[1]) > self.parent.globals[self.image_name].shape[0] else (self.roi_center[1] + self.roi_size[1])),
                             (0 if 0 > self.roi_center[0] > self.parent.globals[self.image_name].shape[1] else self.roi_center[0],
                              self.parent.globals[self.image_name].shape[1] if (self.roi_center[0] + self.roi_size[0]) >self.parent.globals[self.image_name].shape[1] else ( self.roi_center[0] + self.roi_size[0]))
                            ]
        # construct basic image data from roi image
        self.new_data = impr.Image_Basics(self.parent.globals[self.image_name][self.image_bounds[0][0]:self.image_bounds[0][1],
                                                            self.image_bounds[1][0]:self.image_bounds[1][1]],subs_bgnd=self.subs_bgnd)
        # save to globals only small image
        self.parent.globals[self.image_name][self.image_bounds[0][0]:self.image_bounds[0][1],
                        self.image_bounds[1][0]:self.image_bounds[1][1]] = self.new_data.image
        # show image
        self.img.setImage(self.parent.globals[self.image_name],autoRange=True, autoLevels=False,autoHistogramRange=False,autoDownsample=True)
        # handle image saving
        saved = False
        if self.parent.globals.get(self.image_stack_name):
            # print(self.parent.globals.get(self.image_stack_name))
            self.new_data.image_url = self.parent.globals.get(self.image_stack_name)[0]
            saved = self.save_image()
        else:
            print('Recieved image at time ', datetime.datetime.now().time())
            saved = True
            pass
        # smth needed for browser version
        if self.img.qimage is None:
            self.img.render()
        if self.img.qimage and self.image_name=='image':
            try:
                # exporter = pg.exporters.ImageExporter(self.img.qimage)
                # self.globals['imgExport'] = exporter.export(toBytes=True)
                self.parent.globals['imgExport'] = self.img.qimage
                self.parent.signals.imageRendered.emit()
            except Exception as e:
                print(e)

        # fully process image and show fit data
        self.data_processing()
        self.parent.globals[self.image_name + '_new_data'] = self.new_data  # update image data in global for futher access
        if saved:
            self.parent.signals.imageProcessed.emit(self.image_name + '_new_data') # emit signal for data handler
        # this may be implemented in thread
        # sthrd = threading.Thread(target=self.data_processing))
        # sthrd.start()

    def save_image(self):
        im_name = self.parent.globals[self.image_stack_name].pop(0)
        try:
            if im_name.split('/')[-1][0] == '-':
                return False
        except Exception as err:
            print(err)
        print('Save image ', im_name, 'at time ', datetime.datetime.now().time())
        scipy.misc.toimage(self.new_data.image, cmin=0, cmax=1).save(im_name)
        return True

class DisplayWidget(da.DockArea):
    def __init__(self, parent=None, globals=None, signals=None, **kwargs):
        self.config={}
        self.globals = globals
        self.signals = signals
        self.parent = parent
        self.config_file = os.path.join('DigitalPulses\digital_schemes','display_widget_config.json')
        self.screen_size = QDesktopWidget().screenGeometry()
        self.all_plot_data = {'N':[],'width':[]} # online data plot
        self.N_point_to_plot = 40   # number of last points to show in plot

        self.load()
        super(DisplayWidget, self).__init__(parent)
        self.initUI()
        self.show()

    def load(self):
        try:
            with open(self.config_file,'r') as f:
                self.config = json.load(f)
        except json.decoder.JSONDecodeError:
            print('ERROR in reading ', self.config_file)
            return
        except FileNotFoundError:
            print('File not yet exist')
            return
        for key in self.config:
            self.__dict__[key] = self.config[key]

    def save_config(self):
        self.globals['image_lower_left_corner'] = self.roi_center
        print('saveConfig')
        try:
            with open(self.config_file, 'r') as f:
                old_config = json.load(f)
        except json.decoder.JSONDecodeError:
            old_config = {}
        except FileNotFoundError:
            old_config = {}
            print('File not yet exist')
        with open(self.config_file, 'w') as f:
            try:
                json.dump(self.config,f)
            except: # find what error does it raise when cannot dump
                json.dump(old_config, f)
                QMessageBox.warning(None, 'Message', "can not dump config to json, old version will be saved",
                                    QMessageBox.Ok)

    def initUI(self):
        self.resize(self.screen_size.width(),self.screen_size.height())
        self.setWindowTitle('Display widget')
        self.setWindowIcon(QIcon('DigitalPulses\display_image_icon.jpg'))
        self.setWindowState(Qt.WindowMaximized)
        self.d1 = da.Dock("Image main", size=(self.screen_size.width()/2.3, self.screen_size.height()/2))     ## give this dock the minimum possible size
        self.d1_1 = da.Dock("Image top", size=(self.screen_size.width()/2.3, self.screen_size.height()/2))     ## give this dock the minimum possible size
        self.d3 = da.Dock("Info", size=(self.screen_size.width()/2, self.screen_size.height()/20))
        self.d2 = da.Dock("Cloud width", size=(self.screen_size.width()/2, self.screen_size.height()/3))
        self.d4 = da.Dock("N atoms", size=(self.screen_size.width()/2, self.screen_size.height()/3))
        self.area.addDock(self.d1, 'left')      ## place d1 at left edge of dock area (it will fill the whole space since there are no other docks yet)
        self.area.addDock(self.d4, 'right', self.d1)  ## place d4 at right edge of dock area

        self.area.addDock(self.d1_1, 'bottom', self.d1)
        self.area.addDock(self.d2, 'bottom', self.d4)  ## place d5 at left edge of d1
        self.area.addDock(self.d3, 'bottom', self.d2)## place d3 at bottom edge of d1
        self.d5 = da.Dock('Measurement',size=(self.screen_size.width()/2, self.screen_size.height()/3))
        self.area.addDock(self.d5,'bottom',self.d3)
        self.cam1 = CameraWidget(parent=self,
                                 config_file='cam1_config.json',
                                 image_name='image',
                                 default_image=r"D:\Dropbox\Python\Thulium\DigitalPulses\default_camera2.tiff",
                                 image_stack_name='image_stack')
        self.d1.addWidget(self.cam1)
        self.cam2 = CameraWidget(parent=self,
                                 image_stack_name='image2_stack',
                                 image_name='image2',
                                 default_image=r"D:\Dropbox\Python\Thulium\DigitalPulses\default_camera2.tiff",
                                 config_file='cam2_config.json')
        self.d1_1.addWidget(self.cam2)

        self.w2 = pg.PlotWidget()
        self.w2.addLegend()
        # self.w2.setYRange(0,100)
        self.curve11 = self.w2.plot(np.array([]),pen=(255,0,0),name='Nx')
        self.curve12 = self.w2.plot(np.array([]),pen=(0,255,0),name='Ny')
        self.d2.addWidget(self.w2)

        self.w4 = pg.PlotWidget()
        # self.w2.setYRange(0,100)
        self.w4.addLegend(size=(5,20))
        self.curve21 = self.w4.plot(np.array([]), pen=(255, 0, 0),name="w_x1")
        self.curve22 = self.w4.plot(np.array([]), pen=(0, 255, 0),name="w_x2")
        self.d4.addWidget(self.w4)

        plot_config_widget=QWidget()
        plot_config_layout = QHBoxLayout()
        plot_config_layout.addWidget(QLabel('N point to show'))

        n_points_spin = QSpinBox()
        n_points_spin.setMaximum(10000)
        n_points_spin.setValue(self.N_point_to_plot)
        n_points_spin.valueChanged.connect(self.nPointsChanged)
        plot_config_layout.addWidget(n_points_spin)

        # plot_config_layout.addWidget(QLabel('N max'))
        # self.n_max_spin = QSpinBox()
        # self.n_max_spin.setValue(0)
        # #n_points_spin.valueChanged.connect(self.nMaxChanged)
        # plot_config_layout.addWidget(self.n_max_spin)

        # plot_config_layout.addWidget(QLabel('W max'))
        # self.w_max_spin = QSpinBox()
        # self.w_max_spin.setValue(0)
        # # n_points_spin.valueChanged.connect(self.nMaxChanged)
        # plot_config_layout.addWidget(self.w_max_spin)

        plot_config_layout.addStretch(1)


        self.measurement = MeasurementClass(parent=self,signals=self.signals,globals=self.globals)
        self.d5.addWidget(self.measurement)

        deleteButton = QPushButton('delete from DB')
        deleteButton.clicked.connect(self.measurement.deleteLast)
        plot_config_layout.addWidget(deleteButton)

        plot_config_widget.setLayout(plot_config_layout)
        self.d3.addWidget(plot_config_widget)
        self.signals.newImageRead.connect(self.routine)
        self.signals.newImage2Read.connect(self.routine2)

    def nPointsChanged(self,new_val):
        self.N_point_to_plot = new_val
        self.config['N_point_to_plot'] = self.N_point_to_plot
        self.save_config()

    # def chbxClicked(self,attribute,state):
    #     self.__dict__[attribute] = bool(state)
    #     # print(attribute, state)


    def routine(self):
        self.cam1.updateImage()
        if len(self.globals['image_stack']): # if scan is on images have to be saved
            im_name = self.globals['image_stack'].pop(0)
            print('Save image ', im_name, 'at time ',datetime.datetime.now().time())
            scipy.misc.toimage(self.cam1.new_data.image,cmin=0,cmax=1).save(im_name)
        else:
            print('Recieved image at time ',datetime.datetime.now().time())
        self.update_plot(self.cam1.new_data)

    def routine2(self):
        # print('routine2')
        self.cam2.updateImage()

    def update_plot(self,data):
        if 'fit1D_x' in data.__dict__ and 'fit1D_y' in data.__dict__:
            self.all_plot_data['N'].append((data.fit1D_x[0],data.fit1D_y[0]))
            self.all_plot_data['width'].append((data.fit1D_x[2], data.fit1D_y[2]))
            if len(self.all_plot_data['N']) > self.N_point_to_plot:
                points_to_show = self.N_point_to_plot
            else :
                points_to_show = len(self.all_plot_data['N'])
            dataN = np.array(self.all_plot_data['N'])
            xx = np.arange(len(dataN))
            # if self.n_max_spin:
            #     y_max = self.n_max_spin.value()
            # else:
            #     y_max = dataN[len(dataN)-points_to_show:len(dataN)].max()
            # self.w2.setYRange(0,y_max)
            self.w2.setXRange(len(dataN)-points_to_show, len(dataN))
            self.curve11.setData(xx,dataN[:,0])
            self.curve12.setData(xx, dataN[:, 1])

            # # ATTENTION ---------------------------------------
            # msg = 'LOCK_BY_WM %s\n' % ('Ti:Sa')
            # sock.sendto(bytes(msg, "utf-8"), (HOST, PORT))
            # received = str(sock.recv(1024), "utf-8")
            # # print("Received: {}".format(received))
            # received = received.strip().split()
            # if len(received) != 2:
            #     self.unlock('No channel')
            #     return
            # meas_time = float(received[0])
            # frequency = float(received[1])
            # with open(r"D:\!Data\2018_10_08\TiSa.csv", "a") as f:
            #     f.write(str(meas_time)+','+str(frequency)+','+str(data.fit1D_x[0])+','+str(data.fit1D_y[0])+'\n')

            dataW = np.array(self.all_plot_data['width'])
            # if self.w_max_spin:
            #     y_max = self.w_max_spin.value()
            # else:
            #     y_max = dataW[len(dataN)-points_to_show:len(dataN)].max()
            # self.w4.setYRange(0, y_max)
            self.w4.setXRange(len(dataN) - points_to_show, len(dataN))
            self.curve21.setData(xx, dataW[:, 0])
            self.curve22.setData(xx, dataW[:, 1])

class MeasurementClass(QWidget):

    def __init__(self,parent=None,signals=None,globals=None):
        super().__init__()
        self.dataD = {}
        self.fits_list = []
        self.mdb_client = MongoClient('mongodb://192.168.1.59:27017/')  # or IP of MongoDB server
        self.meas_database = self.mdb_client.measData.meas_data
        self.cb_axis_items=['fit1D_x','fit1D_y','fit2D']
        self.cb_index_items = ['0','1','2','3','4']
        self.parent = parent
        self.signals = signals
        self.globals = globals
        self.signals.scanStarted.connect(self.scanStarted)
        self.signals.singleScanFinished.connect(self.onSingleScanFinished)
        self.signals.imageProcessed.connect(self.newDataArrived) # replace signal by one emmited when image processing is over

        self.min_n_to_avr = 3   # minimal number of good images to start everaging

        main_layout = QHBoxLayout()

        info_layout = QVBoxLayout()
        info_layout.addWidget(QLabel('Fit'))
        self.axis_box = QComboBox()
        self.axis_box.addItems(self.cb_axis_items)
        self.axis_box.setCurrentIndex(1)
        self.axis_box.currentIndexChanged.connect(self.onFitParamChanged)
        info_layout.addWidget(self.axis_box)

        info_layout.addWidget(QLabel('Index'))
        self.index_box = QComboBox()
        self.index_box.addItems(self.cb_index_items)
        self.index_box.setCurrentIndex(0)
        self.index_box.currentIndexChanged.connect(self.onFitParamChanged)
        info_layout.addWidget(self.index_box)

        info_layout.addWidget(QLabel('Fit_func'))
        self.fit_func_box = QComboBox()
        self.fit_func_box.addItems([s for s in dir(fit_func_lib) if s[0]!='_'])
        self.fit_func_box.setCurrentText('gaussian2')
        self.fit_func_box.currentIndexChanged.connect(self.onFitParamChanged)
        info_layout.addWidget(self.fit_func_box)

        info_layout.addWidget(QLabel('p0'))
        self.p0_line = QLineEdit()
        self.p0_line.setMaximumWidth(200)
        self.p0_line.editingFinished.connect(self.p0Edited)
        info_layout.addWidget(self.p0_line)

        info_layout.addWidget(QLabel('drop points (by #)'))
        self.drop_points_line = QLineEdit()
        self.drop_points_line.setMaximumWidth(200)
        self.drop_points_line.editingFinished.connect(self.dropPointsEdited)
        info_layout.addWidget(self.drop_points_line)

        info_layout.addStretch(1)

        main_layout.addLayout(info_layout)
        self.single_meas_plot = pg.PlotWidget(background='w',pen=pg.Color('k'))
        # self.single_meas_plot.setMaximumWidth(400)
        # self.single_meas_plot.showGrid(x=True, y=True,alpha=0.5)
        self.single_meas_plot.getAxis('left').setPen(pg.Color('k'))
        self.single_meas_plot.getAxis('bottom').setPen(pg.Color('k'))
        self.curve1 = self.single_meas_plot.plot(np.array([]), pen=None,symbol='o',
                                                 symbolPen=None,symbolBrush=(0,255,0),symbolSize=7)
        self.curve2 = self.single_meas_plot.plot(np.array([]), pen=None,symbol='o',
                                                 symbolPen=None,symbolBrush=(255,0,0),symbolSize=7)
        self.curve3 = self.single_meas_plot.plot(np.array([]), pen=None, symbol='+',
                                                 symbolPen=None,symbolBrush=pg.Color('b'),symbolSize=15)
        self.curve4 = self.single_meas_plot.plot(np.array([]), pen=(0,0,255))
        self.plot_info = pg.TextItem(' ', anchor=(0,1),color=pg.Color('k'))
        main_layout.addWidget(self.single_meas_plot)

        # self.single_meas_plot2 = pg.PlotWidget(background='w',pen=pg.Color('k'))
        # self.single_meas_plot2.setMaximumWidth(400)
        # # self.single_meas_plot.showGrid(x=True, y=True,alpha=0.5)
        # self.single_meas_plot2.getAxis('left').setPen(pg.Color('k'))
        # self.single_meas_plot2.getAxis('bottom').setPen(pg.Color('k'))
        # self.curve21 = self.single_meas_plot2.plot(np.array([]), pen=None,symbol='o',
        #                                          symbolPen=None,symbolBrush=(0,255,0),symbolSize=7)
        # self.curve22 = self.single_meas_plot2.plot(np.array([]), pen=None,symbol='o',
        #                                          symbolPen=None,symbolBrush=(255,0,0),symbolSize=7)
        # self.curve23 = self.single_meas_plot2.plot(np.array([]), pen=None, symbol='+',
        #                                          symbolPen=None,symbolBrush=pg.Color('b'),symbolSize=15)
        # self.curve24 = self.single_meas_plot2.plot(np.array([]), pen=(0,0,255))
        # self.plot_info = pg.TextItem(' ', anchor=(0,1),color=pg.Color('k'))

        # main_layout.addWidget(self.single_meas_plot2)
        self.setLayout(main_layout)

    def dropPointsEdited(self):
        self.doFitMeasurement()

    def p0Edited(self):
        p0 = [float(s.strip()) for s in self.p0_line.text().split(',')]
        if len(p0) == len(self.p0):
            self.p0 = p0
            self.doFitMeasurement()

    def onSingleScanFinished(self):
        # called when intermidiate measurement  in a series is finished
        self.new_scan_started = True

    def scanStarted(self):
        self.new_scan_started=False # flag to handle new scanse in series
        self.dataD = {}
        self.folder = self.globals['current_measurement_folder']
        self.meas_type, self.conf_params, self.x_lbl, self.y_lbl, self.xaxis_calib = impr.get_x_calibration(self.folder, [])
        # if self.meas_type =='T':
        #     self.fit_data_index=2
        # else:
        #     self.fit_data_index=0
        self.fit_data_index = int(self.index_box.currentText())

        self.single_meas_plot.setLabel('left', text=self.y_lbl)
        self.single_meas_plot.setLabel('bottom', text=self.x_lbl)
        self.single_meas_plot.setTitle(self.folder.split('/')[-1],color=pg.Color('k'))
        self.curve1.setData([],[])
        self.curve2.setData([], [])
        self.curve3.setData([],[])
        self.curve4.setData([],[])
        self.single_meas_plot.removeItem(self.plot_info)
        self.single_meas_plot.setXRange(self.xaxis_calib(min(self.globals['active_params_list'][0][0])),
                                        self.xaxis_calib(max(self.globals['active_params_list'][0][0])))

    def newDataArrived(self,image_data_name):
        # print('Image_data_name',image_data_name)
        new_image_data = self.parent.globals[image_data_name]
        print('qwerty')
        if new_image_data.image_url == 'not_defined': # if scan is off
            return
        if not new_image_data.isgood: # for now, may be should be handled saparately
            return
        dr, fr = os.path.split(new_image_data.image_url)
        folderN = float(re.findall(r"[-+]?\d*\.?\d+", dr)[-1])  # current meas folder name
        nbrs = re.findall(r"[-+]?\d*\.?\d+", fr)[0]             # current shot number str!!!
        current_data = self.dataD.get(folderN,{'ind':[],'avr':None,'std_avr':None})
        current_data['ind'].append(new_image_data)
        if len(current_data['ind'])>=self.min_n_to_avr:
            # check what images are good based on SOME rool and available images
            m_c_x = np.median([d.fit1D_x[1] for d in current_data['ind']])
            for d in current_data['ind']:
                d.isgood = abs(d.fit1D_x[1] - m_c_x) < new_image_data.image.shape[0]/10

            if len([d.image for d in current_data['ind'] if d.isgood]) >= self.min_n_to_avr:
                avr_data = impr.Image_Basics(np.mean([d.image for d in current_data['ind'] if d.isgood],0),
                                             subs_bgnd=False)
                try:
                        avr_data.fit1D_x = avr_data.fit_gaussian1D(0)
                        avr_data.fit1D_y = avr_data.fit_gaussian1D(1)
                        avr_data.total_mean = np.mean([d.total for d in current_data['ind'] if d.isgood],0)
                        avr_data.total_std = np.std([d.total for d in current_data['ind'] if d.isgood],0)
                        avr_data.fit1D_x_mean = np.mean([d.fit1D_x for d in current_data['ind'] if d.isgood], 0)
                        avr_data.fit1D_x_std = np.std([d.fit1D_x for d in current_data['ind'] if d.isgood], 0)
                        avr_data.fit1D_y_mean = np.mean([d.fit1D_y for d in current_data['ind'] if d.isgood], 0)
                        avr_data.fit1D_y_std = np.std([d.fit1D_y for d in current_data['ind'] if d.isgood], 0)
                        current_data['avr'] = avr_data
                        current_data['std_avr']=np.std([d.fit1D_x[self.fit_data_index] for d in current_data['ind']
                                                        if d.isgood])
                except RuntimeError:
                    print("RuntimeError, couldn't find fit for image")
                    avr_data.isgood = False

        self.dataD[folderN]=current_data
        # points to be plotted
        good_points = []
        bad_points = []
        avr_points = []
        for key, item in self.dataD.items():
            good_points.extend([(key,d.__dict__.get(self.axis_box.currentText())[self.fit_data_index]) for d in item['ind'] if d.isgood])
            bad_points.extend([(key, d.__dict__.get(self.axis_box.currentText())[self.fit_data_index]) for d in item['ind'] if not d.isgood])
            if item['avr'] != None:
                avr_points.append((key,item['avr'].__dict__.get(self.axis_box.currentText())[self.fit_data_index],item['std_avr']))
        if good_points:
            good_points = self.xaxis_calib(np.array(good_points))
            self.curve1.setData(good_points[:,0], good_points[:,1])
            self.single_meas_plot.setYRange(0,1.1*max(good_points[:,1]))
        if bad_points:
            bad_points =  self.xaxis_calib(np.array(bad_points))
            self.curve2.setData(bad_points[:, 0], bad_points[:, 1])
        if avr_points:
            avr_points =  self.xaxis_calib(np.array(avr_points))
            self.curve3.setData(x=avr_points[:, 0], y=avr_points[:, 1],top=avr_points[:,2])
        if (len(self.dataD) == len(self.globals['active_params_list'][0][0])) and int(nbrs) == (self.globals['number_of_shots']-1):
            print('Measurement finished. Process is on...')
            if len(avr_points) > 0:
                self.avr_points = np.array(list(zip(*sorted(list(zip(avr_points[0,:],avr_points[1,:]))))))
                self.fit_lbl_pos = (min(good_points[:, 0]), 0)
                self.fitMeasurement(avr_points,fit_lbl_pos=(min(good_points[:, 0]), 0))
            self.saveFigandData()
            if self.new_scan_started: # if there is new started scan
                self.scanStarted()

    def onFitParamChanged(self):
        # points to be plotted
        print('ON FIT PARAMS CHANGED')
        if not self.dataD:
            return
        self.fit_data_index = int(self.index_box.currentText())
        good_points = []
        bad_points = []
        avr_points = []
        for key, item in self.dataD.items():
            good_points.extend(
                [(key, d.__dict__.get(self.axis_box.currentText())[self.fit_data_index]) for d in item['ind'] if
                 d.isgood])
            bad_points.extend(
                [(key, d.__dict__.get(self.axis_box.currentText())[self.fit_data_index]) for d in item['ind'] if
                 not d.isgood])
            if item['avr'] != None:
                avr_points.append(
                    (key, item['avr'].__dict__.get(self.axis_box.currentText())[self.fit_data_index], item['std_avr']))
        if good_points:
            good_points = self.xaxis_calib(np.array(good_points))
            self.curve1.setData(good_points[:, 0], good_points[:, 1])
            self.single_meas_plot.setYRange(0, 1.1 * max(good_points[:, 1]))
        if bad_points:
            bad_points = self.xaxis_calib(np.array(bad_points))
            self.curve2.setData(bad_points[:, 0], bad_points[:, 1])
        if avr_points:
            avr_points = self.xaxis_calib(np.array(avr_points))
            self.curve3.setData(x=avr_points[:, 0], y=avr_points[:, 1], top=avr_points[:, 2])
        if len(avr_points) > 0:
            self.avr_points = avr_points[avr_points[:,0].argsort()]
            self.p0 = fit_func_lib._p0_dict[self.fit_func_box.currentText()](avr_points[:,0],avr_points[:,1])
            self.doFitMeasurement()

    def fitMeasurement(self,avr_points,fit_lbl_pos=(0,0)):
        fit_func = fit_func_lib.__dict__[self.fit_func_box.currentText()]
        # print('AVR_POINTS',avr_points)
        xs = np.copy(avr_points[:, 0])
        ys = np.copy(avr_points[:, 1])
        ys_err = np.copy(avr_points[:, 2])

        p0 = fit_func_lib._p0_dict[self.fit_func_box.currentText()](xs,ys)
        self.p0 = p0
        # p0 = (-max(ys) / 20 * (max(xs) - min(xs)), xs[np.argmin(ys)], (max(xs) - min(xs)) / 10, max(ys))
        print(p0)
        self.p0_line.setText(','.join(['%.1e'%x for x in p0]))
        try:
            popt_T, pcov_T = curve_fit(fit_func, xs, ys, sigma=ys_err,p0=p0)
        except RuntimeError as e:
            print(e)
            popt_T = p0
            pcov_T = np.zeros((len(popt_T), len(popt_T)))
        except Exception as e: # just in case (if not enough points, ...)
            print(e)
            popt_T = p0
            pcov_T = np.zeros((len(popt_T), len(popt_T)))

        perr_T = np.sqrt(np.diag(pcov_T))
        self.curve4.setData(np.linspace(min(xs), max(xs), 100),
                            fit_func(np.linspace(min(xs), max(xs), 100), *popt_T))

        s = fit_func.__name__ + ' fit:\n' + usfuncs.construct_fit_description(fit_func,
                                                                              list(zip(popt_T, perr_T)), sep='+-')
        self.plot_info.setText(s)
        self.single_meas_plot.addItem(self.plot_info)
        self.plot_info.setPos(*fit_lbl_pos)
        self.fits_list = [[fit_func.__name__,list(popt_T), list(perr_T)]]

    def doFitMeasurement(self):
        fit_func = fit_func_lib.__dict__[self.fit_func_box.currentText()]
        p0 = self.p0
        # print('PO',p0)
        avr_points = self.avr_points
        # print('AVR_POINTS',avr_points)
        xs = np.copy(avr_points[:, 0])
        # print('XS0', xs)
        ys = np.copy(avr_points[:, 1])
        ys_top = np.copy(avr_points[:, 2])
        try:

            bad_points = [int(s.strip()) for s in self.drop_points_line.text().split(',') if s.strip().isdigit()]
            # print('BAD POINTS',bad_points)
            xs = np.array([xs[i] for i in range(len(xs)) if i not in bad_points])
            ys = np.array([ys[i] for i in range(len(ys)) if i not in bad_points])
            ys_top = np.array([ys_top[i] for i in range(len(ys_top)) if i not in bad_points])
            self.curve3.setData(x=xs, y=ys, top=ys_top)
        except ValueError as e:
            print('ERRORR')
            print(e)
        # print('XS', xs)
        # print(xs,ys)
        try:
            popt_T, pcov_T = curve_fit(fit_func, xs, ys, sigma=ys_top, p0=p0)
        except RuntimeError as e:
            print(e)
            popt_T = p0
            pcov_T = np.zeros((len(popt_T), len(popt_T)))
        except Exception as e: # just in case (if not enough points, ...)
            print(e)
            popt_T = p0
            pcov_T = np.zeros((len(popt_T), len(popt_T)))
        # print(np.linspace(min(xs), max(xs), 100), *popt_T)
        perr_T = np.sqrt(np.diag(pcov_T))
        self.curve4.setData(np.linspace(min(xs), max(xs), 100),
                            fit_func(np.linspace(min(xs), max(xs), 100), *popt_T))
        s = fit_func.__name__ + ' fit:\n' + usfuncs.construct_fit_description(fit_func,
                                                                              list(zip(popt_T, perr_T)), sep='+-')
        self.plot_info.setText(s)
        self.single_meas_plot.addItem(self.plot_info)
        self.plot_info.setPos(*self.fit_lbl_pos)
        self.fits_list = [[fit_func.__name__, list(popt_T), list(perr_T)]]
        self.saveFigandData()

    def saveFigandData(self):
        dr, fr = os.path.split(self.folder)
        if not os.path.exists(os.path.join(dr,'Figures')):
            os.makedirs(os.path.join(dr,'Figures'))
        f_dest = os.path.join(dr,'Figures',fr)
        print('SAVE FIGURE', f_dest)
        pg.exporters.ImageExporter(self.single_meas_plot.getPlotItem()).export(f_dest+'.png')
        navrD = impr.mod_avrData({key:{0:self.dataD[key]['avr']} for key in self.dataD},
                                 self.xaxis_calib,
                                 impr.N_atoms(gain=200, exposure=200, power=6.3, width=1.85, delta=6),
                                 impr.real_size)
        avr_table = impr.get_pandas_table2(navrD)
        ss = 'temp'
        avr_table.to_pickle(ss)
        with open(ss, 'rb') as fl:
            line = fl.read()
        os.remove(ss)
        # prepear dictionary to load to mongoDB
        data_to_db = {
            'time_meas': datetime.datetime.fromtimestamp(os.path.getctime(self.folder)),
            'date_meas': datetime.datetime.strptime(os.path.split(dr)[1][:10], '%Y_%m_%d'),
            'date_mod': datetime.datetime.now(),
            'folder': self.folder,
            'meas_type': self.meas_type,
            'labels': [self.x_lbl, self.y_lbl],
            'conf_params': self.conf_params,
            'fits': self.fits_list,
            'avr_table_pickle': line
        }
        res = self.meas_database.find_one({'date_meas': datetime.datetime.strptime(os.path.split(dr)[1][:10], '%Y_%m_%d'),
                                      'folder': self.folder})
        if res:
            print('Entery for folder "%s" updated' % self.folder)
            self.meas_database.update_one({'_id': res['_id']}, {'$set': data_to_db})
        else:
            print('Entery for folder "%s" created' % self.folder)
            self.meas_database.insert_one(data_to_db)

    def deleteLast(self):
        try:
            self.meas_database.delete_one({'folder': self.folder})
        except Exception as e:
            print(e)
        return


## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    import sys
    # if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
    app = QApplication(sys.argv)
    ex = DisplayWidget()
    ex.show()
    sys.exit(app.exec_())
    # QApplication.instance().exec_()

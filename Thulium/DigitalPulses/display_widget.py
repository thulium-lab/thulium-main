import os, sys, time, datetime, json, scipy.misc, threading, ctypes
import pyqtgraph as pg
import pyqtgraph.dockarea as da
import pyqtgraph.exporters
import numpy as np

from matplotlib.pyplot import imread
from PyQt5.QtCore import (QTimer, Qt,QRect)
from PyQt5.QtGui import (QIcon, QFont,QTransform)
from PyQt5.QtWidgets import (QApplication, QDesktopWidget, QHBoxLayout, QLabel, QWidget, QSpinBox, QCheckBox,
                             QMessageBox)


sys.path.append(r'D:\!Data')

import thulium_python_lib.usefull_functions as usfuncs
import thulium_python_lib.image_processing_new as impr

myAppID = u'LPI.Camera' # arbitrary string
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myAppID)

pg.setConfigOptions(imageAxisOrder='row-major')

ds_dir = r'D:\!Data\2016_04_22\01 T no_ramp a=-6 f=363.9 b=0.8'
# data = []
# for d in os.listdir(ds_dir):
#     d_dir  = os.path.join(ds_dir,d)
#     if os.path.isdir(d_dir):
#         x = imread(os.path.join(d_dir,os.listdir(d_dir)[0]))
#         data.append(x)
# data = np.array(data)
#
# current_data_index = 0;
# app = QApplication([])
# win = QMainWindow()
#
# win.setCentralWidget(area)
# win.resize(1000,500)
# win.setWindowTitle('Dockarea')

class DisplayWidget(da.DockArea):
    def __init__(self, parent=None, globals=None, signals=None, **kwargs):
        self.config={}
        self.globals = globals
        self.signals = signals
        self.parent = parent
        self.config_file = os.path.join('DigitalPulses\digital_schemes','display_widget_config.json')
        self.screen_size = QDesktopWidget().screenGeometry()
        self.roi_center = [200,200]
        self.roi_size = [100,100]
        self.all_plot_data = {'N':[],'width':[]}
        self.N_point_to_plot = 40
        self.do_fit1D_x = True
        self.do_fit1D_y = True
        self.do_fit2D = False
        self.subs_bgnd = True
        self.n_sigmas = 3

        self.image_data_to_display = np.array([
            ('N',0, 0,0),
            ('Center',0 , 0,0),
            ("Width", 0, 0,0),
            ("N_small",0,0 , 0),
            ('Center_full',0,0,0)
        ], dtype=[('Parameter', object), ('x', object), ('y', object), ('2D', object)])

        self.load()
        self.globals['image_lower_left_corner'] = self.roi_center

        super(DisplayWidget, self).__init__(parent)
        self.initUI()

        self.iso = pg.IsocurveItem(pen='g')
        self.iso.setZValue(1000)
        self.iso.setParentItem(self.img)
        self.show()
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.routine)
        # self.timer.start()

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
        # self.area = DockArea()
        # self.setCentralWidget(self.area)
        # self.resize(1000,500)
        self.resize(self.screen_size.width(),self.screen_size.height())
        self.setWindowTitle('Display widget')
        self.setWindowIcon(QIcon('DigitalPulses\display_image_icon.jpg'))
        self.setWindowState(Qt.WindowMaximized)
        self.d1 = da.Dock("Image", size=(self.screen_size.width()/2, self.screen_size.height()))     ## give this dock the minimum possible size
        self.d3 = da.Dock("Number of atoms", size=(self.screen_size.width()/2, self.screen_size.height()/3))
        self.d2 = da.Dock("Image data", size=(self.screen_size.width()/2, self.screen_size.height()/3))
        self.d4 = da.Dock("Cloud width", size=(self.screen_size.width()/2, self.screen_size.height()/3))
        self.area.addDock(self.d1, 'left')      ## place d1 at left edge of dock area (it will fill the whole space since there are no other docks yet)
        self.area.addDock(self.d2, 'right', self.d1)## place d3 at bottom edge of d1
        self.area.addDock(self.d4, 'bottom',self.d2)     ## place d4 at right edge of dock area
        self.area.addDock(self.d3, 'bottom', self.d4)  ## place d5 at left edge of d1
        # #old version
        # self.imv = pg.ImageView()
        # self.imv.setColorMap(pg.ColorMap(np.array([ 0.  ,  0.25,  0.5 ,  0.75,  1.  ]), np.array([[  255, 255, 255, 255],       [  0,   0, 255, 255],       [  0,   0,   0, 255],       [255,   0,   0, 255],       [255, 255,   0, 255]], dtype=np.uint8)))
        # self.imv.setImage(imread(r"D:\!Data\2016_04_22\01 T no_ramp a=-6 f=363.9 b=0.8\0ms\1_1.png"))
        #
        # self.imv.getHistogramWidget().setHistogramRange(0,0.6)
        # self.imv.getHistogramWidget().setLevels(0, 0.6)
        # self.d1.addWidget

        # new version with ROI
        win = pg.GraphicsLayoutWidget()
        self.win = win
        p1 = win.addPlot()
        self.img = pg.ImageItem()
        self.img.setZValue(1)
        p1.addItem(self.img)
        self.globals['image']=imread(r"DigitalPulses\default_camera.tiff").T
        self.img.setImage(self.globals['image'])
        self.roi = pg.ROI(self.roi_center, self.roi_size,pen=pg.mkPen('g', width=1)) #, style=pg.QtCore.Qt.DotLine
        self.roi.addScaleHandle([1, 1], [0, 0])
        # self.roi.addScaleHandle([1, 0.5], [0, 1])
        p1.addItem(self.roi)
        self.roi.setZValue(100)
        self.hist = pg.HistogramLUTItem()
        self.hist.setImageItem(self.img)
        self.hist.setHistogramRange(0,0.6)
        self.hist.setLevels(0, 0.6)
        self.hist.gradient.setColorMap(pg.ColorMap(np.array([ 0.  ,  0.25,  0.5 ,  0.75,  1.  ]),
                                         np.array([[  255, 255, 255, 255],[  0,   0, 255, 255],
                                                   [  0,   0,   0, 255],[255,   0,   0, 255],[255, 255,   0, 255]],
                                                  dtype=np.uint8)))
        win.addItem(self.hist)
        # self.hist.sigLookupTableChanged.connect(self.LUTChanged)
        self.img.setLookupTable(self.hist.getLookupTable(n=256))
        self.roi.sigRegionChangeFinished.connect(self.updateROI)
        self.d1.addWidget(win, col=0, row=0)


        win2 = pg.GraphicsLayoutWidget()
        p1_2 = win2.addPlot()
        self.img2 = pg.ImageItem()
        self.img2.setZValue(1)
        # self.img2.setPxMode(True)
        p1_2.addItem(self.img2)
        self.globals['image2']=imread(r"DigitalPulses\default_camera2.tiff").T
        self.img2.setImage(self.globals['image2'])
        self.roi2 = pg.ROI(self.roi_center, self.roi_size, pen=pg.mkPen('g', width=1))  # , style=pg.QtCore.Qt.DotLine
        self.roi2.addScaleHandle([1, 1], [0, 0])
        # self.roi.addScaleHandle([1, 0.5], [0, 1])
        p1_2.addItem(self.roi2)
        self.roi2.setZValue(100)
        self.hist2 = pg.HistogramLUTItem()
        self.hist2.setImageItem(self.img2)
        self.hist2.setHistogramRange(0, 0.6)
        self.hist2.setLevels(0, 0.6)
        self.hist2.gradient.setColorMap(pg.ColorMap(np.array([0., 0.25, 0.5, 0.75, 1.]),
                                                   np.array([[255, 255, 255, 255], [0, 0, 255, 255],
                                                             [0, 0, 0, 255], [255, 0, 0, 255], [255, 255, 0, 255]],
                                                            dtype=np.uint8)))
        win2.addItem(self.hist2)
        # self.hist.sigLookupTableChanged.connect(self.LUTChanged)
        self.img2.setLookupTable(self.hist2.getLookupTable(n=256))
        self.roi2.sigRegionChangeFinished.connect(self.updateROI2)
        self.d1.addWidget(win2,col=0,row=1)


        self.w2 = pg.PlotWidget()
        self.w2.addLegend()
        # self.w2.setYRange(0,100)
        self.curve11 = self.w2.plot(np.array([]),pen=(255,0,0),name='Nx')
        self.curve12 = self.w2.plot(np.array([]),pen=(0,255,0),name='Ny')
        self.curve13 = self.w2.plot(np.array([]),pen=(0,0,255),name='N')
        self.d2.addWidget(self.w2)

        self.w3 = pg.TableWidget()
        self.w3.setFont(QFont('Arial', 20))
        self.w3.setData(self.image_data_to_display)
        self.d3.addWidget(self.w3)

        # w6 = QHBoxLayout()
        # w6.addWidget(QLabel('fit1D_x'))
        chbx_widget = QWidget()
        chbx_layout = QHBoxLayout()
        chbx_layout.addWidget(QLabel('fit1D_x'))
        self.fit1D_x_chbx = QCheckBox()
        self.fit1D_x_chbx.setChecked(self.do_fit1D_x)
        self.fit1D_x_chbx.stateChanged.connect(lambda state:self.chbxClicked('do_fit1D_x',state))
        chbx_layout.addWidget(self.fit1D_x_chbx)

        chbx_layout.addWidget(QLabel('fit1D_y'))
        self.fit1D_y_chbx = QCheckBox()
        self.fit1D_y_chbx.setChecked(self.do_fit1D_y)
        self.fit1D_y_chbx.stateChanged.connect(lambda state:self.chbxClicked('do_fit1D_y',state))
        chbx_layout.addWidget(self.fit1D_y_chbx)

        chbx_layout.addWidget(QLabel('fit2D'))
        self.fit2D_chbx = QCheckBox()
        self.fit2D_chbx.setChecked(self.do_fit2D)
        self.fit2D_chbx.stateChanged.connect(lambda state:self.chbxClicked('do_fit2D',state))
        chbx_layout.addWidget(self.fit2D_chbx)

        chbx_layout.addWidget(QLabel('substract background'))
        self.fit2D_chbx = QCheckBox()
        self.fit2D_chbx.setChecked(self.subs_bgnd)
        self.fit2D_chbx.stateChanged.connect(lambda state: self.chbxClicked('subs_bgnd', state))
        chbx_layout.addWidget(self.fit2D_chbx)

        chbx_layout.addWidget(QLabel('N points to show'))
        self.n_points_spin_box = QSpinBox()
        self.n_points_spin_box.setRange(10,1000)
        self.n_points_spin_box.setValue(self.N_point_to_plot)
        self.n_points_spin_box.valueChanged.connect(self.nPointsChanged)
        chbx_layout.addWidget(self.n_points_spin_box)
        # w6.addWidget(self.fit1D_x_chbx)
        # self.d3.addWidget(QLabel('fit1D_x'),row=1,col=0)
        # self.d3.addWidget(self.fit1D_x_chbx,row=1,col=1)

        chbx_layout.addStretch(1)
        chbx_widget.setLayout(chbx_layout)
        self.d3.addWidget(chbx_widget)

        self.w5 = pg.TableWidget(editable=True,sortable=False)
        self.w5.setFont(QFont('Arial', 20))
        self.w5.setData(self.getROITableData())
        self.w5.cellChanged.connect(self.roiTableChanged)
        self.d3.addWidget(self.w5,row=0,col=1)


        self.w4 = pg.PlotWidget()
        # self.w2.setYRange(0,100)
        self.w4.addLegend(size=(5,20))
        self.curve21 = self.w4.plot(np.array([]), pen=(255, 0, 0),name="w_x1")
        self.curve22 = self.w4.plot(np.array([]), pen=(0, 255, 0),name="w_x2")
        self.curve23 = self.w4.plot(np.array([]), pen=(0, 0, 255),name="w_y1")
        self.curve24 = self.w4.plot(np.array([]), pen='y',name="w_y2")

        self.d4.addWidget(self.w4)
        self.signals.newImageRead.connect(self.routine)
        self.signals.newImage2Read.connect(self.routine2)

    # def LUTChanged(self):
    #     print('LUTChanged')
    #     print(self.hist.gradient.getGradient())

    def nPointsChanged(self,new_val):
        self.N_point_to_plot = new_val
        self.config['N_point_to_plot'] = self.N_point_to_plot
        self.save_config()

    def chbxClicked(self,attribute,state):
        self.__dict__[attribute] = bool(state)
        # print(attribute, state)

    def getROITableData(self):
        return np.array([
            ('ll corner',*self.roi_center),
            ('Size',*self.roi_size),
        ], dtype=[(' ', object), ('x', object), ('y', object)])

    def roiTableChanged(self,row,column):
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

    def routine(self):
        # global current_data_index
        # current_data_index = (current_data_index + 1) % len(data)
        # print(self.roi_center,self.roi_size,self.globals['image'].shape)
        if (np.array(self.roi_center) < 0).any() or not (np.array(self.roi_center)+np.array(self.roi_size) < self.globals['image'].shape[::-1]).all():
            self.roi_center=[0,0]
            self.roi_size=self.globals['image'].shape[::-1]
            # print(self.roi_size,self.globals['image'].shape[::-1])
            self.roi.setPos(*self.roi_center)
            self.roi.setSize(self.roi_size)
        # print(self.roi_center,self.roi_size,self.globals['image'].shape)
        self.image_bounds = [(0 if 0>self.roi_center[1]>self.globals['image'].shape[0] else self.roi_center[1],
                            self.globals['image'].shape[0] if (self.roi_center[1] + self.roi_size[1]) > self.globals['image'].shape[0] else (self.roi_center[1] + self.roi_size[1])),
                             (0 if 0 > self.roi_center[0] > self.globals['image'].shape[1] else self.roi_center[0],
                              self.globals['image'].shape[1] if (self.roi_center[0] + self.roi_size[0]) >self.globals['image'].shape[1] else ( self.roi_center[0] + self.roi_size[0]))
                            ]
        self.new_data = impr.Image_Basics(self.globals['image'][self.image_bounds[0][0]:self.image_bounds[0][1],
                                                            self.image_bounds[1][0]:self.image_bounds[1][1]],subs_bgnd=self.subs_bgnd)
        # print(new_data.image.shape)
        self.globals['image'][self.image_bounds[0][0]:self.image_bounds[0][1],self.image_bounds[1][0]:self.image_bounds[1][1]] = self.new_data.image
        # self.win.resize(*self.globals['image'].shape)

        self.img.setImage(self.globals['image'],autoRange=True, autoLevels=False,autoHistogramRange=False,autoDownsample=True)
        # wx, wy = self.img.pixelSize()
        # if wx != wy:
        #     # self.win.scaleToImage(self.img)
        #     print(wx,wy)
        #     # self.img.setRect(QRect(0,0,self.img.width(), self.img.height()*wx/wy))
        #     self.img.setTransform(QTransform().fromScale(1,wy/wx))
        #     print(self.img.pixelSize())
        self.img2.setImage(self.globals['image2'], autoRange=False, autoLevels=False, autoHistogramRange=False,autoDownsample=False)

        if self.img.qimage is None:
            self.img.render()
        if self.img.qimage:
            try:
                # exporter = pg.exporters.ImageExporter(self.img.qimage)
                # self.globals['imgExport'] = exporter.export(toBytes=True)
                self.globals['imgExport'] = self.img.qimage
                self.signals.imageRendered.emit()
            except Exception as e:
                print(e)
        # new_data = self.process_image()
        if len(self.globals['image_stack']): # if scan is on images have to be saved
            im_name = self.globals['image_stack'].pop(0)
            print('Save image ', im_name, 'at time ',datetime.datetime.now().time())
            # imsave(im_name,self.globals['image'])
            #old
            # imsave(im_name, new_data.image)
            #new
            scipy.misc.toimage(self.new_data.image,cmin=0,cmax=1).save(im_name)
        else:
            print('Recieved image at time ',datetime.datetime.now().time())
        # self.data_processing()
        sthrd = threading.Thread(target=self.data_processing)
        sthrd.start()
        # print('DOne')
        # self.process_image(new_data) # pprocess image - may be this and below should be done in thread, because fits take time
        # self.update_image_info(new_data)
        # self.update_plot(new_data)
        # self.imv.setImage(new_data.image,autoLevels=False,autoHistogramRange=False,autoRange=False)
        # print(self.imv.getHistogramWidget().gradient.colorMap())
        # # old
        # self.imv.setImage(self.globals['image'],autoRange=False, autoLevels=False,autoHistogramRange=False)#, autoLevels=False, autoHistogramRange=False, autoRange=False)
        # self.imv.getHistogramWidget().setHistogramRange(0,0.6)
        # self.imv.getHistogramWidget().setLevels(0, 0.6)
    def routine2(self):
        print('routine2')
    def data_processing(self):
        # here all image analysis is performed
        self.process_image(self.new_data) # pprocess image - may be this and below should be done in thread, because fits take time
        self.update_image_info(self.new_data)
        self.update_plot(self.new_data)
        # self.updateIsocurve() # takes too much process time, 'Go To' for details
        print('Finished image data processing at ', datetime.datetime.now().time())

    def updateROI(self):
        print('updateRoi')
        self.roi_center = [int(self.roi.pos()[0]),int(self.roi.pos()[1])]
        self.roi_size = [int(self.roi.size()[0]),int(self.roi.size()[1])]
        self.w5.cellChanged.disconnect(self.roiTableChanged)
        self.w5.setData(self.getROITableData())
        self.w5.cellChanged.connect(self.roiTableChanged)
        self.config['roi_center'] = self.roi_center
        self.config['roi_size'] = self.roi_size
        self.save_config()
        # print(self.roi.pos())
        # print(self.roi.size())
    def updateROI2(self):
        print('updateRoi2')
        self.roi2_center = np.array(self.roi2.pos(),dtype=int)#[int(v[0]),int(self.roi2.pos()[1])]
        if (self.roi2_center < 0).any():
            self.roi2_center = np.zeros(2)
            self.roi2.setPos(*self.roi2_center)
        # print(self.roi2_center)
        self.roi2_size = np.array(self.roi2.size(),dtype=int)#[int(self.roi2.size()[0]),int(self.roi2.size()[1])]
        # print(self.roi2_center+self.roi2_size, self.globals['image2'].shape)
        # print((self.roi2_center+self.roi2_size - np.array(self.globals['image2'].shape)[::-1]))
        # if ((self.roi2_center+self.roi2_size - np.array(self.globals['image2'].shape)) > 0).any():
        #     self.roi2_size = np.array(self.globals['image2'].shape)[::-1] - self.roi2_center - 1
        #     self.roi2.setSize(self.roi2_size)
        # self.w5.cellChanged.disconnect(self.roiTableChanged)
        # self.w5.setData(self.getROITableData())
        # self.w5.cellChanged.connect(self.roiTableChanged)
        # self.config['roi_center'] = self.roi_center
        # self.config['roi_size'] = self.roi_size
        # self.save_config()
        # print(self.roi.pos())
        # print(self.roi.size())

    def updateIsocurve(self):
        # #old
        # cur_data = pg.gaussianFilter(self.imv.getImageItem().image, (4, 4))
        # self.iso.setParentItem(self.imv.getImageItem())
        cur_data = pg.gaussianFilter(self.img.image, (4, 4))
        # self.iso.setParentItem(self.img)
        self.iso.setData(cur_data) # this line takes too much process time
        self.iso.setLevel(cur_data.max()/np.e)
        self.iso.setZValue(1000)

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
            self.image_data_to_display['x'] = np.array([*[int(x+0.5) for x in data.fit1D_x[:3]],' ',int(data.fit1D_x[1]+0.5)+int(self.roi.pos()[0])],dtype=object)
        else:
            self.image_data_to_display['x'] = np.array(['-']*5, dtype=object)
        if 'fit1D_y' in data.__dict__:
            self.image_data_to_display['y'] = np.array([*[int(x+0.5) for x in data.fit1D_y[:3]],' ',int(data.fit1D_y[1]+0.5)+int(self.roi.pos()[1])],dtype=object)
        else:
            self.image_data_to_display['y'] = np.array(['-'] * 5, dtype=object)
        if'fit2D' in data.__dict__:
            self.image_data_to_display['2D'] = np.array([data.fit2D[0],"%.0f, %.0f"%(data.fit2D[2],data.fit2D[1]),
                                                         "%.0f, %.0f" %(data.fit2D[4],data.fit2D[3]),data.total_small,' '],dtype=object)
        else:
            self.image_data_to_display['2D'] = np.array(['-'] * 5, dtype=object)
        self.w3.clear()
        self.w3.setData(self.image_data_to_display)

    def update_plot(self,data):
        if 'fit1D_x' in data.__dict__ and 'fit1D_y' in data.__dict__:
            # self.all_plot_data['N'].append((data.fit1D_x[0], data.fit1D_y[0], data.fit2D[0]))
            # self.all_plot_data['width'].append((data.fit1D_x[2], data.fit2D[4], data.fit1D_y[2], data.fit2D[3]))
            self.all_plot_data['N'].append((data.fit1D_x[0],data.fit1D_y[0]))
            self.all_plot_data['width'].append((data.fit1D_x[2], data.fit1D_y[2]))
            if len(self.all_plot_data['N']) > self.N_point_to_plot:
                points_to_show = self.N_point_to_plot
            else :
                points_to_show = len(self.all_plot_data['N'])
            # dataN = self.all_plot_data['N'][len(self.all_plot_data['N'])-points_to_show:len(self.all_plot_data['N'])]
            # dataN = np.array(self.all_plot_data['N'][-points_to_show:])
            dataN = np.array(self.all_plot_data['N'])
            # xx = np.arange(-points_to_show,0)+len(dataN)
            xx = np.arange(len(dataN))
            self.w2.setYRange(0,dataN[len(dataN)-points_to_show:len(dataN)].max())
            self.curve11.setData(xx,dataN[:,0])
            self.curve12.setData(xx, dataN[:, 1])
            # self.curve13.setData(xx, dataN[:, 2])
            self.w2.setXRange(len(dataN)-points_to_show, len(dataN))
            # dataW = np.array(self.all_plot_data['width'][-points_to_show:])
            dataW = np.array(self.all_plot_data['width'])
            self.w4.setYRange(0, dataW[len(dataN)-points_to_show:len(dataN)].max())
            self.curve21.setData(xx, dataW[:, 0])
            self.curve22.setData(xx, dataW[:, 1])
            # self.curve23.setData(xx, dataW[:, 2])
            # self.curve24.setData(xx, dataW[:, 3])
            self.w4.setXRange(len(dataN) - points_to_show, len(dataN))

## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    import sys
    # if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
    app = QApplication(sys.argv)
    ex = DisplayWidget()
    ex.show()
    sys.exit(app.exec_())
    # QApplication.instance().exec_()

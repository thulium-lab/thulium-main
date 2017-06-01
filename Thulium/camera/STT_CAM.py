import time
import numpy as np
from ctypes import *
dll = cdll.LoadLibrary('stt_cam.dll')


class Camera:
    """
    Class to control ONE camera
    If you wish to use another camera, create another instance of this class
    DO NOT use same cameras in different instances of this class
    """
    def __init__(self):
        # camHandler
        self.camera = c_void_p() # CSDUCameraDevice* - pointer to a class to control ONE camera
        self.count = c_int()
        self.camera = dll.sdu_open_interface(byref(self.count))

        # camID
        self.index = c_uint()
        self.name = ""

        # exposition params
        self.exp = c_uint()
        self.expMin = c_uint()
        self.expMax = c_uint()

        # gain params
        self.gain = c_uint()
        self.gainOpt = c_uint()
        self.gainMax = c_uint()

        # other params
        self.trig = c_uint()
        self.binning = c_uint()
        self.ROI = (c_uint*4)(0)
        self.size = (c_uint*2)(0)

        self.status = c_uint()
        self.length = c_uint()
        self.buffer = None
        self.temp = None
        self.image = None
        self.gamma = (c_ushort * 4096)()
        dll.sdu_make_gamma_lut_12to16(self.gamma, 1)
        self.time = time.perf_counter()
        return

    def getTime(self):
        oldTime = self.time
        self.time = time.perf_counter()
        return self.time - oldTime
    
    def __del__(self):
        return dll.sdu_close_interface(self.camera)
    
    def getNumberCameras(self):
        return self.count.value
    
    def openCamera(self, index):
        name = (c_char*64)()
        result = dll.sdu_open_camera(self.camera, c_uint(index), byref(name))
        if result:
            return result
        self.getTrig()
        dll.sdu_set_trigmode(self.camera, 2) # software start
        dll.sdu_set_encoding(self.camera, 1) # 1=12bit, 0=8bit

        self.index = index
        self.name = name.value.decode("utf-8")
        
        self.getExp()
        self.getGain()
        self.getROI()
        self.getBinning()
        self.getSize()
        return result

    def getExp(self):
        dll.sdu_get_min_exp(self.camera, byref(self.expMin))
        dll.sdu_get_max_exp(self.camera, byref(self.expMax))
        dll.sdu_get_exp(self.camera, byref(self.exp))
        return self.exp

    def getGain(self):
        dll.sdu_get_opt_gain(self.camera, byref(self.gainOpt))
        dll.sdu_get_max_gain(self.camera, byref(self.gainMax))
        dll.sdu_get_master_gain(self.camera, byref(self.gain))
        return self.gain

    def getTrig(self):
        dll.sdu_get_trigmode(self.camera, byref(self.trig))
        return self.trig

    def getBinning(self):
        dll.sdu_get_binning(self.camera, byref(self.binning))
        return self.binning

    def getROI(self):
        x=c_uint()
        y=c_uint()
        dll.sdu_get_roi_org(self.camera, byref(x), byref(y))
        self.ROI[0]=x
        self.ROI[1]=y
        dll.sdu_get_roi_size(self.camera, byref(x), byref(y))
        self.ROI[2]=x
        self.ROI[3]=y
        self.length = c_uint(int(self.ROI[2] * self.ROI[3] * 3 / 2))
        self.buffer = (c_ubyte*int(self.length.value))()
        self.temp = (c_ushort*int(self.ROI[2]*self.ROI[3]))()
        # self.image = [[0]*self.ROI[3]]*self.ROI[2]
        return self.ROI

    def getSize(self):
        dll.sdu_get_sensor_width(self.camera, byref(self.size, 0))
        dll.sdu_get_sensor_height(self.camera, byref(self.size, 1))
        return self.size

    def setExp(self, exp):
        exp = min(exp, self.expMax)
        exp = max(exp, self.expMin)
        if self.exp.value == exp:
            return exp
        self.exp.value = exp
        dll.sdu_set_exp(self.camera, byref(self.exp))
        return self.getExp()
    
    def setGain(self, gain = 0):
        gain = min(gain, self.gainMax)
        gain = max(gain, self.gainOpt)
        if self.gain.value == gain:
            return gain
        self.gain.value = gain
        dll.sdu_set_master_gain(self.camera, byref(self.gain))
        return self.getGain()
    
    def setTrig(self, trig):
        if trig!=1 and trig!=2:
            return -1
        if self.trig.value == trig:
            return trig
        self.trig.value = trig
        # set trigger to external only on start
        # dll.sdu_set_trigmode(self.camera, self.trig)
        return trig
    
    def setBinning(self, binning):
        binning = min(binning, 3)
        binning = max(binning, 0)
        if self.binning.value == binning:
            return binning
        self.binning.value = binning
        dll.sdu_set_binning(self.camera, self.binning)
        # optimal gain may have changed
        self.getGain()
        # ROI should have become default for new binning
        self.getROI()
        return self.getBinning()

    def setROI(self, ROI):
        self.ROI[0] = round(ROI[0]/2)*2
        self.ROI[1] = round(ROI[1]/2)*2
        self.ROI[2] = round(ROI[2]/4)*4
        self.ROI[3] = round(ROI[3]/4)*4
        dll.sdu_set_roi_org(self.camera, self.ROI[0], self.ROI[1])
        dll.sdu_set_roi_size(self.camera, self.ROI[2], self.ROI[3])
        return self.getROI()
    
    def getStatus(self):
        dll.sdu_get_status(self.camera, byref(self.status))
        return self.status.value

    def clearFIFO(self):
        return dll.sdu_fifo_init(self.camera)

    def start(self):
        if self.busy():
            self.clearFIFO()
        if self.trig.value == 1:
            dll.sdu_set_trigmode(self.camera, self.trig)
        # else:
        #     dll.sdu_cam_start(self.camera)
        return self.ROI[2]*self.ROI[3]

    def stop(self):
        if self.trig == 1:
            return dll.sdu_set_trigmode(self.camera, 2)
        if self.getStatus() & 2:
            return dll.sdu_cam_stop(self.camera)
        return 0

    def wait(self, timeout=10):
        error = False
        t = time.perf_counter()
        while self.getStatus() & 8:
            # fifo empty
            time.sleep(0.01)
            if time.perf_counter() - t > timeout:
                error = True
                break
        if error:
            self.stop()
            return -1
        return 0

    def busy(self):
        return self.getStatus() & 8

    def read(self):
        if self.trig != 1:
            dll.sdu_cam_start(self.camera)
            self.wait()
        length = c_uint()
        dll.sdu_read_data(self.camera, self.buffer, self.length, byref(length))
        dll.sdu_bw_convert_12to16(self.buffer, self.temp, None, self.ROI[2], self.ROI[3])
        self.image = np.reshape(self.temp, (-1,self.ROI[2])).transpose()
        return self.length != length


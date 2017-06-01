import os
from ctypes import *
dll = cdll.LoadLibrary('stt_cam.dll')

class Camera:
    """
    Class to control ONE camera
    If you wish to use another camera, create another instance of this class
    DO NOT use same cameras in different instances of this class
    """
    def __init__(self):
        self.camera = c_void_p() # CSDUCameraDevice* - pointer to a class to control ONE camera
        self.count = c_int()
        self.camera = dll.sdu_open_interface(byref(self.count))
        return
    
    def __del__(self):
        return dll.sdu_close_interface(self.camera)
    
    def getNumberCameras(self):
        return self.count.value
    
    def openCamera(self, index):
        name = create_string_buffer(64)
        result = dll.sdu_open_camera(self.camera, c_uint(index), name)
        if not result:
            return result
        self.index = index
        self.name = name.value
        self.expMin = c_uint()
        self.expMax = c_uint()
        dll.sdu_get_min_exp(self.camera, byref(self.expMin))
        dll.sdu_get_max_exp(self.camera, byref(self.expMax))
        return result
    
    def setExp(self, exp):
        self.exp = c_uint(exp)
        if self.exp<self.expMin or self.exp>self.expMax:
            return -1
        result = dll.sdu_set_exp(self.camera, byref(self.exp))
        if (result == 3):
            result = 0
        return result
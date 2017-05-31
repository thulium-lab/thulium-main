import threading
import time
import numpy as np
data = {'img':[0,0]}
import os
class Bgnd_Thread(threading.Thread):

    def __init__(self,folder,data,suffics='.tiff'):
        threading.Thread.__init__(self)
        self.data = data
        self.folder = folder
        self.suffics = suffics
        # thread.daemon = True                            # Daemonize thread

    def run(self):
        """ Method that runs forever """
        os.chdir(self.folder)
        from scipy.misc import imread
        # from matplotlib.pyplot import imread
        print('look for images in ', self.folder)
        for f in os.listdir():
            os.remove(f)
        while True:
            if len(os.listdir()):
                f = os.listdir()[0]
                if f.endswith(self.suffics):
                    while(True):
                        try:
                            time.sleep(0.15)
                            self.data['img'] = imread(f)
                            os.remove(f)
                            break;
                        except OSError:
                            time.sleep(0.05)
                            print('w0.05',end=' ')
                    print(f)

example = Bgnd_Thread(data=data,folder=r'Z:\Cam')
example.start()
#test
for i in range(10):
    time.sleep(3)
    print(len(data['img']))
import threading
import time
import numpy as np
# data = {'img':[0,0]}
import os
class Bgnd_Thread(threading.Thread):

    def __init__(self,image_folder,globals=None,signals=None,suffics='.tiff'):
        threading.Thread.__init__(self)

        self.globals = globals if globals != None else {'image':None, 'image_updated':False}
        self.signals = signals
        self.folder = image_folder
        self.suffics = suffics
        # thread.daemon = True                            # Daemonize thread

    def run(self):
        """ Method that runs forever """
        # os.chdir(self.folder)
        from scipy.misc import imread
        # from matplotlib.pyplot import imread
        print('look for images in ', self.folder)
        for f in os.listdir(self.folder):
            os.remove(os.path.join(self.folder,f))
        while True:
            if len(os.listdir(self.folder)):
                f = os.listdir(self.folder)[0]
                if f.endswith(self.suffics):
                    while(True):
                        try:
                            time.sleep(0.15)
                            self.globals['image'] = imread(os.path.join(self.folder,f))
                            self.globals['imaged_updated'] = True
                            os.remove(os.path.join(self.folder,f))
                            self.signals.newImageRead.emit()
                            break
                        except OSError:
                            time.sleep(0.05)
                            print('w0.05',end=' ')
                    print(f)

if __name__ == '__main__':
    example = Bgnd_Thread(image_folder=r'Z:\Camera')
    example.start()
#test
# for i in range(10):
#     time.sleep(3)
#     print(len(data['img']))
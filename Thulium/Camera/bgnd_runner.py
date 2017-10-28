import os, time, datetime, threading
import numpy as np


class Bgnd_Thread(threading.Thread):

    def __init__(self,image_folder,globals=None,signals=None,suffics='.tiff'):
        threading.Thread.__init__(self)

        self.globals = globals if globals != None else {'image':None, 'image_updated':False}
        self.signals = signals
        self.folder = image_folder
        self.folder2 = image_folder+'2'
        self.suffics = suffics
        self.daemon = True # daemonize thread
        self._stop = False # know when to stop

    def run(self):
        """ Method that runs forever """
        # os.chdir(self.folder)
        from scipy.misc import imread
        # from matplotlib.pyplot import imread
        print('look for images in ', self.folder, ' and ', self.folder2)
        for f in os.listdir(self.folder):
            os.remove(os.path.join(self.folder,f))
        for f in os.listdir(self.folder2):
            os.remove(os.path.join(self.folder2, f))
        while not self._stop:
            if len(os.listdir(self.folder)):
                f = os.listdir(self.folder)[0]
                if f.endswith(self.suffics):
                    while(True):
                        try:
                            time.sleep(0.05)
                            img = imread(os.path.join(self.folder,f)).T
                            # print(img.min())
                            img = img >> 4
                            img = img / (1 << 12)
                            # print(img.min())
                            img = np.array([row - row.min() for row in img])
                            self.globals['image'] = img
                            # print(self.globals['image'][:5,:2])
                            self.globals['imaged_updated'] = True
                            os.remove(os.path.join(self.folder,f))
                            print('Image ',f, 'read at ',datetime.datetime.now().time())
                            self.signals.newImageRead.emit()
                            break
                        except OSError:
                            time.sleep(0.05)
                            # print('w0.05',end=' ')
            if len(os.listdir(self.folder2)):
                print('-1-')
                f = os.listdir(self.folder2)[0]
                if f.endswith(self.suffics):
                    print('-2-')
                    while (True):
                        try:
                            time.sleep(0.05)
                            img = imread(os.path.join(self.folder2, f)).T
                            # print(img.min())
                            img = img >> 4
                            img = img / (1 << 12)
                            # print(img.min())
                            img = np.array([row - row.min() for row in img])
                            self.globals['image2'] = img
                            # print(self.globals['image'][:5,:2])
                            self.globals['imaged2_updated'] = True
                            os.remove(os.path.join(self.folder2, f))
                            print('Image ', f, 'read at ', datetime.datetime.now().time())
                            self.signals.newImage2Read.emit()
                            break
                        except OSError:
                            time.sleep(0.05)
                    # print(f)
            time.sleep(0.001)

    def stop(self):
        self._stop = True

if __name__ == '__main__':
    example = Bgnd_Thread(image_folder=r'Z:\Camera')
    example.start()
#test
# for i in range(10):
#     time.sleep(3)
#     print(len(data['img']))
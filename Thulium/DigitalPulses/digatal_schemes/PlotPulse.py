from PyQt5.QtCore import ( Qt, QTimer)
import matplotlib
matplotlib.use('Qt5Agg',force=True)
from PyQt5.QtWidgets import (QApplication)
import pyqtgraph as pg
import numpy as np

class PlotPulse(pg.GraphicsWindow):
    def __init__(self,parent=None,globals={},signals=None,**argd):
        self.signals = signals
        self.parent=parent
        self.globals = globals
        super().__init__(title="PulsePlot")
        # self.resize(600, 600)
        self.signals.anyPulseChange.connect(self.updatePlot)
        self.updatePlot()

    def updatePlot(self):
        """used as a slot called by Pulses class to redraw pulses
            CAN BE DONE IN THREAD"""
        self.plotPulses2(self.globals['Pulses']['pulse_output'],self.globals['Pulses']['t_first'],
                         self.globals['Pulses']['digital_channels'],self.globals['Pulses']['analog_channels'])


    def plotPulses2(self, output_data, t_first, digital_channels=None, analog_channels=None):
        print('PlotPulses2')
        self.clear()    # clear plot
        d_plot = self.addPlot()
        digital_hight=1.2   # place for each curve of height=1
        digital_counter = 0 # number of plotted channel
        dig_list=[]     # list of active digital channels
        # for analog puslses -- not used now
        # analog_counter = 0
        # self.nextRow()
        # a_plot = self.addPlot()
        # analog_out = []
        for name in reversed(sorted(output_data,key=lambda x:int(x,base=16))):
            if name in digital_channels:
                dig_list.append(name)
                value = output_data[name]
                xx = []
                yy = []
                # construct points to show
                for i, point in enumerate(value):
                    if i == 0:
                        xx.append(t_first-(100 if t_first > 100 else t_first))
                        yy.append(point[1])
                        continue
                    if (not i == 0) and (not i == (len(value) - 1)):
                        xx.append(point[0])
                        yy.append(not point[1])
                    xx.append(point[0])
                    yy.append(point[1])
                d_plot.plot(xx,np.array(yy)+digital_counter*digital_hight) # plot data
                d_plot.plot(xx, np.ones_like(xx)*digital_counter*digital_hight,
                                pen=pg.mkPen('w', width=0.5, style=Qt.DashLine)) # plot zero
                digital_counter += 1
            # TODO plot analogs
            # elif name in analog_channels:
            #     local_plot = a_plot
            #
            #     # xx, yy = list(zip(*output_data[name][1:]))
            #     # local_plot.plot(xx,yy)
            #     analog_counter += 1
            # else:
            #     print('Wrong channel')
            #     return -1
                # QMessageBox.warning(self, 'Message', "Not equal length of params", QMessageBox.Yes)
        # set tiks names
        if 'channels_affiliation' in self.globals:
            tiks_names = ['\n'.join([x] + list(set(self.globals['channels_affiliation'][x]))) for x in dig_list]
        else:
            tiks_names = dig_list
        d_plot.getAxis('left').setTicks([list(zip((np.arange(len(dig_list))+1/2)*digital_hight,tiks_names))])



if __name__=='__main__':
    import sys
    app = QApplication(sys.argv)
    mainWindow = PlotPulse()
    mainWindow.show()
    sys.exit(app.exec_())
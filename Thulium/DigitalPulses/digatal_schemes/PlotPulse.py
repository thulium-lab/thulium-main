from PyQt5.QtCore import (QLineF, QPointF, QRectF, Qt, QTimer)
from PyQt5.QtGui import (QBrush, QColor, QPainter)
import matplotlib
matplotlib.use('Qt5Agg',force=True)
from PyQt5.QtWidgets import (QApplication)
import pyqtgraph as pg
import numpy as np
# output_data = {'A0': [(0, 0), (1.0, 1), (1110.0, 1)], '11': [(0, 0), (1.0, 1), (1000.0, 0), (1110.0, 0)], '9': [(0, 0), (1.0, 1), (1000.0, 0), (1110.0, 0)], '10': [(0, 0), (1.0, 1), (1100.0, 0), (1110.0, 0)], '12': [(0, 1), (1100.0, 0), (1110.0, 0)]}

class PlotPulse(pg.GraphicsWindow):
    def __init__(self,parent=None,globals={},**argd):
        self.parent=parent
        self.globals = globals
        super().__init__(title="PulsePlot")
        # self.resize(600, 600)
        if 'Signals' in self.globals and 'Pulses' in self.globals['Signals']:
            self.globals['Signals']['Pulses']['onAnyChange'].connect(self.updatePlot)
        else:
            self.parent.slots_to_bound.append(lambda : self.globals['Signals']['Pulses']['onAnyChange'].connect(self.updatePlot))
        self.updatePlot()
        # self.show()

    def updatePlot(self):
        """used as a slot called by Pulses class to redraw pulses"""
        self.plotPulses2(self.globals['Pulses']['pulse_output'],self.globals['Pulses']['t_first'],
                         self.globals['Pulses']['digital_channels'],self.globals['Pulses']['analog_channels'])

    # def plotPulses(self,output_data,t_first,digital_channels=None,analog_channels=None):
    #     print('PlotPulses')
    #     # self.clear()
    #     for name in sorted(output_data):
    #         value = output_data[name]
    #         p = self.addPlot()
    #         xx = []
    #         yy = []
    #         for i,point in enumerate(value[1:]):
    #             if i==0:
    #                 xx.append(t_first)
    #                 yy.append(point[1])
    #                 continue
    #             if (not i==0) and (not i == (len(value[1:])-1)):
    #                 xx.append(point[0])
    #                 yy.append(not point[1])
    #             xx.append(point[0])
    #             yy.append(point[1])
    #         p.setYRange(0,1)
    #         p.plot(xx,yy)
    #         # if i != len(output_data)-1:
    #         #     p.hideAxis('bottom')
    #         p.showGrid(x=True)
    #         self.nextRow()
    #         p.showButtons()
    #         # self.resize(600,100*len(output_data))

    def plotPulses2(self, output_data, t_first, digital_channels=None, analog_channels=None):
        print('PlotPulses2')
        # print(output_data)
        self.clear()
        digital_hight=1.2
        digital_counter = 0
        analog_counter = 0
        d_plot = self.addPlot()
        self.nextRow()
        a_plot = self.addPlot()
        dig_list=[]
        dig_out = []
        analog_out = []
        for name in reversed(sorted(output_data)):
            if name in digital_channels:
                dig_list.append(name)
                local_plot = d_plot
                value = output_data[name]
                xx = []
                yy = []
                for i, point in enumerate(value):
                    if i == 0:
                        xx.append(t_first-100)
                        yy.append(point[1])
                        continue
                    if (not i == 0) and (not i == (len(value) - 1)):
                        xx.append(point[0])
                        yy.append(not point[1])
                    xx.append(point[0])
                    yy.append(point[1])
                local_plot.plot(xx,np.array(yy)+digital_counter*digital_hight)
                local_plot.plot(xx, np.ones_like(xx)*digital_counter*digital_hight,pen=pg.mkPen('w', width=0.5, style=Qt.DashLine)    )
                digital_counter += 1

            elif name in analog_channels:
                local_plot = a_plot
                xx, yy = list(zip(*output_data[name][1:]))
                local_plot.plot(xx,yy)
                analog_counter += 1
            else:
                print('Wrong channel')
                return -1
                # QMessageBox.warning(self, 'Message', "Not equal length of params", QMessageBox.Yes)
        print([np.arange(1,len(dig_list)+1)*digital_hight,dig_list])
        d_plot.getAxis('left').setTicks([list(zip((np.arange(len(dig_list))+1/2)*digital_hight,dig_list))])
        # self.resize(700, 30 * len(output_data))
        # self.resize()
            # p.setYRange(0, 1)
            # p.plot(xx, yy)
            # if i != len(output_data)-1:
            #     p.hideAxis('bottom')
            # p.showGrid(x=True)
            # self.nextRow()
            # p.showButtons()
            # self.resize(600, 100 * len(output_data))



if __name__=='__main__':
    import sys
    app = QApplication(sys.argv)
    mainWindow = PlotPulse()
    mainWindow.show()
    sys.exit(app.exec_())
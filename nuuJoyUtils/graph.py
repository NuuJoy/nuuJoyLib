#!/usr/bin/python3


import sys
import tkinter
import pyqtgraph
from pyqtgraph.Qt import QtGui, QtCore


__version__ = (2021,1,26,'beta')


class simpleContinuousPlot():
    '''
    Simple continuous graph plot using pyqtgraph module
        Purpose:
            Visualize data in real-time. Working with constantRateAcquisition module
        Example:
            batch_setting = [{'name':'accl_x','key':'x',
                              'sharevar':shareDict_accl,'sharelock':dataAcqs.sv_lock,
                              'x_range':250,'y_range':(-1.05,1.05),'color':'r'},
                             {'name':'accl_y','key':'y',
                              'sharevar':shareDict_accl,'sharelock':dataAcqs.sv_lock,
                              'x_range':250,'y_range':(-1.05,1.05),'color':'g'},]
            graph = simpleContinuousPlot(rate_hz=50.0,
                                         batch_setting=batch_setting,
                                         shareEvent=shareEvent)
            graph.continuous_plot()
    '''
    class XYCurves():
        def __init__(self,canvas,name,key,sharevar,sharelock,x_range,y_range,color):
            self.name      = name
            self.key       = key
            self.sharevar  = sharevar
            self.sharelock = sharelock
            self.x_range   = x_range
            self.y_data    = []
            self.buff      = []
            # subplot = pyqtgraph.PlotItem(parent=canvas,title=self.name)
            self.subplot = canvas.addPlot(title=self.name)
            self.subplot.setXRange(0, x_range, padding=0)
            self.subplot.setYRange(min(y_range), max(y_range), padding=0)
            #self.subplot.enableAutoRange('xy', False)
            self.subplot.setMouseEnabled(x=False, y=True)
            self.curves = self.subplot.plot(pen=color)
        def update(self):
            if self.sharevar[self.key]:
                with self.sharelock:
                    data = self.sharevar[self.key].copy()
                    self.sharevar[self.key] = []
                self.y_data = (self.y_data + data)[-self.x_range:]
                self.curves.setData(self.y_data)
    def __init__(self,rate_hz,batch_setting,shareEvent):
        # define plot setting and init canvas
        pyqtgraph.setConfigOptions(antialias=True)
        self.rate_hz    = rate_hz
        self.shareEvent = shareEvent
        root = tkinter.Tk()
        canvas_width  = int(root.winfo_screenwidth()/4.0)
        canvas_height = int(root.winfo_screenheight()/2.0)
        self.canvas = pyqtgraph.GraphicsLayoutWidget(title='pygraph_simpleContinuousPlot',
                                                size=(canvas_width,canvas_height),
                                                show=True,)
        self.subplots = {}
        for setting in batch_setting:
            self.subplots[setting['name']] = self.XYCurves(canvas=self.canvas,
                                                           key=setting['key'],
                                                           name=setting['name'],
                                                           sharevar=setting['sharevar'],
                                                           sharelock=setting['sharelock'],
                                                           x_range=setting['x_range'],
                                                           y_range=setting['y_range'],
                                                           color=setting['color'])
            self.canvas.nextRow()
    def updater(self):
        for subplot in self.subplots.values():
            subplot.update()
    def continuous_plot(self):
        timer = QtCore.QTimer()
        timer.timeout.connect(self.updater)
        timer.start(1000.0/self.rate_hz)
        # start run app
        if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
            QtGui.QApplication.instance().exec_()
        self.shareEvent.set()


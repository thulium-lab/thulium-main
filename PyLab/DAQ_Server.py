import PyDAQmx as dq
import numpy as np
import ctypes
import time
import datetime

from math import gcd


class DigitalOutput(dq.Task):
    """
    Wrapper of a standard class 'Task', specifically designed
    to continiously generate repeated DO pulses
    Usage:
    __init__(func=None) - create, generate default output (zeros)
        func(count) - callback function, after every period
    run(data=zeros) - write and run
    stop() - stops
        it is possible to explicitly call
        but not necessary (called implicitly when adding new data)
    __del__ - clean on destruction
    """
    def __init__(self, func = None):
        dq.Task.__init__(self)
        self.count = 0
        # you need to ClearTask() every time you want to delete channel from task
        # it may happen too often. Maybe? suggestion:
        # use all channels every time, just fill unused with zeros
        # no other task will be able to use these channels anyway
        # so let's handle all of them, plus 'ChanForAllLines' just feels better
        # cons: consumes 4 times more memory for 1-line output
        # pros: consumes 8 times less memory for 32-line output
        self.CreateDOChan('Dev1/port0', "", dq.DAQmx_Val_ChanForAllLines)
        self.running = False
        self.wait = 0
        self.write()
        self.run()
        self.func = func
        self.time = time.perf_counter()

    def getCount(self):
        return self.count

    def setFunc(self, func):
        self.func = func
        return

    def write(self, data = np.array([0,0], dtype=np.uint32), rate = 2, samples = 2):
        self.stop()
        self.CfgSampClkTiming("", rate, dq.DAQmx_Val_Rising,
                              dq.DAQmx_Val_ContSamps, samples)
        # if self._EveryNSamplesEvent_already_register:
        #     self.RegisterEveryNSamplesEvent(dq.DAQmx_Val_Transferred_From_Buffer, samples, 0,
        #                                     ctypes.cast(None, dq.DAQmxEveryNSamplesEventCallbackPtr), None)
        # self.AutoRegisterEveryNSamplesEvent(dq.DAQmx_Val_Transferred_From_Buffer, samples, 0)
        if samples > 2:
            if self._EveryNSamplesEvent_already_register:
                self.RegisterEveryNSamplesEvent(dq.DAQmx_Val_Transferred_From_Buffer, samples, 0,
                                                ctypes.cast(None, dq.DAQmxEveryNSamplesEventCallbackPtr), 0)
                self._EveryNSamplesEvent_already_register = False
            self.AutoRegisterEveryNSamplesEvent(dq.DAQmx_Val_Transferred_From_Buffer, samples, 0)
        self.wait = samples/rate
        self.WriteDigitalU32(samples, 0, 10.0,
                             dq.DAQmx_Val_GroupByChannel,
                             data, None, None)
        return

    def run(self):
        self.count = 0
        self.time = time.perf_counter()
        self.running = True
        return self.StartTask()

    def stop(self):
        if not self.running:
            return 0
        self.running = False
        return self.StopTask()

    def idle(self):
        return 0

    def EveryNCallback(self):
        if not self.running:
            return 0
        timeOld = self.time
        self.time = time.perf_counter()
        if abs(self.time-timeOld) < 0.001:
            return 0
        self.count += 1
        if self.func:
            self.func(self.count)
        return 0

    def __del__(self):
        self.func = None
        self.write()
        self.run()
        self.stop()
        self.ClearTask()

AON = 4


class AnalogOutput(dq.Task):
    """
    Wrapper of a standard class 'Task', specifically designed
    to continiously generate repeated AO pulses synced with DO
    Usage:
    __init__(sync=True) - create, generate default output (zeros)
        sync - to sync or not to sync
    run(data=zeros) - write and run
    stop() - stops
        it is possible to explicitly call
        but not necessary (called implicitly when adding new data)
    __del__ - clean on destruction (for the sake of NI board, not garbage collection)
    """
    def __init__(self, sync=True):
        dq.Task.__init__(self)
        self.sync = sync
        self.running = False
        for line in range(0,4):
            self.CreateAOVoltageChan('Dev1/ao'+str(line), "", -10.0,
                                     10.0, dq.DAQmx_Val_Volts, None)
        self.write()
        self.run()

    def setSync(self, sync):
        self.sync = sync
        return

    def write(self, data=np.array([0 for x in range(AON*2)], dtype=np.double), rate=2, samples=2):
        self.stop()
        self.CfgSampClkTiming("", rate, dq.DAQmx_Val_Rising,
                              dq.DAQmx_Val_ContSamps, samples)
        if (self.sync):
            self.CfgDigEdgeStartTrig('/Dev1/do/StartTrigger',
                                     dq.DAQmx_Val_Rising)
        self.WriteAnalogF64(samples, 0, 10.0,
                            dq.DAQmx_Val_GroupByChannel,
                            data, None, None)
        return

    def run(self):
        self.running = True
        return self.StartTask()

    def stop(self):
        if not self.running:
            return 0
        self.running = False
        return self.StopTask()

    def __del__(self):
        self.sync = False
        self.write()
        self.run()
        self.stop()
        self.ClearTask()


class DAQHandler:
    """
    Handles DO and AO channels
    Usage:
    __init__(func=None, sync=True) - create, generate zeros on channels
        func(count) - callback function, after each period
        sync - to sync or not to sync
    write(data=zeros) - write data to NI
        use write() to make everything zero
    run() - start a non-running task
    stop() - stop a running task
    __del__ - clean on destruction
    """
    def __init__(self, func=None, sync=True):
        self.DO = DigitalOutput(func)
        self.AO = AnalogOutput(sync)

    def setFunc(self, func):
        return self.DO.setFunc(func)

    def setSync(self, sync):
        return self.AO.setSync(sync)

    def write(self, data={}):
        print('writing to DAQ')
        p = 10000
        if (len(data) == 0):
            self.AO.write()
            return self.DO.write()

        DOtimes = set()
        AOtimes = set()
        AOpattern = 'A'
        DOchans = {}
        AOchans = {}
        for chan in data:
            if (chan[0] == AOpattern):
                AOchans[int(chan[1])] = data[chan]
                for point in data[chan]:
                    AOtimes.add(int(point[0]*p+0.5))
            else:
                DOchans[int(chan)] = data[chan]
                for point in data[chan]:
                    DOtimes.add(int(point[0]*p+0.5))
        DOtimes = sorted(DOtimes)
        AOtimes = sorted(AOtimes)
        DOdt = DOtimes[1] - DOtimes[0]
        AOdt = DOdt
        if len(AOtimes) >= 2:
            AOdt = AOtimes[1] - AOtimes[0]
        for i in range(1, len(DOtimes)):
            DOdt = gcd(DOdt, DOtimes[i] - DOtimes[i-1])
            # print(DOdt, DOtimes[i], DOtimes[i-1])
        for i in range(1, len(AOtimes)):
            AOdt = gcd(AOdt, AOtimes[i] - AOtimes[i-1])
        DOdt /= p
        AOdt /= p
        DOtimes = [x/p for x in DOtimes]
        AOtimes = [x/p for x in AOtimes]
        for chan in DOchans:
            DOchans[chan][-1] = (DOchans[chan][-1][0]-DOdt, DOchans[chan][-1][1])
        for chan in AOchans:
            AOchans[chan][-1] = (AOchans[chan][-1][0]-AOdt, AOchans[chan][-1][1])
        trigger = 31
        DOchans[trigger] = [(0,1),(np.ceil(1./DOdt)*DOdt,0),(DOtimes[-1],0)]
        DOsamples = round((DOtimes[-1] - DOtimes[0])/DOdt)
        AOsamples = DOsamples
        if len(AOtimes) >= 2:
            #AOsamples = round((AOtimes[-1] - AOtimes[0])/AOdt).astype(int)
            AOsamples = int(round((AOtimes[-1] - AOtimes[0]) / AOdt))
        DOrate = 1000./DOdt
        AOrate = 1000./AOdt
        DOdata = np.array([0 for x in range(DOsamples)], dtype=np.uint32)
        AOdata = np.array([0 for x in range(AOsamples*AON)], dtype=np.double)

        print("DOsamples - ", DOsamples)
        print("DOrate - ", DOrate)
        print("AOsamples - ", AOsamples)
        print("AOrate - ", AOrate)

        if len(AOtimes):
            print(AOtimes[0], AOtimes[-1])
        err = 1e-6
        for sample in range(DOsamples):
            last = DOdata[sample-1]
            t = DOdt*sample
            for chan in DOchans:
                if abs(DOchans[chan][0][0]-t) < err:
                    V = DOchans[chan].pop(0)[1]
                    if not V:
                        last = last | (1 << chan)
                    else:
                        last = last & ~(1 << chan)
            DOdata[sample] = last
        for sample in range(AOsamples):
            last = [AOdata[x*AOsamples+sample] for x in range(AON)]
            t = AOdt*sample
            for chan in AOchans:
                while abs(AOchans[chan][0][0]-t) < err:
                    last[chan] += AOchans[chan].pop(0)[1]
                    if len(AOchans[chan]) == 0:
                        break
            for i in range(AON):
                AOdata[i*AOsamples+sample] = last[i]
        self.AO.write(AOdata, AOrate, AOsamples)
        return self.DO.write(DOdata, DOrate, DOsamples)

    def run(self):
        self.AO.run()
        return self.DO.run()

    def stop(self):
        self.DO.stop()
        return self.AO.stop()

    def __del__(self):
        del self.AO
        del self.DO


class AnalogInput(dq.Task):
    """
    TODO
    """
    def __init__(self, channels, rate, samples, trigger=None, edge=1):
        dq.Task.__init__(self)
        self.running = False
        for channel in channels:
            self.CreateAIVoltageChan('Dev1/ai'+str(channel), "", dq.DAQmx_Val_Cfg_Default,
                                     -10.0, 10.0, dq.DAQmx_Val_Volts, None)
        self.channels = channels
        self.edge = dq.DAQmx_Val_Rising

    def config(self, rate, samples, trigger=None, edge=1):
        self.CfgSampClkTiming("", rate, dq.DAQmx_Val_Rising, dq.DAQmx_Val_FiniteSamps, samples)
        if edge:
            self.edge = dq.DAQmx_Val_Rising
        else:
            self.edge = dq.DAQmx_Val_Falling
        if trigger:
            self.CfgDigEdgeStartTrigger(trigger, self.edge)

    def start(self):
        self.start()

    def stop(self):
        if not self.running:
            return 0
        self.running = False
        return self.StopTask()

    def __del__(self):
        self.stop()
        self.ClearTask()

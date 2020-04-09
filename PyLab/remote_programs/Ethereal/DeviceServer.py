import socketserver
import socket
import pickle
import traceback,sys

# from device_lib import COMPortDeviceServer
from serial import Serial
from serial.tools import list_ports
from serial import SerialException
import json
json.encoder.FLOAT_REPR = lambda o: format(o, '.4f')
from PyQt5.QtCore import (Qt, QTimer)
import PyDAQmx as dq
import numpy as np
import ctypes
import time
import copy
import datetime
from math import gcd
import threading

HOST,PORT = "192.168.1.15", 9997
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
PORT2 = 9996
sock.settimeout(.001)
sock2.settimeout(0.05)

WM = 'WM'
LOCK_BY_WM = 'LOCK_BY_WM'
def WM_handler(msg,data):
    if len(msg) != 3:
        return None
    channel, meas_time, freq = msg
    if WM not in data:
        data[WM] = {}
    data[WM][channel] = (float(meas_time.strip()),float(freq.strip()))
    # return '%.7f %.7f'%(data[WM][channel][0], data[WM][channel][1])
    return None

def lock_by_WM(msg,data):
    if len(msg) != 1 or WM not in data:
        return ''
    channel = msg[0]
    if channel not in data[WM]:
        return ''
    return '%.7f %.7f'%(data[WM][channel][0], data[WM][channel][1])

handlers ={WM:WM_handler,
           LOCK_BY_WM:lock_by_WM}
debug = True

class COMPortDeviceServer:
    """Class to run on server, connect and transfer data to COM port
    All settings are in corresponding class in main program - this is basically mirror"""
    idn_messege = b"*IDN?"
    def __init__(self):
        print("Init COMPortDeviceServer")
        self.connected = False

    def close(self): # closes port
        self.stream.close()
        self.connected = False
        return True, "Disconnected"

    def connect(self):
        """tries to connect port.
        idn_message - message to be sent to devise to identify it
        If connected returns 0, if not - value < 0 """
        if self.connected:
            if self.debug_mode:
                print("Another conenction to ", self.name)
            return self.sendBack("Connected")
        try:
            p = Serial(self.port, self.baudrate, timeout=self.timeout)
            p.write(self.idn_messege)
            # s = p.readline().decode()
            # if '*IDN?' in s:
            #     p.write(b'system:echo off\r')
            #     p.readline().decode()
            #     p.write(self.idn_messege)
            #     s = p.readline().decode()
            # s = s.split(',')
            # print('Port answer ', s)
            # print('\n' + 'Device connected on port ' + self.port + '\n')
            self.connected = True
            self.stream = p
            # return "Connected"
        except SerialException as e:
            if self.debug_mode:
                print("Exception in connect()")
                print(e)
            self.stream = None
            return self.sendBack("Not Connected - SerialException")

    def write_com(self,command):
        status = True
        if not self.connected:
            return self.sendBack("Not Connected")
        try:
            self.stream.write(command.encode("ascii"))
            return
        except SerialException as e:
            if self.debug_mode:
                print("SerialException in write_com()")
                print(e)
            self.stream = None
            return self.sendBack("SerialException in write_com(%s)"%command)
        return   # return statuus of reading and readout

    def write_read_com(self, command):
        """tries to write command to devise and read it's response"""
        status = True
        readout = ''
        if not self.connected:
            return (False,'Not connected')
        try:
            self.stream.write(command.encode('ascii'))
            readout = self.stream.readline().decode()
        except SerialException as e:
            status = False
            print("EXCEPTION")
            print(e)
        return (status,readout) # return statuus of reading and readout

    def read_serial(self):
        """function to read all data available in serial stream from arduino"""
        data_read = ''
        if self.connected:
            try:
                res = ''
                for i in range(20):
                    s = self.stream.readline().decode()
                    if s =='':
                        break
                    else:
                        res += s
                # print("arduino >>   ",s,end='')
            except SerialException as e:
                if self.debug_mode:
                    print('SerialException in read_serial()')
                    print(e)
                return self.sendBack("SerialException in read_serial())")
                # self.close()
            except Exception as e:
                if self.debug_mode:
                    print("EXCEPTION")
                    print(e)
                self.sendBack("Exception in read_serial())")
            if res == '':
                return
            if self.debug_mode:
                print('>>ARDUINO',repr(res))
            return self.sendBack(res)

    def sendBack(self,msg):
        s_msg = "arduino_readings" + " " + self.name + " " + msg
        sock.sendto(bytes(s_msg, "utf-8"), (HOST,PORT))

class Arduino(COMPortDeviceServer):
    def __init__(self, data):
        super().__init__() # now it should do nothing
        print('INIT Arduino', data["name"])
        self.poll_time = 100
        self.debug_mode = True
        self.__dict__.update(data)
        # self.poll_timer = QTimer()
        # self.poll_timer.setInterval(self.poll_time)
        # self.poll_timer.timeout.connect(self.pollTimerHandler)
        self.poll_timer = threading.Timer(self.poll_time/1000, self.pollTimerHandler)
        self.poll_timer.start()

    def send(self,msg=''):
        if "debug_mode" in msg:
            if "true" in msg.lower():
                self.debug_mode = True
            elif "false" in msg.lower():
                self.debug_mode = False
            return
        else:
            for line in msg.split("\n"):
                return self.write_com(line)

    def read(self): # should not be used now - done with timer
        if self.connected:
            return self.read_serial()

    def pollTimerHandler(self):
        if self.debug_mode:
            print("pollTimerHandler",self.connected)
        # self.poll_timer.stop()
        self.read_serial()
        self.poll_timer = threading.Timer(self.poll_time/1000, self.pollTimerHandler)
        self.poll_timer.start()
        # self.poll_timer.start()
        # self.poll_timer.start()



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

        def __init__(self,parent=None):
            self.parent = parent
            dq.Task.__init__(self)
            self.count = 0
            self.CreateDOChan('Dev1/port0', "", dq.DAQmx_Val_ChanForAllLines)
            self.running = False
            self.written = ctypes.c_int32(0)
            self.AutoRegisterDoneEvent(0)
            # self.write()
            # self.run()
            self.time = time.perf_counter()

        def getCount(self):
            return self.count

        def write(self, data=np.array([0, 0], dtype=np.uint32), rate=2, samples=2):
            self.stop()
            self.CfgSampClkTiming("", rate, dq.DAQmx_Val_Rising,
                                  dq.DAQmx_Val_FiniteSamps, samples)
            # if self._EveryNSamplesEvent_already_register:
            #     self.RegisterEveryNSamplesEvent(dq.DAQmx_Val_Transferred_From_Buffer, samples, 0,
            #                                     ctypes.cast(None, dq.DAQmxEveryNSamplesEventCallbackPtr), None)
            # self.AutoRegisterEveryNSamplesEvent(dq.DAQmx_Val_Transferred_From_Buffer, samples, 0)
            # if samples > 2:
            #     if self._EveryNSamplesEvent_already_register:
            #         self.RegisterEveryNSamplesEvent(dq.DAQmx_Val_Transferred_From_Buffer, samples, 0,
            #                                         ctypes.cast(None, dq.DAQmxEveryNSamplesEventCallbackPtr), 0)
            #         self._EveryNSamplesEvent_already_register = False
            #     self.AutoRegisterEveryNSamplesEvent(dq.DAQmx_Val_Transferred_From_Buffer, samples, 0)

            # self.wait = samples / rate
            self.WriteDigitalU32(samples, 0, 10.0,
                                 dq.DAQmx_Val_GroupByChannel,
                                 data, reserved=None,
                                 sampsPerChanWritten=ctypes.byref(self.written))
            print("samples written = ", self.written.value)
            return

        def DoneCallback(self, status):
            self.stop()
            self.count += 1
            if self.parent:
                self.parent.digitalCicleFinished(self.count)
            return 0

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
            if abs(self.time - timeOld) < 0.001:
                return 0
            self.count += 1
            if self.parent:
                self.parent.digitalCicleFinished(self.count)
            return 0

        def close(self):
            self.write()
            self.run()
            self.stop()
            self.ClearTask()

        def __del__(self):
            self.close()

    class AnalogOutput(dq.Task):
        """
        Wrapper of a standard class 'Task', specifically designed
        to continiously generate repeated AO pulses synced with DO
        Usage:
        __init__(sync=True) - create, generate default output (zeros)
            sync - to sync or not to sync - SET SYNC BY DEFAULT
        run(data=zeros) - write and run
        stop() - stops
            it is possible to explicitly call
            but not necessary (called implicitly when adding new data)
        __del__ - clean on destruction (for the sake of NI board, not garbage collection)
        """

        def __init__(self, parent=None, sync=True):
            self.parent = parent
            dq.Task.__init__(self)
            self.sync = sync
            self.running = False
            for line in range(0, 4):
                self.CreateAOVoltageChan('Dev1/ao' + str(line), "", -10.0,
                                         10.0, dq.DAQmx_Val_Volts, None)
            self.AutoRegisterDoneEvent(0)
            # self.write()
            # self.run()

        def write(self, data=np.array([0 for x in range(4 * 2)], dtype=np.double), rate=2, samples=2):
            """ 4 in data constructor is AON"""
            self.stop()
            self.CfgSampClkTiming("/Dev1/do/SampleClock", rate, dq.DAQmx_Val_Rising,
                                  dq.DAQmx_Val_FiniteSamps, samples)
            if (self.sync):
                self.CfgDigEdgeStartTrig('/Dev1/do/StartTrigger',
                                         dq.DAQmx_Val_Rising)
            self.WriteAnalogF64(samples, 0, 10.0,
                                dq.DAQmx_Val_GroupByChannel,
                                data, None, None)
            return

        def DoneCallback(self, status):
            self.stop()
            return 0

        def run(self):
            self.running = True
            return self.StartTask()

        def stop(self):
            if not self.running:
                return 0
            self.running = False
            return self.StopTask()

        def close(self):
            self.sync = False
            self.write()
            self.run()
            self.stop()
            self.ClearTask()

        def __del__(self):
            self.close()

    def __init__(self, func=None, sync=True):
        self.DO = self.DigitalOutput(parent=self)
        # self.AO = self.AnalogOutput(parent=self)
        self.AON = 4
        self.buffer_written = False
        self.data_to_send={}
        self.t_start = 0
        self.stop_time = 0
        self.new_points = {}
        self.delayed_write=False
        self.runned_after_written = True
        self.start_timer = threading.Timer(.1, self.run)
        # self.start_timer.cancel()

    def connect(self):
        """For DAQ there no need in connection, but here it is for universality of devices"""
        return "Connected"

    def send(self,msg):
        # new version with t_start
        self.t_start = msg["t_start"]
        self.new_points = copy.deepcopy(msg["points"])
        if self.DO.running:
            self.delayed_write = True
        else:
            self.start_timer.cancel()
            if self.runned_after_written:
                self.write(data=self.new_points)
            else:
                self.delayed_write = True
            t = self.t_start/1000 - (time.perf_counter() - self.stop_time)
            print("left to wait bebore starting DAQ", t)
            if t>0:
                self.start_timer = threading.Timer(t, self.run)
                self.start_timer.start()
            else:
                self.run()

        # old
        # if msg == "start":
        #     if not self.buffer_written:
        #         return False, "No data in buffer"
        #     try:
        #         self.run()
        #         print("DAQ_run started")
        #         return True, "DAQ started"
        #     except Exception as e:
        #         print("PROBLEM WITH DAQ")
        #         print(e)
        #         return False, "Problems with DAQ"
        # elif type(msg) == dict:
        #     try:
        #         self.stop()
        #         self.write(msg)
        #         self.run()
        #         return True, "DAQ updated"
        #     except Exception as e:
        #         print("PROBLEM WITH DAQ")
        #         print(e)
        #         return False, "Problems with DAQ"

    def read(self):
        return True, json.dumps(self.data_to_send)

    def write(self, data={}):
        print('writing to DAQ')
        # print(data)
        p = 10000
        if (len(data) == 0):
            # self.AO.write()
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
                DOchans[int(chan[1:])] = data[chan]
                for point in data[chan]:
                    DOtimes.add(int(point[0]*p+0.5))
        DOtimes = sorted(DOtimes)
        AOtimes = sorted(AOtimes)
        final = int(DOtimes[-1] + 10*p+0.5)
        DOtimes.append(final)
        for chan in DOchans:
            DOchans[chan].append([final/p, DOchans[chan][-1][1]])
        if len(AOtimes):
            final = int(AOtimes[-1] + 10*p+0.5)
            AOtimes.append(final)
            for chan in AOchans:
                AOchans[chan].append([final/p, AOchans[chan][-1][1]])

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
            # if DOchans[chan][-1][0] < DOtimes[-1]:
            #     DOchans[chan].append(DOtimes[-1], DOchans[-1][1])
            DOchans[chan][-1] = (DOchans[chan][-1][0]-DOdt, DOchans[chan][-1][1])
        for chan in AOchans:
            # if AOchans[chan][-1][0] < AOtimes[-1]:
            #     AOchans[chan].append(AOtimes[-1], AOchans[-1][1])
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
        AOdata = np.array([0 for x in range(AOsamples*self.AON)], dtype=np.double)

        print("DOsamples - ", DOsamples)
        print("DOrate - ", DOrate)
        print("AOsamples - ", AOsamples)
        print("AOrate - ", AOrate)

        if len(AOtimes):
            print(AOtimes[0], AOtimes[-1])
        err = 1e-6
        for sample in range(DOsamples):
            #print(sample)
            last = DOdata[sample-1]
            t = DOdt*sample
            #print(sample)
            #print(DOchans)
            for chan in DOchans:
                if not len(DOchans[chan]):
                    continue
                #print(chan)
                if abs(DOchans[chan][0][0]-t) < err:
                    V = DOchans[chan].pop(0)[1]
                    if not V:
                        last = last | (1 << chan)
                    else:
                        last = last & ~(1 << chan)
            DOdata[sample] = last
        #print("sdfkh")
        for sample in range(AOsamples):
            #print(sample)
            last = [AOdata[x*AOsamples+sample] for x in range(self.AON)]
            t = AOdt*sample
            for chan in AOchans:
                while abs(AOchans[chan][0][0]-t) < err:
                    last[chan] += AOchans[chan].pop(0)[1]
                    if len(AOchans[chan]) == 0:
                        break
            for i in range(self.AON):
                AOdata[i*AOsamples+sample] = last[i]
        #print("befor finil write to DAQ")
        self.buffer_written = True
        self.runned_after_written = False
        # self.AO.write(AOdata, AOrate, AOsamples)
        return self.DO.write(DOdata, DOrate, DOsamples)

    def digitalCicleFinished(self,count):
        # self.data_to_send={"count":count}
        self.stop_time = time.perf_counter()
        self.DO.running = False
        print("cicle_finished")
        sock.sendto(bytes("cicle_finished " + str(count), "utf-8"), (HOST,PORT))
        if self.delayed_write:
            if self.runned_after_written:
                self.delayed_write = False
                self.write(data=self.new_points)
            else:
                self.delayed_write = True
        if self.t_start == 0:
            self.run()
        else:
            t = self.t_start/1000 - (time.perf_counter() - self.stop_time)
            if t>0:
                self.start_timer = threading.Timer(t, self.run)
                self.start_timer.start()
            else:
                self.run()
    def run(self):
        # self.AO.run()
        self.runned_after_written = True
        return self.DO.run()

    def stop(self):
        self.DO.stop()
        return# self.AO.stop()

    def close(self):
        # self.AO.close()
        self.DO.close()

    def __del__(self):
        # del self.AO
        del self.DO

N = 1000
class DAQin(dq.Task):
    def __init__(self, parent=None, sync=True):
        self.parent = parent
        dq.Task.__init__(self)
        self.lines = {}
        self.running = False
        self.read = dq.int32()
        self.readTotal = 0
        self._data = np.zeros(N)
        self.data = {}
        self.limits = {}
        self.samples = 1
        self.stopAfter = False
        self.AutoRegisterDoneEvent(0)
        self.TCPconnected = False

    def createTask(self, limits, lines):
        # self.DAQmxTaskControl(dq.DAQmx_Val_Task_Abort)
        self.limits = limits

        for line in lines:
            cfg = dq.DAQmx_Val_Cfg_Default
            if line[1:] == '23':
                cfg = dq.DAQmx_Val_Diff
            self.CreateAIVoltageChan('Dev1/ai' + str(line[1:]), "",
                                     cfg, limits.get(line,(-10,10))[0],
                                     limits.get(line,(-10,10))[1], dq.DAQmx_Val_Volts, None)
        self._data = np.zeros(N*len(lines))
        self.readTotal = 0

    def configTiming(self,rate,samples):
        self.CfgSampClkTiming("", rate, dq.DAQmx_Val_Rising,
                              dq.DAQmx_Val_FiniteSamps, samples)
        # self.CfgDigEdgeStartTrig("/Dev1/PFI0", DAQmx_Val_Falling)
        self.CfgDigEdgeStartTrig("/Dev1/do/StartTrigger", dq.DAQmx_Val_Falling)


    def prepare(self, lines, rate, samples, limits):
        # lines = {line:[[begin,end],[begin,end]]}
        # limits = {line:(low,high)}
        self.samples = samples
        self.stop()
        # try:
        #     dq.DAQmxTaskControl(self.taskHandle, dq.DAQmx_Val_Task_Unreserve)
        # except Exception as e:
        #     print(self.__dict__)
        #     print(e)
        self.lines = lines
        if not limits == self.limits:
            self.createTask(limits, lines)
        self.configTiming(rate, samples)
        self.AutoRegisterEveryNSamplesEvent(dq.DAQmx_Val_Acquired_Into_Buffer, N, 0)


        pass

    def EveryNCallback(self):
        self.ReadAnalogF64(N, 1.0, dq.DAQmx_Val_GroupByChannel,
                           self._data, N*len(self.lines),
                           ctypes.byref(self.read), None)
        self.appendData()
        return 0

    def appendData(self):
        i = 0
        for line,windows in self.lines.items():
            for j,window in enumerate(windows):
                if self.readTotal > window[1]:
                    continue
                if self.readTotal+self.read.value<window[0]:
                    continue
                begin = max(window[0]-self.readTotal,0) + i
                end = min(self.read.value, window[1]-self.readTotal) + i
                low,high = self.limits[line]
                cut = [int(x*2**14) for x in (self._data[begin:end]-low)/(high-low)]
                self.data[line][j].extend(cut)
                i += self.read.value
        self.readTotal += self.read.value

    def DoneCallback(self, status):
        global sock2, HOST, PORT2
        if self.samples%N != 0:
            self.ReadAnalogF64(-1, 1.0, dq.DAQmx_Val_GroupByChannel,
                               self._data, N*len(self.lines),
                               ctypes.byref(self.read), None)
            self.appendData()
        # for line,data in self.data.items():
        #     for i in range(len(data)):
        #         for x in data[i]:
        #             x = np.round(x,6)
        s = "analog_input " + json.dumps(self.data) + '\n'
        try:
            sock2.connect((HOST, PORT2))
            res = sock2.sendall(bytes(s,'utf-8'))
            if res:
                print("error while sending")
            print("analog input sent", len(s))
            sock2.close()
            sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except Exception as e:
            print("exception while sending", e)
            print(len(s))
            self.TCPconnected = False
        self.stop()
        if not self.stopAfter:
            self.run()
        return 0

    def run(self):
        self.readTotal = 0
        self.data = {}
        self.stopAfter = False
        for line,windows in self.lines.items():
            self.data[line] = []
            for window in windows:
                self.data[line].append([])
        self.running = True
        self.StartTask()

    def stop(self):
        if self.running:
            self.StopTask()
            self.running = False

    def connect(self):
        return "Connected"

    def send(self,msg):
        try:
            self.prepare(msg['lines'], msg['rate'], msg['samples'], msg['limits'])
            self.run()
            return True, "DAQIn updated"
        except Exception as e:
            print("PROBLEM WITH DAQin")
            print(e)
            traceback.print_exc(file=sys.stdout)
            return False, "Problems with DAQin"

    def read(self):
        return True, json.dumps(self.data_to_send)

    def close(self):
        # self.write()
        # self.run()
        self.stop()
        self.ClearTask()

    def __del__(self):
        self.close()


CONSTRUCTORS = {"Arduino":Arduino,
                "DAQ":DAQHandler,
                "DAQin":DAQin}


class MyUDPHandler(socketserver.BaseRequestHandler):
    """
    This class works similar to the TCP handler class, except that
    self.request consists of a pair of data and client socket, and since
    there is no connection the client address must be given explicitly
    when sending data back via sendto().
    """
    all_data = {}
    devices = {}

    def handle(self):
        msg = self.request[0].strip().decode('utf-8')
        sender_socket = self.request[1]
        try:
            task, data = msg.split(' ',maxsplit=1)
        except ValueError as e:
            task = msg
            data = ''
        try:
            data = json.loads(data)
        except json.JSONDecodeError as e:
            data = {}
        print('task:',task, ",data:",data)
        if task == "UpdateCOM":
            available_com_ports = [port.device for port in list(list_ports.comports())]
            print('AvailableCOMs ',available_com_ports)
            sock.sendto(bytes("AvailableCOMs " + json.dumps(available_com_ports), "utf-8"), (HOST,PORT))
        elif task == "Connect":
            print("Devices", self.devices)
            if data["name"] in self.devices:
                self.devices[data['name']].connect()
                # sender_socket.sendto(bytes(res, "utf-8"), self.client_address)
                return
            try:
                d = CONSTRUCTORS[data["device"]](data)
                self.devices[data['name']] = d
                d.connect()
                # print("Result", res)
                # if res != "Connected":
                #     sender_socket.sendto(bytes(res, "utf-8"), self.client_address)
                #     return
                # else:
                #     self.devices[data['name']] = d
                #     sender_socket.sendto(bytes(res, "utf-8"), self.client_address)
                #     return
            except Exception as e:
                print("Can not create or connect to ", data)
                print(e)
                # sender_socket.sendto(bytes("PROBLEMS", "utf-8"), self.client_address)
        elif task == "Send":
            print(data)
            if data['name'] == 'DAQin':
                self.devices[data['name']] = CONSTRUCTORS[data['name']](data)
                self.devices[data['name']].connect()
            try:
                self.devices[data['name']].send(msg=data["msg"])
                # print("Status",status, " ,Answer", answer)
                # if status:
                #     sender_socket.sendto(bytes(answer, "utf-8"), self.client_address)
                #     return
                # else:
                #     print('Problems with sending msg', msg)
                #     print(answer)
                #     sender_socket.sendto(bytes(answer, "utf-8"), self.client_address)
            except Exception as e:
                print("Exception while sending", data)
                print(e)
                # sender_socket.sendto(bytes("PROBLEMS", "utf-8"), self.client_address)
        elif task == "Read":
            try:
                status, answer = self.devices[data['name']].read()
                print("Status",status, " ,Answer", answer)
                if status:
                    sender_socket.sendto(bytes(answer, "utf-8"), self.client_address)
                    return
                else:
                    print('Problems with reading', data)
                    sender_socket.sendto(bytes(answer, "utf-8"), self.client_address)
            except Exception as e:
                print("Esception while sending", data)
                print(e)
                sender_socket.sendto(bytes("PROBLEMS", "utf-8"), self.client_address)
        elif task == "Close":
            try:
                status, answer = self.devices[data['name']].close()
                print("Status",status, " ,Answer", answer)
                if status:
                    sender_socket.sendto(bytes(answer, "utf-8"), self.client_address)
                    return
                else:
                    print('Problems with sending msg', msg)
                    sender_socket.sendto(bytes(answer, "utf-8"), self.client_address)
            except Exception as e:
                print("Esception while sending", data)
                print(e)
                sender_socket.sendto(bytes("PROBLEMS", "utf-8"), self.client_address)
        elif task == "Finished":
            keys = list(self.devices.keys())
            for key in keys:
                device = self.devices.pop(key)
                device.close()


        # if debug:
        #     print("{} wrote:".format(self.client_address))
        #     print(msg)
        # if prog in handlers:
        #     answer = handlers[prog](msg,self.all_data)
        #     print('Answer:',answer)
        #     if answer != None:
        #         socket.sendto(bytes(answer, "utf-8"), self.client_address)
        # else:
        #     print('No handler for ' + prog)
        #     socket.sendto(bytes('no handler on server', "utf-8"), self.client_address)
if __name__ == "__main__":
    # HOST, PORT = "192.168.1.227", 9998
    server = socketserver.UDPServer(("192.168.1.227", 9998), MyUDPHandler)
    print("Server started at HOST, PORT", "192.168.1.227", 9998)
    server.serve_forever()

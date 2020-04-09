import socketserver
import socket

# from device_lib import COMPortDeviceServer
from serial import Serial
from serial.tools import list_ports
from serial import SerialException
import json
from PyQt5.QtCore import (Qt, QTimer)
import PyDAQmx as dq
import numpy as np
import ctypes
import time
import copy
import datetime
from math import gcd

HOST,PORT = "192.168.1.15", 9997
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(.001)

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
            print("Another conenction to ", self.name)
            return "Connected"
        try:
            p = Serial(self.port, self.baudrate, timeout=self.timeout)
            p.write(self.idn_messege)
            s = p.readline().decode()
            if '*IDN?' in s:
                p.write(b'system:echo off\r')
                p.readline().decode()
                p.write(self.idn_messege)
                s = p.readline().decode()
            s = s.split(',')
            print('Port answer ', s)
            print('\n' + 'Device connected on port ' + self.port + '\n')
            self.connected = True
            self.stream = p
            return "Connected"
            # below is check for IDN command respons  --- old part, mostly not used now
            # if len(s) < len(self.identification_names): # if length of identification names is smaller than expected
            #     p.close()
            #     self.stream = None
            #     return "Identification names length problem. Port answer "+str(s)
            # else:
            #     status = True
            #     for i in range(len(self.identification_names)): # checks every name
            #         if s[i] != self.identification_names[i]:
            #             status = False
            #             print(s[i], self.identification_names[i])
            #             break
            #     if status: # if there no mistakes while name comparison
            #         print('\n' + 'Device ' + str(self.identification_names) + ' connected on port ' + self.port + '\n')
            #         self.connected = True
            #         self.stream = p
            #         return "Ok"
            #     else: # if any mistake while name comparison
            #         p.close()
            #         return "Identification names problem. Port answer "+str(s)
        except SerialException as e:
            print(e)
            self.stream = None
            return "Serial exception occured"

    def write_com(self,command):
        status = True
        readout = ''
        if not self.connected:
            return (False, 'Not connected')
        try:
            self.stream.write(command)
            readout='Ok'
        except SerialException as e:
            status = False
            readout='bad'
            print("EXCEPTION")
            print(e)
        return (status, readout)  # return statuus of reading and readout

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
                # print('>>ARDUINO',repr(s))
                return True, res
                # print("arduino >>   ",s,end='')
            except SerialException as e:
                print('There are problems with arduino.')
                print(e)
                return False, "SerialException"
                # self.close()
            except Exception as e:
                print("EXCEPTION")
                print(e)
                return False, "Exception"
        else:
            return False,"Not connected"

class Arduino(COMPortDeviceServer):
    def __init__(self, data):
        print('INIT Arduino')
        super().__init__() # now it should do nothing
        self.__dict__.update(data)
        # self.read_timer = QTimer()
        # self.read_timer.setInterval(100)
        # self.read_timer.timeout.connect(self.readTimerHandler)
        # self.read_timer.start()

    def send(self,msg=''):
        res = self.write_read_com(msg)
        return res

    def read(self):
        return self.read_serial()

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
        self.AO = self.AnalogOutput(parent=self)
        self.AON = 4
        self.buffer_written = False
        self.data_to_send={}

    def connect(self):
        """For DAQ there no need in connection, but here it is for universality of devices"""
        return "Connected"

    def send(self,msg):
        if msg == "start":
            if not self.buffer_written:
                return False, "No data in buffer"
            try:
                self.run()
                print("DAQ_run started")
                return True, "DAQ started"
            except Exception as e:
                print("PROBLEM WITH DAQ")
                print(e)
                return False, "Problems with DAQ"
        elif type(msg) == dict:
            try:
                self.stop()
                self.write(msg)
                self.run()
                return True, "DAQ updated"
            except Exception as e:
                print("PROBLEM WITH DAQ")
                print(e)
                return False, "Problems with DAQ"

    def read(self):
        return True, json.dumps(self.data_to_send)

    def write(self, data={}):
        print('writing to DAQ')
        # print(data)
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
        self.AO.write(AOdata, AOrate, AOsamples)
        return self.DO.write(DOdata, DOrate, DOsamples)

    def digitalCicleFinished(self,count):
        # self.data_to_send={"count":count}
        print("cicle_finished")
        sock.sendto(bytes("cicle_finished " + str(count), "utf-8"), (HOST,PORT))
        self.run()

    def run(self):
        self.AO.run()
        return self.DO.run()

    def stop(self):
        self.DO.stop()
        return self.AO.stop()

    def close(self):
        self.AO.close()
        self.DO.close()

    def __del__(self):
        del self.AO
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
        self.stopAfter = False

    def createTask(self, limits, lines):
        self.DAQmxTaskControl(dq.DAQmx_Val_Task_Abort)
        self.limits = limits
        for line in lines:
            self.CreateAIVoltageChan('Dev1/ai' + str(line), "",
                                     dq.DAQmx_Val_Cfg_default, limits[0],
                                     limits[1], dq.DAQmx_Val_Volts, None)
        self._data = np.zeros(N*len(self.lines))
        self.readTotal = 0

    def configTiming(self,rate,samples):
        self.CfgSampClkTiming("/Dev1/do/SampleClock", rate, dq.DAQmx_Val_Rising,
                              dq.DAQmx_Val_FiniteSamps, samples)
        # self.CfgDigEdgeStartTrig("/Dev1/PFI0", DAQmx_Val_Falling)
        self.CfgDigEdgeStartTrig("/Dev1/do/StartTrigger", DAQmx_Val_Falling)


    def prepare(self, lines, rate, samples, limits):
        # lines = {line:[[begin,end],[begin,end]]}
        # limits = {line:(low,high)}
        if self.running:
            self.StopTask()
        if not limits == self.limits:
            self.createTask(limits, lines)
        self.configTimitng(rate, samples)
        self.AutoRegisterEveryNSamplesEvent(dq.DAQmx_Val_Acquired_Into_Buffer, N, 0)
        self.AutoRegisterDoneEvent(0)
        self.lines = lines
        pass

    def EveryNCallback(self):
        self.ReadAnalogF64(N, 1.0, dq.DAQmx_Val_GroupByChannel,
                           self._data, N*len(self.lines),
                           ctypes.byref(self.read), None)
        self.appendData()
        return 0

    def appendData(self):
        i = 0
        for line,window in self.lines:
            if self.readTotal > window[1]:
                continue
            if self.readTotal+self.read.value<window[0]:
                continue
            begin = max(window[0]-self.readTotal,0) + i
            end = min(self.read.value, window[1]-self.readTotal) + i
            self.data[line].append(seld._data[begin:end])
            i += self.read.value
        self.readTotal += self.read.value

    def DoneCallback(self, status):
        self.ReadAnalogF64(-1, 1.0, dq.DAQmx_Val_GroupByChannel,
                           self._data, N*len(self.lines),
                           ctypes.byref(self.read), None)
        self.appendData()
        sock.sendto(bytes("analog_input " + str(self.data), "utf-8"), (HOST,PORT))
        self.StopTask()
        if not self.stopAfter:
            self.run()
        return 0

    def run(self):
        self.readTotal = 0
        self.data = {}
        self.stopAfter = False
        for line,window in self.lines:
            self.data[line] = []
        self.StartTask()


CONSTRUCTORS = {"Arduino":Arduino,}
                # "DAQ":DAQHandler}


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
            print('available COM ports:',available_com_ports)
            sender_socket.sendto(bytes("AvailableCOMs " + json.dumps(available_com_ports), "utf-8"), self.client_address)
        elif task == "Connect":
            print("Devices", self.devices)
            if data["name"] in self.devices:
                res = self.devices[data['name']].connect()
                sender_socket.sendto(bytes(res, "utf-8"), self.client_address)
                return
            try:
                d = CONSTRUCTORS[data["device"]](data)
                res = d.connect()
                print("Result", res)
                if res != "Connected":
                    sender_socket.sendto(bytes(res, "utf-8"), self.client_address)
                    return
                else:
                    self.devices[data['name']] = d
                    sender_socket.sendto(bytes(res, "utf-8"), self.client_address)
                    return
            except Exception as e:
                print("Can not connect to ", data)
                print(e)
                sender_socket.sendto(bytes("PROBLEMS", "utf-8"), self.client_address)
        elif task == "Send":
            try:
                status, answer = self.devices[data['name']].send(msg=data["msg"])
                print("Status",status, " ,Answer", answer)
                if status:
                    sender_socket.sendto(bytes(answer, "utf-8"), self.client_address)
                    return
                else:
                    print('Problems with sending msg', msg)
                    print(answer)
                    sender_socket.sendto(bytes(answer, "utf-8"), self.client_address)
            except Exception as e:
                print("Esception while sending", data)
                print(e)
                sender_socket.sendto(bytes("PROBLEMS", "utf-8"), self.client_address)
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
    server = socketserver.UDPServer(("192.168.1.227", 9997), MyUDPHandler)
    print("Serever started at HOST, PORT", "192.168.1.227", 9997)
    server.serve_forever()

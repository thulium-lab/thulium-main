import socketserver
from device_lib import COMPortDeviceServer
from serial.tools import list_ports
from serial import SerialException
import json
from PyQt5.QtCore import (Qt, QTimer)
# import PyDAQmx as dq
import numpy as np
import ctypes
import time
import datetime
from math import gcd

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

# class DAQHandler:
#     """
#     Handles DO and AO channels
#     Usage:
#     __init__(func=None, sync=True) - create, generate zeros on channels
#         func(count) - callback function, after each period
#         sync - to sync or not to sync
#     write(data=zeros) - write data to NI
#         use write() to make everything zero
#     run() - start a non-running task
#     stop() - stop a running task
#     __del__ - clean on destruction
#     """
#
#     class DigitalOutput(dq.Task):
#         """
#         Wrapper of a standard class 'Task', specifically designed
#         to continiously generate repeated DO pulses
#         Usage:
#         __init__(func=None) - create, generate default output (zeros)
#             func(count) - callback function, after every period
#         run(data=zeros) - write and run
#         stop() - stops
#             it is possible to explicitly call
#             but not necessary (called implicitly when adding new data)
#         __del__ - clean on destruction
#         """
#
#         def __init__(self,parent=None):
#             self.parent = parent
#             dq.Task.__init__(self)
#             self.count = 0
#             self.CreateDOChan('Dev1/port0', "", dq.DAQmx_Val_ChanForAllLines)
#             self.running = False
#             self.wait = 0
#             self.write()
#             self.run()
#             self.time = time.perf_counter()
#
#         def getCount(self):
#             return self.count
#
#         def write(self, data=np.array([0, 0], dtype=np.uint32), rate=2, samples=2):
#             self.stop()
#             self.CfgSampClkTiming("", rate, dq.DAQmx_Val_Rising,
#                                   dq.DAQmx_Val_ContSamps, samples)
#             # if self._EveryNSamplesEvent_already_register:
#             #     self.RegisterEveryNSamplesEvent(dq.DAQmx_Val_Transferred_From_Buffer, samples, 0,
#             #                                     ctypes.cast(None, dq.DAQmxEveryNSamplesEventCallbackPtr), None)
#             # self.AutoRegisterEveryNSamplesEvent(dq.DAQmx_Val_Transferred_From_Buffer, samples, 0)
#             if samples > 2:
#                 if self._EveryNSamplesEvent_already_register:
#                     self.RegisterEveryNSamplesEvent(dq.DAQmx_Val_Transferred_From_Buffer, samples, 0,
#                                                     ctypes.cast(None, dq.DAQmxEveryNSamplesEventCallbackPtr), 0)
#                     self._EveryNSamplesEvent_already_register = False
#                 self.AutoRegisterEveryNSamplesEvent(dq.DAQmx_Val_Transferred_From_Buffer, samples, 0)
#             self.wait = samples / rate
#             self.WriteDigitalU32(samples, 0, 10.0,
#                                  dq.DAQmx_Val_GroupByChannel,
#                                  data, None, None)
#             return
#
#         def run(self):
#             self.count = 0
#             self.time = time.perf_counter()
#             self.running = True
#             return self.StartTask()
#
#         def stop(self):
#             if not self.running:
#                 return 0
#             self.running = False
#             return self.StopTask()
#
#         def idle(self):
#             return 0
#
#         def EveryNCallback(self):
#             if not self.running:
#                 return 0
#             timeOld = self.time
#             self.time = time.perf_counter()
#             if abs(self.time - timeOld) < 0.001:
#                 return 0
#             self.count += 1
#             if self.parent:
#                 self.parent.digitalCicleFinished(self.count)
#             return 0
#
#         def __del__(self):
#             self.write()
#             self.run()
#             self.stop()
#             self.ClearTask()
#
#     class AnalogOutput(dq.Task):
#         """
#         Wrapper of a standard class 'Task', specifically designed
#         to continiously generate repeated AO pulses synced with DO
#         Usage:
#         __init__(sync=True) - create, generate default output (zeros)
#             sync - to sync or not to sync - SET SYNC BY DEFAULT
#         run(data=zeros) - write and run
#         stop() - stops
#             it is possible to explicitly call
#             but not necessary (called implicitly when adding new data)
#         __del__ - clean on destruction (for the sake of NI board, not garbage collection)
#         """
#
#         def __init__(self, parent=None, sync=True):
#             self.parent = parent
#             dq.Task.__init__(self)
#             self.sync = sync
#             self.running = False
#             for line in range(0, 4):
#                 self.CreateAOVoltageChan('Dev1/ao' + str(line), "", -10.0,
#                                          10.0, dq.DAQmx_Val_Volts, None)
#             self.write()
#             self.run()
#
#         def write(self, data=np.array([0 for x in range(4 * 2)], dtype=np.double), rate=2, samples=2):
#             """ 4 in data constructor is AON"""
#             self.stop()
#             self.CfgSampClkTiming("", rate, dq.DAQmx_Val_Rising,
#                                   dq.DAQmx_Val_ContSamps, samples)
#             if (self.sync):
#                 self.CfgDigEdgeStartTrig('/Dev1/do/StartTrigger',
#                                          dq.DAQmx_Val_Rising)
#             self.WriteAnalogF64(samples, 0, 10.0,
#                                 dq.DAQmx_Val_GroupByChannel,
#                                 data, None, None)
#             return
#
#         def run(self):
#             self.running = True
#             return self.StartTask()
#
#         def stop(self):
#             if not self.running:
#                 return 0
#             self.running = False
#             return self.StopTask()
#
#         def __del__(self):
#             self.sync = False
#             self.write()
#             self.run()
#             self.stop()
#             self.ClearTask()
#
#     def __init__(self, func=None, sync=True):
#         self.DO = self.DigitalOutput(parent=self)
#         self.AO = self.AnalogOutput(parent=self)
#         self.AON = 4
#         self.data_to_send={}
#
#     def connect(self):
#         """For DAQ there no need in connection, but here it is for universality of devices"""
#         return "Ok"
#
#     def send(self,msg):
#         try:
#             data = json.loads(msg)
#             self.write(data)
#             return True, "DAQ updated"
#         except Exception as e:
#             print("PROBLEM WITH DAQ")
#             print(e)
#             return False, "Problems with DAQ"
#
#     def read(self):
#         return True, json.dumps(self.data_to_send)
#
#     def write(self, data={}):
#         print('writing to DAQ')
#         p = 10000
#         if (len(data) == 0):
#             self.AO.write()
#             return self.DO.write()
#
#         DOtimes = set()
#         AOtimes = set()
#         AOpattern = 'A'
#         DOchans = {}
#         AOchans = {}
#         for chan in data:
#             if (chan[0] == AOpattern):
#                 AOchans[int(chan[1])] = data[chan]
#                 for point in data[chan]:
#                     AOtimes.add(int(point[0]*p+0.5))
#             else:
#                 DOchans[int(chan)] = data[chan]
#                 for point in data[chan]:
#                     DOtimes.add(int(point[0]*p+0.5))
#         DOtimes = sorted(DOtimes)
#         AOtimes = sorted(AOtimes)
#         DOdt = DOtimes[1] - DOtimes[0]
#         AOdt = DOdt
#         if len(AOtimes) >= 2:
#             AOdt = AOtimes[1] - AOtimes[0]
#         for i in range(1, len(DOtimes)):
#             DOdt = gcd(DOdt, DOtimes[i] - DOtimes[i-1])
#             # print(DOdt, DOtimes[i], DOtimes[i-1])
#         for i in range(1, len(AOtimes)):
#             AOdt = gcd(AOdt, AOtimes[i] - AOtimes[i-1])
#         DOdt /= p
#         AOdt /= p
#         DOtimes = [x/p for x in DOtimes]
#         AOtimes = [x/p for x in AOtimes]
#         for chan in DOchans:
#             DOchans[chan][-1] = (DOchans[chan][-1][0]-DOdt, DOchans[chan][-1][1])
#         for chan in AOchans:
#             AOchans[chan][-1] = (AOchans[chan][-1][0]-AOdt, AOchans[chan][-1][1])
#         trigger = 31
#         DOchans[trigger] = [(0,1),(np.ceil(1./DOdt)*DOdt,0),(DOtimes[-1],0)]
#         DOsamples = round((DOtimes[-1] - DOtimes[0])/DOdt)
#         AOsamples = DOsamples
#         if len(AOtimes) >= 2:
#             #AOsamples = round((AOtimes[-1] - AOtimes[0])/AOdt).astype(int)
#             AOsamples = int(round((AOtimes[-1] - AOtimes[0]) / AOdt))
#         DOrate = 1000./DOdt
#         AOrate = 1000./AOdt
#         DOdata = np.array([0 for x in range(DOsamples)], dtype=np.uint32)
#         AOdata = np.array([0 for x in range(AOsamples*self.AON)], dtype=np.double)
#
#         print("DOsamples - ", DOsamples)
#         print("DOrate - ", DOrate)
#         print("AOsamples - ", AOsamples)
#         print("AOrate - ", AOrate)
#
#         if len(AOtimes):
#             print(AOtimes[0], AOtimes[-1])
#         err = 1e-6
#         for sample in range(DOsamples):
#             last = DOdata[sample-1]
#             t = DOdt*sample
#             for chan in DOchans:
#                 if abs(DOchans[chan][0][0]-t) < err:
#                     V = DOchans[chan].pop(0)[1]
#                     if not V:
#                         last = last | (1 << chan)
#                     else:
#                         last = last & ~(1 << chan)
#             DOdata[sample] = last
#         for sample in range(AOsamples):
#             last = [AOdata[x*AOsamples+sample] for x in range(self.AON)]
#             t = AOdt*sample
#             for chan in AOchans:
#                 while abs(AOchans[chan][0][0]-t) < err:
#                     last[chan] += AOchans[chan].pop(0)[1]
#                     if len(AOchans[chan]) == 0:
#                         break
#             for i in range(self.AON):
#                 AOdata[i*AOsamples+sample] = last[i]
#         self.AO.write(AOdata, AOrate, AOsamples)
#         return self.DO.write(DOdata, DOrate, DOsamples)
#
#     def digitalCicleFinished(self,count):
#         self.data_to_send={"count":count}
#
#     def run(self):
#         self.AO.run()
#         return self.DO.run()
#
#     def stop(self):
#         self.DO.stop()
#         return self.AO.stop()
#
#     def __del__(self):
#         del self.AO
#         del self.DO



CONSTRUCTORS = {"Arduino":Arduino,
                # "DAQ":DAQHandler
                }


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
        socket = self.request[1]
        task, data = msg.split(' ',maxsplit=1)
        data = json.loads(data)
        print('task:',task, ",data:",data)
        if task == "UpdateCOM":
            available_com_ports = [port.device for port in list(list_ports.comports())]
            print('available COM ports:',available_com_ports)
            socket.sendto(bytes(json.dumps(available_com_ports), "utf-8"), self.client_address)
        elif task == "Connect":
            try:

                d = CONSTRUCTORS[data["device"]](data)
                res = d.connect()
                print(res)
                if res != "Ok":
                    socket.sendto(bytes(res, "utf-8"), self.client_address)
                    return
                else:
                    self.devices[data['name']] = d
                    socket.sendto(bytes(res, "utf-8"), self.client_address)
                    return
            except Exception as e:
                print("Can not connect to ", data)
                print(e)
                socket.sendto(bytes("PROBLEMS", "utf-8"), self.client_address)
        elif task == "Send":
            try:
                status, answer = self.devices[data['name']].send(msg=data["msg"])
                print(status, answer)
                if status:
                    socket.sendto(bytes(answer, "utf-8"), self.client_address)
                    return
                else:
                    print('Problems with sending msg', msg)
                    socket.sendto(bytes(answer, "utf-8"), self.client_address)
            except Exception as e:
                print("Esception while sending", data)
                print(e)
                socket.sendto(bytes("PROBLEMS", "utf-8"), self.client_address)

        elif task == "Read":
            try:
                status, answer = self.devices[data['name']].read()
                print(status, answer)
                if status:
                    socket.sendto(bytes(answer, "utf-8"), self.client_address)
                    return
                else:
                    print('Problems with reading', data)
                    socket.sendto(bytes(answer, "utf-8"), self.client_address)
            except Exception as e:
                print("Esception while sending", data)
                print(e)
                socket.sendto(bytes("PROBLEMS", "utf-8"), self.client_address)

        elif task == "Close":
            try:
                status, answer = self.devices[data['name']].close()
                print(status, answer)
                if status:
                    socket.sendto(bytes(answer, "utf-8"), self.client_address)
                    return
                else:
                    print('Problems with sending msg', msg)
                    socket.sendto(bytes(answer, "utf-8"), self.client_address)
            except Exception as e:
                print("Esception while sending", data)
                print(e)
                socket.sendto(bytes("PROBLEMS", "utf-8"), self.client_address)



        if debug:
            print("{} wrote:".format(self.client_address))
            print(msg)
        # if prog in handlers:
        #     answer = handlers[prog](msg,self.all_data)
        #     print('Answer:',answer)
        #     if answer != None:
        #         socket.sendto(bytes(answer, "utf-8"), self.client_address)
        # else:
        #     print('No handler for ' + prog)
        #     socket.sendto(bytes('no handler on server', "utf-8"), self.client_address)
if __name__ == "__main__":
    HOST, PORT = "localhost", 9998
    server = socketserver.UDPServer((HOST, PORT), MyUDPHandler)
    server.serve_forever()
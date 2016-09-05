__author__ = 'FNMTuser'

from pynifpga import pynifpga
import pynifpga as pni
from FPGA_resgisters import *
from fpga_header_parser import *
from FPGA_utils import *
import time
import re

# class Fpga_old():
#
#     myfpgainfo = fpga_info()
#     res = "RIO0"
#     fname = "D:\\MyDocumentsLatin\\DocumentsLatin\\Akimov\\LabVeiw\\Experiment\\new\\6.2.3\\FPGA Bitfiles\\NiFpga_spin_controller_main_with_mem.lvbitx"
#
#     #sig = "F26DBECE0D920ED12F0DF8A887A1A3AD"
#     sig = myfpgainfo.sig
#     timeout = 100000 # msec
#
#     programm_test = [set_loops(1000), 0xC0000001, 0x90000017, 0xC0000000, 0xC0000004,
#                 0x90000017, 0xC0000000, 0x90000010, 0xC0000004, 0xC0000029,
#                  0xC0000000, 0x90000010, 0xC0000004, 0x90000017, 0xC0000000,
#                  0xC0000009, 0x9000000B, 0xC0000000, 0x90000027, 0x20000001, finish()]
#
#     programm_timetrace = [set_loops(1000),
#                           # 0xC0000001, 0x90000017, 0xC0000000,
#                           # 0xC0000004, 0x90000017,
#                           # 0xC0000000, 0x90000010,
#                           # 0xC0000004, 0x9000002F,
#                           # 0xC0000000, 0x90000010,
#                           # 0xC0000004, 0x90000017,
#                           0xC0000000, 0xC0000029, 0x9000000F,
#                           0xC0000000, 0x90000027,
#                           0x20000001,
#                           finish()]
#
#     prev_programm = []
#     running = False
#
#     def programm_esr(self, t, t_delay, t_ref, number_of_repeats):
#
#         t =int(t/12.5)
#         t_delay = int(t_delay/12.5)
#         t_ref = int(t_ref/12.5)
#
#         programm = [set_loops(number_of_repeats),0xC0000015,delay(100),0xC0000000,0xC000000D]
#         programm.append(delay(t))
#         programm.append(0xC0000001)#programm.append(0xC0000001)
#         programm.append(delay(t_delay))
#         programm.append(0xC0000021)
#         programm.append(delay(t_ref))
#         programm.append(0xC0000001)
#         #programm.append(0xC0000011)
#         programm.append(0x20000004)
#         programm.append(finish())
#         return programm
#
#     def programm_rabi(self,tau_exc,tau_del,
#                       tau_r,number_of_repeats,
#
#                       t_signal, t_ref_delay,t_ref):
#
#         programm = [set_loops(number_of_repeats)]
#         programm.append(0xC0000001)
#         programm.append(delay(tau_exc))
#         programm.append(0xC0000000)
#         programm.append(delay(tau_del-tau_r))
#         programm.append(0xC0000004)
#         programm.append(delay(tau_r))
#        # read out
#         programm.append(0xC0000009)
#         programm.append(delay(t_signal))
#         programm.append(0xC0000001)
#         programm.append(delay(t_ref_delay))
#         programm.append(0xC0000021)
#         programm.append(delay(t_ref))
#         programm.append(finish())
#         return programm
#
#     def programm_exc_enable(self):
#
#         return [0xC0000001]
#
#     def print_all_regs(self,fpga):
#         name_regex = re.compile(r'((Indicator)|(Control))([^_]+)_(.+)')
#         for k,v in FPGA_All_registers.items():
#             reg_match = name_regex.match(k)
#             if reg_match is None:
#                 print('Failed to parse parameter name: {0}'.format(k))
#                 continue
#             reg_type = reg_match.group(4)
#
#         print('{0: <30}= {1}'.format(reg_match.group(5),fpga.__getattribute__('Read'+reg_type)(v)))
#
#     def run_sequence(self,programm, number_repeats = 1):
#         # privet
#         # kak uspehi? Kagetsya ponyal v chem delo
#         # Fix i stepa budet volokno delat
#         #  t0 = time.time()
#
#         status = True
#         fpga = pynifpga()
#         status = fpga.Initialize()
#         status = fpga.Open(self.fname, self.sig[1:-1], self.res, 0)
#
#         if not status:
#             return status, 0,0,0,0
#
#         fpga.Run(0)
#         # TODO swalow warning!
#
#         fpga.WriteBool(self.myfpgainfo.registers['ControlBool_repeat_set'],False)
#         fpga.WriteBool(self.myfpgainfo.registers['ControlBool_program_load'],True)
#         fpga.WriteBool(self.myfpgainfo.registers['ControlBool_program_reset'],True)
#         fpga.WriteBool(self.myfpgainfo.registers['ControlBool_program_reset'],False)
#         t1 = time.time()
#         #print t1-t0, 'init'
#         # initial data values
#         refc =  fpga.ReadI64(self.myfpgainfo.registers['IndicatorI64_Refcounts'])
#         c = fpga.ReadI64(self.myfpgainfo.registers['IndicatorI64_Counts'])
#         col_signal = fpga.ReadI64(self.myfpgainfo.registers['IndicatorI64_Collectedsignal'])
#         col_ref_signal = fpga.ReadI64(self.myfpgainfo.registers['IndicatorI64_CollectedRefSignal'])
#         fpga.AcknowledgeIrqs(1)
#
#         ## FIFO programm
#         status = fpga.ConfigureFifo(self.myfpgainfo.registers['HostToTargetFifoU32_ProgramFIFO'],len(programm)), 'config fifo'
#
#         if not status:
#             return status, 2,0,0,0
#
#         ## FIFO data
#         status = fpga.ConfigureFifo(self.myfpgainfo.registers['TargetToHostFifoU64_DataFIFO'],number_repeats)
#         if not status:
#             return status, 2.1,0,0,0
#         status = fpga.ConfigureFifo(self.myfpgainfo.registers['TargetToHostFifoI64_Analog'],number_repeats)
#         if not status:
#             return status, 2.1,0,0,0
#
#
#
#         status = fpga.StartFifo(self.myfpgainfo.registers['HostToTargetFifoU32_ProgramFIFO']), 'start Fifo', fpga.GetLastStatus(),'error'
#
#         if not status:
#             return status, 3,0,0,0
#
#         status = fpga.StartFifo(self.myfpgainfo.registers['TargetToHostFifoU64_DataFIFO']), 'start data Fifo', fpga.GetLastStatus(),'error'
#         if not status:
#             return status, 3,0,0,0
#         status = fpga.StartFifo(self.myfpgainfo.registers['TargetToHostFifoI64_Analog']), 'start analog data Fifo', fpga.GetLastStatus(),'error'
#
#         if not status:
#             return status, 3,0,0,0
#
#
#         fpga.WriteFifoU32(self.myfpgainfo.registers['HostToTargetFifoU32_ProgramFIFO'],programm,self.timeout)
#
#         if not status:
#             return status, 4,0,0,0
#
#         t2 = time.time()
#         #print t2-t1, ' fifo'
#
#         status = fpga.ReadBool(self.myfpgainfo.registers['ControlBool_program_load'])
#
#         index= 0
#         while 1:
#             time.sleep(0.001)
#             index +=1
#             #print fpga.ReadI64(IndicatorI64_Programlength), len(programm)
#             if len(programm) == fpga.ReadI64(self.myfpgainfo.registers['IndicatorI64_Programlength']):
#                 break
#             if index > 500:
#                 print '\n fail'
#                 print fpga.WriteBool(self.myfpgainfo.registers['ControlBool_program_load'],False)
#                 fpga.StopFifo(self.myfpgainfo.registers['HostToTargetFifoU32_ProgramFIFO'])
#                 fpga.WriteBool(self.myfpgainfo.registers['ControlBool_program_load'],True)
#                 #self.print_all_regs(fpga)
#                 fpga.Close(0)# closes FPGA connection
#                 fpga.Finalize()
#                 return False, 5,0,0,0
#
#         t3 = time.time()
#
#         #print t3-t2, 'wait command'
#
#         fpga.WriteBool(self.myfpgainfo.registers['ControlBool_program_load'],False)
#         status =  fpga.StopFifo(self.myfpgainfo.registers['HostToTargetFifoU32_ProgramFIFO'])
#         if not status:
#             return status, 6,0,0,0
#
#         # TODO make parser
#         fpga.WriteU32(self.myfpgainfo.registers['ControlU32_repeat_counter'],number_repeats-1)
#         fpga.WriteBool(self.myfpgainfo.registers['ControlBool_repeat_set'],True)
#         fpga.WriteBool(self.myfpgainfo.registers['ControlBool_repeat_set'],False)
#
#         #self.print_all_regs(fpga)
#
#         fpga.ReadBool(self.myfpgainfo.registers['ControlBool_program_load'])
#         #print 'point1'
#         ## IRQ
#         pyobject_p = fpga.ReserveIrqContext()
#         #print 'point1.1'
#
#         # TODO fix timedout IRQ
#         fpga.WaitOnIrqs(pyobject_p,1,self.timeout)
#
#         #print 'point 1.2'
#         fpga.AcknowledgeIrqs(1)
#         #self.print_all_regs(fpga)
#         #print 'point2'
#
#         # Get Data
#         c = fpga.ReadI64(self.myfpgainfo.registers['IndicatorI64_Counts'])-c
#         refc = fpga.ReadI64(self.myfpgainfo.registers['IndicatorI64_Refcounts']) - refc
#         col_signal =  fpga.ReadI64(self.myfpgainfo.registers['IndicatorI64_Collectedsignal']) - col_signal
#         col_ref_signal = fpga.ReadI64(self.myfpgainfo.registers['IndicatorI64_CollectedRefSignal']) - col_ref_signal
#         # vot oni
#
#         # Load data from Fifo
#
#
#         data = fpga.ReadFifoU64(self.myfpgainfo.registers['TargetToHostFifoU64_DataFIFO'],number_repeats-1,self.timeout)
#
#
#         data.append(divmod(fpga.ReadI64(self.myfpgainfo.registers['IndicatorI64_Collectedsignal']),2**32)[1] +
#                     divmod(fpga.ReadI64(self.myfpgainfo.registers['IndicatorI64_CollectedRefSignal']),2**32)[1] * (2**32))
#         print data
#         self.data = data
#         # Run????
#
#         #print col_signal, 'signal'
#         #TODO: DIVMOD bi nado syuda perenesti
#
#         fpga.Close(0)
#         fpga.Finalize()
#         t4 = time.time()
#         #print t4-t0, 'total'
#         return status,c,refc,col_signal,col_ref_signal
#


class Fpga():

    myfpgainfo = fpga_info()
    res = "RIO0"
    fname = "D:\\MyDocumentsLatin\\DocumentsLatin\\Akimov\\LabVeiw\\Experiment\\new\\6.2.3\\FPGA Bitfiles\\NiFpga_spin_controller_main_with_mem.lvbitx"

    #sig = "F26DBECE0D920ED12F0DF8A887A1A3AD"
    sig = myfpgainfo.sig

    # TODO estimate time from scheme.
    timeout = 10000 # msec

    programm_test = [set_loops(1000), 0xC0000001, 0x90000017, 0xC0000000, 0xC0000004,
                0x90000017, 0xC0000000, 0x90000010, 0xC0000004, 0xC0000029,
                 0xC0000000, 0x90000010, 0xC0000004, 0x90000017, 0xC0000000,
                 0xC0000009, 0x9000000B, 0xC0000000, 0x90000027, 0x20000001, finish()]

    programm_timetrace = [set_loops(1000),
                          # 0xC0000001, 0x90000017, 0xC0000000,
                          # 0xC0000004, 0x90000017,
                          # 0xC0000000, 0x90000010,
                          # 0xC0000004, 0x9000002F,
                          # 0xC0000000, 0x90000010,
                          # 0xC0000004, 0x90000017,
                          0xC0000000, 0xC0000029, 0x9000000F,
                          0xC0000000, 0x90000027,
                          0x20000001,
                          finish()]

    prev_programm = []
    running = False

    def __init__(self):
        status = True
        self.fpga = pynifpga()
        status = self.fpga.Initialize()
        status = self.fpga.Open(self.fname, self.sig[1:-1], self.res, 0)

        if not status:
            return status, 0,0,0,0

        self.fpga.Run(0)

    def programm_esr(self, t, t_delay, t_ref, number_of_repeats):

        t =int(t/12.5)
        t_delay = int(t_delay/12.5)
        t_ref = int(t_ref/12.5)

        programm = [set_loops(number_of_repeats),0xC0000015,delay(100),0xC0000000,0xC000000D]
        programm.append(delay(t))
        programm.append(0xC0000001)#programm.append(0xC0000001)
        programm.append(delay(t_delay))
        programm.append(0xC0000021)
        programm.append(delay(t_ref))
        programm.append(0xC0000001)
        #programm.append(0xC0000011)
        programm.append(0x20000004)
        programm.append(finish())
        return programm

    def programm_ssr(self,t_delay,t_mw, t_readout, N_cycles):

        t_delay = int(t_delay/12.5)
        t_mw = int(t_mw/12.5)
        t_readout = int(t_readout /12.5)

        programm = [set_loops(N_cycles), 0xC0000000, delay(t_delay)]
        programm.append(0xC000004)
        programm.append(delay(t_mw))
        programm.append(0xC0000009)
        programm.append(delay(t_readout))
        programm.append(0x20000001)
        programm.append(finish())
        return programm




    def programm_rabi(self,tau_exc,tau_del,
                      tau_r,number_of_repeats,

                      t_signal, t_ref_delay,t_ref,tau_rest=200):

        tau_exc = int(tau_exc/12.5)
        tau_del = int(tau_del/12.5)
        tau_r = int(tau_r/12.5)
        t_signal = int(t_signal/12.5)
        t_ref_delay = int(t_ref_delay/12.5)
        t_ref = int(t_ref/12.5)
        tau_rest = int(tau_rest/12.5)

        # init
        programm = [set_loops(number_of_repeats)]
        programm.append(0xC0000001)
        programm.append(delay(tau_exc))
        # rest
        programm.append(0xC0000000)
        programm.append(delay(tau_del-tau_r))
        programm.append(0xC0000004)
        programm.append(delay(tau_r))

       # rest
        programm.append(0xC0000000)
        programm.append(delay(tau_rest))

       # read out
        programm.append(0xC0000009)
        programm.append(delay(t_signal))
        programm.append(0xC0000001)
        programm.append(delay(t_ref_delay))
        programm.append(0xC0000021)
        programm.append(delay(t_ref))
        programm.append(0xC0000001)
        programm.append(delay(2*t_ref))
        programm.append(0x20000001)
        programm.append(finish())
        return programm


    def programm_fid(self, tau_exc, tau_pi2, tau_pi, tau_fid,
                     t_signal, t_ref_delay, t_ref, tau_rest, number_of_repeats):

        tau_exc = int(tau_exc/12.5)
        tau_fid = int(tau_fid/12.5)
        tau_pi2 = int(tau_pi2/12.5)
        t_signal = int(t_signal/12.5)
        t_ref_delay = int(t_ref_delay/12.5)
        t_ref = int(t_ref/12.5)
        tau_pi = int(tau_pi/12.5)
        t_rest = int(tau_rest/12.5)

        # init
        programm = [set_loops(number_of_repeats)]
        programm.append(0xC0000001)
        programm.append(delay(tau_exc))
        # rest
        programm.append(0xC0000000)
        programm.append(delay(t_rest-tau_fid))

        # fid
        #1st pi/2
        programm.append(0xC0000004)
        programm.append(delay(tau_pi2))

        # rest
        programm.append(0xC0000000)
        programm.append(delay(tau_fid))

        #2nd pi/2
        programm.append(0xC0000004)
        programm.append(delay(tau_pi2))

        # read out
        programm.append(0xC0000009)
        programm.append(delay(t_signal))
        programm.append(0xC0000001)
        programm.append(delay(t_ref_delay))
        programm.append(0xC0000021)
        programm.append(delay(t_ref))
        programm.append(0xC0000001)
        programm.append(delay(10*t_ref))
        programm.append(0x20000001)
        programm.append(finish())
        return programm

    def set_loops(self,repeats):

        maxrepeat = 16**6
        if repeats >= maxrepeat:
            repeats = maxrepeat

        command = 0x10000000 + repeats-1

        return command

    def programm_align_exc_col(self,tau_exc,tau_coll,tau_shift,num_repeats=10):

        tau_exc = int(tau_exc/12.5)
        tau_coll = int(tau_coll/12.5)
        tau_shift = int(tau_shift/12.5)
        programm = [set_loops(num_repeats)]


        if tau_shift < 0:
            if abs(tau_shift) < tau_coll: # slivautsya


                programm.append(0xC0000008) # collection
                programm.append(delay(-tau_shift))
                programm.append(0xC0000009) # collection + excitation
                programm.append(delay(tau_coll+tau_shift))
                programm.append(0xC0000001) # excitation
                programm.append(delay(tau_exc-tau_coll-tau_shift))
            elif abs(tau_shift) >= tau_coll:

                programm.append(0xC0000008) # collection
                programm.append(delay(tau_coll))
                programm.append(0xC0000000) # collection + excitation
                programm.append(delay(-tau_shift-tau_coll))
                programm.append(0xC0000001) # excitation
                programm.append(delay(tau_exc))

        else:

            if tau_shift < tau_exc: # slivautsya

                programm.append(0xC0000001) # excitation
                programm.append(delay(tau_shift))
                programm.append(0xC0000009) # collection + excitation
                programm.append(delay(tau_exc-tau_shift))
                programm.append(0xC0000008) # excitation
                programm.append(delay(tau_coll-tau_exc+tau_shift))

            elif tau_shift >= tau_exc:

                programm.append(0xC0000001) # exc
                programm.append(delay(tau_exc))
                programm.append(0xC0000000) # collection + excitation
                programm.append(delay(tau_shift-tau_exc))
                programm.append(0xC0000008) # collection
                programm.append(delay(tau_coll))

        programm.append(0xC0000000)
        programm.append(delay(1000-abs(tau_shift)))
        programm.append(0x20000001)
        programm.append(finish())

        #print [hex(p) for p in programm]

        return programm

    def programm_initialisation(self, tau_readout, tau_delay, num_repeats = 10):

        tau_readout = self.ns2ticks(tau_readout)
        tau_delay = self.ns2ticks(tau_delay)

        programm = [set_loops(num_repeats)]
        programm.append(0xC0000001)
        programm = [set_loops(num_repeats),0xC000000D]
        programm.append(delay(tau_readout))
        programm.append(0xC0000001)#programm.append(0xC0000001)
        programm.append(delay(tau_delay))
        programm.append(0xC0000021)
        programm.append(delay(tau_readout))
        programm.append(0xC0000001)
        #programm.append(0xC0000011)
        programm.append(0x20000001)
        programm.append(finish())
        return programm

    def programm_pulsed_esr(self, tau_exc, tau_delay, tau_pi, t_signal, t_ref_delay, t_ref, num_repeats = 10):

        # Pulsed ESR, a marige of ESR and Rabi

        tau_exc = ns_to_ticks(tau_exc)
        tau_delay = ns_to_ticks(tau_delay)
        tau_pi = ns_to_ticks(tau_pi)

        t_signal = ns_to_ticks(t_signal)
        t_ref_delay = ns_to_ticks(t_ref_delay)
        t_ref = ns_to_ticks(t_ref)

        programm = [set_loops(num_repeats),0xC0000015,delay(100),0xC0000001]
        programm.append(delay(tau_exc))
        programm.append(0xC0000000)#programm.append(0xC0000001)
        programm.append(delay(tau_delay))

        programm.append(0xC0000004)
        programm.append(delay(tau_pi))

        # rest
        programm.append(0xC0000000)
        # TODO add control and study this parameter.
        programm.append(delay(30))

        progr = self.readout(t_signal,t_ref_delay, t_ref)

        for p in progr:
            programm.append(p)

        #programm.append(0xC0000021)
        #programm.append(delay(t_ref))
        #programm.append(0xC0000001)
        programm.append(0x20000003)
        programm.append(finish())
        #print [hex(p) for p in programm]
        return programm

    def readout(self, t_s,t_r_d,t_r):

        programm = []
        programm.append(0xC0000009)
        programm.append(delay(t_s))
        programm.append(0xC0000001)
        programm.append(delay(t_r_d))
        programm.append(0xC0000021)
        programm.append(delay(t_r))

        return programm

    def channels2command(self,channels):
        command = 0xc0000000
        for chann in channels:

            if chann == 'Laser':
                command+=2**0
            elif chann == 'RF':
                command +=2**1
            elif chann == 'MW':
                command +=2**2
            elif chann == 'Detect':
                command += 2**3
            elif chann == 'RefDet':
                command += 2**5
        return command

    def finish(self):
        command  = 0xF0000000
        return command

    def delayFromNS(self,delay):

        delay = self.ns2ticks(delay)
        zerodelay = 0x90000000
        if delay > 2**24-1:
            delay = 2**24-1

        return delay + zerodelay - 1


    def ns2ticks(self,tau):

        return int(tau/12.5)


    def programm_exc_enable(self):

        return [0xC0000001,delay(100),finish()]

    def print_all_regs(self,fpga):
        name_regex = re.compile(r'((Indicator)|(Control))([^_]+)_(.+)')
        for k,v in FPGA_All_registers.items():
            reg_match = name_regex.match(k)
            if reg_match is None:
                print('Failed to parse parameter name: {0}'.format(k))
                continue
            reg_type = reg_match.group(4)

        print('{0: <30}= {1}'.format(reg_match.group(5),fpga.__getattribute__('Read'+reg_type)(v)))
    def configure_delays(self):
        self.fpga.WriteU16(self.myfpgainfo.registers['ControlU16_Collection2delay'],265)
        self.fpga.WriteU16(self.myfpgainfo.registers['ControlU16_Collectiondelay'],260)
        self.fpga.WriteU16(self.myfpgainfo.registers['ControlU16_Excitationdelay'],207)
        self.fpga.WriteU16(self.myfpgainfo.registers['ControlU16_MWdelay'],215)
        self.fpga.WriteU16(self.myfpgainfo.registers['ControlU16_RFdelay'],215)

    def clearCounters(self):
        self.fpga.WriteBool(self.myfpgainfo.registers['ControlBool_Clearcounter'],True)
        self.fpga.WriteBool(self.myfpgainfo.registers['ControlBool_Clearcounter'],False)

    def run_sequence(self,programm, number_repeats = 1, detectors = 0, laser_referencing = 1):
        self.configure_delays()
        #self.clearCounters()
        #  t0 = time.time()
        # status = True
        # fpga = pynifpga()
        # status = fpga.Initialize()
        # status = fpga.Open(self.fname, self.sig[1:-1], self.res, 0)
        #
        # if not status:
        #     return status, 0,0,0,0
        #
        # fpga.Run(0)
        # TODO swalow warning!
        # print detectors
        # set APD or Photodetectors.
        if detectors == 0:
            self.fpga.WriteBool(self.myfpgainfo.registers['ControlBool_use_analog'],False)
        elif detectors == 1:
            self.fpga.WriteBool(self.myfpgainfo.registers['ControlBool_use_analog'],True)

        self.fpga.WriteBool(self.myfpgainfo.registers['ControlBool_repeat_set'],False)
        self.fpga.WriteBool(self.myfpgainfo.registers['ControlBool_program_load'],True)
        self.fpga.WriteBool(self.myfpgainfo.registers['ControlBool_program_reset'],True)
        self.fpga.WriteBool(self.myfpgainfo.registers['ControlBool_program_reset'],False)

        t1 = time.time()
        #print t1-t0, 'init'
        # initial data values
        refc =  self.fpga.ReadI64(self.myfpgainfo.registers['IndicatorI64_Refcounts'])
        c = self.fpga.ReadI64(self.myfpgainfo.registers['IndicatorI64_Counts'])

        col_signal = self.fpga.ReadI64(self.myfpgainfo.registers['IndicatorI64_Collectedsignal'])
        #print col_signal
        col_ref_signal = self.fpga.ReadI64(self.myfpgainfo.registers['IndicatorI64_CollectedRefSignal'])
        self.fpga.AcknowledgeIrqs(1)

        ## FIFO programm
        status = self.fpga.ConfigureFifo(self.myfpgainfo.registers['HostToTargetFifoU32_ProgramFIFO'],len(programm)), 'config fifo'

        if not status:
            return status, 2,0,0,0

        ## FIFO data
        status = self.fpga.ConfigureFifo(self.myfpgainfo.registers['TargetToHostFifoU64_DataFIFO'],number_repeats*7)
        #self.fpga.
        if not status:
            return status, 2.1,0,0,0

        # status = self.fpga.ConfigureFifo(self.myfpgainfo.registers['TargetToHostFifoI64_Analog'],number_repeats)
        # if not status:
        #     return status, 2.1,0,0,0

        status = self.fpga.StartFifo(self.myfpgainfo.registers['HostToTargetFifoU32_ProgramFIFO']), 'start Fifo', self.fpga.GetLastStatus(),'error'

        if not status:
            return status, 3,0,0,0

        status = self.fpga.StartFifo(self.myfpgainfo.registers['TargetToHostFifoU64_DataFIFO']), 'start data Fifo', self.fpga.GetLastStatus(),'error'

        if not status:
            return status, 3,0,0,0

        # status = self.fpga.StartFifo(self.myfpgainfo.registers['TargetToHostFifoI64_Analog']), 'start data Fifo', self.fpga.GetLastStatus(),'error'

        if not status:
            return status, 3.1,0,0,0

#        print programm
        self.fpga.WriteFifoU32(self.myfpgainfo.registers['HostToTargetFifoU32_ProgramFIFO'],programm,self.timeout)

        if not status:
            return status, 4,0,0,0

        t2 = time.time()
        #print t2-t1, ' fifo'

        status = self.fpga.ReadBool(self.myfpgainfo.registers['ControlBool_program_load'])

        index= 0
        while 1:
            time.sleep(0.001)
            index +=1
            #print self.fpga.ReadI64(IndicatorI64_Programlength), len(programm)
            if len(programm) == self.fpga.ReadI64(self.myfpgainfo.registers['IndicatorI64_Programlength']):
                break
            if index > 500:
                print '\n fail'
                print self.fpga.WriteBool(self.myfpgainfo.registers['ControlBool_program_load'],False)
                self.fpga.StopFifo(self.myfpgainfo.registers['HostToTargetFifoU32_ProgramFIFO'])
                self.fpga.WriteBool(self.myfpgainfo.registers['ControlBool_program_load'],True)
                #self.print_all_regs(fpga)
                self.fpga.Close(0)# closes FPGA connection
                self.fpga.Finalize()
                return False, 5,0,0,0

        t3 = time.time()

        #print t3-t2, 'wait command'

        self.fpga.WriteBool(self.myfpgainfo.registers['ControlBool_program_load'],False)
        status =  self.fpga.StopFifo(self.myfpgainfo.registers['HostToTargetFifoU32_ProgramFIFO'])
        if not status:
            return status, 6,0,0,0

        #
        self.fpga.WriteU32(self.myfpgainfo.registers['ControlU32_repeat'],number_repeats)
        self.fpga.WriteBool(self.myfpgainfo.registers['ControlBool_repeat_set'],True)
        self.fpga.WriteBool(self.myfpgainfo.registers['ControlBool_repeat_set'],False)

        #self.print_all_regs(fpga)

        self.fpga.ReadBool(self.myfpgainfo.registers['ControlBool_program_load'])
        #print 'point1'
        ## IRQ
        pyobject_p = self.fpga.ReserveIrqContext()
        #print 'point1.1'

        # TODO fix timedout IRQ
        self.fpga.WaitOnIrqs(pyobject_p,1,self.timeout)

        #print 'point 1.2'
        self.fpga.AcknowledgeIrqs(1)
        #self.print_all_regs(fpga)
        #print 'point2'

        # Get Data
        c = self.fpga.ReadI64(self.myfpgainfo.registers['IndicatorI64_Counts'])#-c
        refc = self.fpga.ReadI64(self.myfpgainfo.registers['IndicatorI64_Refcounts'])# - refc
        col_signal =  self.fpga.ReadI64(self.myfpgainfo.registers['IndicatorI64_Collectedsignal'])# - col_signal
        col_ref_signal = self.fpga.ReadI64(self.myfpgainfo.registers['IndicatorI64_CollectedRefSignal'])# - col_ref_signal

        if laser_referencing:
            laser_signal = 1.0*self.fpga.ReadI64(self.myfpgainfo.registers['IndicatorI64_IntLaser'])
            laser_ref_signal = 1.0*self.fpga.ReadI64(self.myfpgainfo.registers['IndicatorI64_IntReferenceLaser'])

            try:
                col_signal /=laser_signal
                col_ref_signal /=laser_ref_signal
            except:
                pass




        # vot oni
        #data1 = None
        # Load data from Fifo
        data = self.fpga.ReadFifoU64(self.myfpgainfo.registers['TargetToHostFifoU64_DataFIFO'],7*(number_repeats),self.timeout)

        #print data

        if detectors == 1:
            pass
            # data1 = self.fpga.ReadFifoU64(self.myfpgainfo.registers['TargetToHostFifoI64_Analog'],6*number_repeats-1,self.timeout)

        # append last point
        if detectors == 0:
            pass
            # data.append(divmod(self.fpga.ReadI64(self.myfpgainfo.registers['IndicatorI64_Counts']),2**32)[1] +
            #         divmod(self.fpga.ReadI64(self.myfpgainfo.registers['IndicatorI64_Refcounts']),2**32)[1] * (2**32))
        elif detectors == 1:
            # data.append(self.fpga.ReadI64(self.myfpgainfo.registers['IndicatorI64_Collectedsignal']))
            # data.append(self.fpga.ReadI64(self.myfpgainfo.registers['IndicatorI64_CollectedRefSignal']))
            # data.append(self.fpga.ReadI64(self.myfpgainfo.registers['IndicatorI64_IntLaser']))
            # data.append(self.fpga.ReadI64(self.myfpgainfo.registers['IndicatorI64_IntReferenceLaser']))
            # data.append(self.fpga.ReadI64(self.myfpgainfo.registers['IndicatorI64_Counts']))
            # data.append(self.fpga.ReadI64(self.myfpgainfo.registers['IndicatorI64_Refcounts']))
            # data.append(-1)
            pass


        # Reset registers

        # self.fpga.WriteBool(self.myfpgainfo.registers['ControlBool_Clearcounter'],True)
        # self.fpga.WriteBool(self.myfpgainfo.registers['ControlBool_Clearcounter'],False)
        #print self.fpga.ReadBool(self.myfpgainfo.registers[''])
        #print data
        self.data = data
        #self.data1 = data1
        # Run????

        #print col_signal, 'signal'
        #TODO: DIVMOD bi nado syuda perenesti
        #print col_signal
        # self.fpga.Close(0)
        # self.fpga.Finalize()
        t4 = time.time()
        #print t4-t0, 'total'
        return status,c,refc,col_signal,col_ref_signal

    def __del__(self):
        self.fpga.Close(0)
        self.fpga.Finalize()

debug = False
if debug:

    myfpga = Fpga()
    data =  myfpga.run_sequence(myfpga.programm_esr(4e5,1e4,4e5,10), number_repeats = 3
                                , detectors = 1)
    for x in range(len(myfpga.data)/7):
        try:
            d = myfpga.data[x*7:(x+1)*7]
            print(str(d)+'    '+str(len(d)))
        except IndexError:
            pass
    print len(myfpga.data)

    #print myfpga.run_sequence(programm=myfpga.programm_timetrace)

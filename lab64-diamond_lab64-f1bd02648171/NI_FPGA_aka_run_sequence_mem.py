__author__ = 'FNMTuser'
res = "RIO0" # instrument address (resource name, for example RIO0)

fname = "D:\\MyDocumentsLatin\\DocumentsLatin\\Akimov\\LabVeiw\\Experiment\\new" \
        "\\6.2.3\\FPGA Bitfiles\\NiFpga_spin_controller_main_with_mem.lvbitx"

#sig = "7096474DBEBA63E3173DCD64405AA225"
sig = "79457B7C15E06125FF0E96F2E066C985"
sig = "F9A1447764D7849A19B3A8587276C881"

timeout = 2000 # operation timeout in msec
from pynifpga import pynifpga
import pynifpga as pni
from FPGA_resgisters import *
from FPGA_utils import *
import time
import re

# loads file into the FPGA

programm = [set_loops(10000), 0xC0000001, 0x90000017, 0xC0000000, 0xC0000004,
                0x90000017, 0xC0000000, 0x90000010, 0xC0000004, 0x9000002F,
                 0xC0000000, 0x90000010, 0xC0000004, 0x90000017, 0xC0000000,
                 0xC0000009, 0x9000000B, 0xC0000000, 0x90000027, 0x20000001, finish()]
#programm = [0x10001000, 0xC00000FF, 0x90001000, 0xC0000000,
 #               0x90001000, 0x20000001, 0xF0000000]

def print_all_regs(fpga):
    name_regex = re.compile(r'((Indicator)|(Control))([^_]+)_(.+)')
    for k,v in FPGA_All_registers.items():
        reg_match = name_regex.match(k)
        if reg_match is None:
            print('Failed to parse parameter name: {0}'.format(k))
            continue
        reg_type = reg_match.group(4)

        print('{0: <30}= {1}'.format(reg_match.group(5),fpga.__getattribute__('Read'+reg_type)(v)))

def wrapper(programm):
    fpga = pynifpga()
    fpga.Initialize()
    fpga.Open(fname, sig, res, 0)
    fpga.Run(0)



    fpga.WriteBool(ControlBool_repeat_set,False)
    fpga.WriteBool(ControlBool_program_load,True)
    fpga.WriteBool(ControlBool_program_reset,True)
    fpga.WriteBool(ControlBool_program_reset,False)

    # fpga.WriteBool(ControlBool_program_load,True)
    # fpga.WriteBool(ControlBool_program_load,False)
    # fpga.WriteBool(ControlBool_program_load,True)
    # # fpga.WriteBool(ControlBool_program_load,False)

   # print_all_regs(fpga)

    #refc = fpga.ReadI32(IndicatorI64_Refcounts)
    #c = fpga.ReadI64(IndicatorI64_Counts)
    col_signal = fpga.ReadI64(IndicatorI64_Collectedsignal)
    #col_ref_signal = fpga.ReadI64(IndicatorI64_CollectedRefSignal)
    fpga.AcknowledgeIrqs(1)
    #
    # print fpga.ReadBool(ControlBool_program_load), 'program load'
    # # Program load true
    # fpga.WriteBool(ControlBool_program_load,True)
    # time.sleep(0.1)
    # print fpga.ReadBool(ControlBool_program_load), 'program load'

    #print fpga.ReadI64(IndicatorI64_Programlength),'program length'
    ## FIFO

    print fpga.ConfigureFifo(HostToTargetFifoU32_ProgramFIFO,len(programm)), 'config fifo'
    print fpga.StartFifo(HostToTargetFifoU32_ProgramFIFO), 'start Fifo', fpga.GetLastStatus(),'error'
    fpga.WriteFifoU32(HostToTargetFifoU32_ProgramFIFO,programm,timeout)

    print fpga.ReadBool(ControlBool_program_load), 'program load'

    index= 0
    while 1:
        time.sleep(1)
        index +=1
        print fpga.ReadI64(IndicatorI64_Programlength), len(programm)
        if len(programm) == fpga.ReadI64(IndicatorI64_Programlength):
            break
        if index > 5:
            print '\n fail'
            print fpga.WriteBool(ControlBool_program_load,False)
            fpga.StopFifo(HostToTargetFifoU32_ProgramFIFO)
            fpga.WriteBool(ControlBool_program_load,True)
            print_all_regs(fpga)
            fpga.Close(0)# closes FPGA connection
            fpga.Finalize()
            return

    fpga.WriteBool(ControlBool_program_load,False)
    print fpga.StopFifo(HostToTargetFifoU32_ProgramFIFO), 'fifo stop'

    # TODO make parser
    fpga.WriteU32(ControlU32_repeat_counter,100)
    fpga.WriteBool(ControlBool_repeat_set,True)
    fpga.WriteBool(ControlBool_repeat_set,False)

    print_all_regs(fpga)

    print fpga.ReadBool(ControlBool_program_load), ': program load'
    print 'point1'
    ## IRQ
    pyobject_p = fpga.ReserveIrqContext()
    print 'point1.1'

    # TODO fix timedout IRQ
    fpga.WaitOnIrqs(pyobject_p,1,timeout)

    print 'point 1.2'
    fpga.AcknowledgeIrqs(1)

    print_all_regs(fpga)

    print 'point2'
    # Get Data
    #c = fpga.ReadI64(IndicatorI64_Counts)-c
    # refc = fpga.ReadI64(IndicatorI64_Refcounts) - refc
    col_signal =  fpga.ReadI64(IndicatorI64_Collectedsignal) - col_signal
    #col_ref_signal = fpga.ReadI64(IndicatorI64_CollectedRefSignal) - col_ref_signal



    print col_signal, 'signal'

    fpga.Close(0)
    fpga.Finalize()


wrapper(programm)
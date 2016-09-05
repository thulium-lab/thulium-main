import CppHeaderParser
import sys
import os

#sys.path = ["../"] + sys.path

class fpga_info():
    def __init__(self, header_file="D:\\MyDocumentsLatin\\DocumentsLatin\\Akimov\\LabVeiw\\Experiment\\new\\"
                                   "6.2.3\\FPGA Bitfiles\\NiFpga_spin_controller_main_with_mem.h"):
        try:
            self.cppHeader = CppHeaderParser.CppHeader(header_file)
        except CppHeaderParser.CppParseError as e:
            print(e)
            sys.exit(1)

        self.dir = "D:\\MyDocumentsLatin\\DocumentsLatin\\Akimov\\LabVeiw\\Experiment\\new\\6.2.3" \
                   "\\FPGA Bitfiles"
        self.fname = self.cppHeader.defines[2].split(' ')[1]
        self.sig = self.cppHeader.variables[0]['default']
        self.init_registers()

    def init_registers(self):
        self.registers = {}
        for i,en in enumerate(self.cppHeader.enums):
            if i > 0 and i < 9:
                for reg in en['values']:
                    try:
                        self.registers[reg['name'].split('_')[6]+'_'+reg['name'].split('_')[7]+'_'+reg['name'].split('_')[8]] = int(reg['raw_value'],16)
                    except:
                        self.registers[reg['name'].split('_')[6]+'_'+reg['name'].split('_')[7]] = int(reg['raw_value'],16)
            elif i >= 9:
                for reg in en['values']:
                    self.registers[reg['name'].split('_')[6]+'_'+reg['name'].split('_')[7]] = reg['value']
debug = True
if debug:

    meregs = fpga_info()
    for i in meregs.registers.items():
        print i[0],i[1]

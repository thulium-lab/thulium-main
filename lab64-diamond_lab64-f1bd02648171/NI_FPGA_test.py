__author__ = 'FNMTuser'
res = "RIO0" # instrument address (resource name, for example RIO0)
#fname = 'D:\\MyDocumentsLatin\\DocumentsLatin\\Akimov\\LabVeiw\\Experiment\\new\\6.2.3\\FPGA Bitfiles\\NiFpga_spin_controller_main_with_mem.lvbitx'
#fname = 'D:\\MyDocumentsLatin\\DocumentsLatin\\Akimov\\LabVeiw\\Experiment\\new\\6.2.3\\FPGA Bitfiles\\NiFpga_spin_controller_main_with_mem.lvbitx'

#fname = "NiFpga_niScopeEXP2PInterleavedDataFPGA.lvbitx" # Bitfile name

fname = "D:\\MyDocumentsLatin\\DocumentsLatin\\Akimov\\LabVeiw\\Experiment\\new\\6.2.3\\FPGA Bitfiles\\NiFpga_spin_controller_main_with_mem.lvbitx"
#fname = "D:\\MyDocumentsLatin\\DocumentsLatin\\Akimov\\LabVeiw\\Experiment\\new\\6.2.3\\FPGA Bitfiles\\ScanMain_FPGATarget_spincontrollerma_jgroIvpXcg8.lvbitx"

#sig = "F403A835F6DA6B5BEAF03002AFD0A58E"
sig = "7096474DBEBA63E3173DCD64405AA225"
numPoints = 2000 # number of points to read
timeout = 1500 # operation timeout in msec
from pynifpga import pynifpga

fpga = pynifpga()

# loads file into the FPGA
fpga.Open(fname, sig, res, 0)

print 'FPGA Opened'

# writes some value in one register on the FPGA
# the control number can be read from the Offset property of a Register node in the LVBITX file.
#fpga.WriteU32(0,207)
print fpga.ReadBool(0x810E)
fpga.WriteBool(0x810E,True)
print fpga.ReadBool(0x810E)
#print [fpga.ReadU16(i) for i in range(400)]
# reads data from a FPGA DMA-to-host channel
#data = array(fpga.ReadFifoI16(1, numPoints, timeout))

# add here what you want to do with the data

fpga.Close(0) # closes FPGA connection
fpga.Finalize() # cleans up FPGA driver
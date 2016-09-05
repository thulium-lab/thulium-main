# Registers


#IndicatorI32_Pumppower = 0x8160
IndicatorI32_Pumppower = 0x8164
IndicatorI32_iter = 0x8124
#IndicatorU32_repeat_counter_local = 0x812C
IndicatorU32_repeat_counter_local = 0x8130
#IndicatorI64_CollectedRefSignal = 0x8110
IndicatorI64_CollectedRefSignal = 0x8114
IndicatorI64_Collectedsignal = 0x811C
#IndicatorI64_Counts = 0x816C
IndicatorI64_Counts = 0x8170

#IndicatorI64_Refcounts = 0x815C # OLD BITX
IndicatorI64_Refcounts = 0x8160 # Correct bitx



#IndicatorU64_Commandcounter = 0x8164
IndicatorU64_Commandcounter = 0x8168

IndicatorU64_Counter1 = 0x8140
IndicatorU64_Counter2 = 0x8144
ControlBool_ClearCounter = 0x810E
ControlBool_Clearcounter = 0x810E
ControlBool_Usecounter2 = 0x814A
ControlBool_program_load = 0x8136
ControlBool_program_reset = 0x8112
ControlBool_repeat_set = 0x813E
ControlI16_Testsignalhalfperiod125ns = 0x816A
ControlU16_Collection2delay = 0x813E
ControlU16_Collectiondelay = 0x814E
ControlU16_Excitationdelay = 0x815A
ControlU16_MWdelay = 0x8156
ControlU16_RFdelay = 0x8152
ControlU32_repeat_counter = 0x8138
IndicatorI64_Programlength = 0x812C

# IndicatorI32_Pumppower = 0x8164
# IndicatorI32_iter = 0x8124
# IndicatorU32_repeat_counter_local = 0x8130
# IndicatorI64_CollectedRefSignal = 0x8114
# IndicatorI64_Collectedsignal = 0x811C
# IndicatorI64_Counts = 0x8170
# IndicatorI64_Programlength = 0x812C
# IndicatorI64_Refcounts = 0x8160
# IndicatorU64_Commandcounter = 0x8168
IndicatorU64_Counter1 = 0x8144
IndicatorU64_Counter2 = 0x8148
ControlBool_Clearcounter = 0x810E
ControlBool_Usecounter2 = 0x814E
ControlBool_program_load = 0x8136
ControlBool_program_reset = 0x8112
ControlBool_repeat_set = 0x813E
ControlI16_Testsignalhalfperiod125ns = 0x816E
ControlU16_Collection2delay = 0x8142
ControlU16_Collectiondelay = 0x8152
ControlU16_Excitationdelay = 0x815E
ControlU16_MWdelay = 0x815A
ControlU16_RFdelay = 0x8156
ControlU32_repeat_counter = 0x8138
# TargetToHostFifoU64_DataFIFO = 1
# HostToTargetFifoU32_ProgramFIFO = 0
#




from pynifpga import pynifpga
FPGA_reg_funcs ={
    'Bool':(),

}

FPGA_All_registers = dict(
    #Bool_ClearCounter = 0x810E,
    # IndicatorI32_Pumppower = 0x8160,
    IndicatorI32_iter = 0x8124,
    # IndicatorU32_repeat_counter_local = 0x812C,
    # IndicatorI64_CollectedRefSignal = 0x8110,
    # IndicatorI64_Collectedsignal = 0x8118,
    # IndicatorI64_Counts = 0x816C,
    # IndicatorI64_Refcounts = 0x815C,
    # IndicatorU64_Commandcounter = 0x8164,
    # IndicatorU64_Counter1 = 0x8140,
    # IndicatorU64_Counter2 = 0x8144,
    # ControlBool_Clearcounter = 0x810E,
    # ControlBool_Usecounter2 = 0x814A,
    ControlBool_program_load = 0x8136,
    # ControlBool_repeat_set = 0x813A,
    # ControlI16_Testsignalhalfperiod125ns = 0x816A,
    # ControlU16_Collection2delay = 0x813E,
    # ControlU16_Collectiondelay = 0x814E,
    # ControlU16_Excitationdelay = 0x815A,
    # ControlU16_MWdelay = 0x8156,
    # ControlU16_RFdelay = 0x8152,
    # ControlU32_repeat_counter = 0x8134,
    IndicatorI64_Programlength = 0x812C,

)

#FIFO

TargetToHostFifoU64_DataFIFO = 1
HostToTargetFifoU32_ProgramFIFO = 0

"""
#define NiFpga_spin_controller_main_with_mem_Bitfile "NiFpga_spin_controller_main_with_mem.lvbitx"

/**
 * The signature of the FPGA bitfile.
 */
static const char* const NiFpga_spin_controller_main_with_mem_Signature = "F9A1447764D7849A19B3A8587276C881";

   NiFpga_spin_controller_main_with_mem_IndicatorI32_Pumppower = 0x8164,
   NiFpga_spin_controller_main_with_mem_IndicatorI32_iter = 0x8124,
   NiFpga_spin_controller_main_with_mem_IndicatorU32_repeat_counter_local = 0x8130,
   NiFpga_spin_controller_main_with_mem_IndicatorI64_CollectedRefSignal = 0x8114,
   NiFpga_spin_controller_main_with_mem_IndicatorI64_Collectedsignal = 0x811C,
   NiFpga_spin_controller_main_with_mem_IndicatorI64_Counts = 0x8170,
   NiFpga_spin_controller_main_with_mem_IndicatorI64_Programlength = 0x812C,
   NiFpga_spin_controller_main_with_mem_IndicatorI64_Refcounts = 0x8160,
   NiFpga_spin_controller_main_with_mem_IndicatorU64_Commandcounter = 0x8168,
   NiFpga_spin_controller_main_with_mem_IndicatorU64_Counter1 = 0x8144,
   NiFpga_spin_controller_main_with_mem_IndicatorU64_Counter2 = 0x8148,
   NiFpga_spin_controller_main_with_mem_ControlBool_Clearcounter = 0x810E,
   NiFpga_spin_controller_main_with_mem_ControlBool_Usecounter2 = 0x814E,
   NiFpga_spin_controller_main_with_mem_ControlBool_program_load = 0x8136,
   NiFpga_spin_controller_main_with_mem_ControlBool_program_reset = 0x8112,
   NiFpga_spin_controller_main_with_mem_ControlBool_repeat_set = 0x813E,
   NiFpga_spin_controller_main_with_mem_ControlI16_Testsignalhalfperiod125ns = 0x816E,
   NiFpga_spin_controller_main_with_mem_ControlU16_Collection2delay = 0x8142,
   NiFpga_spin_controller_main_with_mem_ControlU16_Collectiondelay = 0x8152,
   NiFpga_spin_controller_main_with_mem_ControlU16_Excitationdelay = 0x815E,
   NiFpga_spin_controller_main_with_mem_ControlU16_MWdelay = 0x815A,
   NiFpga_spin_controller_main_with_mem_ControlU16_RFdelay = 0x8156,
   NiFpga_spin_controller_main_with_mem_ControlU32_repeat_counter = 0x8138,
   NiFpga_spin_controller_main_with_mem_TargetToHostFifoU64_DataFIFO = 1,
   NiFpga_spin_controller_main_with_mem_HostToTargetFifoU32_ProgramFIFO = 0,

"""
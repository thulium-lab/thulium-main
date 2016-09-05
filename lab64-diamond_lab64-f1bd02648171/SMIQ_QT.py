__author__ = 'Vadim Vorobyov'

import numpy
import time
import visa


class lastList:
    lastFreqList=numpy.array([])
    lastPowerList=numpy.array([])
    
class SMIQ():

    last=lastList()
    rm = visa.ResourceManager()
    # smiq = rm.open_resource('GPIB0::28::INSTR', timeout=60000)
    smiq = rm.open_resource('USB0::0x0AAD::0x0048::111344::INSTR', timeout=60000)

    def Output(self):
        return self.smiq.ask(':OUTP?')

    def On(self):
        self.smiq.write(':OUTP ON')
        self.smiq.write('*WAI')
        #~ return self.smiq.ask(':OUTP?')

    def Off(self):
        if self.smiq.ask(':FREQ:MODE?') == 'LIST':
            self.smiq.write(':FREQ:MODE CW')
        self.smiq.write(':OUTP OFF')
        self.smiq.write('*WAI')
        #~ return self.smiq.ask(':OUTP?')

    def Power(self,power=None):
        if power != None:
            self.smiq.write(':POW %f' % power)
        return float(self.smiq.ask(':POW?'))

    def Freq(self,f=None):
        if f != None:
            self.smiq.write(':FREQ %f' % f)
        return float(self.smiq.ask(':FREQ?'))

    def CW(self,f=None, power=None):
        self.smiq.write(':FREQ:MODE CW')
        if f != None:
            self.smiq.write(':FREQ %f' % f)
        if power != None:
            self.smiq.write(':POW %f' % power)

    def checkFreqAndPowerList(self,freq,power):
        if len(self.last.lastFreqList)!=len(freq) or len(self.last.lastPowerList)!=len(power):
            return False
        for i in range(len(freq)):
            if freq[i] != self.last.lastFreqList[i]:
                return False
        for i in range(len(power)):
            if power[i]!=self.last.lastPowerList[i]:
                return False
        return True

    def List(self,freq, power):
        if numpy.iterable(power)!=0:
            powerlist=power
        else:
            powerlist=numpy.array([power for k in freq])

        self.smiq.write(':FREQ:MODE CW')
        self.smiq.write(':FREQ %f' % freq[0])
        self.smiq.write(':POW %f' % power)
        self.smiq.write('*WAI')
        if self.checkFreqAndPowerList(freq,powerlist)==False:
            self.last.lastFreqList=freq
            self.last.lastPowerList=powerlist
            self.smiq.write(':LIST:DEL:ALL')
            self.smiq.write('*WAI')
            self.smiq.write(":LIST:SEL 'ODMR'")
            FreqString = ''
            for f in freq[:-1]:
                FreqString += ' %f,' % f
            PowerString=''
            for p in powerlist[:-1]:
                PowerString+=' %f,' % p
            FreqString += ' %f' % freq[-1]
            PowerString += ' %f' % powerlist[-1]
            self.smiq.write(':LIST:FREQ' + FreqString)
            self.smiq.write('*WAI')
            self.smiq.write(':LIST:POW'  +  PowerString)
            self.smiq.write('*WAI')
        self.smiq.write(':TRIG1:LIST:SOUR EXT')
        self.smiq.write(':TRIG1:SLOP NEG')
        self.smiq.write(':LIST:MODE STEP')
        self.smiq.write('*WAI')
        time.sleep(0.5)
        N = int(numpy.round(float(self.smiq.ask(':LIST:FREQ:POIN?'))))
        if N != len(freq):
            raise RuntimeError, 'Error in SMIQ with List Mode'
        return N

    def ListCount(self):
        return self.smiq.ask(':LIST:FREQ:POIN?')

    def ListOn(self):
        self.smiq.write(':OUTP ON')
        self.smiq.write('*WAI')
        self.smiq.write(':LIST:LEAR')
        self.smiq.write('*WAI')
        self.smiq.write(':FREQ:MODE LIST')
        return self.smiq.ask(':OUTP?')

    def ResetListPos(self):
        self.smiq.write(':FREQ:MODE CW; :FREQ:MODE LIST')
        self.smiq.write('*WAI')
        return self.smiq.ask(':FREQ:MODE?')

    def Sweep(self,f_start, f_stop, df):
        self.smiq.write(':FREQ:MODE SWE')
        self.smiq.write(':SWE:MODE STEP')
        self.smiq.write(':TRIG1:SOUR EXT')
        self.smiq.write(':TRIG1:SLOP NEG')
        self.smiq.write(':SWE:SPAC LIN')
        self.smiq.write(':SOUR:FREQ:STAR %e' % f_start)
        self.smiq.write(':SOUR:FREQ:STOP %e' % f_stop)
        self.smiq.write(':SWE:STEP:LIN %e' % df)
        self.smiq.write(':FREQ:MAN %e' % f_start)
        self.smiq.write('*WAI')

        N = float(self.smiq.ask(':SWE:POINTS?'))

        return int(round(N))

    def SweepPos(self,f=None):
        if f != None:
            self.smiq.write(':FREQ:MAN %e' % f)
            self.smiq.write('*WAI')
        return float(self.smiq.ask(':FREQ?'))

    def AM(self,depth=None):
        if depth is None:
            self.smiq.write(':AM:STAT OFF')
        else:
            self.smiq.write('AM:SOUR EXT')
            self.smiq.write('AM:EXT:COUP DC')
            self.smiq.write('AM %f' % float(depth))
            self.smiq.write('AM:STAT ON')
        self.smiq.write('*WAI')
        return float(self.smiq.ask('AM?'))

    def Trigger(self,a, b):
        pass

    def Modulation(self,flag=None):
        return False

    def listmode(self,startfreq, endfreq, power, numbval):

        # freqs in Hz

        # reboot the smiq
        self.CW()
        self.Off()


        # Write new settings
        self.smiq.write(':SOUR:LIST:MODE STEP')
        self.smiq.write(':TRIG:LIST:SOUR EXT')
        self.smiq.write(':SOUR:LIST:SEL  "GPIBLIST"')

        freqs = ''
        powers = ''
        df = (endfreq - startfreq) / float(numbval)

        for i in range(numbval-1):
            curfreq = startfreq + i*df
            freqs += str(round(curfreq/1e6,5)) + ' MHz, '
            powers += str(power) + ' dbm, '
        freqs += str(round((startfreq + (numbval-1)*df)/1e6,5)) + ' MHz'
        powers += str(power) + ' dbm'

        #??????? [freqlist, pwlist] = obj.create_list(startfreq, endfreq, power, numbval)
        print len(freqs),freqs
        print powers
        self.smiq.write(':SOUR:LIST:FREQ '+ freqs)
        self.smiq.write(':SOUR:LIST:POW '+ powers)
        #%freqlist-format: '1.4GHz, 1.3GHz, 1.2GHz,...'
        #%pwlist-format: '0dBm, -2dBm, -2dBm, -3dBm,...'
        #self.smiq.onoff(1)
        self.smiq.write(':OUTP:STAT 1')
        self.smiq.write(':OUTP:STAT?')
        self.smiq.read()


        self.smiq.write(':SOUR:LIST:LEARn')     #               %Learn previous setting
        self.smiq.write(':SOUR:FREQ:MODE LIST')
        time.sleep(5)
        return

    def listmodeExplicit(self,f,p):
        # freqs in Hz

        # reboot the smiq
        self.CW()
        self.Off()


        # Write new settings
        self.smiq.write(':SOUR:LIST:MODE STEP')
        self.smiq.write(':TRIG:LIST:SOUR EXT')
        self.smiq.write(':SOUR:LIST:SEL  "GPIBLIST"')

        freqs = ''
        powers = ''


        for freq in f[:-1]:
            curfreq = freq
            freqs += str(round(curfreq/1e6,5)) + ' MHz, '
            powers += str(p) + ' dbm, '
        freqs += str(round(f[-1]/1e6,5)) + ' MHz'
        powers += str(p) + ' dbm'

        #??????? [freqlist, pwlist] = obj.create_list(startfreq, endfreq, power, numbval)
        print freqs
        print powers
        self.smiq.write(':SOUR:LIST:FREQ '+ freqs)
        self.smiq.write(':SOUR:LIST:POW '+ powers)
        #%freqlist-format: '1.4GHz, 1.3GHz, 1.2GHz,...'
        #%pwlist-format: '0dBm, -2dBm, -2dBm, -3dBm,...'
        #self.smiq.onoff(1)
        self.smiq.write(':OUTP:STAT 1')
        self.smiq.write(':OUTP:STAT?')
        self.smiq.read()


        self.smiq.write(':SOUR:LIST:LEARn')     #               %Learn previous setting
        self.smiq.write(':SOUR:FREQ:MODE LIST')
        time.sleep(5)
        return

        #self.ListOn()

        #self.On()

    def FM(self, fcentral= None, df=None, modulationfreq=None, power=None):

        if fcentral is None or df is None or modulationfreq is None:
            # switch FM off
            self.smiq.write(':FM1:STAT OFF')
        else:
            if power < 10.0001:
                self.CW(fcentral,power)
                self.smiq.write(':FM1 '+str(df)+'kHz')
                self.smiq.write(':FM1:SOUR INT')
                self.smiq.write(':FM1:STAT ON')
                self.smiq.write(':FM1:INT:FREQ '+str(modulationfreq)+'Hz')
            #self.smiq.write('')


        # should modulate the frequency of the smiq on a mudulation frequency
        # with amplitude of df and around f central
        #self.write()

debug = False

if debug:
    smiq = SMIQ()
    smiq.CW(2.87e9,0)
    smiq.AM()
    smiq.FM(2.87e9,5e5,1e5,0)
    #smiq.On()
    time.sleep(1)
    #smiq.Off()
    smiq.listmode(2.8645e9,2.8655e9,10,401)
    print 1




from serial import Serial
import time
import numpy as np

# comment - library for a specific generator (WHICH???) everysing is clean/
# interestin function List - writes to th generator list of (freq, amp) and the function Trigger changes generator
# parameters


class generator():
    def __init__(self):
        COMPortN = 'COM10'

        self.p = Serial(COMPortN,baudrate=115200,timeout=10000,rtscts=True)
        #p.write()
        self.p.write(b"*IDN?\n")
        print('Found: ' + self.p.readline().decode('ASCII'))
        self.p.write(b"FREQ?\n")
        print('curr freq: '+ self.p.readline().decode('ASCII').split()[0]+' Hz')

    def On(self):

        self.p.write(b"ENBL 1\n")
        self.p.write(b"ENBR 1\n")

    def Off(self):
        self.p.write(b"ENBL 0\n")
        self.p.write(b"ENBR 0\n")

    def OnOffStatus(self):

        self.p.write(b"ENBL?\n")
        return self.p.readline()

    def CW(self, f, p):

        #f - float in Hz
        #p - in dbms
        self.p.write(b"FREQ "+str(f)+"\n")
        self.p.write(b"AMPL "+str(p)+"\n")



    def List(self, freqs, powers):
        N = freqs.shape[0]

        notchanged1 = ",0,"
        notchanged2 = ",N,N,N,N,N,N,N,N,N,N,N,N"

        self.p.write(b"LSTC? "+str(N)+"\n")
        for i,f in enumerate(freqs):
            self.p.write(b"LSTP "+str(i)+","+
                         str(f)+notchanged1+str(powers[i])+
                          notchanged2+"\n")
        self.p.write(b"LSTE 1\n")



    def Trigger(self):

        self.p.write(b"*TRG\n")

    def __del__(self):
        self.p.close()





def test_scenario1():

    # enable CW
    mygena.CW(f=5e6,p=0)
    mygena.On()
    #print mygena.OnOffStatus()
    time.sleep(10)
    mygena.Off()
    #print mygena.OnOffStatus()
    return

def test_scenario2():

    # run list of freqs
    freqs = np.arange(1e6,10e6,1e5)
    powers = -30*np.ones(freqs.shape)
    mygena.On()
    mygena.List(freqs=freqs,powers=powers)

    for f in freqs:
        #print f
        time.sleep(0.05)
        mygena.Trigger()
    mygena.Off()
    return

debug = False
if debug:
    mygena = generator()
    test_scenario1()
    #test_scenario2()

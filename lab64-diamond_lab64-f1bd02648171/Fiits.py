from scipy import optimize as opt
import numpy as np

class LorentzFit():
    def __init__(self,freqs,data):


        self.sp = data
        self.freq = freqs


    def updatedata(self, data):

        self.sp = data

    def fitfun(self,f,f0,fwhm,contrast,scale):
        return scale*(1-(abs(contrast)*(fwhm/2)**2/((f-f0)**2+(fwhm/2)**2)))

    def initial_guess(self):
        f0 = self.freq[list(self.sp).index(min(self.sp))]
        return [f0,0.0002,0.01,0.0946]

    def findfit(self):

        self.sp = np.array(self.sp)
        self.freq = np.array(self.freq)
        params = self.initial_guess()
        popt,pcov = opt.curve_fit(self.fitfun,self.freq,self.sp,p0=params)
        self.f0 = popt[0]
        self.width = abs(popt[1])*1e6
        self.errwidth = abs(np.sqrt(pcov[1,1])*1e6)
        self.contrast = abs(popt[2])*100
        self.fitedcurve = self.fitfun(self.freq,popt[0],popt[1],popt[2],popt[3])
        #print self.name[0:11],'|| fwhm: ',abs(popt[1])*1e6, 'kHz || contrast', abs(popt[2])*100,'% || ','f0 =',round(self.f0,6),' GHz'
        #self.fitedcurve = self.fitfun(self.freq,params[0],params[1],params[2],params[3])
        return self.fitedcurve, abs(popt[0]), abs(popt[1]), abs(popt[2])
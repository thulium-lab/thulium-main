"""
Module to work with Angstrom WS7 wavelength meter
A lot taken from Stepan Snigirev code


"""

import argparse
import ctypes, os, sys, random, time

n_air = 1.0002926

class WavelengthMeter:
    cSignalInterferometer = ctypes.c_long(0)
    cSignalWideInterferometer = ctypes.c_long(1)
    def __init__(self, dllpath="C:\Windows\System32\wlmData.dll", debug=False):
        """
        Wavelength meter class.
        Argument: Optional path to the dll. Default: "C:\Windows\System32\wlmData.dll"
        """
        self.channels = []
        self.dllpath = dllpath
        self.debug = debug
        if not debug:
            self.dll = ctypes.WinDLL(dllpath)
            self.dll.ConvertUnit.restype = ctypes.c_double
            self.dll.GetWavelengthNum.restype = ctypes.c_double
            self.dll.GetFrequencyNum.restype = ctypes.c_double
            self.dll.GetSwitcherMode.restype = ctypes.c_long
            self.dll.GetTemperature.restype = ctypes.c_double
            self.dll.GetPowerNum.restype = ctypes.c_long
            self.dll.GetAmplitudeNum.restype = ctypes.c_long
            self.dll.GetPatternItemSize.restype = ctypes.c_long
            self.dll.GetPatternItemCount.restype = ctypes.c_long
            self.dll.GetPattern.restype = ctypes.c_longlong
            self.dll.GetExposure.restype = ctypes.c_ushort
            setter = self.dll.SetPattern
            setter.restype = ctypes.c_long
            setter(ctypes.c_long(1), ctypes.c_long(1))
            setter(ctypes.c_long(0), ctypes.c_long(1))


    @property
    def wavelength(self):
        return self.dll.ConvertUnit(ctypes.c_double(self.dll.GetWavelengthNum(ctypes.c_long(1), ctypes.c_double(0))),0,1)
        # return self.dll.GetWavelengthNum(ctypes.c_long(1), ctypes.c_double(0))

    @property
    def frequency(self):
        return self.dll.GetFrequencyNum(ctypes.c_long(1), ctypes.c_double(0))
    @property
    def exposure(self):
        return self.dll.GetExposure(0)

    @property
    def amplitudes(self):
        return (self.dll.GetAmplitudeNum(ctypes.c_long(1), ctypes.c_long(4), ctypes.c_long(0)),
                self.dll.GetAmplitudeNum(ctypes.c_long(1), ctypes.c_long(5), ctypes.c_long(0)))

    @property
    def temperature(self):
        return self.dll.GetTemperature(ctypes.c_double(0))

    @property
    def power(self):
        return self.dll.GetPowerNum(ctypes.c_long(1), ctypes.c_double(0))

    @property
    def spectrum(self):
        #  res will be a list of two spectrums from small and wide interferometers
        res = []
        for interferometer in [self.cSignalInterferometer,self.cSignalWideInterferometer]:
            size, length, adress = (self.dll.GetPatternItemSize(interferometer),
                                    self.dll.GetPatternItemCount(interferometer),
                                    self.dll.GetPattern(interferometer))
            # print(size, length, adress)
            # here c_int is choosen based on size (=2) value
            mem = ctypes.c_int * length
            b = ctypes.cast(adress, ctypes.POINTER(mem))
            res.append([b.contents[i] for i in range(0, length)])
        return res



    def GetAll(self):
        return {
            "debug": self.debug,
            "wavelength": self.GetWavelength(),
            "frequency": self.GetFrequency(),
            "exposureMode": self.GetExposureMode(),
        }

    @property
    def switcher_mode(self):
        if not self.debug:
            return self.dll.GetSwitcherMode(ctypes.c_long(0))
        else:
            return 0

    @switcher_mode.setter
    def switcher_mode(self, mode):
        if not self.debug:
            self.dll.SetSwitcherMode(ctypes.c_long(int(mode)))
        else:
            pass
    # NOT USED IN MY PROGRAMM
    # def GetExposureMode(self):
    #     if not self.debug:
    #         return (self.dll.GetExposureMode(ctypes.c_bool(0)) == 1)
    #     else:
    #         return True
    #
    # def SetExposureMode(self, b):
    #     if not self.debug:
    #         return self.dll.SetExposureMode(ctypes.c_bool(b))
    #     else:
    #         return 0

    # def GetWavelength(self, channel=1):
    #     if not self.debug:
    #         return self.dll.GetWavelengthNum(ctypes.c_long(channel), ctypes.c_double(0))
    #     else:
    #         wavelengths = [460.8618, 689.2643, 679.2888, 707.2016, 460.8618 * 2, 0, 0, 0]
    #         if channel > 5:
    #             return 0
    #         return wavelengths[channel - 1] + channel * random.uniform(0, 0.0001)
    #
    # def GetFrequency(self, channel=1):
    #     if not self.debug:
    #         return self.dll.GetFrequencyNum(ctypes.c_long(channel), ctypes.c_double(0))
    #     else:
    #         return 38434900
    #

if __name__ == '__main__':

    # command line arguments parsing
    parser = argparse.ArgumentParser(
        description='Reads out wavelength values from the High Finesse Angstrom WS7 wavemeter.')
    parser.add_argument('--debug', dest='debug', action='store_const',
                        const=True, default=False,
                        help='runs the script in debug mode simulating wavelength values')
    parser.add_argument('channels', metavar='ch', type=int, nargs='*',
                        help='channel to get the wavelength, by default all channels from 1 to 8',
                        default=range(1, 8))

    args = parser.parse_args()

    wlm = WavelengthMeter(debug=args.debug)

    for i in args.channels:
        print("Wavelength at channel %d:\t%.4f nm" % (i, wlm.GetWavelength(i)))

        # old_mode = wlm.switcher_mode

        # wlm.switcher_mode = True

        # print(wlm.wavelengths)
        # time.sleep(0.1)
        # print(wlm.wavelengths)

        # wlm.switcher_mode = old_mode

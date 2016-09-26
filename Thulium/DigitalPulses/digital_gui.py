



class IndividualPulse():
    def __init__(self, group = None,name='',channel = '0', edge = 0, delay=0, length=0,is_active=False):
        self.name = name   # name of the pulse
        # self.group = group # group of pulses it belongs to
        self.channel = channel # physical channel of the signal (or may be name in dictionary)
        self.edge = edge # start the pulse from group's t_start=0 or t_end=1
        self.variables = {'delay':delay,
                          'length':length}  # for easy scanning
        self.is_active = is_active
    def getPoints(self):
        pass

    def updateTime(self,group):
        if not self.edge:
            self.t_start = group.t_start + self.variables['delay']
            if self.variables['length'] == 0:
                self.t_end = group.t_end
            elif self.variables['length'] > 0:
                self.t_end = self.t_start + self.variables['length']
            else:
                self.t_end = group.t_end + self.variables['length']
        else:
            if self.variables['length'] == 0:
                self.t_start = group.t_start + self.variables['delay']
                self.t_end = group.t_end
            elif self.variables['length'] > 0:
                self.t_start = group.t_end + self.variables['delay']
                self.t_end = self.t_start + self.variables['length']
            else:
                self.t_end = group.t_end + self.variables['delay']
                self.t_start = self.t_end + self.variables['length']

    def getPoints(self):
        return [(self.t_start,1),(self.t_end,0)]

class AnalogPulse(IndividualPulse):
    def __init__(self,type='Points'):
        super().__init__()
        self.type = type
        self.formula = '' # iether string of points if type Point ore string of formula if type Formula
        # self.timeStep # to define timestap if type=='Formula'
    def getPoints(self):
        time_step = 5
        points = []
        if self.type == 'Points':
            temp1 = re.findall('[(](.*?)[)]',self.formula)
            temp1 = [t.split(',') for t in temp1]
            temp1 = [[t[0].strip(),t[1].strip()] for t in temp1]
            for point in temp1:
                for i,value in enumerate(point):
                    sp_value = re.split("([+-/*])",value)
                    for j,elem in enumerate(sp_value):
                        if elem in self.variables:
                            sp_value[j] = str(self.variables[elem])
                    point[i] = ''.join(sp_value)
                    try:
                        # print(point[i])
                        point[i] = eval(point[i])
                    except ValueError:
                        self.errorInFormula()
                        return -1
            # print(temp1)
            for i in range(1,len(temp1)):
                if not i == len(temp1)-1:
                    xs = self.t_start + np.arange(temp1[i-1][0],temp1[i][0],time_step)
                    # print(xs)
                else:
                    xs = self.t_start + np.arange(temp1[i-1][0],temp1[i][0]+time_step,time_step)
                    # print(xs)
                ys = temp1[i-1][1] + (temp1[i][1] - temp1[i-1][1]) / (xs[-1] - xs[0]) *(xs -xs[0])
                p = np.reshape(np.array([xs,ys]).T,(-1,2))
                points.extend(p)
        else:
            sp_form= re.split("([+-/*()])", self.formula)
            sp_form = [s.strip() for s in sp_form]
            for i, s in enumerate(sp_form):
                if s in self.variables:
                    sp_form[i] = str(self.variables[s])
            formula = ''.join(sp_form)
            formula = parse_expr(formula)
            t = sp.symbols('t')
            func = lambdify(t,formula,'numpy')
            xs = np.arange(0,self.t_end-self.t_start+time_step, time_step)
            ys = func(xs)
            print(xs)
            points = np.reshape(np.array([xs, ys]).T, (-1, 2))
        return [list(point) for point in points]

    def errorInFormula(self):
        print('Error')

from sympy.utilities.lambdify import lambdify
import re
import numpy as np
from numpy import *
import sympy as sp
from sympy.parsing.sympy_parser import parse_expr
dig = IndividualPulse('digital')
dig.t_start = 100
dig.t_end = 150

an = AnalogPulse(type='Formula')
an.t_start = 100
an.t_end = 150
an.variables['l'] = an.t_end - an.t_start
an.variables['a'] = 2
an.variables['b'] = 5

an.formula = 'a*cos(t) + b'

print(dig.getPoints())
print(an.getPoints())


print(2*cos(arange(0,51,5)) +5)















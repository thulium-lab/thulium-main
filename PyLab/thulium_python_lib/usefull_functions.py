
# coding: utf-8

# In[ ]:

"""
Module for usefull functions
"""


# In[ ]:

import numpy as np

def points_for_simple_scan(w=1,x0=0,rvs=False,random=False,n=20):
    scans = [-4*w,-3*w] + list(np.linspace(-2*w,2*w,n-4)) + [3*w,+4*w]
    scans = [float(str(round(i,int(-np.log10(w/10))+1))) for i in scans]
    if rvs:
        scans = reversed(scans)
    if random:
        np.random.shuffle(scans)
    return scans

def P(V, lda):
    return V*(6.07620337 - 0.19694817*(lda-813.33))  


def exp_decay(t, N0, tau, background):
    r'N0 * np.exp(- t / tau) + background'
    return N0 * np.exp(- t / tau) + background

def exp_decay_no_bg(t, N0, tau):
    r'N0 * np.exp(- t / tau)'
    return N0 * np.exp(- t / tau)

def cloud_expansion(t, T, r0, t0):
    r'np.sqrt(r0**2 + 2 * k_b * T * (t + 1*t0)**2 / m)'
    k_b = 1.38e-23
    m = 169 * 1.66e-27
    return np.sqrt(r0**2 + 2 * k_b * T * (t + 1*t0)**2 / m)

def cloud_expansion0(t, T, r0):
    r'cloud_expansion(t, T, r0, 0)'
    return cloud_expansion(t, T, r0, 0)

def exp_grouth(t, N0, tau, background):
    return N0 * ( 1 - np.exp( - t / tau)) + 1*background

def construct_fit_description(fit_func, popt_T,sep='\t'):
    """constructs a set of string of type 'variable=value\n' for all [1:] function variables"""
    from inspect import getargspec
    res = ''
    for item in zip(getargspec(fit_func)[0][1:], popt_T):
        params = item[1] if hasattr(item[1],'__iter__') else [item[1]]
        res += str(item[0]) + ' =   ' + sep.join(['%.4f'%(x) for x in params]) + '\n'
    res = res.rstrip('\n')
    return res

def lorentz(x, N, x0, sigma, background):
    return N/np.pi * 1/2 * sigma / ( (x - x0)**2 + (1/2*sigma)**2) + background


# ### Including some losses 

# In[ ]:

def tow_body_loss(t, N0, betta, background):
    r'return 1 / ( betta * t + 1 / N0) + background'
    return 1 / ( betta * t + 1 / N0) + background
def exp_plus_tw_body_decay(t, N0, tau, betta,  background):
    r'return N0 * np.exp(- t / tau) / ( 1 + betta * N0 * tau * (1 - np.exp( -t / tau))) + 0 * background'
    return N0 * np.exp(- t / tau) / ( 1 + betta * N0 * tau * (1 - np.exp( -t / tau))) + 0 * background
def exp_plus_tw_body_decay_no_bg(t, N0, tau, betta):
    r'return N0 * np.exp(- t / tau) / ( 1 + betta * N0 * tau * (1 - np.exp( -t / tau)))'
    return N0 * np.exp(- t / tau) / ( 1 + betta * N0 * tau * (1 - np.exp( -t / tau)))
def two_frac_decay(t, N0, N1, tau, betta,  background):
    r'return exp_decay(t, N0, tau, 0) + exp_plus_tw_body_decay(t,N1, tau, betta,  0) + abs(background)'
    return exp_decay(t, N0, tau, 0) + exp_plus_tw_body_decay(t,N1, tau, betta,  0) + abs(background)
def two_frac_decay_no_bg(t, N0, N1, tau, betta, background):
    r'return two_frac_decay(t, N0, N1, tau, betta,0)'
    return two_frac_decay(t, N0, N1, tau, betta,0)

def Pcalib1(V,lda=813.33, R=2e3):
    # WORKING RANGE 805-840 nm
    def P(lda,a,b,c):
        return a*lda/(lda-c)+b
    return P(lda,*array([  4.07355031e-01,  -5.70904336e+00,   7.86168098e+02])) * R / 2e3 * V

def Pcalib2(V,lda=813.33, R=2e3):
    def P1(x,a,b,c,d,e,f,g):
        return a + b*x + c*x**2 + d*x**3 + e*sin(0.2*f*x+g)
    return P1(lda,*array([ -4.65981894e+04,   1.70190515e+02,  -2.07292684e-01,
         8.42096330e-05,   4.59460444e-01,   1.23672569e+00,
        -3.59062175e+01])) * R/2e3 * V

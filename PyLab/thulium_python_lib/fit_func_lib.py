import numpy as np
from numpy import pi
#from math import *

def my_sinc0(x,N,x0,sigma, background):
    return N*np.sin(1/2*pi*np.sqrt(1 + (x-x0)**2/sigma**2))**2 / (1+(x-x0)**2/sigma**2) + background
def gaussian(x,N,x0,sigma, background):
    """Returns value of a 1D-gaussian with the given parameters ,N,x0,sigma, background"""
    #from numpy import sqrt,pi,exp
    return N/ (sigma * np.sqrt(pi)) * np.exp(-(x - x0)**2/(sigma**2)) + background
def gaussian2(x,N,x0,sigma, background):
    """Returns value of a 1D-gaussian 1/e2 with the given parameters ,N,x0,sigma, background"""
    #from numpy import sqrt,pi,exp
    return N/ (sigma * np.sqrt(pi)) * np.exp(-2*(x - x0)**2/(sigma**2)) + background

def two_gaussian(x, N1, N2, x0, sigma1, sigma2, background):
    return gaussian(x,N1,x0,sigma1,0) + gaussian(x,N2,x0,sigma2,0) + background
def two_gaussian2(x, N, alpha_cool, x0, sigma1, sigma2, background):
    """alpha_cool is fraction [0,1] of cold atoms"""
    return two_gaussian(x, N*alpha_cool, N*(1-alpha_cool), x0, sigma1, sigma2, background)

def lorentz(x, N, x0, sigma, background):
    return N/np.pi * 1/2 * sigma / ( (x - x0)**2 + (1/2*sigma)**2) + background

def exp_decay(t, N, tau, background):
    r'N * np.exp(- t / tau) + background'
    return N * np.exp(- t / tau) + background

def exp_decay_no_bg(t, N, tau):
    r'N * np.exp(- t / tau)'
    return N * np.exp(- t / tau)

def exp_plus_tw_body_decay(t, N, tau, betta,  background):
    r'return N0 * np.exp(- t / tau) / ( 1 + betta * N0 * tau * (1 - np.exp( -t / tau))) + 0 * background'
    return N * np.exp(- t / tau) / ( 1 + betta * N * tau * (1 - np.exp( -t / tau))) + 0 * background

def cloud_expansion(t, T, r0, t0):
    r'np.sqrt(r0**2 + 2 * k_b * T * (t + 1*t0)**2 / m)'
    k_b = 1.38e-23
    m = 169 * 1.66e-27
    return np.sqrt(r0**2 + 2 * k_b * T * (t + 1*t0)**2 / m)
def cloud_expansion0(t, T, r0):
    r'cloud_expansion(t, T, r0, 0)'
    return cloud_expansion(t, T, r0, 0)


def _gaussian_p0(xs,ys):
    """Returns M, x0,sigma,background"""
    return (-max(ys) / 20 * (max(xs) - min(xs)), xs[np.argmin(ys)], (max(xs) - min(xs)) / 10, max(ys))
def _exp_decay_p0(xs,ys):
    """Returns N,tau,background"""
    return (max(ys), (max(xs) - min(xs))/3,0)
def _exp_decay_no_bg_p0(xs,ys):
    """Returns N,tau"""
    return (max(ys), (max(xs) - min(xs))/3)
def _exp_plus_tw_body_decay_p0(xs,ys):
    """Returns N, tau, betta,  background"""
    return (max(ys), (max(xs) - min(xs))/3,0,0)

_p0_dict = {'gaussian':_gaussian_p0,
           'gaussian2':_gaussian_p0,
           'my_sinc0':_gaussian_p0,
           'lorentz': _gaussian_p0,
           'exp_decay':_exp_decay_p0,
           'exp_decay_no_bg':_exp_decay_no_bg_p0,
           'exp_plus_tw_body_decay': _exp_plus_tw_body_decay_p0}
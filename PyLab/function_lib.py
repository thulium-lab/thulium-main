import numpy as np



def shuffled_arange(x0,xn,dx):
    arr = np.arange(x0,xn,dx)
    np.random.shuffle(arr)
    return arr

def shuffled_linspace(x0,xn,n):
    arr = np.linspace(x0,xn,n)
    np.random.shuffle(arr)
    return arr

def get_points_for_simle_scan(w=1,x0=0,rvs=False,shuffled=False):
    scans = [-4*w,-3*w] + list(np.linspace(-2*w,2*w,11)) + [3*w,+4*w]
    if rvs:
        scans = list(reversed(scans))
    scans = np.array(scans)
    if shuffled:
        np.random.shuffle(scans)
    scans = scans+x0
    return np.array([round(i,int(-np.log10(w/10))+1) for i in scans])

##################             Fit functions                       ##############

def gaussian(x,N,x0,sigma, background):
    """Returns value of a 1D-gaussian with the given parameters"""
    #from numpy import sqrt,pi,exp
    return N / (sigma * np.sqrt(np.pi)) * np.exp(-(x - x0)**2/(sigma**2)) + background

def my_sinc0(x,N,x0,sigma, background):
    return N*np.sin(1/2*np.pi*np.sqrt(1 + (x-x0)**2/sigma**2))**2 / (1+(x-x0)**2/sigma**2) + background

def lorentz(x, N, x0, sigma, background):
    return N/np.pi * 1/2 * sigma / ( (x - x0)**2 + (1/2*sigma)**2) + background

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

def exp_grouth(t, N0, tau):
    return N0 * ( 1 - np.exp( - t / tau))

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
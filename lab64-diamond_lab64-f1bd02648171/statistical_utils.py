import numpy as np


def alanarray(array,dt):
    nmax = np.log10(array.shape[0]/10.0)
    N = 1000
    dn = max(0.01, nmax / N)

    ind = np.power(10,np.arange(1,nmax,dn))
    dev1 = [calcalan(array,n) for n in ind]

    return ind*dt,dev1

def calcalan(array,n):

    # this is for the 2nd order alan deviation
    # reshapes array into n subgroups
    n = int(n)
    index= divmod(array.shape[0],n)[1]
    number = divmod(array.shape[0],n)[0]
    clustersmean = array[:-index].reshape((-1,n)).mean(axis = 1)
    diffs = np.diff(clustersmean)
    diffs2 = diffs**2
    return np.sqrt(np.sum(diffs2)/(2*(number-1)))

def sralanarray(array,dt, tau):

    if tau is None:
        tau = dt

    srarray = filteringbyselfreferencing(tau=tau,array=array,dt=dt)
    times,dev = alanarray(srarray,2*tau)
    return times,dev

def standarderrorofthemeanforTsec(dt, array, tau, t):
    # t = 1s, for example

    referencedarray = filteringbyselfreferencing(tau,array,dt)
    ind = int(t/tau)
    dev = calcdev(referencedarray,ind)
    return dev

def filteringbyselfreferencing(tau,array,dt):

        numeberofsamples = int(tau/dt)
        index = divmod(array.shape[0],numeberofsamples*2)[1]

        if index != 0:
            subarray = array[:-index].reshape((-1,2,numeberofsamples))[:,0]-array[:-index].reshape((-1,2,numeberofsamples))[:,1]
        else:
            subarray = array.reshape((-1,2,numeberofsamples))[:,0]-array.reshape((-1,2,numeberofsamples))[:,1]

        newarray = np.mean(subarray, axis = 1)
        return newarray

def deviatearray(array, dt):

        nmax = np.log10(array.shape[0]/10.0)
        N = 1000
        dn = max(0.01, nmax / N)

        ind = np.power(10,np.arange(1,nmax,dn))
        dev1 = [calcdev(array,n) for n in ind]

        return ind*dt,dev1

def srdeviatearray(array,dt, tau):

    if tau is None:
        tau =dt

    srarray = filteringbyselfreferencing(tau=tau,array=array,dt=dt)
    times,dev = deviatearray(srarray,2*tau)

    return times,dev

def calcdev(array,n):
    n= int(n)
    index= divmod(array.shape[0],n)[1]
    index2= divmod(array.shape[0],n)[0]

    if index !=0:
        try:
            clustersmean = array[:-index-1].reshape((-1,n)).mean(axis = 1)
        except:
            clustersmean = array[:n*index2].reshape((-1,n)).mean(axis = 1)
    else:
        clustersmean = array.reshape((-1,n)).mean(axis = 1)

    varr = np.var(clustersmean)
    devv = np.sqrt(varr)
    return devv
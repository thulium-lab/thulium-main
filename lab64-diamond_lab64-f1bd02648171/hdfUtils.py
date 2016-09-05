import h5py
import numpy as np

def writehdf(file,data):
    fname = file + '.hdf5'
    f = h5py.File(fname, "w")

    for key in data.keys():
        dset = f.create_dataset(key,data=data[key])


def readhdf(file):

    data = {}
    fname = file + '.hdf5'
    f = h5py.File(fname, "r")
    keys = f.keys()

    for key in keys:
        data[key] = f[key].value

    return data


# datatowrite = {"1":np.array([1,2,3]),"2":[2,3,4]}
#
# writehdf('1',datatowrite)
#
# print readhdf('1')["2"]
from STRIDR.comms.analysis.base import *
import numpy as np

class RandomSample(Environment):
##untested
    def __init__(self,num_samples=2,**kwargs):
        self.params={'num_samples':num_samples};
        super().__init__(**kwargs);
        self.byteID=0b0001
    def characterize(self, start_time=None, end_time=None):
        reduced = {};
        for k in self.database.keys:
            data = self.database.get_data(k,start_time=start_time,end_time=end_time);
            data = data.transpose((1,0,2));
            data = data.reshape((data.shape[0],-1));
            rets = np.zeros((data.shape[0],self.num_samples));
            inds = np.random.randint(data.shape[-1],size=(data.shape[0],self.num_samples));
            for n,ind in enumerate(inds):
                    rets[n,:]=data[n,ind];
            reduced[k] = [inds,rets];
        return Signal(priority=3,time=[start_time,end_time],components=reduced)
    def model(self,signal,order=2):
        rets={};
        for k in signal.components.keys():
            if order>signal.components[k][0].shape[1]:
                print('Order is too high for number of samples in '+k)
            sigshape=list(self.database.get_data(k,start_time=signal.time[0], end_time=signal.time[1]).shape);
            sigshape[0:2]=[sigshape[1],sigshape[0]]
            rets[k] = np.zeros(sigshape)
            for n,q in enumerate(signal.components[k][0]):
                p = np.polyfit(q,signal.components[k][1][n],deg=order)
                rets[k][n,:]=(np.polyval(p,np.arange(sigshape[1]*sigshape[2]))).reshape(sigshape[1:]);
            rets[k] = rets[k].transpose((1,0,2))
        return rets;
    def remove(self, signal, start_time=None, end_time=None):
        rets={};
        model = self.model(signal);
        for k in self.database.keys:
            data = self.database.get_data(k,start_time=signal.time[0], end_time=signal.time[1]);
            rets[k]=data-model[k];
        return rets;
    def components(self):
        return ['Index','Value']

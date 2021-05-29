

import math
import json


class denselayer(object):
    ''' nn-layer with only forward-propagation part class
        nlayer =  layer(weight=[[1,2],[3,4]],bias=[5,6],actv='r') '''
    @staticmethod
    def relu(xarray): # just return 0.0 if x is negative
        return tuple((x if (x>0.0) else 0.0) for x in xarray)
    @staticmethod
    def sigmoid(xarray): # magic number 709.7827128933839 to avoid float-overflow
        return tuple(1.0/(1.0+math.exp(-x)) if (-x<709.7827128933839) else 0.0 for x in xarray)
    def __init__(self,weight,bias,actv): # weight/bias can be init with None to assign later
        self.weight, self.bias = weight, bias 
        self.actv = {'r':self.relu,'s':self.sigmoid}[actv] # if 'r' use relu, 's use sigmoid, as activation function
    def frwdprop(self,xarray): # do forward propagation y = actv(w*x+b)
        wxarray = tuple(sum(tuple(x*w for x,w in zip(xarray,warray))) for warray in self.weight) # matric multiplication for w*x part
        wxplusb = tuple(wx + b for wx,b in zip(wxarray,self.bias)) # do element-wise for addition b
        return self.actv(wxplusb) # apply activation function then return result

        
class frwdpropsqnc(object):
    ''' wrap nn-layer to nn-model
        model = frwdpropsqnc((None,None,'r'),(None,None,'s'),)
        model.loadweightbias('weight_n_bias_that_was_dumped_to_json_format_file.jsv') '''
    def __init__(self,*lyrseq): # init with series of (weight, bias, actvtype)
        self.layerseq = tuple(denselayer(*args) for args in lyrseq) # init each layer with user-setting
    def predict(self,array): # tranform input-array to output-array
        for layer in self.layerseq: # by sequenctially calling each layer
            array = layer.frwdprop(array) # forward propagation function
        return array # then return result
    def loadweightbias(self,target):
        if isinstance(target,(str,)): # if string input, assumed it's json-save-file location
            with open(target,'r') as file:
                target = json.loads(file.read()) # read file and loads with json, list of weightbias are expected
        for layer,w,b in zip(self.layerseq,target[::2],target[1::2]): # iterate [w1,b1,w2,b2,...,wx,bx] from target list
            layer.weight = w # assign new weight and bias to each layer
            layer.bias = [bb if isinstance(bb,(float,int,)) else bb[0] for bb in b]


class envstate(object):
    ''' state memory can be used as nn-model virtual-environment
        state = envstate([2,3,4,5,6,7,8,9,10,11,12,13,14])
        state.create_state('frstsctr')
        state.clamp_action(minclrnc,passiveclrnc)
    '''
    def __init__(self,actnlist,reqpoint=((0.2,0.35),(0.35,0.5),(0.5,0.65),(0.65,0.8),)):
        self.actnlist = tuple(actnlist) # creat available action list
        self.actnxcld = []
        self._state = {}
        self._reqpoint = reqpoint
    @property
    def avlbactn(self):
        return tuple(act for act in self.actnlist if not(act in self.actnxcld))
    def clamp_action(self,min,max):
        for act in self.actnlist:
            if (act < min) or (act > max):
                self.actnxcld.append(act)
    def create_state(self,sctr):
        self._state[sctr] = [-1.0 for _ in self.actnlist] # add new state to state-dict
    def discretize_action(self,action): # find nearest available action for input-action
        err = tuple((act-action)**2 for act in self.avlbactn) # calculate error (of available action)
        ind = err.index(min(err)) # find minimum error index (of available action)
        index = self.actnlist.index(self.avlbactn[ind]) # fine actnlist index
        return {'index':index,'value':self.actnlist[index]} # return in dict
    def get_state(self,sctr):
        return tuple(self._state[sctr])
    def update_state(self,sctr,action,feedback):
        actnindx = self.discretize_action(action)['index']
        self._state[sctr][actnindx] = feedback # update new state for an action
        self.actnxcld.append(action)
    def isdone(self,sctr):
        discovered = 0 # init score
        for (rmn,rmx) in self._reqpoint:
            for stt in self.self._state[sctr]:
                if rmn <= stt < rmx: # if state is in required range
                    discovered += 1 # score if in-range point found
                    break # grab only 1 point then break to next req
        return discovered>=len(self._reqpoint) # check if current state is satisfied req


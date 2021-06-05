

import numpy
numpy.seterr(all='raise') # raise error if numpy got under/overflow or numpy will silently produce 'nan'


class _nodes_layer(object):
    def __init__(self):
        self._id = numpy.random.randint(2147483647)
        self._child = None
        self._parent = None
    @property
    def id(self):
        return self._id
    def clear_buffer(self,buffnamelist=None):
        if not buffnamelist: ('_outputbuff','_dcstdintbuff','_dcstdwghbuff','_dcstdbiabuff')
        for attr in buffnamelist:
            if hasattr(self,attr):
                setattr(self, attr, None)
    def nodes_chain_call(self,funcname,passargs={},targetchain='selfonly'):
        if not(targetchain in ('selfonly','upstream','dnstream','linked')):
            raise ValueError('invalid buffer clearing target, should be upstream, dnstream or linked')
        # call target function
        getattr(self,funcname)(**passargs)
        # dnstream node chain
        if targetchain in ('dnstream','linked'):
            if hasattr(self,'_child'):
                if not(self._child is None):
                    self._child.nodes_chain_call(funcname,passargs,'dnstream')
        # upstream node chain
        if targetchain in ('upstream','linked'):
            if hasattr(self,'_parent'):
                if not(self._parent is None):
                    self._parent.nodes_chain_call(funcname,passargs,'upstream')


class input_layer(_nodes_layer):
    def __init__(self,nodenums):
        super().__init__()
        self.nodenums = nodenums
        self._outputbuff = None
    @property
    def output(self):
        # return output from buffer if possible, or else, calculate it
        if self._outputbuff is None:
            raise AttributeError('output of input_layer was not set, syntax: input_layer.output=<user_input>')
        return self._outputbuff
    @output.setter
    def output(self,inptarry):
        if (inptarry.shape[1] != self.nodenums) or (inptarry.shape[2] != 1):
            raise ValueError('invalid input, expect numpy-array shape (n,{},1) , but got {}'.format(self.nodenums,inptarry.shape))
        else:
            self.nodes_chain_call('clear_buffer',{'buffnamelist':('_outputbuff',)},targetchain='dnstream')
            self._outputbuff = inptarry
    @property
    def state(self):
        self_state = {'layer_type':self.__class__.__name__,
                        'layer_id':self.id,
                           'child':self._child.id if self._child else None,
                          'parent':self._parent.id if self._parent else None,
                          'nodenums':self.nodenums,
                          'params':{'_outputbuff':self._outputbuff.tolist(),},
                     }
        return self_state
    def restore_state(self,state):
        pass

# define activation function
def actvfunc_none(inptarry,diff=False):
    return inptarry if not diff else numpy.ones(inptarry.shape)
def actvfunc_relu(inptarry,diff=False):
    return inptarry*(inptarry>0) if not diff else 1.0*(inptarry>0)
def actvfunc_lrelu(inptarry,diff=False):
    if not diff:
        return inptarry*(inptarry>0) + 0.01*inptarry*(inptarry<=0)
    else:
        return 1.0*(inptarry>0) + 0.01*(inptarry<=0)
def actvfunc_sigmoid(inptarry,diff=False):
    if not diff:
        return 1.0/(1.0+numpy.exp(-numpy.clip(inptarry,a_min=-500.0,a_max=500.0)))
    else:
        return actvfunc_sigmoid(inptarry)*(1.0-actvfunc_sigmoid(inptarry))


class neuron_layer(_nodes_layer):
    def __init__(self,nodenums,actvfunc='relu'):
        super().__init__()
        self.nodenums = nodenums
        self.actvfunc = actvfunc
        if self.actvfunc == 'relu':
            self._actvfunc = actvfunc_relu
        elif self.actvfunc == 'lrelu':
            self._actvfunc = actvfunc_lrelu
        elif self.actvfunc == 'sigmoid':
            self._actvfunc = actvfunc_sigmoid
        else:
            raise ValueError('only support \'relu\' or \'sigmoid\' as activation function')
        self._outputbuff = None
        self._dcstdintbuff = None
        self._dcstdwghbuff = None
        self._dcstdbiabuff = None

    @property   
    def input(self):
        return self._parent.output # pulling self-input from parent
    @property
    def weight(self):
        return self._weight
    @property
    def bias(self):
        return self._bias

    @property
    def output(self):
        # return output from buffer if possible, or else, calculate it
        if self._outputbuff is None:
            self.forward_propagation() # calculate output
        return self._outputbuff

    @property
    def dcstdint(self):
        # return output from buffer if possible, or else, calculate it
        if self._dcstdintbuff is None:
            self.backward_propagation() # calculate output
        return self._dcstdintbuff

    @property
    def dcstdwgh(self):
        # return output from buffer if possible, or else, calculate it
        if self._dcstdwghbuff is None:
            self.backward_propagation() # calculate output
        return self._dcstdwghbuff

    @property
    def dcstdbia(self):
        # return output from buffer if possible, or else, calculate it
        if self._dcstdbiabuff is None:
            self.backward_propagation() # calculate output
        return self._dcstdbiabuff

    def init_weightbias(self):
        self._weight = 2.0/numpy.sqrt(self._parent.nodenums)*(0.5-numpy.random.random([self.nodenums,self._parent.nodenums]))
        self._bias = 2.0/numpy.sqrt(self._parent.nodenums)*(0.5-numpy.random.random([self.nodenums,1]))

    def forward_propagation(self,inptarry=None):
        if inptarry is None:
            inptarry = self.input # pulling method (take parent's output as self-input)
        self._outputbuff = self._actvfunc(numpy.matmul(self._weight,inptarry) + self._bias)
        return self.output

    def backward_propagation(self):
        doutdint = self._actvfunc(self.output,diff=True)
        if isinstance(self._child,(cost_layer,)):
            dcstdout = self._child.diffcost # pull loss-function differential
        else:
            dcstdout = numpy.matmul(self._child.weight.T,self._child.dcstdint) # leverage cost from child layer weight and dCost/dIntermidiateOutpt
        self._dcstdintbuff = doutdint*dcstdout # apply chain rule and save dcstdint for parent layer
        dintdwgh = self._parent.output
        self._dcstdwghbuff = numpy.matmul(self.dcstdint,numpy.transpose(dintdwgh,(0,2,1))) # apply chain rule (matrix multiplication part)
        dintdbia = 1.0
        self._dcstdbiabuff = dintdbia*self.dcstdint # chain rule for bias, just replace actvoutp with 1.0 (dIntermidiateOutpt/dBias is 1)

    @property
    def state(self):
        self_state = {'layer_type':self.__class__.__name__,
                        'layer_id':self.id,
                           'child':self._child.id if self._child else None,
                          'parent':self._parent.id if self._child else None,
                        'actvfunc':self.actvfunc,
                        'nodenums':self.nodenums,
                          'params':{
                                    '_outputbuff':self._outputbuff.tolist(),
                                    '_weight':self._weight.tolist(),
                                    '_bias':self._bias.tolist(),
                                    '_dcstdintbuff':self._dcstdintbuff.tolist(),
                                    '_dcstdwghbuff':self._dcstdwghbuff.tolist(),
                                    '_dcstdbiabuff':self._dcstdbiabuff.tolist(),
                                    },
                     }
        return self_state


# define loss function
def lossfunc_bce(pred,trgt,eps=1e-2,diff=False):
    if not diff:
        return -(trgt*numpy.log(numpy.clip(pred,eps,1))+(1-trgt)*numpy.log(numpy.clip(1.0-pred,eps,1)))
    else:
        return -1.0*numpy.clip(trgt,eps,1)/numpy.clip(pred,eps,1) + numpy.clip(1.0-trgt,eps,1)/numpy.clip(1.0-pred,eps,1)
def lossfunc_sqerr(pred,trgt,diff=False):
    return (pred-trgt)**2.0 if not diff else 2.0*(pred-trgt)


class cost_layer(_nodes_layer):
    
    def __init__(self,lossfunc='sqe'):
        super().__init__()
        self.lossfunc = lossfunc
        if self.lossfunc == 'sqe':
            self._lossfunc = lossfunc_sqerr
        elif self.lossfunc == 'bce':
            self._lossfunc = lossfunc_bce
        else:
            raise ValueError('only support \'sqe\' or \'bce\' as loss function')
        self._costbuff = None
        self._diffcostbuff = None

    def calculate_cost(self,trgt):
        self.nodes_chain_call('clear_buffer',{'buffnamelist':('_dcstdintbuff','_dcstdwghbuff','_dcstdbiabuff')},targetchain='upstream')
        if self._parent.output.shape[1:] != trgt.shape[1:]:
            raise ValueError('output size and target size not match')
        self._costbuff = self._lossfunc(self._parent.output,trgt,diff=False)
        self._diffcostbuff = self._lossfunc(self._parent.output,trgt,diff=True)
        return self.cost

    @property
    def cost(self):
        if self._costbuff is None:
            raise AttributeError('cost not be calculated, should call self.calculate_cost with passing target')
        return numpy.sum(numpy.mean(self._costbuff,axis=0))

    @property
    def diffcost(self):
        if self._diffcostbuff is None:
            raise AttributeError('cost not be calculated, should call self.calculate_cost with passing target')
        return self._diffcostbuff

    @property
    def state(self):
        self_state = {'layer_type':self.__class__.__name__,
                        'layer_id':self.id,
                           'child':self._child.id if self._child else None,
                          'parent':self._parent.id if self._child else None,
                        'lossfunc':self.lossfunc,
                          'params':{
                                    '_costbuff':self._costbuff.tolist(),
                                    '_diffcostbuff':self._diffcostbuff.tolist(),
                                    },
                     }
        return self_state


def layer_factory(state):
    layertype = state['layer_type']
    if layertype == 'input_layer':
        layer = input_layer(None)
        layer.nodenums = state['nodenums']
    elif layertype == 'neuron_layer':
        actvfunc = state['actvfunc']
        layer = neuron_layer(None,actvfunc)
        layer.nodenums = state['nodenums']
    elif layertype == 'cost_layer':
        lossfunc = state['lossfunc']
        layer = cost_layer(lossfunc)
    layer._id = state['layer_id']
    layer._childid = state['child']
    layer._parentid = state['parent']
    for key,val in state['params'].items():
        setattr(layer,key,numpy.array(val))
    return layer


class gradientdescent(object):
    def __init__(self,learn_rate=0.1,decay_step=128,decay_rate=0.9):
        self.learn_rate = learn_rate
        self.decay_step = decay_step
        self.decay_rate = decay_rate
        self.iter_count = 0
    @property
    def learnrate(self):
        return self.learn_rate*self.decay_rate**(self.iter_count//self.decay_step)
    def calculate_dparam(self,dcostdpara):
        self.iter_count += 1
        mt = numpy.mean(dcostdpara,axis=0)
        dparam = self.learnrate*mt
        return dparam
    @property
    def state(self):
        self_state = {'method':'gradientdescent',
                      'learn_rate':self.learn_rate,
                      'decay_step':self.decay_step,
                      'decay_rate':self.decay_rate,
                      'iter_count':self.iter_count,}
        return self_state


class momentum(gradientdescent):
    def __init__(self,learn_rate=0.1,decay_step=128,decay_rate=0.9,beta1=0.9):
        super().__init__(learn_rate=learn_rate, decay_step=decay_step, decay_rate=decay_rate)
        self.beta1 = beta1
        self.mtn1 = 0.0
    def calculate_dparam(self,dcostdpara):
        self.iter_count += 1
        mt = self.beta1*self.mtn1 + dcostdpara
        self.mtn1 = numpy.mean(mt,axis=0)
        dparam = self.learnrate*self.mtn1
        return dparam
    @property
    def state(self):
        self_state = super().state
        self_state.update({'method':'momentum','beta1':self.beta1,'mtn1':self.mtn1.tolist(),})
        return self_state


class rmsprop(gradientdescent):
    def __init__(self,learn_rate=0.1,decay_step=128,decay_rate=0.9,beta2=0.99):
        super().__init__(learn_rate=learn_rate, decay_step=decay_step, decay_rate=decay_rate)
        self.beta2 = beta2
        self.eps = 1e-16
        self.vtn1 = 0.0
    def calculate_dparam(self,dcostdpara):
        self.iter_count += 1
        vt = self.beta2*self.vtn1 + (1-self.beta2)*dcostdpara**2
        mt = (1.0/(numpy.sqrt(vt)+self.eps))*dcostdpara
        self.vtn1 = numpy.mean(vt,axis=0)
        dparam = self.learnrate*numpy.mean(mt,axis=0)
        return dparam
    @property
    def state(self):
        self_state = super().state
        self_state.update({'method':'rmsprop','beta2':self.beta2,'eps':self.eps,'vtn1':self.vtn1.tolist(),})
        return self_state


class adam(gradientdescent):
    def __init__(self,learn_rate=0.1,decay_step=128,decay_rate=0.9,beta1=0.9,beta2=0.999):
        super().__init__(learn_rate=learn_rate, decay_step=decay_step, decay_rate=decay_rate)
        self.beta1 = beta1
        self.beta2 = beta2
        self.eps = 1e-16
        self.mtn1 = 0.0
        self.vtn1 = 0.0
    def calculate_dparam(self,dcostdpara):
        self.iter_count += 1
        mt_corr = 1 - self.beta1**self.iter_count
        vt_corr = 1 - self.beta2**self.iter_count
        mt = self.beta1*self.mtn1 + (1-self.beta1)*dcostdpara
        vt = self.beta2*self.vtn1 + (1-self.beta2)*dcostdpara**2
        self.mtn1 = numpy.mean(mt,axis=0)
        self.vtn1 = numpy.mean(vt,axis=0)
        dparam = self.learnrate*(self.mtn1/mt_corr)*(1.0/(numpy.sqrt(self.vtn1/vt_corr) + self.eps))
        return dparam
    @property
    def state(self):
        self_state = super().state
        self_state.update({'method':'adam','beta1':self.beta2,'beta1':self.beta2,'eps':self.eps,'mtn1':self.mtn1.tolist(),'vtn1':self.vtn1.tolist(),})
        return self_state


def optim_factory(state):
    method = state['method']
    if method == 'gradientdescent':
        optim = gradientdescent()
    elif method == 'momentum':
        optim = momentum()
    elif method == 'rmsprop':
        optim = rmsprop()
    elif method == 'adam':
        optim = adam()
    for key,val in state.items():
        setattr(optim,key,val if not(key in ('mtn1','vtn1',)) else numpy.array(val))
    return optim


class optimizer(object):
    def __init__(self,method,setting={}):
        self.method = method
        if not self.method in ('gradientdescent','momentum','rmsprop','adam'):
            raise ValueError('Invalid optimization method, only \'gradientdescent\',\'momentum\',\'rmsprop\' and \'adam\' are support')
        self._optmclss = {'gradientdescent':gradientdescent,'momentum':momentum,'rmsprop':rmsprop,'adam':adam}[self.method]
        self._setting = setting
    def assign_resplyrs(self,nnlyrs):
        self._resplyrs = nnlyrs
        self._respoptm = {}
        for layr in self._resplyrs:
            self._respoptm[layr.id] = {'weight':self._optmclss(**self._setting),
                                       'bias':self._optmclss(**self._setting)}
    def adjustparam(self):
        numpy.seterr(all='ignore')
        for layr in self._resplyrs:
            layr._weight -= numpy.nan_to_num( self._respoptm[layr.id]['weight'].calculate_dparam(layr.dcstdwgh) )
            layr._bias   -= numpy.nan_to_num( self._respoptm[layr.id]['bias'].calculate_dparam(layr.dcstdbia) )
        numpy.seterr(all='raise')
    @property
    def state(self):
        self_state = {
                      'method':self.method,
                      '_respoptm':{id:{'weight':optim['weight'].state,'bias':optim['bias'].state} for id,optim in self._respoptm.items()},
                     }
        return self_state


class sequential_nn_model():
    def __init__(self,*layers,optimizer=None):
        self.layers = []
        self.neuronlayers = []
        for i,layer in enumerate(layers):
            if i == 0:
                if isinstance(layer,(input_layer,)):
                    self.inputlayer = layer
                else:
                    raise ValueError('expect input_layer instance as first layer')
            elif i == (len(layers)-1):
                if isinstance(layer,(cost_layer,)):
                    self.costlayer = layer
                else:
                    raise ValueError('expect cost_layer instance as last layer')
            else:
                if isinstance(layer,(neuron_layer,)):
                    self.neuronlayers.append(layer)
                    self.outputlayer = layer # keep only last-neuron_layer as output_layer
                else:
                    raise ValueError('support only neuron_layer instance as hidden and output layer')
            self.layers.append(layer)
        self.build()
        # assign optimizer job
        self.optimizer = optimizer
        self.optimizer.assign_resplyrs(self.neuronlayers)

    def build(self):
        for i,layer in enumerate(self.layers):
            if i > 0: # add parent if it has one
                layer._parent = self.layers[i-1]
            if (i+1) < len(self.layers): # add child if it has one
                layer._child = self.layers[i+1]
            if isinstance(layer, (neuron_layer,)): 
                layer.init_weightbias() # init weight and bias in neuron layer

    def predict(self,inptarry):
        self.inputlayer.output = inptarry # assign state to input_layer
        return self.outputlayer.output # then take output from last-neuron_layer (not cost layer)

    def train(self,inptarry,trgtarry):
        self.inputlayer.output = inptarry # assign input
        traincost = self.costlayer.calculate_cost(trgtarry) # assign target-output
        self.optimizer.adjustparam()
        return traincost

    @property
    def state(self):
        self_state = {
                    'inputlayer.id':self.inputlayer.id,
                    'outputlayer.id':self.outputlayer.id,
                    'costlayer.id':self.costlayer.id,
                    'neuronlayers.id':[layer.id for layer in self.neuronlayers],
                    'layers_state':{layer.id:layer.state for layer in self.layers},
                    'optimizer_state':self.optimizer.state
                    }
        return self_state

    def restore_state(self,state):
        # layers restoration
        layers_store = {int(id):layer_factory(state) for id,state in state['layers_state'].items()}
        self.inputlayer = layers_store[state['inputlayer.id']]
        self.outputlayer = layers_store[state['outputlayer.id']]
        self.costlayer = layers_store[state['costlayer.id']]
        self.neuronlayers = [layers_store[id] for id in state['neuronlayers.id']]
        self.layers = [self.inputlayer] + self.neuronlayers + [self.outputlayer,self.costlayer]
        for layer in self.layers:
            if not layer._childid is None: layer._child = layers_store[layer._childid]
            if not layer._parentid is None: layer._parent = layers_store[layer._parentid]
        # optimizer restoration
        optim_state = state['optimizer_state']
        self.optimizer = optimizer(optim_state['method'])
        self.optimizer._resplyrs = self.neuronlayers
        self.optimizer._respoptm = {}
        for id,optimstate in optim_state['_respoptm'].items():
            self.optimizer._respoptm[int(id)] = {'weight':optim_factory(optimstate['weight']),
                                                 'bias':optim_factory(optimstate['bias']),}


# credits and refs
# https://towardsdatascience.com/part-1-a-neural-network-from-scratch-foundation-e2d119df0f40 <<< foundation
# https://towardsdatascience.com/part-2-gradient-descent-and-backpropagation-bf90932c066a <<< back propagation knowledge
# https://github.com/pytorch/pytorch/blob/master/torch/optim/adam.py <<< adam optimizer knowledge


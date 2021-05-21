

import numpy

__version__ = (2021,5,22,'alpha')


class _nodes_layer():
    def __init__(self,layername):
        self._child = None
        self._parent = None
        self.layername = layername

    def reset_buffer(self):
        # reset self buffers
        for attr in ('_intermbuff',
                     '_outputbuff',
                     '_dcostdintermbuff',
                     '_dcostdoutputbuff',
                     '_dcostdweightbuff',
                     '_dcostdbiasbuff'):
            if hasattr(self,attr):
                setattr(self, attr, None)

    def nodes_chain_call(self,funcname,targetchain='selfonly'):
        if not(targetchain in ('selfonly','upstream','dnstream','linked')):
            raise ValueError('invalid buffer clearing target, should be upstream, dnstream or linked')
        # call target function
        getattr(self,funcname)()
        # downstream node chain
        if targetchain in ('downstream','linked'):
            if hasattr(self,'_child'):
                if not(self._child is None):
                    self._child.nodes_chain_call(funcname,'downstream')
        # upstream node chain
        if targetchain in ('upstream','linked'):
            if hasattr(self,'_parent'):
                if not(self._parent is None):
                    self._parent.nodes_chain_call(funcname,'upstream')


class input_layer(_nodes_layer):
    def __init__(self,nodenums,layername=None):
        super().__init__(layername)
        self._outputbuff = None
        self.nodenums = nodenums

    @property
    def output(self):
        # return output from buffer if possible, or else, calculate it
        if self._outputbuff is None:
            raise AttributeError('output of input_layer was not set, syntax: input_layer.output=<user_input>')
        return self._outputbuff

    @output.setter
    def output(self,array):
        array = numpy.array(array)
        if (array.shape[0] < 1) or (array.shape[1] != 1):
            raise ValueError('invalid input, expect array shape (x,1)')
        else:
            self._outputbuff = array


# define activation function
def actvfunc_none(input):
    return input
def actvfunc_deriv_none(input):
    return numpy.ones(input.shape)
def actvfunc_relu(input):
    return numpy.where(input<0,0,input)
def actvfunc_deriv_relu(input):
    return numpy.where(input<0,0,1)
def actvfunc_lrelu(input):
    return numpy.where(input<0,0.01*input,input)
def actvfunc_deriv_lrelu(input):
    return numpy.where(input<0,0.01,1)
def actvfunc_sigmoid(input):
    return 1.0/(1.0+numpy.exp(-input))
def actvfunc_deriv_sigmoid(input):
    return actvfunc_sigmoid(input)*(1.0-actvfunc_sigmoid(input))

class neuron_layer(_nodes_layer):

    def actvfunc(self,input,mode='norm'):
        return self._actvfunc[self._actvtype][mode](input)

    def __init__(self,nodenums,layername=None,actvfunc='relu',learnrate=0.1):
        super().__init__(layername)
        # init self-buffer to reduce calculating time
        self._intermbuff = None
        self._outputbuff = None
        self._dcostdintermbuff = None
        self._dcostdweightbuff = None
        self._dcostdbiasbuff = None
        # init self-adjusted-hyper-param buffer
        self.nodenums = nodenums
        self._actvfunc = {'none':{'norm':actvfunc_none,
                                  'deriv':actvfunc_deriv_none},
                          'relu':{'norm':actvfunc_relu,
                                  'deriv':actvfunc_deriv_relu},
                          'lrelu':{'norm':actvfunc_lrelu,
                                  'deriv':actvfunc_deriv_lrelu},
                          'sigmoid':{'norm':actvfunc_sigmoid,
                                     'deriv':actvfunc_deriv_sigmoid},}
        self._actvtype = actvfunc
        self.learnrate = learnrate
        self.clear_dropout() # set dropprob to zero

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
    def interm(self):
        # return intermediate-value (output before activated) from buffer if possible, or else, calculate it
        if self._intermbuff is None:
            self.forward_propagation() # calculate output
        return self._intermbuff

    @property
    def output(self):
        # return output from buffer if possible, or else, calculate it
        if self._outputbuff is None:
            self.forward_propagation() # calculate output
        return self._drptmtrx*self._outputbuff

    @property
    def dcostdinterm(self):
        # return output from buffer if possible, or else, calculate it
        if self._dcostdintermbuff is None:
            self.backward_propagation() # calculate output
        return self._dcostdintermbuff

    def init_weightbiasmatrix(self):
        self._weight = numpy.random.randn(self.nodenums,self._parent.nodenums)
        self._bias = numpy.random.randn(self.nodenums,1)

    def forward_propagation(self,array=None):
        if array is None:
            array = self.input # pulling method (take parent's output as self-input)
        else:
            array = numpy.array(array) # pushing method (usually from full_forward_propagation of model class)
        array = numpy.nan_to_num(array)
        self._intermbuff = numpy.dot(self._weight,array) + self._bias
        self._outputbuff = self.actvfunc(self._intermbuff)
        return self.output
    
    def backward_propagation(self):
        # chain rule for dcost by dweight/dbias calculation
        # [dcost_dweight(i)] = [dinterm(i)_dweight(i)]*[doutput(i)_dinterm(i)]*[dcost_doutput(i)]
        # [dcost_dbias(i)] = [dinterm(i)_dbias(i)]*[doutput(i)_dinterm(i)]*[dcost_doutput(i)]
        # get dcostdinterm from child or calculate from cost_layer feedback
        if isinstance(self._child,(cost_layer,)):
            doutputdinterm = self.actvfunc(self.interm,mode='deriv')
            dcostdoutput = self._child.dcostdoutput # leveraged dcost-by-doutput from cost_layer-child
            self._dcostdintermbuff = doutputdinterm*dcostdoutput # apply chain rule and keep this value for parent's backpropagation
        else:
            # product of (leveraged dcost-by-dinterm from child layer) and (weight of child layer)
            self._dcostdintermbuff = numpy.dot(numpy.transpose(self._child.weight),self._child.dcostdinterm)
        dintermdweight = numpy.transpose(self.input) # d(m*x+c)/d(c), just x: parent layer output (self-input actually)
        self._dcostdweightbuff = numpy.dot(self._dcostdintermbuff,dintermdweight) # apply chain rule
        dintermdbias = numpy.identity(self._dcostdintermbuff.size) # d(m*x+c)/d(c), deriv of c is just 1, then make identity-matrix that support _dcostdintermbuff-vector
        self._dcostdbiasbuff = numpy.dot(dintermdbias,self._dcostdintermbuff) # apply chain rule

    def update_hyperparams(self):
        # OBSOLETED
        self._weight = self._weight - self.learnrate*self._dcostdweightbuff
        self._bias = self._bias - self.learnrate*self._dcostdbiasbuff

    def reset_batchdcostbuff(self):
        self._batchdcostbuff = {'_dcostdweightbuff':[],
                                '_dcostdbiasbuff':[]}

    def save_batchdcostbuff(self):
        if not hasattr(self,'_batchdcostbuff'):
            self.reset_batchdcostbuff()
        self._batchdcostbuff['_dcostdweightbuff'].append(numpy.array(self._dcostdweightbuff).copy())
        self._batchdcostbuff['_dcostdbiasbuff'].append(numpy.array(self._dcostdbiasbuff).copy())
        
    def update_batchhyperparams(self,optim='sgd'):
        if not (optim in ('sgd','momentum','rmsprop','adam',)):
            raise ValueError('optim method should be \'sgd\', \'momentum\', \'rmsprop\' or \'adam\'')
        if optim == 'sgd':
            dwt_sgd = numpy.nanmean(self._batchdcostbuff['_dcostdweightbuff'],axis=0)
            dbt_sgd = numpy.nanmean(self._batchdcostbuff['_dcostdbiasbuff'],axis=0)
            # adjust weight and bias from dwt and dbt from optim method
            self._weight = self._weight - self.learnrate*dwt_sgd
            self._bias = self._bias - self.learnrate*dbt_sgd
        elif optim == 'momentum':
            if not hasattr(self,'optim_moment'):
                self.optim_moment = {'beta':0.9,'mtn1_w':0,'mtn1_b':0,'cnt':1}
            beta = min(self.optim_moment['beta'],1.0-(1.0/self.optim_moment['cnt']))
            mtn1_w = self.optim_moment['mtn1_w']
            mtn1_b = self.optim_moment['mtn1_b']
            dwt_moment = beta*mtn1_w + (1-beta)*numpy.nanmean(self._batchdcostbuff['_dcostdweightbuff'],axis=0)
            dbt_moment = beta*mtn1_b + (1-beta)*numpy.nanmean(self._batchdcostbuff['_dcostdbiasbuff'],axis=0)
            self.optim_moment['mtn1_w'] = dwt_moment
            self.optim_moment['mtn1_b'] = dbt_moment
            self.optim_moment['cnt'] += 1
            # adjust weight and bias from dwt and dbt from optim method
            self._weight = self._weight - self.learnrate*dwt_moment
            self._bias = self._bias - self.learnrate*dbt_moment
        elif optim == 'rmsprop':
            if not hasattr(self,'rmsprop'):
                self.optim_rmsp = {'beta':0.99,'eps':1e-8,'vtn1_w':0,'vtn1_b':0,'cnt':1}
            beta = min(self.optim_rmsp['beta'],1.0-(1.0/self.optim_rmsp['cnt']))
            eps = self.optim_rmsp['eps']
            vtn1_w = self.optim_rmsp['vtn1_w']
            vtn1_b = self.optim_rmsp['vtn1_b']
            dwt_array = []
            dbt_array = []
            vt_w_array = []
            vt_b_array = []
            for dcostdw, dcostdb in zip(self._batchdcostbuff['_dcostdweightbuff'],self._batchdcostbuff['_dcostdbiasbuff']):
                vt_w = beta*vtn1_w + (1-beta)*dcostdw**2
                vt_w_array.append( vt_w )
                dwt_array.append( (1.0/numpy.sqrt(vt_w+eps))*dcostdw )
                vt_b = beta*vtn1_b + (1-beta)*dcostdb**2
                vt_b_array.append( vt_b )
                dbt_array.append( (1.0/numpy.sqrt(vt_b+eps))*dcostdb )
            self.optim_rmsp['vtn1_w'] = numpy.nanmean(vt_w_array,axis=0)
            self.optim_rmsp['vtn1_b'] = numpy.nanmean(vt_b_array,axis=0)
            dwt_rsmp = numpy.nanmean(dwt_array,axis=0)
            dbt_rsmp = numpy.nanmean(dbt_array,axis=0)
            # adjust weight and bias from dwt and dbt from optim method
            self._weight = self._weight - self.learnrate*dwt_rsmp
            self._bias = self._bias - self.learnrate*dbt_rsmp
        else: # adam (momentum and rmsprop combined)
            if not hasattr(self,'rmsprop'):
                self.optim_adam = {'beta1':0.9,'mtn1_w':0,'mtn1_b':0,'cnt':1,'beta2':0.99,'eps':1e-8,'vtn1_w':0,'vtn1_b':0,'cnt':1}
            # calculate rmsprop part
            beta1 = min(self.optim_adam['beta1'],1.0-(1.0/self.optim_adam['cnt']))
            beta2 = min(self.optim_adam['beta2'],1.0-(1.0/self.optim_adam['cnt']))
            eps = self.optim_adam['eps']
            vtn1_w = self.optim_adam['vtn1_w']
            vtn1_b = self.optim_adam['vtn1_b']
            mtn1_w = self.optim_adam['mtn1_w']
            mtn1_b = self.optim_adam['mtn1_b']
            dwt_array = []
            dbt_array = []
            vt_w_array = []
            vt_b_array = []
            for dcostdw, dcostdb in zip(self._batchdcostbuff['_dcostdweightbuff'],self._batchdcostbuff['_dcostdbiasbuff']):
                vt_w = beta2*vtn1_w + (1-beta2)*dcostdw**2
                vt_w_array.append( vt_w )
                dwt_array.append( (1.0/numpy.sqrt(vt_w+eps))*dcostdw )
                vt_b = beta2*vtn1_b + (1-beta2)*dcostdb**2
                vt_b_array.append( vt_b )
                dbt_array.append( (1.0/numpy.sqrt(vt_b+eps))*dcostdb )
            dwt_rsmp = numpy.nanmean(dwt_array,axis=0)
            dbt_rsmp = numpy.nanmean(dbt_array,axis=0)
            # calculate momentum part
            dwt_adam = beta1*mtn1_w + (1-beta1)*dwt_rsmp
            dbt_adam = beta1*mtn1_b + (1-beta1)*dbt_rsmp
            # update momentum
            self.optim_adam['vtn1_w'] = numpy.nanmean(vt_w_array,axis=0)
            self.optim_adam['vtn1_b'] = numpy.nanmean(vt_b_array,axis=0)
            self.optim_adam['mtn1_w'] = dwt_adam
            self.optim_adam['mtn1_b'] = dbt_adam
            # adjust weight and bias from dwt and dbt from optim method
            self._weight = self._weight - self.learnrate*dwt_adam
            self._bias = self._bias - self.learnrate*dbt_adam

    def set_dropout(self,dropprob):
        self._drptmtrx = numpy.where(numpy.random.random((self.nodenums,1))>dropprob,1,numpy.nan)

    def clear_dropout(self):
        self._drptmtrx = numpy.ones((self.nodenums,1))


# define cost function
def lossfunc_cross_entropy(y_predict,y_target,epsilon=1e-15):
    return numpy.nan_to_num(-(y_target*numpy.log(y_predict+epsilon)+(1-y_target)*numpy.log(1-y_predict+epsilon)))
def lossfunc_cross_entropy_deriv(y_predict,y_target,epsilon=1e-15):
    return numpy.nan_to_num((-((y_target+epsilon)/(y_predict+epsilon))+((1-y_target+epsilon)/(1-y_predict+epsilon)))/len(y_target))
def lossfunc_square_error(y_predict,y_target):
    return numpy.nan_to_num((y_predict-y_target)**2)
def lossfunc_square_error_deriv(y_predict,y_target):
    return numpy.nan_to_num(2.0*(y_predict-y_target))

class cost_layer(_nodes_layer):

    def costfunc(self,y_predict,y_target,mode='norm'):
        return self._costfunc[self._costtype][mode](y_predict,y_target)

    def __init__(self,costfunc,layername=None):
        super().__init__(layername)
        self._cost = None
        self._dcostdoutputbuff = None
        self._costfunc = {'square_error':{'norm':lossfunc_square_error,
                                         'deriv':lossfunc_square_error_deriv},
                         'cross_entropy':{'norm':lossfunc_cross_entropy,
                                         'deriv':lossfunc_cross_entropy_deriv},}
        self._costtype = costfunc

    def calculate_cost(self,y_target):
        y_target = numpy.array(y_target)
        self._cost = self.costfunc(self._parent.output, y_target,mode='norm')
        self._dcostdoutputbuff = numpy.array(self.costfunc(self._parent.output, y_target,mode='deriv'))
        return self.cost

    @property
    def cost(self):
        if self._cost is None:
            raise AttributeError('cost not be calculated, should call self.calculate_cost with passing target')
        return self._cost

    @property
    def dcostdoutput(self):
        if self._dcostdoutputbuff is None:
            raise AttributeError('cost not be calculated, should call self.calculate_cost with passing target')
        return self._dcostdoutputbuff


class neural_network_model():
    '''
    just neuron layer wrapper for easy build
    '''
    def __init__(self):
        self.layers = []
        
    def add_layer(self,layer):
        if not(self.layers):
            if not(isinstance(layer, (input_layer,))):
                # raise if first added layer is not input_layer
                raise TypeError('first layer must be input_layer class')
        else:
            if isinstance(self.layers[-1],(cost_layer,)):
                # raise if model already closed
                raise TypeError('cost_layer was already added, network closed')
        self.layers.append(layer)

    def build(self):
        for i,layer in enumerate(self.layers):
            if i > 0: # add parent if it has one
                layer._parent = self.layers[i-1]
            if (i+1) < len(self.layers): # add child if it has one
                layer._child = self.layers[i+1]
            if isinstance(layer, (neuron_layer,)): 
                layer.init_weightbiasmatrix() # init weight and bias in neuron layer

    def reset_buffer(self):
        for layer in self.layers:
            layer.reset_buffer()
        # optional: use nodes-chain method,
        # self._layers[0].nodes_chain_call('reset_buffer',targetchain='linked') 

    def set_input(self,array):
        self.layers[0].output = array

    def predict(self,userinput):
        self.reset_buffer()
        # return output from lastest-neuron-layer
        self.layers[0].output = userinput
        for layer in reversed(self.layers):
            if isinstance(layer, (neuron_layer,)):
                return layer.output
        raise TypeError('no neuron_layer found')

    def calculate_cost(self,y_target):
        # find last cost_layer and call cost-calculation
        for layer in reversed(self.layers):
            if isinstance(layer, (cost_layer,)):
                layer.calculate_cost(numpy.array(y_target))
                return layer.cost
        raise TypeError('no cost_layer found')
        
    def do_backpropagation(self):
        # find first neuron_layer and call backward_propagation,
        # all other downstream-nodes will automatically call calculate propagation to satisfy buffer-request
        for layer in self.layers:
            if isinstance(layer, (neuron_layer,)):
                layer.backward_propagation()
                return

    def adjust_weightbias(self):
        for layer in self.layers:
            if isinstance(layer, (neuron_layer,)):
                layer.update_hyperparams()

    def save_batchdcost(self):
        for layer in self.layers:
            if isinstance(layer, (neuron_layer,)):
                layer.save_batchdcostbuff()

    def adjust_batchweightbias(self,optim='sgd'):
        for layer in self.layers:
            if isinstance(layer, (neuron_layer,)):
                layer.update_batchhyperparams(optim=optim)
                layer.reset_batchdcostbuff()

    def get_model_info(self):
        print('-------- get_model_info')
        for layer in self.layers:
            print('---- layername: {}'.format(layer.layername))
            print('class: {}'.format(layer.__class__.__name__))
            if hasattr(layer, 'weight'): print('weight: {}'.format(str(layer.weight).replace('\n',',')))
            if hasattr(layer, 'bias'): print('bias: {}'.format(str(layer.bias).replace('\n',',')))

    def set_dropout(self,dropprob):
        for layer in self.layers:
            if isinstance(layer, (neuron_layer,)):
                layer.set_dropout(dropprob)

    def clear_dropout(self):
        for layer in self.layers:
            if isinstance(layer, (neuron_layer,)):
                layer.clear_dropout()

    def pack_weightbias(self):
        weightbaislist = []
        for layer in self.layers:
            if hasattr(layer,'_weight'):
                weightbaislist.append(numpy.ndarray.tolist(layer._weight))
            if hasattr(layer,'_bias'):
                weightbaislist.append([b[0] for b in numpy.ndarray.tolist(layer._bias)])
        return weightbaislist

    def pack_model_info(self):
        model_info = []
        for i,layer in enumerate(self.layers):
            layernum = i
            layername = layer.layername if hasattr(layer,'layername') else None
            classname = layer.__class__.__name__
            nodenums = layer.nodenums if hasattr(layer,'nodenums') else None
            actvtype = layer._actvtype if hasattr(layer,'_actvtype') else None
            costtype = layer._costtype if hasattr(layer,'_costtype') else None
            weight = numpy.ndarray.tolist(layer._weight) if hasattr(layer,'_weight') else None
            bias = numpy.ndarray.tolist(layer._bias) if hasattr(layer,'_bias') else None
            model_info.append({'layernum':layernum,
                               'layername':layername,
                               'classname':classname,
                               'nodenums':nodenums,
                               'actvtype':actvtype,
                               'costtype':costtype,
                               'weight':weight,
                               'bias':bias})
        return model_info

    def load_model_weight_bias(self,modelinfo):
        for info in modelinfo:
            if info['weight'] and info['bias']:
                layer = self.layers[info['layernum']]
                layer._weight = numpy.array(info['weight'])
                layer._bias = numpy.array(info['bias'])


# credits and refs
# https://towardsdatascience.com/part-1-a-neural-network-from-scratch-foundation-e2d119df0f40
# https://towardsdatascience.com/part-2-gradient-descent-and-backpropagation-bf90932c066a




import numpy

numpy.seterr(all='raise')

def actvfunc_relu(inputarray):
    return numpy.clip(inputarray,a_min=0.0,a_max=None) # return value only if its positive
def actvfunc_relu_diff(inputarray):
    return numpy.where(inputarray<0.0,0.0,1.0) # return 1 if positive else 0

def actvfunc_sigmoid(inputarray):
    return 1.0/(1.0+numpy.exp(-numpy.clip(inputarray,a_min=-500.0,a_max=500.0)))
def actvfunc_sigmoid_diff(inputarray):
    return actvfunc_sigmoid(inputarray)*(1.0-actvfunc_sigmoid(inputarray))

def lossfunc_bce(pred,trgt,eps=1e-2):
    return -(trgt*numpy.log(numpy.clip(pred,1e-2,1))+(1-trgt)*numpy.log(numpy.clip(1.0-pred,1e-2,1)))
def lossfunc_bce_diff(pred,trgt,eps=1e-2):
    return -1.0*(trgt)/numpy.clip(pred,1e-2,1) + (1.0-trgt)/numpy.clip(1.0-pred,1e-2,1)

def lossfunc_sqerr(pred,trgt):
    return (pred-trgt)**2.0
def lossfunc_sqerr_diff(pred,trgt):
    return 2.0*(pred-trgt)


class relu2sigm2bcel(object):
    def __init__(self,inptnods,hddnnods,outpnods,optimizr_class,optimizr_setting={}):
        self.hdn_weight = 2.0/numpy.sqrt(inptnods)*(0.5-numpy.random.random([hddnnods,inptnods]))
        self.hdn_bias = 2.0/numpy.sqrt(inptnods)*(0.5-numpy.random.random([hddnnods,1]))
        self.out_weight = 2.0/numpy.sqrt(hddnnods)*(0.5-numpy.random.random([outpnods,hddnnods]))
        self.out_bias = 2.0/numpy.sqrt(hddnnods)*(0.5-numpy.random.random([outpnods,1]))
        self.hdn_weight_optimizr = optimizr_class(**optimizr_setting)
        self.hdn_bias_optimizr = optimizr_class(**optimizr_setting)
        self.out_weight_optimizr = optimizr_class(**optimizr_setting)
        self.out_bias_optimizr = optimizr_class(**optimizr_setting)
    def frwdprop(self,inptbtch):
        btchnums = len(inptbtch) # get batch nums
        hdnlyr_wghttnsr = numpy.tile(self.hdn_weight,(btchnums,1,1)) # tile hddnwght to support batch
        hdnlyr_wghtoutp = numpy.matmul(hdnlyr_wghttnsr,inptbtch) # weight mul
        del hdnlyr_wghttnsr
        hdnlyr_biastnsr = numpy.tile(self.hdn_bias,(btchnums,1,1)) # tile hddnbias to support batch
        hdnlyr_biasoutp = hdnlyr_wghtoutp + hdnlyr_biastnsr # bias add
        del hdnlyr_wghtoutp, hdnlyr_biastnsr
        hdnlyr_actvoutp = actvfunc_relu(hdnlyr_biasoutp) # sigmoid
        del hdnlyr_biasoutp
        outlyr_wghttnsr = numpy.tile(self.out_weight,(btchnums,1,1)) # tile outpwght to support batch
        outlyr_wghtoutp = numpy.matmul(outlyr_wghttnsr,hdnlyr_actvoutp) # weight mul
        outlyr_biastnsr = numpy.tile(self.out_bias,(btchnums,1,1)) # tile outpbias to support batch
        outlyr_biasoutp = outlyr_wghtoutp + outlyr_biastnsr # bias add
        del outlyr_wghtoutp, outlyr_biastnsr
        outlyr_actvoutp = actvfunc_sigmoid(outlyr_biasoutp) # sigmoid
        return hdnlyr_actvoutp, outlyr_actvoutp, outlyr_wghttnsr
    def calcloss(self,outlyr_actvoutp,trgtbtch):
        predloss = lossfunc_bce(outlyr_actvoutp,trgtbtch) # just for monitoring
        diffloss = lossfunc_bce_diff(outlyr_actvoutp,trgtbtch) # for optim
        return predloss, diffloss
    def backprop(self,inptbtch,hdnlyr_actvoutp,outlyr_actvoutp,outlyr_wghttnsr,diffloss):
        outlyr_dintdwgh = hdnlyr_actvoutp # dIntermidiateOutpt/dWeight is input of layer
        outlyr_doutdint = actvfunc_sigmoid_diff(outlyr_actvoutp) # dOutput/dIntermidiateOutpt, output layer activation is Sigmoid
        outlyr_dcstdout = diffloss # dCost/dOutput
        outlyr_dcstdint = outlyr_doutdint*outlyr_dcstdout # apply chain rule (element-wise part)
        outlyr_dcstdwgh = numpy.matmul(outlyr_dcstdint,numpy.transpose(outlyr_dintdwgh,(0,2,1))) # apply chain rule (matrix multiplication part)
        outlyr_dcstdbai = 1.0*outlyr_doutdint*outlyr_dcstdout # chain rule for bias, just replace hdnlyr_actvoutp with 1.0 (dIntermidiateOutpt/dBias is 1)
        del outlyr_doutdint
        hdnlyr_dintdwgh = inptbtch # Use input array since input of hidden layer is user-input
        hdnlyr_doutdint = actvfunc_relu_diff(hdnlyr_actvoutp) # dOutput/dIntermidiateOutpt, output layer activation is ReLU
        hdnlyr_dcstdout = numpy.matmul(numpy.transpose(outlyr_wghttnsr,(0,2,1)),outlyr_dcstdint) # leverage cost from output layer weight and dCost/dIntermidiateOutpt
        del outlyr_dcstdint
        hdnlyr_dcstdint = hdnlyr_doutdint*hdnlyr_dcstdout # chain rule for bias, just replace hdnlyr_actvoutp with 1.0 (dIntermidiateOutpt/dBias is 1)
        hdnlyr_dcstdwgh = numpy.matmul(hdnlyr_dcstdint,numpy.transpose(hdnlyr_dintdwgh,(0,2,1)))
        del hdnlyr_dcstdint
        hdnlyr_dcstdbai = 1.0*hdnlyr_doutdint*hdnlyr_dcstdout
        del hdnlyr_dcstdout, hdnlyr_doutdint
        return hdnlyr_dcstdwgh,hdnlyr_dcstdbai,outlyr_dcstdwgh,outlyr_dcstdbai
    def predict(self,inptarry):
        inptbtch = numpy.array([[[inpt] for inpt in inptarry]])
        _, outlyr_actvoutp, _ = self.frwdprop(inptbtch)
        return outlyr_actvoutp.squeeze().tolist()
    def train(self,inptbtch,trgtbtch):
        hdnlyr_actvoutp, outlyr_actvoutp, outlyr_wghttnsr = self.frwdprop(inptbtch)
        predloss, diffloss = self.calcloss(outlyr_actvoutp,trgtbtch)
        del trgtbtch
        hdnlyr_dcstdwgh,hdnlyr_dcstdbai,outlyr_dcstdwgh,outlyr_dcstdbai = self.backprop(inptbtch,hdnlyr_actvoutp,outlyr_actvoutp,outlyr_wghttnsr,diffloss)
        del inptbtch,hdnlyr_actvoutp,outlyr_actvoutp,outlyr_wghttnsr,diffloss
        self.hdn_weight = self.hdn_weight_optimizr.update_params(self.hdn_weight,hdnlyr_dcstdwgh)
        self.hdn_bias = self.hdn_bias_optimizr.update_params(self.hdn_bias,hdnlyr_dcstdbai)
        self.out_weight = self.out_weight_optimizr.update_params(self.out_weight,outlyr_dcstdwgh)
        self.out_bias = self.out_bias_optimizr.update_params(self.out_bias,outlyr_dcstdbai)
        del hdnlyr_dcstdwgh,hdnlyr_dcstdbai,outlyr_dcstdwgh,outlyr_dcstdbai
        return predloss
    def pack_model_state(self):
        state_dict = {'hdn_weight':self.hdn_weight.tolist(),
                      'hdn_bias':self.hdn_bias.tolist(),
                      'out_weight':self.out_weight.tolist(),
                      'out_bias':self.out_bias.tolist(),}
        for optimname in ('hdn_weight_optimizr','hdn_bias_optimizr','out_weight_optimizr','out_bias_optimizr'):
            optim = getattr(self,optimname)
            state_dict[optimname] = {}
            for optimattr in ('learn_rate','decay_step','decay_rate','iter_count','beta1','beta2','eps'):
                state_dict[optimname][optimattr] = getattr(optim,optimattr) if hasattr(optim,optimattr) else None
            for optimattr in ('mtn1','vtn1'):
                state_dict[optimname][optimattr] = getattr(optim,optimattr).tolist() if hasattr(optim,optimattr) else None
        return state_dict
    def load_model_state(self,state_dict):
        self.hdn_weight = numpy.array(state_dict['hdn_weight'])
        self.hdn_bias = numpy.array(state_dict['hdn_bias'])
        self.out_weight = numpy.array(state_dict['out_weight'])
        self.out_bias = numpy.array(state_dict['out_bias'])
        for optimname in ('hdn_weight_optimizr','hdn_bias_optimizr','out_weight_optimizr','out_bias_optimizr'):
            optim = getattr(self,optimname)
            for optimattr in ('learn_rate','decay_step','decay_rate','iter_count','beta1','beta2','eps'):
                if not(state_dict[optimname][optimattr] is None):
                    setattr(optim,optimattr,state_dict[optimname][optimattr])
            for optimattr in ('mtn1','vtn1'):
                if not(state_dict[optimname][optimattr] is None):
                    setattr(optim,optimattr,numpy.array(state_dict[optimname][optimattr]))


class gradient(object):
    def __init__(self,learn_rate=0.1,decay_step=128,decay_rate=0.9):
        self.learn_rate = learn_rate
        self.decay_step = decay_step
        self.decay_rate = decay_rate
        self.iter_count = 0
    @property
    def learnrate(self):
        return self.learn_rate*self.decay_rate**(self.iter_count//self.decay_step)
    def update_params(self,params,dcostdpara):
        self.iter_count += 1
        mt = numpy.mean(dcostdpara,axis=0)
        return params-self.learnrate*mt


class momentum(gradient):
    def __init__(self,learn_rate=0.1,decay_step=128,decay_rate=0.9,beta1=0.9):
        super().__init__(learn_rate=learn_rate, decay_step=decay_step, decay_rate=decay_rate)
        self.beta1 = beta1
        self.mtn1 = 0.0
    def update_params(self,params,dcostdpara):
        self.iter_count += 1
        mt = self.beta1*self.mtn1 + (1-self.beta1)*dcostdpara
        self.mtn1 = numpy.mean(mt,axis=0)
        return params-self.learnrate*self.mtn1


class rmsprop(gradient):
    def __init__(self,learn_rate=0.1,decay_step=128,decay_rate=0.9,beta2=0.99):
        super().__init__(learn_rate=learn_rate, decay_step=decay_step, decay_rate=decay_rate)
        self.beta2 = beta2
        self.eps = 1e-8
        self.vtn1 = 0.0
    def update_params(self,params,dcostdpara):
        self.iter_count += 1
        vt = self.beta2*self.vtn1 + (1-self.beta2)*dcostdpara**2
        mt = (1.0/(numpy.sqrt(vt)+self.eps))*dcostdpara
        self.vtn1 = numpy.mean(vt,axis=0)
        return params-self.learnrate*numpy.mean(mt,axis=0)


class adam(gradient):
    def __init__(self,learn_rate=0.1,decay_step=128,decay_rate=0.9,beta1=0.9,beta2=0.999):
        super().__init__(learn_rate=learn_rate, decay_step=decay_step, decay_rate=decay_rate)
        self.beta1 = beta1
        self.beta2 = beta2
        self.eps = 1e-8
        self.mtn1 = 0.0
        self.vtn1 = 0.0
    def update_params(self,params,dcostdpara):
        self.iter_count += 1
        mt_corr = 1 - self.beta1**self.iter_count
        vt_corr = 1 - self.beta2**self.iter_count
        mt = self.beta1*self.mtn1 + (1-self.beta1)*dcostdpara
        vt = self.beta2*self.vtn1 + (1-self.beta2)*dcostdpara**2
        # vt = self.beta2*self.vtn1 + (1-self.beta2)*dcostdpara**2
        # mt = self.beta1*self.mtn1 + (1-self.beta1)*((1.0/(numpy.sqrt(vt)/vt_corr+self.eps))*dcostdpara)
        self.mtn1 = numpy.mean(mt,axis=0)
        self.vtn1 = numpy.mean(vt,axis=0)
        # return params-(self.learnrate/mt_corr)*self.mtn1
        return params-self.learnrate*(self.mtn1/mt_corr)*(1.0/(numpy.sqrt(self.vtn1/vt_corr) + self.eps))


if __name__ == '__main__':
    pass


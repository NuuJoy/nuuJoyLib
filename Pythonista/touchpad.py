

import time
import math
import ui
import scene
import multiprocessing


__version__ = (2021,2,17,'beta')


class touchPadCore(scene.Scene):
    '''
    touchPad user interface
    Purpose:
        Custom game pad on touch screen and handle output action from external function
    Note:
        - You can init and use default ui, or use clear_widgets and add_widget to customize,
          or maybe override setup function and define self.components by coding.
        - Prior widget in self.components will be called if their responses area is intersect.
    Example:
        # init touchPad class, this come with default ui, you can call joypad.run() even here.
        joypad = touchPad()
        # clear all default widgets if you want to build it from ground
        joypad.clear_widget()
        # add new widget one-by-one
        joypad.add_widget('analog_round','analog_left',(0.0,0.0,0.5,1.0),
                          touchended_extfunc=lambda*args:print(args))
        # overriding external function, this let you override exist component (also default ui).
        joypad.override_extfunc('analog_round','touchbegan_extfunc',some_func_here)
        # start the scene
        joypad.run()
    '''

    class mousepad():
        def __init__(self,name='default',
                          label=None,
                          respond_area=(0.0,0.0,1.0,1.0),
                          color={'normal':{'stroke':(1,1,1,1),
                                           'fill':(1,1,1,0.25),
                                           'weight':1.0},
                              'highlight':{'stroke':(1,0,0,1),
                                           'fill':(1,0,0,0.25),
                                           'weight':1.0}},
                          touchbegan_extfunc=lambda*args:None,
                          touchmoved_extfunc=lambda*args:None,
                          touchended_extfunc=lambda*args:None,):
            self.scrnWdth, self.scrnHght = ui.get_screen_size()
            self.name = name
            self.label = name if label is None else label
            self.respond_area = {'x1':respond_area[0],
                                 'y1':respond_area[1],
                                 'x2':respond_area[2],
                                 'y2':respond_area[3],}
            self.color = color
            self.touchbegan_extfunc = touchbegan_extfunc
            self.touchmoved_extfunc = touchmoved_extfunc
            self.touchended_extfunc = touchended_extfunc
            self._clear_touch()
        def _clear_touch(self):
            self.touch = self.clamp_x = self.clamp_y = self.ref_x = self.ref_y = None
        def is_respond_area(self,touch):
            if not(self.touch):
                return ((self.respond_area['x1'] <= (touch.location.x/self.scrnWdth) <= self.respond_area['x2']) and
                        (self.respond_area['y1'] <= (touch.location.y/self.scrnHght) <= self.respond_area['y2']))
        
        def touch_began(self,touch):
            self.touch = touch
            self.ref_x = self.touch.location.x
            self.ref_y = self.touch.location.y
            self.touchbegan_extfunc('touch_began',self.current_state)
        def touch_moved(self,touch):
            self.touch = touch
            self.touchmoved_extfunc('touch_move',self.current_state)
        def touch_ended(self,touch):
            self._clear_touch()
            self.touchended_extfunc('touch_ended',self.current_state)
        def rescreen(self):
            if self.touch:
                # get old self on-screen position
                ref_x_mark = self.ref_x/self.scrnWdth
                ref_y_mark = self.ref_y/self.scrnHght
                # update new position
                self.scrnWdth, self.scrnHght = ui.get_screen_size()
                self.ref_x = ref_x_mark*self.scrnWdth 
                self.ref_y = ref_y_mark*self.scrnHght
            else:
                self.scrnWdth, self.scrnHght = ui.get_screen_size()
        def scene_draw(self):
            if self.touch:
                scene.stroke_weight(self.color['highlight']['weight'])
                scene.stroke(*self.color['highlight']['stroke'])
                scene.fill(*self.color['highlight']['fill'])
                scene.line(self.touch.location.x,self.respond_area['y1'],self.touch.location.x,self.respond_area['y2'])
                scene.line(self.respond_area['x1'],self.touch.location.y,self.respond_area['x2'],self.touch.location.y)
            else:
                scene.stroke_weight(self.color['normal']['weight'])
                scene.stroke(*self.color['normal']['stroke'])
                scene.fill(*self.color['normal']['fill'])
            scene.rect(self.respond_area['x1'],self.respond_area['y1'],self.respond_area['x2'],self.respond_area['y2'])
            scene.text(self.label, x=self.ref_x, y=self.ref_y)
        @property
        def x(self):
            return self.touch.location.x - self.ref_x
        @property
        def y(self):
            return self.touch.location.y - self.ref_y
        @property
        def current_state(self):
            return {'name':self.name,'type':self.__class__.__name__,'x':self.x,'y':self.y}


    class analog_rect(mousepad):
        def __init__(self,name='default',
                          label=None,
                          respond_area=(0.0,0.0,1.0,1.0),
                          max_length=0.25,
                          color={'normal':{'stroke':(1,1,1,1),
                                           'fill':(1,1,1,0.25),
                                           'weight':1.0},
                              'highlight':{'stroke':(1,0,0,1),
                                           'fill':(1,0,0,0.25),
                                           'weight':1.0}},
                          touchbegan_extfunc=lambda*args:None,
                          touchmoved_extfunc=lambda*args:None,
                          touchended_extfunc=lambda*args:None,):
            super().__init__(name,label,respond_area,color,touchbegan_extfunc,touchmoved_extfunc,touchended_extfunc)
            self.max_length   = max_length*min(self.scrnWdth, self.scrnHght)
            self._clear_touch()
        def touch_began(self,touch):
            self.touch = touch
            self.ref_x = self.clamp_x = max(min(self.touch.location.x,self.scrnWdth-self.max_length),self.max_length)
            self.ref_y = self.clamp_y = max(min(self.touch.location.y,self.scrnHght-self.max_length),self.max_length)
            self.touchbegan_extfunc('touch_began',self.current_state)
        def touch_moved(self,touch):
            self.touch = touch
            self.clamp_x = max(min(self.touch.location.x,self.boundary['right']),self.boundary['left'])
            self.clamp_y = max(min(self.touch.location.y,self.boundary['upper']),self.boundary['lower'])
            self.touchmoved_extfunc('touch_move',self.current_state)
        def rescreen(self):
            if self.touch:
                # get old self on-screen position
                ref_x_mark = (self.ref_x-self.max_length)/(self.scrnWdth-2.0*self.max_length)
                ref_y_mark = (self.ref_y-self.max_length)/(self.scrnHght-2.0*self.max_length)
                # update new position
                self.scrnWdth, self.scrnHght = ui.get_screen_size()
                self.ref_x = self.max_length + ref_x_mark*(self.scrnWdth - 2.0*self.max_length)
                self.ref_y = self.max_length + ref_y_mark*(self.scrnHght - 2.0*self.max_length)
            else:
                self.scrnWdth, self.scrnHght = ui.get_screen_size()
        def scene_draw(self):
            if self.touch:
                if not(int(self.x) or int(self.y)):
                    scene.stroke_weight(self.color['normal']['weight'])
                    scene.stroke(*self.color['normal']['stroke'])
                    scene.fill(*self.color['normal']['fill'])
                else:
                    scene.stroke_weight(self.color['highlight']['weight'])
                    scene.stroke(*self.color['highlight']['stroke'])
                    scene.fill(*self.color['highlight']['fill'])
                scene.rect(self.boundary['left'],self.boundary['lower'],2.0*self.max_length,2.0*self.max_length)
                scene.line(self.clamp_x,self.boundary['upper'],self.clamp_x,self.boundary['lower'])
                scene.line(self.boundary['left'],self.clamp_y,self.boundary['right'],self.clamp_y)
                scene.text(self.label, x=self.ref_x, y=self.ref_y)
        @property
        def x(self):
            return min(max((self.clamp_x-self.ref_x)/self.max_length,-1.0),1.0) if self.touch else 0.0
        @property
        def y(self):
            return min(max((self.clamp_y-self.ref_y)/self.max_length,-1.0),1.0) if self.touch else 0.0
        @property
        def boundary(self):
            if self.touch: return {'left':self.ref_x-self.max_length,
                                   'right':self.ref_x+self.max_length,
                                   'upper':self.ref_y+self.max_length,
                                   'lower':self.ref_y-self.max_length}


    class analog_round(analog_rect):
        def touch_moved(self,touch):
            self.touch   = touch
            self.clamp_x = self.ref_x + self.scaled_axes*(self.touch.location.x - self.ref_x)
            self.clamp_y = self.ref_y + self.scaled_axes*(self.touch.location.y - self.ref_y)
            self.touchmoved_extfunc('touch_move',self.current_state)
        def scene_draw(self):
            if self.touch:
                if (self.magnitude < 0.99*self.max_length):
                    scene.stroke_weight(self.color['normal']['weight'])
                    scene.stroke(*self.color['normal']['stroke'])
                    scene.fill(*self.color['normal']['fill'])
                else:
                    scene.stroke_weight(self.color['highlight']['weight'])
                    scene.stroke(*self.color['highlight']['stroke'])
                    scene.fill(*self.color['highlight']['fill'])
                scene.ellipse(self.boundary['left'],self.boundary['lower'],2.0*self.max_length,2.0*self.max_length)
                scene.line(self.ref_x,self.ref_y,self.clamp_x,self.clamp_y)
                scene.text(self.label, x=self.ref_x, y=self.ref_y)
        @property
        def magnitude(self):
            return math.sqrt((self.touch.location.x-self.ref_x)**2+(self.touch.location.y-self.ref_y)**2)
        @property
        def scaled_axes(self):
            return 1.0 if (self.magnitude <= self.max_length) else (self.max_length/self.magnitude)
        @property
        def x(self):
            return (self.clamp_x-self.ref_x)/self.max_length if self.touch else 0.0
        @property
        def y(self):
            return (self.clamp_y-self.ref_y)/self.max_length  if self.touch else 0.0


    class button():
        def __init__(self,name='default',
                          label=None,
                          respond_area=(0.4,0.25,0.6,0.75),
                          toggle=None,
                          color={'normal':{'stroke':(1,1,1,1),
                                           'fill':(1,1,1,0.25),
                                           'weight':1.0},
                              'highlight':{'stroke':(1,0,0,1),
                                           'fill':(1,0,0,1),
                                           'weight':1.0}},
                          touchbegan_extfunc=lambda*args:None,
                          touchended_extfunc=lambda*args:None,
                          toggle_on_extfunc=lambda*args:None,
                          toggle_off_extfunc=lambda*args:None):
            self.scrnWdth, self.scrnHght = ui.get_screen_size()
            self.name = name
            self.label = name if label is None else label
            self.touch = None
            self.respond_area = {'x1':respond_area[0],
                                 'y1':respond_area[1],
                                 'x2':respond_area[2],
                                 'y2':respond_area[3],}
            self.toggle = toggle
            self.color  = color
            self.touchbegan_extfunc = touchbegan_extfunc
            self.touchended_extfunc = touchended_extfunc
            self.toggle_on_extfunc  = toggle_on_extfunc
            self.toggle_off_extfunc  = toggle_off_extfunc
        def is_respond_area(self,touch):
            return ((self.respond_area['x1'] <= (touch.location.x/self.scrnWdth) <= self.respond_area['x2']) and
                    (self.respond_area['y1'] <= (touch.location.y/self.scrnHght) <= self.respond_area['y2']))
        def touch_began(self,touch):
            self.touch = touch
            self.touchbegan_extfunc('touch_began',self.current_state)
            # check button toggle
            if not(self.toggle is None):
                self.toggle = not(self.toggle)
                if self.toggle:
                    self.toggle_on_extfunc('toggle_on',self.current_state)
                else:
                    self.toggle_off_extfunc('toggle_off',self.current_state)
        def touch_moved(self,touch):
            pass
        def touch_ended(self,touch):
            self.touch = None
            self.touchended_extfunc('touch_ended',self.current_state)
        def rescreen(self):
            self.scrnWdth, self.scrnHght = ui.get_screen_size()
        def scene_draw(self):
            if not(self.touch or (self.toggle)):
                scene.stroke_weight(self.color['normal']['weight'])
                scene.stroke(*self.color['normal']['stroke'])
                scene.fill(*self.color['normal']['fill'])
            else:
                scene.stroke_weight(self.color['highlight']['weight'])
                scene.stroke(*self.color['highlight']['stroke'])
                scene.fill(*self.color['highlight']['fill'])
            scene.rect(self.respond_area['x1']*self.scrnWdth,
                       self.respond_area['y1']*self.scrnHght,
                       (self.respond_area['x2']-self.respond_area['x1'])*self.scrnWdth,
                       (self.respond_area['y2']-self.respond_area['y1'])*self.scrnHght)
            scene.text(self.label, x=0.5*(self.respond_area['x1']+self.respond_area['x2'])*self.scrnWdth, 
                                   y=0.5*(self.respond_area['y1']+self.respond_area['y2'])*self.scrnHght,)
        @property
        def current_state(self):
            return {'name':self.name,'type':self.__class__.__name__,'press':bool(self.touch),'toggle':self.toggle}

    def __init__(self,stop_event=None):
        super().__init__()
        self.scrnWdth, self.scrnHght = ui.get_screen_size()
        self.components =  [self.button(name='button_A',respond_area=(0.7,0.0,0.85,0.15),toggle=False,
                                        color={'normal':{'stroke':(0.961,0.949,0.388,0.5),'fill':(0.961,0.949,0.388,0.25),'weight':1.0},
                                               'highlight':{'stroke':(0.961,0.949,0.388,1),'fill':(0.961,0.949,0.388,0.5),'weight':2.0}},
                                        touchbegan_extfunc=lambda*args:print(args),
                                        touchended_extfunc=lambda*args:print(args),
                                        toggle_on_extfunc=lambda*args:print(args),
                                        toggle_off_extfunc=lambda*args:print(args)),
                            self.button(name='button_B',respond_area=(0.85,0.0,1.0,0.3),toggle=None,
                                        color={'normal':{'stroke':(1.000,0.616,0.310,0.5),'fill':(1.000,0.616,0.310,0.25),'weight':1.0},
                                               'highlight':{'stroke':(1.000,0.616,0.310,1),'fill':(1.000,0.616,0.310,0.5),'weight':2.0}},
                                        touchbegan_extfunc=lambda*args:print(args),
                                        touchended_extfunc=lambda*args:print(args)),
                            self.analog_round(name='analog',respond_area=(0.0,0.0,1.0,1.0),max_length=0.25,
                                              color={'normal':{'stroke':(0.357,0.302,0.718,1.0),'fill':(0.357,0.302,0.718,0.5),'weight':1.0},
                                                     'highlight':{'stroke':(1,0,0,1),'fill':(0.357,0.302,0.718,0.5),'weight':2.0}},
                                              touchbegan_extfunc=lambda*args:print(args),
                                              touchmoved_extfunc=lambda*args:print(args),
                                              touchended_extfunc=lambda*args:print(args),),]
        self.stop_event = multiprocessing.Event() if stop_event is None else stop_event
        self.user_setup()
    def user_setup(self):
        # self.components can be fully-overrided in this function
        pass
    def clear_widgets(self):
        self.components = []
    def add_widget(self,widget,*args,**kwargs):
        widget_class = {'button':self.button,'analog_rect':self.analog_rect,'analog_round':self.analog_round}[widget]
        self.components.append(widget_class(*args,**kwargs))
    def override_extfunc(self,target_name,target_func_name,func):
        for comp in self.components:
            if comp.name == target_name:
                setattr(comp,target_func_name,func)
    def did_change_size(self):
        for comp in self.components:
            comp.rescreen()
    def draw(self):
        scene.background(0,0,0)
        for comp in self.components:
            comp.scene_draw()
    def touch_began(self, touch):
        for comp in self.components:
            if comp.is_respond_area(touch):
                comp.touch_began(touch)
                return
    def touch_moved(self, touch):
        for comp in self.components:
            if comp.touch:
                if comp.touch.touch_id == touch.touch_id:
                    comp.touch_moved(touch)
                    return
    def touch_ended(self, touch):
        for comp in self.components:
            if comp.touch:
                if comp.touch.touch_id == touch.touch_id:
                    comp.touch_ended(touch)
                    return
    def run(self):
        scene.run(self)
    def stop(self):
        self.stop_event.set()


class DS4GamePad(touchPadCore):
    '''
    DualShock4 GamePad
    '''
    def user_setup(self):
        self.components =  [# ---------------------------------------------------------------------------------------------- DPad button
                            self.button(name='dpad_y_up',label='UP',respond_area=(0.12,0.7,0.21,0.84),toggle=None,
                                        color={'normal':{'stroke':(1,1,1,1),'fill':(1,1,1,0.25),'weight':1.0},
                                               'highlight':{'stroke':(1,1,1,1),'fill':(1,1,1,1),'weight':1.0}},
                                        touchbegan_extfunc=lambda*args:print(args),
                                        touchended_extfunc=lambda*args:print(args),),
                            self.button(name='dpad_y_down',label='DN',respond_area=(0.12,0.42,0.21,0.56),toggle=None,
                                        color={'normal':{'stroke':(1,1,1,1),'fill':(1,1,1,0.25),'weight':1.0},
                                               'highlight':{'stroke':(1,1,1,1),'fill':(1,1,1,1),'weight':1.0}},
                                        touchbegan_extfunc=lambda*args:print(args),
                                        touchended_extfunc=lambda*args:print(args),),
                            self.button(name='dpad_x_left',label='LEFT',respond_area=(0.03,0.56,0.12,0.70),toggle=None,
                                        color={'normal':{'stroke':(1,1,1,1),'fill':(1,1,1,0.25),'weight':1.0},
                                               'highlight':{'stroke':(1,1,1,1),'fill':(1,1,1,1),'weight':1.0}},
                                        touchbegan_extfunc=lambda*args:print(args),
                                        touchended_extfunc=lambda*args:print(args),),
                            self.button(name='dpad_x_right',label='RIGHT',respond_area=(0.21,0.56,0.3,0.70),toggle=None,
                                        color={'normal':{'stroke':(1,1,1,1),'fill':(1,1,1,0.25),'weight':1.0},
                                               'highlight':{'stroke':(1,1,1,1),'fill':(1,1,1,1),'weight':1.0}},
                                        touchbegan_extfunc=lambda*args:print(args),
                                        touchended_extfunc=lambda*args:print(args),),
                            # ---------------------------------------------------------------------------------------------- ABXY button
                            self.button(name='button_cross',label='CROSS',respond_area=(0.79,0.05,0.88,0.19),toggle=None,
                                        color={'normal':{'stroke':(0,0,1,1),'fill':(0,0,1,0.25),'weight':1.0},
                                            'highlight':{'stroke':(0,0,1,1),'fill':(0,0,1,1),'weight':1.0}},
                                        touchbegan_extfunc=lambda*args:print(args),
                                        touchended_extfunc=lambda*args:print(args),),
                            self.button(name='button_circle',label='CIRCLE',respond_area=(0.88,0.19,0.97,0.33),toggle=None,
                                        color={'normal':{'stroke':(1,0,0,1),'fill':(1,0,0,0.25),'weight':1.0},
                                            'highlight':{'stroke':(1,0,0,1),'fill':(1,0,0,1),'weight':1.0}},
                                        touchbegan_extfunc=lambda*args:print(args),
                                        touchended_extfunc=lambda*args:print(args),),
                            self.button(name='button_square',label='SQUARE',respond_area=(0.7,0.19,0.79,0.33),toggle=None,
                                        color={'normal':{'stroke':(1,0,1,1),'fill':(1,0,1,0.25),'weight':1.0},
                                            'highlight':{'stroke':(1,0,1,1),'fill':(1,0,1,1),'weight':1.0}},
                                        touchbegan_extfunc=lambda*args:print(args),
                                        touchended_extfunc=lambda*args:print(args),),
                            self.button(name='button_triangle',label='TRIANGLE',respond_area=(0.79,0.33,0.88,0.47),toggle=None,
                                        color={'normal':{'stroke':(0,1,1,1),'fill':(0,1,1,0.25),'weight':1.0},
                                            'highlight':{'stroke':(0,1,1,1),'fill':(0,1,1,1),'weight':1.0}},
                                        touchbegan_extfunc=lambda*args:print(args),
                                        touchended_extfunc=lambda*args:print(args),),
                            # ---------------------------------------------------------------------------------------------- LR button
                            self.button(name='button_l1',label='L1',respond_area=(0.05,0.87,0.15,0.98),toggle=None,
                                        color={'normal':{'stroke':(1,1,1,1),'fill':(1,1,1,0.25),'weight':1.0},
                                            'highlight':{'stroke':(1,1,1,1),'fill':(1,1,1,1),'weight':1.0}},
                                        touchbegan_extfunc=lambda*args:print(args),
                                        touchended_extfunc=lambda*args:print(args),),
                            self.button(name='button_l2',label='L2',respond_area=(0.15,0.87,0.25,0.98),toggle=None,
                                        color={'normal':{'stroke':(1,1,1,1),'fill':(1,1,1,0.25),'weight':1.0},
                                            'highlight':{'stroke':(1,1,1,1),'fill':(1,1,1,1),'weight':1.0}},
                                        touchbegan_extfunc=lambda*args:print(args),
                                        touchended_extfunc=lambda*args:print(args),),
                            self.button(name='button_r1',label='R1',respond_area=(0.85,0.87,0.95,0.98),toggle=None,
                                        color={'normal':{'stroke':(1,1,1,1),'fill':(1,1,1,0.25),'weight':1.0},
                                            'highlight':{'stroke':(1,1,1,1),'fill':(1,1,1,1),'weight':1.0}},
                                        touchbegan_extfunc=lambda*args:print(args),
                                        touchended_extfunc=lambda*args:print(args),),
                            self.button(name='button_r2',label='R2',respond_area=(0.75,0.87,0.85,0.98),toggle=None,
                                        color={'normal':{'stroke':(1,1,1,1),'fill':(1,1,1,0.25),'weight':1.0},
                                            'highlight':{'stroke':(1,1,1,1),'fill':(1,1,1,1),'weight':1.0}},
                                        touchbegan_extfunc=lambda*args:print(args),
                                        touchended_extfunc=lambda*args:print(args),),
                            # ---------------------------------------------------------------------------------------------- Misc button
                            self.button(name='button_option',label='OPT',respond_area=(0.35,0.02,0.45,0.07),toggle=None,
                                        color={'normal':{'stroke':(1,1,1,1),'fill':(1,1,1,0.25),'weight':1.0},
                                            'highlight':{'stroke':(1,1,1,1),'fill':(1,1,1,1),'weight':1.0}},
                                        touchbegan_extfunc=lambda*args:print(args),
                                        touchended_extfunc=lambda*args:print(args),),
                            self.button(name='button_ps',label='PS',respond_area=(0.45,0.02,0.55,0.07),toggle=None,
                                        color={'normal':{'stroke':(1,1,1,1),'fill':(1,1,1,0.25),'weight':1.0},
                                            'highlight':{'stroke':(1,1,1,1),'fill':(1,1,1,1),'weight':1.0}},
                                        touchbegan_extfunc=lambda*args:print(args),
                                        touchended_extfunc=lambda*args:print(args),),
                            self.button(name='button_share',label='SHR',respond_area=(0.55,0.02,0.65,0.07),toggle=None,
                                        color={'normal':{'stroke':(1,1,1,1),'fill':(1,1,1,0.25),'weight':1.0},
                                            'highlight':{'stroke':(1,1,1,1),'fill':(1,1,1,1),'weight':1.0}},
                                        touchbegan_extfunc=lambda*args:print(args),
                                        touchended_extfunc=lambda*args:print(args),),
                            # ---------------------------------------------------------------------------------------------- Analog Stick
                            self.analog_round(name='left_analog',label='LEFT_ANALOG',respond_area=(0.0,0.0,0.5,0.50),max_length=0.25,
                                            color={'normal':{'stroke':(1,1,1,1),'fill':(1,1,1,0.25),'weight':1.0},
                                                'highlight':{'stroke':(1,0,0,1),'fill':(1,0,0,0.25),'weight':1.0}},
                                            touchbegan_extfunc=lambda*args:print(args),
                                            touchmoved_extfunc=lambda*args:print(args),
                                            touchended_extfunc=lambda*args:print(args),),
                            self.analog_round(name='right_analog',label='RIGHT_ANALOG',respond_area=(0.5,0.43,1.0,0.86),max_length=0.25,
                                            color={'normal':{'stroke':(1,1,1,1),'fill':(1,1,1,0.25),'weight':1.0},
                                                'highlight':{'stroke':(1,0,0,1),'fill':(1,0,0,0.25),'weight':1.0}},
                                            touchbegan_extfunc=lambda*args:print(args),
                                            touchmoved_extfunc=lambda*args:print(args),
                                            touchended_extfunc=lambda*args:print(args),),
                            ]


class MousePad(touchPadCore):
    '''
    MousePad
    '''
    def user_setup(self):
        self.components =   [
                            self.button(name='right_bttn',label='Right',respond_area=(0.0,0.75,0.15,1.0),toggle=None,
                                        color={'normal':{'stroke':(0,1,0,0.5),'fill':(1,1,1,0.25),'weight':1.0},
                                            'highlight':{'stroke':(0,1,0,1),'fill':(1,1,1,1),'weight':1.0}},
                                        touchbegan_extfunc=lambda*args:print(args),
                                        touchended_extfunc=lambda*args:print(args),),
                            self.button(name='drag_bttn',label='Press',respond_area=(0.0,0.5,0.15,0.75),toggle=None,
                                        color={'normal':{'stroke':(0,1,1,0.5),'fill':(1,1,1,0.25),'weight':1.0},
                                            'highlight':{'stroke':(0,1,1,1),'fill':(1,1,1,1),'weight':1.0}},
                                        toggle_on_extfunc=lambda*args:print(args),
                                        toggle_off_extfunc=lambda*args:print(args),),
                            self.button(name='left_bttn',label='Click',respond_area=(0.0,0.0,0.15,0.5),toggle=None,
                                        color={'normal':{'stroke':(0,1,0,0.5),'fill':(1,1,1,0.25),'weight':1.0},
                                            'highlight':{'stroke':(0,1,0,1),'fill':(1,1,1,1),'weight':1.0}},
                                        touchbegan_extfunc=lambda*args:print(args),
                                        touchended_extfunc=lambda*args:print(args),),
                            self.analog_rect(name='rectpad',
                                            respond_area=(0.2,0.0,1.0,1.0),
                                            max_length=0.4,
                                            color={'normal':{'stroke':(0,0,0,0),'fill':(0,0,0,0),'weight':0},
                                                'highlight':{'stroke':(0,0,0,0),'fill':(0,0,0,0),'weight':0}},
                                            touchbegan_extfunc=lambda*args:print(args),
                                            touchmoved_extfunc=lambda*args:print(args),
                                            touchended_extfunc=lambda*args:print(args),)
                            ]




import math
import ui
import scene


__version__ = (2021,2,2,'beta')


class touchGamePad(scene.Scene):
    '''
    Example:
        joypad = touchGamePad(leftA_button_press_func=None,
                            leftB_button_release_func=None,
                            rightA_button_toggle_on_func=lambda:print('leftA_button_toggle_on'),
                            rightB_button_toggle_off_func=lambda:print('leftA_button_toggle_off'),
                            left_analog_move_func=left_analog,)
        joypad.run()
    '''
    class analog_rect():
        def __init__(self,touch,scrnWdth,scrnHght,scale=0.25,move_func=None):
            self.touch = touch
            self.scale = scale
            self.move_func = move_func
            self.scrnWdth, self.scrnHght = scrnWdth, scrnHght
            self.max_length = self.scale*min(self.scrnWdth, self.scrnHght)
            self.ref_x = max(min(self.touch.location.x,self.scrnWdth-self.max_length),self.max_length)
            self.ref_y = max(min(self.touch.location.y,self.scrnHght-self.max_length),self.max_length)
        def rescreen(self,new_scrnWdth,new_scrnHght):
            ref_x_mark = (self.ref_x-self.max_length)/(self.scrnWdth-2.0*self.max_length)
            ref_y_mark = (self.ref_y-self.max_length)/(self.scrnHght-2.0*self.max_length)
            self.ref_x = self.max_length + ref_x_mark*(new_scrnWdth - 2.0*self.max_length)
            self.ref_y = self.max_length + ref_y_mark*(new_scrnHght - 2.0*self.max_length)
            self.scrnWdth, self.scrnHght = new_scrnWdth, new_scrnHght
        def update_touch(self,touch):
            self.touch = touch
            self.touch.location.x = max(min(self.touch.location.x,self.right_bound),self.left_bound)
            self.touch.location.y = max(min(self.touch.location.y,self.upper_bound),self.lower_bound)
            #print('x: {:0.2f}, y: {:0.2f}'.format(self.x,self.y))
            if self.move_func:
                self.move_func(self.x,self.y)
        def scene_draw(self):
            scene.fill(1,1,1,0.25)
            scene.stroke_weight(1.0)
            if int(self.x) or int(self.y):
                scene.stroke(1,0,0,1)
            else:
                scene.stroke(1,1,1,1)
            scene.rect(self.left_bound,self.lower_bound,2.0*self.max_length,2.0*self.max_length)
            scene.line(self.touch.location.x,self.upper_bound,self.touch.location.x,self.lower_bound)
            scene.line(self.left_bound,self.touch.location.y,self.right_bound,self.touch.location.y)
        @property
        def touch_id(self):
            return self.touch.touch_id
        @property
        def x(self):
            return min(max((self.touch.location.x-self.ref_x)/self.max_length,-1.0),1.0)
        @property
        def y(self):
            return min(max((self.touch.location.y-self.ref_y)/self.max_length,-1.0),1.0)
        @property
        def left_bound(self):
            return self.ref_x-self.max_length
        @property
        def right_bound(self):
            return self.ref_x+self.max_length
        @property
        def upper_bound(self):
            return self.ref_y+self.max_length
        @property
        def lower_bound(self):
            return self.ref_y-self.max_length

    class analog_round(analog_rect):
        def update_touch(self,touch):
            self.touch = touch
            scaled_axes = self.scaled_axes
            self.touch.location.x = self.ref_x + scaled_axes*(self.touch.location.x - self.ref_x)
            self.touch.location.y = self.ref_y + scaled_axes*(self.touch.location.y - self.ref_y)
            #print('x: {:0.2f}, y: {:0.2f}'.format(self.x,self.y))
            if self.move_func:
                self.move_func(self.x,self.y)
        def scene_draw(self):
            scene.fill(1,1,1,0.25)
            scene.stroke_weight(1.0)
            if (self.magnitude < 0.99*self.max_length):
                scene.stroke(1,1,1,1)
            else:
                scene.stroke(1,0,0,1)
            scene.ellipse(self.left_bound,self.lower_bound,2.0*self.max_length,2.0*self.max_length)
            scene.line(self.ref_x,self.ref_y,self.touch.location.x,self.touch.location.y)
        @property
        def magnitude(self):
            return math.sqrt((self.touch.location.x-self.ref_x)**2+(self.touch.location.y-self.ref_y)**2)
        @property
        def scaled_axes(self):
            return 1.0 if (self.magnitude <= self.max_length) else (self.max_length/self.magnitude)
        @property
        def x(self):
            return self.scaled_axes*(self.touch.location.x-self.ref_x)/self.max_length
        @property
        def y(self):
            return self.scaled_axes*(self.touch.location.y-self.ref_y)/self.max_length

    class button():
        def __init__(self,scrnWdth,scrnHght,x1,y1,x2,y2,toggle=None,press_func=None,release_func=None,toggle_on_func=None,toggle_off_func=None):
            self.scrnWdth, self.scrnHght = scrnWdth, scrnHght
            self.bound  = {'x1':x1,'y1':y1,'x2':x2,'y2':y2}
            self.toggle = toggle
            self.state  = 'release'
            self.press_func   = press_func
            self.release_func = release_func
            self.toggle_on_func  = toggle_on_func
            self.toggle_off_func = toggle_off_func
        def is_inner_bound(self,touch):
            x_check = (self.bound['x1'] <= (touch.location.x/self.scrnWdth) <= self.bound['x2'])
            y_check = (self.bound['y1'] <= (touch.location.y/self.scrnHght) <= self.bound['y2'])
            return x_check and y_check
        def press(self,touch):
            if self.is_inner_bound(touch):
                self.state = 'press'
                if not(self.toggle is None):
                    self.toggle = not(self.toggle)
                    if self.toggle and self.toggle_on_func:
                        self.toggle_on_func()
                    elif not(self.toggle) and self.toggle_off_func:
                        self.toggle_off_func()
                if self.press_func:
                    self.press_func()
        def release(self,touch):
            if self.is_inner_bound(touch) :
                self.state = 'release'
                if self.release_func:
                    self.release_func()
        def rescreen(self,new_scrnWdth,new_scrnHght):
            self.scrnWdth, self.scrnHght = new_scrnWdth, new_scrnHght
        def scene_draw(self):
            if (self.state == 'press') or (self.toggle):
                scene.fill(1,0,0,0.25)
                scene.stroke(1,0,0,1)
            else:
                scene.fill(1,1,1,0.25)
                scene.stroke(1,1,1,1)
            scene.stroke_weight(1.0)
            scene.rect(self.bound['x1']*self.scrnWdth,
                       self.bound['y1']*self.scrnHght,
                       (self.bound['x2']-self.bound['x1'])*self.scrnWdth,
                       (self.bound['y2']-self.bound['y1'])*self.scrnHght)


    def __init__(self,leftA_button_press_func=None,
                      leftA_button_release_func=None,
                      leftA_button_toggle_on_func=None,
                      leftA_button_toggle_off_func=None,
                      leftB_button_press_func=None,
                      leftB_button_release_func=None,
                      leftB_button_toggle_on_func=None,
                      leftB_button_toggle_off_func=None,
                      rightA_button_press_func=None,
                      rightA_button_release_func=None,
                      rightB_button_press_func=None,
                      rightB_button_release_func=None,
                      left_analog_move_func=None,
                      right_analog_move_func=None,):
        super().__init__()
        # target function
        self.leftA_button_press_func      = leftA_button_press_func
        self.leftA_button_release_func    = leftA_button_release_func
        self.leftA_button_toggle_on_func  = leftA_button_toggle_on_func
        self.leftA_button_toggle_off_func = leftA_button_toggle_off_func
        self.leftB_button_press_func      = leftB_button_press_func
        self.leftB_button_release_func    = leftB_button_release_func
        self.leftB_button_toggle_on_func  = leftB_button_toggle_on_func
        self.leftB_button_toggle_off_func = leftB_button_toggle_off_func
        self.rightA_button_press_func     = rightA_button_press_func
        self.rightA_button_release_func   = rightA_button_release_func
        self.rightB_button_press_func     = rightB_button_press_func
        self.rightB_button_release_func   = rightB_button_release_func
        self.left_analog_move_func        = left_analog_move_func
        self.right_analog_move_func       = right_analog_move_func
        # initial gamepad
        self.scrnWdth, self.scrnHght = ui.get_screen_size()
        self.left_analog  = None
        self.right_analog = None
        self.active_touch = {}
        self.active_button = {}
        
    def setup(self):
        self.leftA_button = self.button(self.scrnWdth, self.scrnHght,0.05,0.8,0.2,0.95,
                                        toggle=False,
                                        press_func=self.leftA_button_press_func,
                                        release_func=self.leftA_button_release_func,
                                        toggle_on_func=self.leftA_button_toggle_on_func,
                                        toggle_off_func=self.leftA_button_toggle_off_func)
        self.leftB_button = self.button(self.scrnWdth, self.scrnHght,0.2,0.8,0.35,0.95,
                                        toggle=False,
                                        press_func=self.leftB_button_press_func,
                                        release_func=self.leftB_button_release_func,
                                        toggle_on_func=self.leftB_button_toggle_on_func,
                                        toggle_off_func=self.leftB_button_toggle_off_func)
        self.rightA_button = self.button(self.scrnWdth, self.scrnHght,0.8,0.05,0.95,0.2,
                                        press_func=self.rightA_button_press_func,
                                        release_func=self.rightA_button_release_func)
        self.rightB_button = self.button(self.scrnWdth, self.scrnHght,0.65,0.05,0.8,0.2,
                                        press_func=self.rightB_button_press_func,
                                        release_func=self.rightB_button_release_func)
        
    def did_change_size(self):
        self.scrnWdth, self.scrnHght = ui.get_screen_size()
        for comp in self.active_touch.values():
            comp.rescreen(self.scrnWdth,self.scrnHght)
        for bttn in (self.leftA_button,self.leftB_button,self.rightA_button,self.rightB_button):
            bttn.rescreen(self.scrnWdth,self.scrnHght)

    def draw(self):
        scene.background(0,0,0)
        for comp in self.active_touch.values():
            comp.scene_draw()
        for bttn in (self.leftA_button,self.leftB_button,self.rightA_button,self.rightB_button):
            bttn.scene_draw()

    def touch_began(self, touch):
        #button check
        if self.leftA_button.is_inner_bound(touch):
            self.active_button.update({touch.touch_id:self.leftA_button})
            self.leftA_button.press(touch)
        elif self.leftB_button.is_inner_bound(touch):
            self.active_button.update({touch.touch_id:self.leftB_button})
            self.leftB_button.press(touch)
        elif self.rightA_button.is_inner_bound(touch):
            self.active_button.update({touch.touch_id:self.rightA_button})
            self.rightA_button.press(touch)
        elif self.rightB_button.is_inner_bound(touch):
            self.active_button.update({touch.touch_id:self.rightB_button})
            self.rightB_button.press(touch)
        #axes check
        elif (touch.location.x<(self.scrnWdth/2.0)) and not(self.left_analog):
            self.left_analog = self.analog_round(touch,self.scrnWdth,self.scrnHght,scale=0.2,
                                                 move_func=self.left_analog_move_func)
            self.active_touch.update({touch.touch_id:self.left_analog})
        elif (touch.location.x>=(self.scrnWdth/2.0)) and not(self.right_analog):
            self.right_analog = self.analog_rect(touch,self.scrnWdth,self.scrnHght,scale=0.2,
                                                 move_func=self.right_analog_move_func)
            self.active_touch.update({touch.touch_id:self.right_analog})
        
    def touch_moved(self, touch):
        if touch.touch_id in self.active_touch:
            self.active_touch[touch.touch_id].update_touch(touch)

    def touch_ended(self, touch):
        if touch.touch_id in self.active_touch:
            if self.left_analog:
                if self.left_analog.touch.touch_id == touch.touch_id:
                    self.left_analog = None
            if self.right_analog:
                if self.right_analog.touch.touch_id == touch.touch_id:
                    self.right_analog = None
            del self.active_touch[touch.touch_id]
        elif touch.touch_id in self.active_touch:
            self.active_button[touch.touch_id].release(touch)
            del self.active_button[touch.touch_id]

        if touch.touch_id in self.active_button:
            self.active_button[touch.touch_id].release(touch)
            del self.active_button[touch.touch_id]

    def run(self):
        scene.run(self)


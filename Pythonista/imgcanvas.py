

import scene
import ui
import time
import multiprocessing


__version__ = (2021,3,2,'beta')


class backgroundCanvas(scene.Scene):
    def setup(self):
        self.player = None # creat empty player attribute
        self.did_change_size() # update current screen info
        self.stop_event = multiprocessing.Event() # init stop event for external monitor
    def update_image(self,newimage):
        new_image = ui.Image.from_data(newimage) # convert raw binary to ui.image object
        if not self.player: # init new spritenote if not exited yet (first-time run)
            self.player =  scene.SpriteNode(scene.Texture(new_image),parent=self,) # create spritenode texture
            if new_image.size[0]/new_image.size[1] >= self.scrnratio: # image resizing (shrink to fit narrow-side screen)
                self.player.scale = self.scrnWdth/new_image.size[0] # fit width
            else:
                self.player.scale = self.scrnHght/new_image.size[1] # fit height
            self.player.position = (self.cen_xpos,self.cen_ypos)
        else:
            self.player.texture = scene.Texture(new_image) # update spritenode texture
    def did_change_size(self):
        self.scrnWdth, self.scrnHght = ui.get_screen_size() # update screen resolution
        self.scrnratio = self.scrnWdth/self.scrnHght # calculate screen ratio
        self.cen_xpos = int(self.scrnWdth/2)
        self.cen_ypos = int(self.scrnHght/2)
        if self.player:
            self.player.position = (self.cen_xpos,self.cen_ypos) # update picture center-position
    def run(self):
        scene.run(self)
    def stop(self):
        self.stop_event.set()


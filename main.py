""" 
The aim of this project is to emulate the light patterns known as water caustics
typically seen on on the bottom of a swimming pool. 
"""

__author__ = "Peter Bennett"
__copyright__ = "Copyright 2012, Peter A Bennett"
__license__ = "LGPL"
__version__ = "0.1"
__maintainer__ = "Peter Bennett"
__email__ = "pab850@gmail.com"
__contact__ = "www.bytebash.com"

# Pyglet provides the OpenGL context and control input
from pyglet import *
from pyglet.gl import *
from pyglet.window import key
# gletools ShaderProgram is required to compile GLSL shaders, this can
# be replaced with a standalone shader class if preferred
# For example: 
# http://swiftcoder.wordpress.com/2008/12/19/simple-glsl-wrapper-for-pyglet/
from gletools import ShaderProgram
from math import *
# Renderers:
import renderer
import ripples
import camera

# Global constants
kScreenWidth = 864          ## Window width
kScreenHeight= 864          ## Window height
kFullScreenMode = False      ## Fulscreen mode
kMouseFocus = True          ## Window holds mouse focus
kDesiredFPS = 120           ## Desired FPS (not guaranteed)
                            
# Derived constants
kFPS = 1/float(kDesiredFPS) ## Loop period ms

# Setup        
config = Config(buffers=2, samples=4)
window = pyglet.window.Window(caption='Caustics', 
                              width=kScreenWidth, 
                              height=kScreenHeight, 
                              config=config, 
                              vsync=False, 
                              fullscreen=kFullScreenMode)
                              
window.set_exclusive_mouse(kMouseFocus)

camera = camera.Camera(kScreenWidth, kScreenHeight, 65.0, 0.1, 1000.)
renderer = renderer.Renderer(window, camera) 
# Main Render Loop
def on_draw(dt):
    window.clear()
    renderer.draw(dt)
    
# Initialisation
if __name__ == '__main__':
    glClearColor(0.0, 0.0, 0.0, 1.0);
    glViewport(0, 0, kScreenWidth, kScreenHeight)
  
clock.schedule_interval(on_draw, kFPS)
pyglet.app.run()



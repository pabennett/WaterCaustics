""" 
The aim of this project is to emulate the light patterns known as water caustics
typically seen on on the bottom of a swimming pool. 
"""

__author__ = "Peter Bennett"
__copyright__ = "Copyright 2012, Peter A Bennett"
__license__ = "LGPL"
__maintainer__ = "Peter Bennett"
__email__ = "pab850@gmail.com"
__contact__ = "www.bytebash.com"

import sys, getopt
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
from source import scene,camera,console

# Global constants
kScreenWidth = 864          # Window width
kScreenHeight= 864          # Window height
kFullScreenMode = False     # Fulscreen mode
kMouseFocus = True          # Window holds mouse focus
kDesiredFPS = 120           # Desired FPS (not guaranteed)
kFixedTimeStep = False      # Render using a fixed time step?
kTimeStep = 0.1             # Time step to use for fixed time step rendering.
kFrameGrabPath = 'F:/temp'  # Where to save caustic frame grabs
                            
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

status = console.StatusConsole(x=window.width * 0.005, 
                          y=window.height * 0.98,
                          width=window.width)
                          
status.setTitle('Information:')                          
status.addParameter('FPS')      
status.addParameter('Position')
status.addParameter('Velocity')               
                                           
camera = camera.Camera(kScreenWidth, kScreenHeight, 65.0, 0.1, 1000.)

renderer = scene.Scene(window, camera, status)

def statusUpdates(dt):
    position = tuple(int(a) for a in camera.position.values())
    velocity = tuple(int(a) for a in camera.moveVelocity.values())
    fps = clock.get_fps()
    
    status.setParameter('Position', position)
    status.setParameter('Velocity', velocity)
    status.setParameter('FPS', fps)
    
    renderer.statusUpdates(dt)

# Main Render Loop
def on_draw(dt):
    window.clear()
    
    if kFixedTimeStep:
        renderer.draw(kTimeStep)
    else:
        renderer.draw(dt)
    # Show Console Data
    status.draw()
        
# Frame grabber loop for saving caustic animations
def frameGrabberLoop():
    # Keep grabbing frames until the frameGrabber has captured a full period
    while True:
        try:
            res = renderer.frameGrab(kTimeStep, directory=kFrameGrabPath)
            if res:
                break
        except IOError:
            print("The supplied path for saving frames was not valid or is \
                   unavailable")
            break
def main():
    glClearColor(0.0, 0.49, 1.0 ,1.0)
    glViewport(0, 0, kScreenWidth, kScreenHeight)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_PROGRAM_POINT_SIZE)
    clock.schedule_interval(on_draw, kFPS)
    clock.schedule_interval(statusUpdates, 0.2)
    pyglet.app.run()

if len(sys.argv) > 1:
    if sys.argv[1] == '--grab':
        frameGrabberLoop()
    else:
        main()
else:
    main()



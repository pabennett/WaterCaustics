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

import sys, ConfigParser
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

# Settings
options = ConfigParser.RawConfigParser()
options.read('options.ini')

# Global constants
kScreenWidth = options.getint('Options', 'screenwidth')
kScreenHeight = options.getint('Options', 'screenheight')
kFullScreenMode = options.getboolean('Options', 'fullscreen')
kMouseFocus = options.getboolean('Options', 'mousefocus')        
maxFPS = options.getint('Options', 'maxfps')
kFixedTimeStep = options.getboolean('Options', 'fixedtimestep')   
kTimeStep = options.getfloat('Options', 'timestep')           
kFrameGrabPath = options.get('Options', 'framegrabpath')   
kBuffers = options.getint('Options', 'buffers')
kSamples = options.getint('Options', 'samples') 
kVFOV = options.getfloat('Options', 'vfov')
kShowInfo = options.getboolean('Options', 'info') 
            
# Derived constants
kFPS = 1/float(maxFPS) ## Loop period ms

# Setup        
config = Config(buffers=kBuffers, samples=kSamples)
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
                                           
camera = camera.Camera(kScreenWidth, kScreenHeight, kVFOV, 0.1, 1000.)

# Offset and orient the camera so that it is looking at the water.
camera.setpos(0.0, 140.0, 50.0)
camera.orient(225.0,-55.0,0.0)

renderer = scene.Scene(window, camera, status, options)

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
    if kShowInfo:
        # Show Console Data
        status.draw()
        
# Frame grabber loop for saving caustic animations
def frameGrabberLoop():
    # Keep grabbing frames until the frameGrabber has captured a full period
    print("Starting frame grabber, output files will be stored in " + 
          kFrameGrabPath)
    while True:
        try:
            res = renderer.frameGrab(kTimeStep, directory=kFrameGrabPath)
            if res:
                break
        except IOError:
            print("The supplied path for saving frames was not valid or is unavailable")
            break
def main():
    clock.schedule_interval(on_draw, kFPS)
    clock.schedule_interval(statusUpdates, 0.2)
    pyglet.app.run()

# Call this script with the "--grab" switch to create a looping animated set
# of caustic images for use in another program.
glClearColor(0.0, 0.49, 1.0 ,1.0)
glViewport(0, 0, kScreenWidth, kScreenHeight)
glEnable(GL_DEPTH_TEST)
glEnable(GL_PROGRAM_POINT_SIZE)
if len(sys.argv) > 1:
    if sys.argv[1] == '--grab':
        frameGrabberLoop()
    else:
        main()
else:
    main()



__author__ = "Peter Bennett"
__copyright__ = "Copyright 2012, Peter A Bennett"
__license__ = "LGPL"
__maintainer__ = "Peter Bennett"
__email__ = "pab850@gmail.com"
__contact__ = "www.bytebash.com"

''' 
This class implements the ocean surface algorithms detailed in Tessendorf's
"Simulating Ocean Water". A 2D heightmap representing the surface of a body
of water is generated.
'''

""" Renderer Imports """
from pyglet import *
from pyglet.gl import *
from ctypes import pointer, sizeof
from pyglet.window import key, mouse
import console
import ctypes
from vector import Vector2, Vector3

from water import Ocean, Pool
       
class Scene():
    def __init__(self, window, camera, statusConsole, options):
        ''' Constructor '''
        # Options
        self.options = options
        # Register the renderer for control input
        self.keys = key.KeyStateHandler()
        self.pressedKeys = {}
        self.window = window
        self.window.push_handlers(self.on_key_press)
        self.window.push_handlers(self.on_key_release)
        self.window.push_handlers(self.on_mouse_motion)
        self.window.push_handlers(self.keys)   
        # Window size
        (szx, szy) = self.window.get_size()
        self.windowWidth = szx
        self.windowHeight = szy
        self.camera = camera
        # Console
        self.status = statusConsole
        self.status.addParameter('Wind')      
        self.status.addParameter('Wave height')
        self.status.addParameter('Ocean depth')
        self.status.addParameter('Time')
        self.status.addParameter('Caustics intensity')
        self.status.addParameter('Caustics scale')
        
        self.time = 0.0
        
        # Ocean Render Parameters
        self.wireframe = False
        self.oceanDepth = self.options.getfloat('Scene', 'oceandepth')
        self.enableUpdates = True
        self.oceanWind = Vector2(
                            self.options.getfloat('Scene', 'oceanwindx'),
                            self.options.getfloat('Scene', 'oceanwindy'))
        self.oceanWaveHeight = self.options.getfloat('Scene', 'oceanwaveheight')
        self.oceanTileSize = self.options.getint('Scene', 'oceantilesize')
        self.oceanTiles = Vector2(
                            self.options.getint('Scene', 'oceantilesx'),
                            self.options.getint('Scene', 'oceantilesy'))
        self.drawSurface = True
        self.drawFloor = True
        self.enableCaustics = True
        self.causticIntensity= self.options.getfloat('Scene','causticintensity')
        self.causticPhotonScale = self.options.getfloat('Scene', 'causticscale')
        self.period = self.options.getfloat('Scene', 'period')
        self.frame = 0

        # Renderables
        self.scene = []
        self.ocean = Ocean( self.camera,
                            depth=self.oceanDepth,
                            waveHeight=self.oceanWaveHeight,
                            wind=self.oceanWind,
                            tileSize=self.oceanTileSize,
                            tilesX=self.oceanTiles.x,
                            tilesZ=self.oceanTiles.y,
                            photonScale=self.causticPhotonScale,
                            photonIntensity=self.causticIntensity,
                            period=self.period)
                                                        
        self.scene.append(self.ocean)

    def statusUpdates(self, dt):
        '''
        Called periodically by main loop for onscreen text updates
        '''
        self.status.setParameter('Wind', self.oceanWind)
        self.status.setParameter('Wave height', self.oceanWaveHeight)
        self.status.setParameter('Ocean depth', self.oceanDepth)
        self.status.setParameter('Time', self.time)
        self.status.setParameter('Caustics intensity', self.causticIntensity)
        self.status.setParameter('Caustics scale', self.causticPhotonScale) 

    def draw(self, dt):
    
        # Set depth
        if self.isKeyPressed(key.C):
            self.oceanDepth += 1
            self.ocean.setDepth(self.oceanDepth)
        elif self.isKeyPressed(key.V):
            self.oceanDepth -= 1
            self.ocean.setDepth(self.oceanDepth)
    
        if self.isKeyPressed(key.U):
            self.causticPhotonScale += 0.1
            self.ocean.setCausticPhotonScale(self.causticPhotonScale)
        if self.isKeyPressed(key.J):
            if self.causticPhotonScale > 0.1:
                self.causticPhotonScale -= 0.1
                self.ocean.setCausticPhotonScale(self.causticPhotonScale)
        if self.isKeyPressed(key.Y):
            self.causticIntensity += 0.1
            self.ocean.setCausticPhotonIntensity(self.causticIntensity)
        if self.isKeyPressed(key.H):
            if self.causticIntensity > 0.1:
                self.causticIntensity -= 0.1
                self.ocean.setCausticPhotonIntensity(self.causticIntensity)
    
        # Update camera orientation and position
        self.cameraUpdate(dt)
        
        if self.enableUpdates:
            self.time += dt
        else:
            dt = 0.0
        
        # Draw scene
        if self.wireframe:
            glPolygonMode(GL_FRONT, GL_LINE)
        else:
            glPolygonMode(GL_FRONT, GL_FILL)
        
        for drawable in self.scene:
            drawable.draw(dt)

        glPolygonMode(GL_FRONT, GL_FILL)
        
    def frameGrab(self, dt, directory=""):
        '''
        Save successive caustic frames to an image sequence so that it may be
        used as an animated texture or video in another program
        '''
        self.time += dt
        # Update the ocean surface so caustics can be generated
        self.ocean.surface.update(dt)
        # Update caustics
        self.ocean.caustics.update(dt)
        # Save the caustic texture to output image until a full period of the
        # ocean surface has been processed
        if self.time < self.period:
            self.ocean.causticTexture.save(directory + '/frame_' + 
                ('%03d' % self.frame) + '.png')
            print("Saved " + directory + '/frame_' + 
                ('%03d' % self.frame) + '.png')
            self.frame += 1
        else:
            print("Frame grabbing is complete, " + str(self.frame)
                  + " frames were generated in " + directory)
            return True
        return False
    
    def cameraUpdate(self, dt):
        self.camera.update(dt)
        
        if self.isKeyPressed(key.W):
            self.camera.addVelocity(0.0, 0.0, 1.0)
        if self.isKeyPressed(key.S):
            self.camera.addVelocity(0.0, 0.0, -1.0)
        if self.isKeyPressed(key.A):
            self.camera.addVelocity(-1.0, 0.0, 0.0)
        if self.isKeyPressed(key.D):
            self.camera.addVelocity(1.0, 0.0, 0.0)
        if self.isKeyPressed(key.Q):
            self.camera.addAngularVelocity(0.0, 0.0, 2)
        if self.isKeyPressed(key.E):
            self.camera.addAngularVelocity(0.0, 0.0, -2)
    def on_key_press(self, symbol, modifiers):
        """ Handle key press events"""
        
        # Set the pressedKeys dict to allow us to have while-key-pressed actions
        self.pressedKeys[symbol] = True
        
        if symbol == key.L:
            self.wireframe = not self.wireframe
        if symbol == key.SPACE:
            self.enableUpdates = not self.enableUpdates

        if symbol == key.NUM_1:
            self.oceanWind.x *= 2.0
            self.ocean.setWind(self.oceanWind)
        if symbol == key.NUM_2:
            self.oceanWind.x /= 2.0
            self.ocean.setWind(self.oceanWind)
        if symbol == key.NUM_4:
            self.oceanWind.y *= 2.0
            self.ocean.setWind(self.oceanWind)
        if symbol == key.NUM_5:
            self.oceanWind.y /= 2.0
            self.ocean.setWind(self.oceanWind)
        if symbol == key.NUM_7:
            self.oceanWaveHeight *= 2.0
            self.ocean.setWaveHeight(self.oceanWaveHeight)
        if symbol == key.NUM_8:
            self.oceanWaveHeight /= 2.0
            self.ocean.setWaveHeight(self.oceanWaveHeight)
        
        if symbol == key.Z:
            self.drawSurface = not self.drawSurface
            self.ocean.drawSeaSurface = self.drawSurface
        if symbol == key.X:
            self.drawFloor = not self.drawFloor
            self.ocean.drawSeaFloor = self.drawFloor
        if symbol == key.M:
            self.enableCaustics = not self.enableCaustics
            self.ocean.enableCaustics = self.enableCaustics
            
    def isKeyPressed(self, symbol):
        if symbol in self.pressedKeys:
            return self.pressedKeys[symbol]
        return False
          
    def on_key_release(self, symbol, modifiers):
        """ Handle key release events """
        self.pressedKeys[symbol] = False
        
    def on_mouse_motion(self, x, y, dx, dy):
        """ Handle mouse motion events """
        self.camera.addAngularVelocity(-dx/2., dy/2., 0.0)
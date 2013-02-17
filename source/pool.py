from heightfields import Ripples
from surface import Surface
from caustics import Caustics

from pyglet import *
from pyglet.gl import *
from gletools import ShaderProgram

from vector import Vector2, Vector3

class Pool():
    def __init__(   self,
                    camera,
                    scale=1.0,
                    tileSize=128,
                    tilesX=1,
                    tilesZ=1,
                    depth=30.0):
    
        self.depth = depth

        self.tileSize = tileSize
        self.tilesX = tilesX
        self.tilesZ = tilesZ

        self.camera = camera
        self.scale = scale
        
        self.surfaceShader = ShaderProgram.open('shaders/colour_by_height.shader')

        
        # Use Tessendorf FFT synthesis to create a convincing ocean surface.
        self.heightfield = Ripples(self.camera, self.tileSize)
                                           
        # The water surface
        self.surface = Surface( self.surfaceShader,
                                self.camera,
                                texture=None,
                                heightfield=self.heightfield,
                                tileSize=self.tileSize, 
                                tilesX=self.tilesX,
                                tilesZ=self.tilesZ,
                                scale=self.scale, 
                                offset=Vector3(0.0,self.depth,0.0))

    def setDepth(self, depth):
        self.surface.setDepth(self.depth)
    def tap(self, tapPosition):
        self.heightfield.tap(tapPosition)

    def draw(self,dt):
        self.surface.draw(dt)        
from pyglet import *
from pyglet.gl import *
from gletools import ShaderProgram

from vector import Vector2, Vector3
from matrix16 import Matrix16

from utilities import frameBuffer, Pointfield2D, Mesh2DSurface

import numpy as np

import ctypes

import random

class Caustics():
    def __init__(self,
                camera,
                surface,
                depth,
                causticTexture,
                photonScale=4.0,
                photonIntensity=2.0):
                  
        self.surface = surface
        self.depth = depth
        self.camera = camera
        self.lightPosition = Vector3(0.0,5000.0,0.0)
        
        # The dimension of the photon map should match the tile size
        self.tileSize = self.surface.tileSize
        
        # Compile the shader
        self.shader = ShaderProgram.open('shaders/photonMap.shader')
        
        self.causticTexture = causticTexture     
        
        self.photonIntensity = photonIntensity
        self.photonScale = photonScale
        
        # Photon Texture Shader Handles
        self.positionHandle = glGetAttribLocation(
                                    self.shader.id,
                                    "vPosition"
                                )
        self.normalHandle = glGetAttribLocation(
                                    self.shader.id,
                                    "vNormal"
                                )                                        
        self.lightPositionHandle = glGetUniformLocation(
                                    self.shader.id,
                                    "vLightPosition"
                                )
        self.depthHandle = glGetUniformLocation(
                                    self.shader.id,
                                    "depth"
                                ) 
        self.sizeHandle = glGetUniformLocation(
                                    self.shader.id,
                                    "viewportSize"
                                )
        self.photonIntensityHandle = glGetUniformLocation(
                                    self.shader.id,
                                    "photonIntensity"
                                )
        self.photonScaleHandle = glGetUniformLocation(
                                    self.shader.id,
                                    "photonScale"
                                )
                                
        # Get a framebuffer object
        self.pointMapFBO = frameBuffer(self.causticTexture)
                
        self.setupVAO()
        
    def setupVAO(self):
        '''
        Perform initial setup for this object's vertex array object, which
        stores the vertex VBO and indices VBO. This is used to draw the surface
        geometry for computing caustics in the shader.
        '''
        # Vertex Array Object for Position and Normal VBOs
        self.VAO = GLuint()
        glGenVertexArrays(1,ctypes.pointer(self.VAO))
        glBindVertexArray(self.VAO)
        
        # Vertex Buffer Objects (Positions Normals and Indices)
        self.vertVBO = GLuint()
        self.indexVBO = GLuint()
        glGenBuffers(1, ctypes.pointer(self.vertVBO))
        glGenBuffers(1, ctypes.pointer(self.indexVBO))
                
        indicesGL = np.ctypeslib.as_ctypes(self.surface.indices)
        vertsGL = np.ctypeslib.as_ctypes(self.surface.verts)
        vertexSize = ctypes.sizeof(GLfloat) * 8
        offsetNormals = ctypes.sizeof(GLfloat) * 3
        offsetTexture = ctypes.sizeof(GLfloat) * 6

        # Set up vertices VBO (associated with VAO)
        glBindBuffer(GL_ARRAY_BUFFER, self.vertVBO)      
        glBufferData(GL_ARRAY_BUFFER, ctypes.sizeof(vertsGL), vertsGL, GL_STATIC_DRAW)
        # Positions
        glEnableVertexAttribArray(self.positionHandle) 
        glVertexAttribPointer(self.positionHandle, 3, GL_FLOAT, GL_FALSE, vertexSize, 0)
        # Normals
        glEnableVertexAttribArray(self.normalHandle) 
        glVertexAttribPointer(self.normalHandle, 3, GL_FLOAT, GL_FALSE, vertexSize, offsetNormals)

        # Set up indices VBO (associated with VAO)
        # Indices
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.indexVBO)      
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, ctypes.sizeof(indicesGL), indicesGL, GL_STATIC_DRAW)

        glBindVertexArray(0)
        
        
    def genPhotonMap(self):
        '''
        Bind and draw surface geometry using the photon shader and output
        the pixels to the caustic texture via a framebuffer.
        '''                
        # Update the vertex VBO
        glBindBuffer(GL_ARRAY_BUFFER, self.vertVBO)
        
        glBufferData(GL_ARRAY_BUFFER, 
                     self.surface.verts.size*4, 
                     np.ctypeslib.as_ctypes(self.surface.verts),
                     GL_STATIC_DRAW)
        
        # Bind FBO A/B to set Texture A/B as the output texture
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, self.pointMapFBO)
            
        # Set the viewport to the size of the texture 
        # (we are going to render to texture)
        glViewport(0,0, self.tileSize, self.tileSize)
            
        # Clear the output texture
        glClearColor(0.0, 0.0, 0.0 ,1.0)
        glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
             
        # Bind the photon shader
        glUseProgram(self.shader.id)

        glUniform3f(self.lightPositionHandle, *self.lightPosition.elements())
        glUniform1f(self.depthHandle, self.depth)
        glUniform1f(self.sizeHandle, self.tileSize)    
        glUniform1f(self.photonIntensityHandle, self.photonIntensity)
        glUniform1f(self.photonScaleHandle, self.photonScale)
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        
        glBindVertexArray(self.VAO)
        glDrawElements(GL_POINTS, self.surface.vertexCount, GL_UNSIGNED_INT, 0)            

        # Unbind shader and FBO
        glBindVertexArray(0)
        glUseProgram(0)   
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, 0)  
        
        glDisable(GL_BLEND)
        glEnable(GL_DEPTH_TEST)
        glClearColor(0.0, 0.49, 1.0 ,1.0)
        # Restore viewport
        glViewport(0, 0, self.camera.width, self.camera.height)
    
    def update(self, dt):
        '''
        Regenerate the caustic texture using the surface normals, only needs
        calling if the surface normals or light position has changed.
        '''
        self.genPhotonMap()
        
    def setDepth(self, depth):
        '''
        Set the depth of the ocean by modifying the Y offset which is ultimately
        applied to the Y translation component of the model matrix.
        '''
        self.depth = depth  
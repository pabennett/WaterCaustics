from pyglet import *
from pyglet.gl import *
from gletools import ShaderProgram

from vector import Vector2, Vector3

from utilities import frameBuffer, Pointfield2D

import numpy as np

import ctypes

class Caustics():
    def __init__(self, camera, surface, depth, causticTexture):
        self.surface = surface
        self.depth = depth
        self.camera = camera
        
        # The dimension of the photon map should match the tile size
        self.tileSize = self.surface.tileSize
        
        # Compile the shader
        self.shader = ShaderProgram.open('shaders/photonMap.shader')
        self.pointShader = ShaderProgram.open('shaders/pointMap.shader')
        
        self.photonMap = image.DepthTexture.create_for_size(GL_TEXTURE_2D, 
                                                            self.tileSize, 
                                                            self.tileSize,
                                                            GL_RGBA)
        self.causticTexture = causticTexture     
        
        # Photon Texture Shader Handles
        self.positionHandle = glGetAttribLocation(
                                    self.shader.id,
                                    "vPosition"
                                )
        self.tileSizeormalHandle = glGetAttribLocation(
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
        
        # Point Shader Handles
        self.pointPositionHandle = glGetAttribLocation(
                                    self.pointShader.id,
                                    "vPosition"
                                )
        self.pointTexcoordHandle = glGetAttribLocation(
                                    self.pointShader.id,
                                    "vTexcoord"
                                )
        self.pointTextureHandle = glGetUniformLocation(
                                    self.pointShader.id,
                                    "texture"
                                )
         
        # Get a framebuffer object
        self.causticMapFBO = frameBuffer(self.photonMap)
        self.pointMapFBO = frameBuffer(self.causticTexture)
        
        # Texbuffer
        self.buffer = (GLubyte * (self.tileSize * self.tileSize * 4))()
        
        # Points
        self.points, self.pointIndices, self.vertexSize = Pointfield2D(self.tileSize, 1.0)

        print self.points
        #self.points = np.ctypeslib.as_ctypes(self.points) 
        #self.pointIndices = np.ctypeslib.as_ctypes(self.pointIndices)
        
        print self.pointIndices[0], self.pointIndices[50]
        print self.points[0], self.points[50]
        self.pointVertVBO = GLuint()
        glGenBuffers(1, ctypes.pointer(self.pointVertVBO))  
        self.offsetTexcoords = ctypes.sizeof(GLfloat) * 3
        

        
    def genPhotonMap(self):
        '''
        Bind and draw surface geometry using the photon shader and output
        the pixels to the caustic texture via a framebuffer.
        '''
        # Bind FBO A/B to set Texture A/B as the output texture
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, self.causticMapFBO)
            
        # Set the viewport to the size of the texture 
        # (we are going to render to texture)
        glViewport(0,0, self.tileSize, self.tileSize)
            
        # Clear the output texture
        glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
             
        # Bind the photon shader
        glUseProgram(self.shader.id)

        #glUniform3f(self.rsLightPositionHandle, *self.lightPosition.values())
        glUniform1f(self.depthHandle, self.depth)
        glUniform1f(self.sizeHandle, self.tileSize)    
        
        glBindVertexArray(self.surface.VAO)
        glDrawElements(GL_TRIANGLES, self.surface.vertexCount, GL_UNSIGNED_INT, 0)
        
        # Unbind shader and FBO
        glBindVertexArray(0)
        glUseProgram(0)   
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, 0)  
        
        # Restore viewport
        glViewport(0, 0, self.camera.width, self.camera.height)
        
    def genCausticTexture(self):
        '''
        Bind and draw surface geometry using the photon shader and output
        the pixels to the caustic texture via a framebuffer.
        '''
        # Bind FBO A/B to set Texture A/B as the output texture
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, self.pointMapFBO)
            
        # Set the viewport to the size of the texture 
        # (we are going to render to texture)
        glViewport(0,0, self.tileSize, self.tileSize)
            
        # Clear the output texture
        glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
             
        # Bind the photon shader
        glUseProgram(self.pointShader.id)

        glEnable(GL_PROGRAM_POINT_SIZE)
        glPointSize( 0.2 ) 
        
        
        #print glIsEnabled(GL_PROGRAM_POINT_SIZE)

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.photonMap.id)
        glUniform1i(self.pointTextureHandle, 0)
        
        glEnable(GL_BLEND)
        glBlendFunc(GL_ZERO, GL_SRC_COLOR)
            
        # Set up vertices VBO
        glBindBuffer(GL_ARRAY_BUFFER, self.pointVertVBO)  
        
        glBufferData(   GL_ARRAY_BUFFER,
                        ctypes.sizeof(self.points),
                        self.points,
                        GL_STATIC_DRAW)
    
        # Set up vertex attributes
        glEnableVertexAttribArray(self.pointPositionHandle)
        glVertexAttribPointer(  self.pointPositionHandle,
                                3,
                                GL_FLOAT,
                                GL_FALSE,
                                self.vertexSize,
                                0)
                                
        glEnableVertexAttribArray(self.pointTexcoordHandle)          
        glVertexAttribPointer(  self.pointTexcoordHandle,
                                2,
                                GL_FLOAT,
                                GL_FALSE,
                                self.vertexSize,
                                self.offsetTexcoords)

        glDrawElements(GL_POINTS,
                       len(self.pointIndices), 
                       GL_UNSIGNED_SHORT,
                       self.pointIndices)
        
        
        # Disable arrays
        glDisableVertexAttribArray(self.pointPositionHandle)
        glDisableVertexAttribArray(self.pointTexcoordHandle)
        # Unbind shader and FBO
        glUseProgram(0)   
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, 0)  
        
        # Restore viewport
        glViewport(0, 0, self.camera.width, self.camera.height)
        
    def histogram(self):
        '''
        Compute the histogram of the photon map texture and write the result to
        the caustics texture
        '''
        glBindTexture(GL_TEXTURE_2D, self.photonMap.id)
                
        glGetTexImage(GL_TEXTURE_2D, 0, GL_RGBA, GL_UNSIGNED_BYTE, self.buffer)

        histo,_,_ = np.histogram2d( self.buffer[0::4],
                                    self.buffer[1::4],
                                    weights=self.buffer[2::4],
                                    bins=(self.tileSize,self.tileSize))
                               
        histo = histo.astype(GLubyte)
                
        glBindTexture(GL_TEXTURE_2D, self.causticTexture.id)
        
        glTexImage2D(GL_TEXTURE_2D,
                     0,
                     GL_RED,
                     self.tileSize,
                     self.tileSize,
                     0,
                     GL_RED,
                     GL_UNSIGNED_BYTE,
                     np.ctypeslib.as_ctypes(histo))
                     
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
                  
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, 0)        
        glUseProgram(0)   
                     
    def update(self, dt):
        '''
        Regenerate the caustic texture using the surface normals, only needs
        calling if the surface normals or light position has changed.
        '''
        self.genPhotonMap()
        self.genCausticTexture()
        #self.histogram()
        # The caustic texture is now updated
        
    def setDepth(self, depth):
        '''
        Set the depth of the ocean by modifying the Y offset which is ultimately
        applied to the Y translation component of the model matrix.
        '''
        self.depth = depth  
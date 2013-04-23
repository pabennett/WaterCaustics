from pyglet import *
from pyglet.gl import *
from vector import Vector2, Vector3
from matrix16 import Matrix16
from utilities import *
from ctypes import pointer, sizeof, c_float

class Surface():
    '''
    The ocean surface is formed from a 2D tiled mesh where the vertices are 
    displaced according to a heightfield generated from a surface generator
    object.
    '''
    def __init__(self,
                 shaderProgram,
                 camera,
                 texture=None,
                 causticTexture=None,
                 cubemapTexture=None,
                 heightfield=None,
                 tileSize=64, 
                 tilesX=1,
                 tilesZ=1,
                 scale=1.0, 
                 offset=Vector3(0.0,0.0,0.0)):
        
        '''
        Initial setup of constants and openGL attribute and uniform handles
        '''
        self.tileSize = tileSize        # N - should be power of 2
        self.offset = offset            # World space offset
        self.scale = scale              # Size of each quad in world space
        self.camera = camera            # A camera object (provides MVP)
        self.tileCount = Vector2(tilesX,tilesZ)
        self.texture = texture
        self.causticTexture = causticTexture
        self.cubemapTexture = cubemapTexture
        # Set the shader and obtain references to shader uniforms/attributes
        self.setShader(shaderProgram)
        # Generate a 2D plane composed of tiled Quads
        # Directly access the positions, normals and indices of the mesh
        self.verts, self.indices = Mesh2DSurface(self.tileSize, self.scale)
        # Keep a copy of the original vertex positions and apply displacements
        # from the heightfield to them to produce new vertex positions
        self.v0 = self.verts.copy()
        self.vertexCount = self.indices.size
        
        self.modelMatrix = Matrix16()
        self.modelMatrix[12] = self.offset.x
        self.modelMatrix[13] = self.offset.y
        self.modelMatrix[14] = self.offset.z
        
        '''
        Perform initial setup of this obhect's vertex array object, which stores
        the vertex VBO and indices VBO.
        '''
        # Vertex Array Object for Position and Normal VBOs
        self.VAO = GLuint()
        glGenVertexArrays(1,pointer(self.VAO))
        glBindVertexArray(self.VAO)
        
        # Vertex Buffer Objects (Positions Normals and Indices)
        self.vertVBO = GLuint()
        self.indexVBO = GLuint()
        glGenBuffers(1, pointer(self.vertVBO))
        glGenBuffers(1, pointer(self.indexVBO))
                
        indicesGL = np.ctypeslib.as_ctypes(self.indices)
        vertsGL = np.ctypeslib.as_ctypes(self.verts)
        vertexSize = sizeof(GLfloat) * 8
        offsetNormals = sizeof(GLfloat) * 3
        offsetTexture = sizeof(GLfloat) * 6

        # Set up vertices VBO (associated with VAO)
        glBindBuffer(GL_ARRAY_BUFFER, self.vertVBO)      
        glBufferData(GL_ARRAY_BUFFER, sizeof(vertsGL), vertsGL, GL_STATIC_DRAW)
        # Positions
        glEnableVertexAttribArray(self.positionHandle) 
        glVertexAttribPointer(  self.positionHandle,
                                3,
                                GL_FLOAT,
                                GL_FALSE,
                                vertexSize,
                                0)
        # Normals
        glEnableVertexAttribArray(self.normalHandle) 
        glVertexAttribPointer(  self.normalHandle,
                                3,
                                GL_FLOAT,
                                GL_FALSE,
                                vertexSize,
                                offsetNormals)
        
        if self.texture:
            # TexCoords
            glEnableVertexAttribArray(self.texCoordHandle) 
            glVertexAttribPointer(  self.texCoordHandle,
                                    2,
                                    GL_FLOAT,
                                    GL_FALSE,
                                    vertexSize,
                                    offsetTexture)
            
        # Set up indices VBO (associated with VAO)
        # Indices
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.indexVBO)      
        glBufferData(   GL_ELEMENT_ARRAY_BUFFER,
                        sizeof(indicesGL),
                        indicesGL,
                        GL_STATIC_DRAW)

        glBindVertexArray(0)
        
        '''
        Set up the surface generator. The surface generator creates a
        heightfield representing the surface of an ocean using the FFT synthesis
        technique detailed in Tessendorf's "Simulating Ocean Water"
        '''
        # Ocean Heightfield Generator
        self.time = 0.0
        self.heightfield = heightfield
    def setShader(self, shader):
        self.shader = shader     # The GLSL shader program handle
        # Set up GLSL uniform and attribute handles
        self.positionHandle = glGetAttribLocation(self.shader.id, "vPosition")
        self.normalHandle = glGetAttribLocation(self.shader.id, "vNormal")
        self.texCoordHandle = glGetAttribLocation(self.shader.id, "vTexCoord")
        self.modelMatrixHandle = glGetUniformLocation(self.shader.id, "model")
        self.viewMatrixHandle = glGetUniformLocation(self.shader.id, "view")
        self.projMatrixHandle = glGetUniformLocation(self.shader.id, "projection")
        self.textureHandle = glGetUniformLocation(self.shader.id, "texture")
        self.causticTextureHandle = glGetUniformLocation(self.shader.id, "caustics")   
        self.cubemapTextureHandle = glGetUniformLocation(self.shader.id, "cubemap")
        self.eyeHandle = glGetUniformLocation(self.shader.id, "eye")  
        self.eyePositionHandle = glGetUniformLocation(self.shader.id, "eyePosition")  
        
        self.tileSizeHandle = glGetUniformLocation(self.shader.id, "tileSize") 
        self.tileCountHandle = glGetUniformLocation(self.shader.id, "tileCount")
        self.tileOffsetHandle = glGetUniformLocation(self.shader.id, "tileOffset")
    def setHeightfield(self, heightfield):
        self.heightfield = heightfield
        
    def setDepth(self, depth):
        '''
        Set the depth of the ocean by modifying the Y offset which is ultimately
        applied to the Y translation component of the model matrix.
        '''
        self.offset.y = depth

    def update(self, dt):
        '''
        If deltaTime is not zero, perform an ocean surface update for time T.
        This update will run heightmap, diplacement and normal generation
        routines and then passes the updated values into the vertex array.
        '''
        if dt > 0.0 and self.heightfield:
            self.time += dt
            self.heightfield.update(self.time, self.verts, self.v0)
            # Update the vertex VBO
            glBindBuffer(GL_ARRAY_BUFFER, self.vertVBO)
            
            glBufferData(GL_ARRAY_BUFFER, 
                         self.verts.size*4, 
                         np.ctypeslib.as_ctypes(self.verts),
                         GL_STATIC_DRAW)
                         
    def size(self, tilesX, tilesZ):
        self.tileCount = Vector2(tilesX,tilesZ)
    
    def draw(self, dt):
        '''
        Draw this object.
        This ocean surface tile can be repeated in X and Z by increasing the
        value of tilesX and tilesZ respectively.
        '''        
        # Update the ocean surface heightfield
        self.update(dt)
        
        glUseProgram(self.shader.id)             
        glUniformMatrix4fv( self.projMatrixHandle,
                            1,
                            False,
                            self.camera.getProjection())
        glUniformMatrix4fv( self.viewMatrixHandle,
                            1,
                            False,
                            self.camera.getModelView())
                            
        glUniform3fv(self.eyeHandle, 3, self.camera.getEye())
        glUniform3fv(self.eyePositionHandle, 3, self.camera.getPosition())
         
        glUniform1f(self.tileSizeHandle, self.tileSize)
        glUniform2fv(self.tileCountHandle, 2, self.tileCount.cvalues())
         
        if self.texture:
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, self.texture.id)
            glUniform1i(self.textureHandle, 0)
            
        if self.causticTexture:
            glActiveTexture(GL_TEXTURE1)
            glBindTexture(GL_TEXTURE_2D, self.causticTexture.id)
            glUniform1i(self.causticTextureHandle, 1)
            
        if self.cubemapTexture:
            glActiveTexture(GL_TEXTURE2)
            glBindTexture(GL_TEXTURE_CUBE_MAP, self.cubemapTexture)
            glUniform1i(self.cubemapTextureHandle, 2)
         
        glBindVertexArray(self.VAO)
        
        # Translate Y 
        self.modelMatrix[13] = self.offset.y        
                    
        for i in range(self.tileCount.x):
            # Translate X
            self.modelMatrix[12] =  self.offset.x + \
                                    self.tileSize * self.scale * i
            for j in range(self.tileCount.y):
                # Translate Z
                self.modelMatrix[14] =  self.offset.z + \
                                        self.tileSize * self.scale * j 
                glUniform2fv(self.tileOffsetHandle, 2, (c_float*2)(*[i, j]))        
                glUniformMatrix4fv( self.modelMatrixHandle,
                                    1,
                                    False,
                                    self.modelMatrix.elements)
                glDrawElements(GL_TRIANGLES,self.vertexCount,GL_UNSIGNED_INT, 0)        

        glBindTexture(GL_TEXTURE_2D, 0)        
        glBindTexture(GL_TEXTURE_CUBE_MAP, 0)   
        glActiveTexture(GL_TEXTURE0)   
        glBindVertexArray(0)
        glUseProgram(0)
        glDisable(GL_BLEND)
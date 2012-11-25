__author__ = "Peter Bennett"
__copyright__ = "Copyright 2012, Peter A Bennett"
__license__ = "LGPL"
__maintainer__ = "Peter Bennett"
__email__ = "pab850@gmail.com"
__contact__ = "www.bytebash.com"

""" 
This class implements the ocean surface algorithms detailed in Tessendorf's
"Simulating Ocean Water". A 2D heightmap representing the surface of a body
of water is generated.
"""

""" Simulator imports """
from math import *
import numpy as np
from vector import Vector2, Vector3
from matrix16 import Matrix16

""" Renderer Imports """
from pyglet import *
from pyglet.gl import *
from ctypes import pointer, sizeof
from pyglet.window import key, mouse
from gletools import ShaderProgram
import console
         
def np2DArray(initialiser, rows, columns):
    """ Utility Function for generating numpy arrays """
    return np.array([[initialiser for i in range(columns)] for j in range(rows)])        

def np3DArray(initialiser, points, rows, columns, dtype=np.float32):
    """ Utility Function for generating numpy array of vertices """
    return np.array([[[initialiser for i in range(points)]  \
                                   for j in range(columns)] \
                                   for k in range(rows)], \
                                   dtype=dtype)    
                                                               
def Mesh2DSurface(dimension=64, scale=1.0):
    """
    Generate a 2D surface mesh with the given dimensions, scale and offset.

          1   2   3   4  
        +---+---+---+---+   Size in Quads: NxN where N is the dimension
      1 |   |   |   |   |   Quad size (world space) = scale
        +---+---+---+---+   
      2 |   |   |   |   |  
        +---+---+---+---+       
      3 |   |   |   |   |           
        +---+---+---+---+       
      4 |   |   |   |   |  
        +---+---+---+---+     
    """
    """ 
    ------------------------------------------------------------------------
    Initialisation
    ------------------------------------------------------------------------
    """
    N = dimension               # Dimension - should be power of 2

    N1 = N+1                    # Vertex grid has additional row and
                                # column for tiling purposes
                                                                 
    # Vertex arrays are 3-dimensional have have the following structure:
    # [[[v0x,v0y,v0z,n0x,n0y,n0z],[v1x,v1y,v1z,n1x,n1y,n1z]],
    #  [[v2x,v2y,v2z,n2x,n2y,n2z],[v3x,v3y,v3z,n3x,n3y,n3z]],
    #  [[v4x,v4y,v4z,n4x,n4y,n4z],[v5x,v5y,v5z,n5x,n5y,n5z]]]
    verts = np3DArray(0.0, 8, N1, N1, GLfloat)
    # Indicies are grouped per quad (6 indices for each quad)
    # The mesh is composed of NxN quads
    indices = np3DArray(0,6,N,N,dtype='u4')
    
    # Initialise the surface mesh
    # Populate the index array
    for i in range(N):
        for j in range(N):
            idx = i * N1 + j
            indices[i][j][0] = idx
            indices[i][j][1] = idx + N1
            indices[i][j][2] = idx + 1
            indices[i][j][3] = idx + 1
            indices[i][j][4] = idx + N1
            indices[i][j][5] = idx + N1 + 1
            
    # Populate the initial positions and normals
    for i in range(N+1):
        for j in range(N+1):
            # Position X
            verts[i][j][0] = (j-N/2.0) * scale
            # Position Y                        
            verts[i][j][1] = 0.0
            # Position Z
            verts[i][j][2] = (i-N/2.0) * scale
            # # Normal X
            verts[i][j][3] = 0.0
            # # Normal Y                        
            verts[i][j][4] = 1.0
            # # Normal Z
            verts[i][j][5] = 0.0 
            # # Texture X
            verts[i][j][6] = i/float(N)
            # # Texture Y                        
            verts[i][j][7] = j/float(N)
            
    return verts, indices

class Heightfield():
    def __init__(self, dimension=64, A=0.0005,w=Vector2(32.0, 32.0),length=64.0):

        """ 
        ------------------------------------------------------------------------
        Constants
        ------------------------------------------------------------------------
        """
        self.N = dimension              # Dimension - should be power of 2
        
        self.N1 = self.N+1              # Vertex grid has additional row and
                                        # column for tiling purposes
                                        
        self.NSq = self.N * self.N
        self.N1Sq = self.N1 * self.N1
        self.NVec = self.N1Sq * 3       # Number of floats for vector data
                                                                                
        self.length = float(length)     # Length Parameter
        
        self.w = w                      # Wind Parameter
        
        self.a = A                      # Phillips spectrum parameter
                                        # affects heights of waves
                                           
        self.w0 = 2.0 * pi / 200.0      # Used by the dispersion function
        
        self.g = 9.81                   # Constant acceleration due to gravity
                       
        # Wave surface property arrays (displacements, normals, etc)
        self.hTilde0 = np2DArray(0.0+0j,self.N,self.N)      # Height @ t = 0
        self.hTilde0mk = np2DArray(0.0+0j,self.N,self.N)    # H conjugate @t = 0
        self.hTilde = np2DArray(0.0+0j,self.N,self.N)       # Height @ t
        self.hTildeSlopeX = np2DArray(0.0+0j,self.N,self.N) # NormalX @ t
        self.hTildeSlopeZ = np2DArray(0.0+0j,self.N,self.N) # NormalZ @ t
        self.hTildeDx = np2DArray(0.0+0j,self.N,self.N)     # DisplacementX @ t
        self.hTildeDz = np2DArray(0.0+0j,self.N,self.N)     # DisplacementZ @ t
        
        # Lookup tables for code optimisation
        self.dispersionLUT = np2DArray(0.0, self.N, self.N) # Dispersion Lookup
        self.kxLUT = np2DArray(0.0, self.N, self.N)         # kx Lookup
        self.kzLUT = np2DArray(0.0, self.N, self.N)         # kz Lookup
        self.lenLUT = np2DArray(0.0, self.N, self.N)        # Length Lookup
                                        
        # Build Lookup Tables and vertex indices list (N*N)        
        for i in range(self.N):
            # Build k LUT for wave evaluation loop
            kz = pi * (2.0 * i - self.N) / self.length
            for j in range(self.N):
                kx = pi * (2.0 * j - self.N) / self.length
                # Generate index LUT
                self.kxLUT[i][j] = kx
                self.kzLUT[i][j] = kz
                # Generate HTilde initial values
                self.hTilde0[i][j] = self.getHTilde0(j, i)
                self.hTilde0mk[i][j] = self.getHTilde0(-j, i)        
                # Build a dispersion LUT
                self.dispersionLUT[i][j] = self.dispersion(j, i) 
                # Build a length LUT
                self.lenLUT[i][j] = sqrt(kx * kx + kz * kz)

    def phillips(self, nPrime, mPrime):
        """
        The phillips spectrum
        """
        k = Vector2(pi * (2 * nPrime - self.N) / self.length, \
                    pi * (2 * mPrime - self.N) / self.length)

        k_length = k.magnitude()
        
        if(k_length < 0.000001): return 0.0
        
        k_length2 = k_length * k_length
        k_length4 = k_length2 * k_length2
        
        k_dot_w = k.normalise().dot(self.w.normalise())
        k_dot_w2 = k_dot_w * k_dot_w
        
        w_length = self.w.magnitude()
        L = w_length * w_length / self.g
        l2 = L*L

        damping = 0.001
        ld2 = l2 * damping * damping
        
        return self.a * exp(-1.0 / (k_length2 * l2)) / k_length4 * k_dot_w2 * \
               exp(-k_length2 * ld2);

    def dispersion(self, nPrime, mPrime):
        kx = pi * (2.0 * nPrime - self.N) / self.length
        kz = pi * (2.0 * mPrime - self.N) / self.length
        return floor(sqrt(self.g * sqrt(kx**2 + kz**2)) / self.w0) * self.w0
        
    def getHTilde0(self, nPrime, mPrime):
        import random
        r = random.random()
        return r * sqrt(self.phillips(nPrime, mPrime) / 2.0)
        
    def getHTilde(self, t, nPrime, mPrime):    
        """ 
        Get the wave height value for time t at position (m',n')
        """
        omegat = self.dispersionLUT[mPrime][nPrime] * t
        
        cos_ = cos(omegat)
        sin_ = sin(omegat)
        c0 = cos_ + (sin_ * 1j)
        c1 = cos_ + (-sin_ * 1j)

        return self.hTilde0[mPrime][nPrime] * c0 + self.hTilde0mk[mPrime][nPrime] * c1
          
    def genHTildeArray(self, t):
        """ 
        Generate array of wave height values for time t 
        """
        omegat = self.dispersionLUT * t
        
        sin_ = np.sin(omegat)
        cos_ = np.cos(omegat)
        
        c0 = cos_ + (sin_ * 1j)
        c1 = cos_ + (-sin_ * 1j)
    
        self.hTilde = self.hTilde0 * c0 + self.hTilde0mk * c1 

    def genHTilde(self, t):
        """ 
        ------------------------------------------------------------------------
        Generate hTilde for time t 
        ------------------------------------------------------------------------
        """
        
        # Update the hTilde values
        self.genHTildeArray(t)
        
        # Generate normals for X and Z
        self.hTildeSlopeX = self.hTilde * self.kxLUT * 1j
        self.hTildeSlopeZ = self.hTilde * self.kzLUT * 1j
        
        # Generate a set of indices for which the length in the length 
        # look-up table is less than 0.000001
        zeros = self.lenLUT < 0.000001
        nonzeros = self.lenLUT >= 0.000001
        
        # If the length contained in the length look-up table (lenLUT) is 
        # greater than 0.000001 set the displacements in x and z to:
        # Dx = hTilde * complex(0.0,-kx/length)
        # Dz = hTilde * complex(0.0,-kz/length)
        # Otherwise, set the displacements to 0.0+0j
        self.hTildeDx = self.hTilde * 1j * -self.kxLUT / self.lenLUT
        self.hTildeDz = self.hTilde * 1j * -self.kzLUT / self.lenLUT
        self.hTildeDx[zeros] = 0.0+0j
        self.hTildeDz[zeros] = 0.0+0j
        
    def doFFT(self):
        """ 
        ------------------------------------------------------------------------
        Compute FFT
        ------------------------------------------------------------------------
        """
        
        # Heights
        self.hTilde = np.fft.fft2(self.hTilde)
        # Displacements
        self.hTildeDx = np.fft.fft2(self.hTildeDx)
        self.hTildeDz = np.fft.fft2(self.hTildeDz)
         
    def updateVerts(self, t, verts, v0):
        """
        Update the input vertex arrays
        # Vertex arrays are 3-dimensional have have the following structure:
        [
         [[v0x,v0y,v0z,n0x,n0y,n0z],[v1x,v1y,v1z,n1x,n1y,n1z]],
         [[v2x,v2y,v2z,n2x,n2y,n2z],[v3x,v3y,v3z,n3x,n3y,n3z]],
         [[v4x,v4y,v4z,n4x,n4y,n4z],[v5x,v5y,v5z,n5x,n5y,n5z]]
        ]
        Positions and normals are sampled from the heightfield and applied to
        the input array.
        verts: input array to be modified
        v0: the original vertex positions
        """
        
        # First, do a surface update
        self.evaluateWavesFFT(t)
        
        # Update Normals
        self.hTildeSlopeX[::2,::2] = -self.hTildeSlopeX[::2,::2]
        self.hTildeSlopeZ[::2,::2] = -self.hTildeSlopeZ[::2,::2]
        self.hTildeSlopeX[1::2,1::2] = -self.hTildeSlopeX[1::2,1::2]
        self.hTildeSlopeZ[1::2,1::2] = -self.hTildeSlopeZ[1::2,1::2]
                                  
        verts[:self.N:,:self.N:,3] = -self.hTildeSlopeX
        verts[:self.N:,:self.N:,4] = 1.0
        verts[:self.N:,:self.N:,5] = -self.hTildeSlopeZ
        
        # Update Displacements
        self.hTilde[::2,::2] = -self.hTilde[::2,::2]
        self.hTildeDx[::2,::2] = -self.hTildeDx[::2,::2]
        self.hTildeDz[::2,::2] = -self.hTildeDz[::2,::2]
          
        self.hTilde[1::2,1::2] = -self.hTilde[1::2,1::2]
        self.hTildeDx[1::2,1::2] = -self.hTildeDx[1::2,1::2]
        self.hTildeDz[1::2,1::2] = -self.hTildeDz[1::2,1::2]
                   
        #Update the vertex list for all elements apart from max indices
        #Vertex X (Displacement)
        verts[:self.N:,:self.N:,0] = v0[:self.N:,:self.N:,0] + self.hTildeDx * -1
        # Vertex Y
        verts[:self.N:,:self.N:,1] = self.hTilde
        # Vertex Z (Displacement)
        verts[:self.N:,:self.N:,2] = v0[:self.N:,:self.N:,2]  + self.hTildeDz * -1
        
        # # Allow seamless tiling:

        # Top index of vertices - reference bottom index of displacement array
        # vertices(N,N) = original(N,N) + hTilde(0,0) * - 1
        # Vertex X  
        verts[self.N,self.N,0] = v0[self.N,self.N,0] + \
                                      self.hTildeDx[0,0] * -1
        # Vertex Y                           
        verts[self.N,self.N,1] = self.hTilde[0,0]
        # Vertex Z
        verts[self.N,self.N,2] = v0[self.N,self.N,2] + \
                                      self.hTildeDz[0,0] * -1
                                      
        verts[self.N,self.N,3] = -self.hTildeSlopeX[0,0]
        verts[self.N,self.N,4] = 1.0
        verts[self.N,self.N,5] = -self.hTildeSlopeZ[0,0]
        
        # Last row of vertices - Reference first row of the displacement array
        # vertices(N,[0..N]) = original(N,[0..N]) + hTilde(0,[0..N]) * -1
        # Vertex X  
        verts[self.N,0:self.N:,0] = v0[self.N,0:self.N:,0] + \
                                         self.hTildeDx[0,0:self.N:] * -1
        # Vertex Y                            
        verts[self.N,0:self.N:,1] = self.hTilde[0,0:self.N:]
        # Vertex Z
        verts[self.N,0:self.N:,2] = v0[self.N,0:self.N:,2] + \
                                         self.hTildeDz[0,0:self.N:] * -1
                                         
        verts[self.N,0:self.N:,3] = -self.hTildeSlopeX[0,0:self.N:]
        verts[self.N,0:self.N:,4] = 1.0
        verts[self.N,0:self.N:,5] = -self.hTildeSlopeZ[0,0:self.N:]
        
        # Last col of vertices - Reference first col of the displacement array
        # vertices([0..N],N) = original([0..N],N) + hTilde([0..N],0) * -1
        # Vertex X  
        verts[0:self.N:,self.N,0] = v0[0:self.N:,self.N,0] + \
                                         self.hTildeDx[0:self.N:,0] * -1
        # Vertex Y    
        verts[0:self.N:,self.N,1] = self.hTilde[0:self.N:,0]
        # Vertex Z
        verts[0:self.N:,self.N,2] = v0[0:self.N:,self.N,2] + \
                                         self.hTildeDz[0:self.N:,0] * -1
                                         
        verts[0:self.N:,self.N,3] = -self.hTildeSlopeX[0:self.N:,0]
        verts[0:self.N:,self.N,4] = 1.0
        verts[0:self.N:,self.N,5] = -self.hTildeSlopeZ[0:self.N:,0]
        
    def evaluateWavesFFT(self, t):
        self.genHTilde(t)
        self.doFFT()
        
        
class OceanSurface():
    def __init__(self,
                 shaderProgram,
                 camera,
                 N=64, 
                 scale=1.0, 
                 offset=Vector3(0.0,0.0,0.0),
                 wind=Vector2(0.0,0.0),
                 height=0.0005):
                 
        self.N = N                      # N - should be power of 2
        self.offset = offset            # World space offset
        self.scale = scale              # Size of each quad in world space
        self.shader = shaderProgram     # The GLSL shader program handle
        self.camera = camera            # A camera object (provides MVP)
        
        # Set up GLSL uniform and attribute handles
        self.positionHandle = glGetAttribLocation(self.shader.id, "vPosition")
        self.normalHandle = glGetAttribLocation(self.shader.id, "vNormal")
        self.texCoordHandle = glGetAttribLocation(self.shader.id, "vTexCoord")
        self.modelMatrixHandle = glGetUniformLocation(self.shader.id, "model")
        self.viewMatrixHandle = glGetUniformLocation(self.shader.id, "view")
        self.projMatrixHandle = glGetUniformLocation(self.shader.id, "projection")
        self.MVPMatrixHandle = glGetUniformLocation(self.shader.id, "MVP")
        self.enableTexture = glGetUniformLocation(self.shader.id, "texEnable")
                
        # Generate a 2D plane composed of tiled Quads
        # Directly access the positions, normals and indices of the mesh
        self.verts, self.indices = Mesh2DSurface(self.N, 1.0)
        # Keep a copy of the original vertex positions and apply displacements
        # from the heightfield to them to produce new vertex positions
        self.v0 = self.verts.copy()
        self.vertexCount = self.indices.size
        
        self.modelMatrix = Matrix16()
        self.modelMatrix[12] = self.offset.x
        self.modelMatrix[13] = self.offset.y
        self.modelMatrix[14] = self.offset.z
        # Set up the VAO for rendering
        self.setupVAO()
        
        # Set up the surface generator. The surface generator creates a height
        # field representing the surface of an ocean using the FFT synthesis
        # technique detailed in Tessendorf's "Simulating Ocean Water"
        
        # Ocean Parameters
        self.oceanWind = wind                 # Ocean wind in X,Z axis
        self.oceanWaveHeight = height         # The phillips spectrum parameter
        self.oceanTileSize = N                # Must be a power of 2    
        self.oceanLength = N                  # Ocean length parameter
        self.time = 0.0                       # Time parameter
        # Ocean Heightfield Generator
        self.heightfield = Heightfield(self.oceanTileSize,
                                       self.oceanWaveHeight, 
                                       self.oceanWind,
                                       self.oceanLength)

    def setupVAO(self):
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
        glVertexAttribPointer(self.positionHandle, 3, GL_FLOAT, GL_FALSE, vertexSize, 0)
        # Normals
        glEnableVertexAttribArray(self.normalHandle) 
        glVertexAttribPointer(self.normalHandle, 3, GL_FLOAT, GL_FALSE, vertexSize, offsetNormals)
        
        # Set up indices VBO (associated with VAO)
        # Indices
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.indexVBO)      
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, sizeof(indicesGL), indicesGL, GL_STATIC_DRAW)

        glBindVertexArray(0)
    def setHeightfieldParams(self, wind, waveHeight):
        self.oceanWind = wind
        self.oceanWaveHeight = waveHeight
        del self.heightfield
        self.heightfield = Heightfield(self.oceanTileSize,
                                       self.oceanWaveHeight, 
                                       self.oceanWind,
                                       self.oceanLength)
    def updateHeightfield(self, dt):
        if dt > 0.0:
            self.time += dt
            self.heightfield.updateVerts(self.time, self.verts, self.v0)
            # Update the vertex VBO
            glBindBuffer(GL_ARRAY_BUFFER, self.vertVBO)
            
            glBufferData(GL_ARRAY_BUFFER, 
                         self.verts.size*4, 
                         np.ctypeslib.as_ctypes(self.verts),
                         GL_STATIC_DRAW)
        
    def draw(self, dt, tilesX=1, tilesZ=1):
        """
        Draw this object.
        Multiple copies of this object can be drawn by specifying a tilesX and
        tilesZ value.
        """
        tilesX = 1 if tilesX < 1 else tilesX
        tilesZ = 1 if tilesZ < 1 else tilesZ
        
        # Update the ocean surface heightfield
        self.updateHeightfield(dt)
        
        glUseProgram(self.shader.id)             
        glUniformMatrix4fv(self.MVPMatrixHandle, 1, False, self.camera.getMVP()) 
        glUniformMatrix4fv(self.projMatrixHandle, 1, False, self.camera.getProjection())
        glUniformMatrix4fv(self.viewMatrixHandle, 1, False, self.camera.getModelView())
                
        glUniform1i(self.enableTexture, 0)
        
        glBindVertexArray(self.VAO)
                    
        for i in range(tilesX):
            self.modelMatrix[12] = self.offset.x + self.N * self.scale * i # Translate X
            for j in range(tilesZ):
                self.modelMatrix[14] = self.offset.z + self.N * self.scale * j # Translate Z
                glUniformMatrix4fv(self.modelMatrixHandle, 1, False, self.modelMatrix.elements)
                glDrawElements(GL_TRIANGLES, self.vertexCount, GL_UNSIGNED_INT, 0)        

        glBindVertexArray(0)
        glUseProgram(0)
        
class OceanFloor():
    def __init__(self,
                 shaderProgram,
                 camera,
                 texture,
                 N=64, 
                 scale=1.0, 
                 offset=Vector3(0.0,0.0,0.0)):
                 
        self.N = N                      # N - should be power of 2
        self.offset = offset            # World space offset
        self.scale = scale              # Size of each quad in world space
        self.shader = shaderProgram     # The GLSL shader program handle
        self.camera = camera            # A camera object (provides MVP)
        
        self.camera.setpos(-10.0, 2.0, -10.0)
        
        # Set up GLSL uniform and attribute handles
        self.positionHandle = glGetAttribLocation(self.shader.id, "vPosition")
        self.normalHandle = glGetAttribLocation(self.shader.id, "vNormal")
        self.texCoordHandle = glGetAttribLocation(self.shader.id, "vTexCoord")
        self.modelMatrixHandle = glGetUniformLocation(self.shader.id, "model")
        self.viewMatrixHandle = glGetUniformLocation(self.shader.id, "view")
        self.projMatrixHandle = glGetUniformLocation(self.shader.id, "projection")
        self.MVPMatrixHandle = glGetUniformLocation(self.shader.id, "MVP")
        self.textureHandle = glGetUniformLocation(self.shader.id, "texture")
        self.enableTexture = glGetUniformLocation(self.shader.id, "texEnable")
        
        self.texture = texture
        
        # Generate a 2D plane composed of tiled Quads
        self.verts, self.indices = Mesh2DSurface(self.N, 1.0)
        # Directly access the positions, normals and indices of the mesh
        self.vertexCount = self.indices.size
        
        self.modelMatrix = Matrix16()
        self.modelMatrix[12] = self.offset.x
        self.modelMatrix[13] = self.offset.y
        self.modelMatrix[14] = self.offset.z
        # Set up the VAO for rendering
        self.setupVAO()
        
    def setupVAO(self):
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
        glVertexAttribPointer(self.positionHandle, 3, GL_FLOAT, GL_FALSE, vertexSize, 0)
        # Normals
        glEnableVertexAttribArray(self.normalHandle) 
        glVertexAttribPointer(self.normalHandle, 3, GL_FLOAT, GL_FALSE, vertexSize, offsetNormals)
        # TexCoords
        glEnableVertexAttribArray(self.texCoordHandle) 
        glVertexAttribPointer(self.texCoordHandle, 2, GL_FLOAT, GL_FALSE, vertexSize, offsetTexture)
        
        # Set up indices VBO (associated with VAO)
        # Indices
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.indexVBO)      
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, sizeof(indicesGL), indicesGL, GL_STATIC_DRAW)

        glBindVertexArray(0)
    def draw(self, dt, tilesX=1, tilesZ=1):
        """
        Draw this object.
        Multiple copies of this object can be drawn by specifying a tilesX and
        tilesZ value.
        """
        tilesX = 1 if tilesX < 1 else tilesX
        tilesZ = 1 if tilesZ < 1 else tilesZ
        
        glUseProgram(self.shader.id)             
        glUniformMatrix4fv(self.MVPMatrixHandle, 1, False, self.camera.getMVP()) 
        glUniformMatrix4fv(self.projMatrixHandle, 1, False, self.camera.getProjection())
        glUniformMatrix4fv(self.viewMatrixHandle, 1, False, self.camera.getModelView())
        
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.texture.id)
        glUniform1i(self.textureHandle, 0)
        glUniform1i(self.enableTexture, 1)
        
        glBindVertexArray(self.VAO)
            
        for i in range(tilesX):
            self.modelMatrix[12] = self.offset.x + self.N * self.scale * i # Translate X
            for j in range(tilesZ):
                self.modelMatrix[14] = self.offset.z + self.N * self.scale * j # Translate Z
                glUniformMatrix4fv(self.modelMatrixHandle, 1, False, self.modelMatrix.elements)
                glDrawElements(GL_TRIANGLES, self.vertexCount, GL_UNSIGNED_INT, 0)        

        glBindVertexArray(0)
        glUseProgram(0)

class oceanRenderer():
    def __init__(self, window, camera, statusConsole):
        """ Constructor """
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
        # Animation Timer
        self.time = 0.0
        # Ocean Render Parameters
        self.oceanTilesX = 10
        self.oceanTilesZ = 10
        self.wireframe = False
        self.enableUpdates = False
        # Ocean Parameters
        self.oceanWind = Vector2(32.0,32.0)   # Ocean wind in X,Z axis
        self.oceanWaveHeight = 0.0005         # The phillips spectrum parameter
        self.oceanTileSize = 64               # Must be a power of 2    
        self.oceanLength = 64                 # Ocean length parameter
        self.oceanDepth = 30.0
        # OpenGL Shader
        self.mMainShader = ShaderProgram.open('shaders/waves.shader')
        # Textures
        self.oceanFloorTexture = pyglet.image.load('images/sand.png').get_texture() 
        # Ocean Floor Renderable
        self.oceanFloor = OceanFloor(
                            self.mMainShader,
                            self.camera,
                            self.oceanFloorTexture,
                            self.oceanTileSize, 
                            1.0, 
                            Vector3(0.0,0.0,0.0))             
        # Ocean Surface Renderable
        self.oceanSurface = OceanSurface(
                            self.mMainShader,
                            self.camera,
                            self.oceanTileSize, 
                            1.0, 
                            Vector3(0.0,self.oceanDepth,0.0),
                            self.oceanWind,
                            self.oceanWaveHeight)
                            
    def statusUpdates(self, dt):
        """
        Called periodically by main loop for onscreen text updates
        """
        self.status.setParameter('Wind', self.oceanWind)
        self.status.setParameter('Wave height', self.oceanWaveHeight)
    def resetOcean(self):
        """
        Recreate the ocean generator with new parameters
        """                                
        self.oceanSurface.setHeightfieldParams(
                                      self.oceanWind,
                                      self.oceanWaveHeight)
    def loadShaders(self):
        """ 
        Load the shaders
        Allow hotloading of shaders while the program is running
        """
        self.mMainShader = ShaderProgram.open('shaders/waves.shader')
    def render(self, dt):
        """ Alternative draw loop"""
        # Update timer
        self.time += dt
        # Update camera orientation and position
        self.cameraUpdate(dt)
        
        # Draw ocean surface and floor
        
        glUseProgram(self.mMainShader.id)  
        
        if self.wireframe:
            glPolygonMode(GL_FRONT, GL_LINE)
        else:
            glPolygonMode(GL_FRONT, GL_FILL)

        self.oceanFloor.draw(dt, self.oceanTilesX, self.oceanTilesZ)
        
        if self.enableUpdates:
            self.oceanSurface.draw(dt, self.oceanTilesX, self.oceanTilesZ)
        else:
            self.oceanSurface.draw(0.0, self.oceanTilesX, self.oceanTilesZ)
            
        glPolygonMode(GL_FRONT, GL_FILL)
        glUseProgram(0)
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
        
        if symbol == key.P:
            self.loadShaders()
        if symbol == key.L:
            self.wireframe = not self.wireframe
        if symbol == key.SPACE:
            self.enableUpdates = not self.enableUpdates
   
        if symbol == key.NUM_1:
            self.oceanWind.x *= 2.0
            self.resetOcean()
        if symbol == key.NUM_2:
            self.oceanWind.x /= 2.0
            self.resetOcean()
        if symbol == key.NUM_4:
            self.oceanWind.y *= 2.0
            self.resetOcean()
        if symbol == key.NUM_5:
            self.oceanWind.y /= 2.0
            self.resetOcean()
        if symbol == key.NUM_7:
            self.oceanWaveHeight *= 2.0
            self.resetOcean()
        if symbol == key.NUM_8:
            self.oceanWaveHeight /= 2.0
            self.resetOcean()

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
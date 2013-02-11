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
import ctypes
       
def frameBuffer(tex):
    """ Create a framebuffer object and link it to the given texture """
    fbo = GLuint()
    glGenFramebuffers(1, ctypes.byref(fbo))
    glBindFramebuffer(GL_FRAMEBUFFER, fbo)
    glFramebufferTexture2DEXT(GL_FRAMEBUFFER_EXT,
                              GL_COLOR_ATTACHMENT0_EXT,
                              GL_TEXTURE_2D,
                              tex.id,
                              0)

    status = glCheckFramebufferStatusEXT(GL_FRAMEBUFFER_EXT)
    assert status == GL_FRAMEBUFFER_COMPLETE_EXT
    glBindFramebuffer(GL_FRAMEBUFFER, 0)
    return fbo

 
def np2DArrayToImage(array, name="figure.png"):
    """
    Plot the numpy array as an intensity chart and save the figure as an image
    """
    import matplotlib
    matplotlib.use('wxagg')
    import matplotlib.pyplot as plt
    from matplotlib import cm
    
    fig = plt.figure()
    
    plt.imshow(array, cmap=cm.jet)
    
    plt.savefig(name)
    
def np2DArray(initialiser, rows, columns):
    """ Utility Function for generating numpy arrays """
    return np.array([[initialiser for i in range(columns)] for j in range(rows)])        

def np3DArray(initialiser, points, rows, columns, dtype=np.float32):
    """ Utility Function for generating numpy array of vertices """
    return np.array([[[initialiser for i in range(points)]  \
                                   for j in range(columns)] \
                                   for k in range(rows)], \
                                   dtype=dtype)    
 
def gaussianRandomVariable():
    import random
    w = 1.0
    x1 = 0.0
    x2 = 0.0
    while(w >= 1.):
        x1 = 2. * random.random() - 1.
        x2 = 2. * random.random() - 1.
        w = x1 * x1 + x2 * x2
    w = sqrt((-2. * log(w)) / w)
    res = complex(x1 * w, x2 * w) 
    return res 
 
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
    def __init__(self, 
                 dimension=64, 
                 A=0.0005,
                 w=Vector2(32.0, 32.0),
                 length=64.0,
                 period=200.0):

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
                                           
        self.w0 = 2.0 * pi / period     # Used by the dispersion function
        
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
                self.hTilde0mk[i][j] = self.getHTilde0(-j, -i).conjugate()      
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
        k_dot_w2 = k_dot_w * k_dot_w * k_dot_w * k_dot_w * k_dot_w * k_dot_w
        
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
        r = gaussianRandomVariable()
        return r * sqrt(self.phillips(nPrime, mPrime) / 2.0)
        
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
        # Normals
        self.hTildeSlopeX = np.fft.fft2(self.hTildeSlopeX)
        self.hTildeSlopeZ = np.fft.fft2(self.hTildeSlopeZ)
         
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

        # Apply -1**x, -1**z factors
        self.hTildeSlopeX[::2,::2] = -self.hTildeSlopeX[::2,::2]
        self.hTildeSlopeX[1::2,1::2] = -self.hTildeSlopeX[1::2,1::2]
        self.hTildeSlopeZ[::2,::2] = -self.hTildeSlopeZ[::2,::2]
        self.hTildeSlopeZ[1::2,1::2] = -self.hTildeSlopeZ[1::2,1::2]
        self.hTilde = -self.hTilde
        self.hTilde[::2,::2] = -self.hTilde[::2,::2]
        self.hTilde[1::2,1::2] = -self.hTilde[1::2,1::2]
        self.hTildeDx[::2,::2] = -self.hTildeDx[::2,::2]
        self.hTildeDx[1::2,1::2] = -self.hTildeDx[1::2,1::2]
        self.hTildeDz[::2,::2] = -self.hTildeDz[::2,::2]
        self.hTildeDz[1::2,1::2] = -self.hTildeDz[1::2,1::2]
                           
        # Update the vertex list for all elements apart from max indices
        # Position X,Y,Z
        verts[:self.N:,:self.N:,0] = v0[:self.N:,:self.N:,0] + self.hTildeDx * -1
        verts[:self.N:,:self.N:,1] = self.hTilde
        verts[:self.N:,:self.N:,2] = v0[:self.N:,:self.N:,2]  + self.hTildeDz * -1
        # Normal X,Y,Z
        verts[:self.N:,:self.N:,3] = -self.hTildeSlopeX
        verts[:self.N:,:self.N:,4] = 1.0
        verts[:self.N:,:self.N:,5] = -self.hTildeSlopeZ
        
        # Allow seamless tiling:

        # Top index of vertices - reference bottom index of displacement array
        # vertices(N,N) = original(N,N) + hTilde(0,0) * - 1
        # Position X,Y,Z
        verts[self.N,self.N,0] = v0[self.N,self.N,0] + \
                                      self.hTildeDx[0,0] * -1                         
        verts[self.N,self.N,1] = self.hTilde[0,0]
        verts[self.N,self.N,2] = v0[self.N,self.N,2] + \
                                      self.hTildeDz[0,0] * -1
        # Normal X,Y,Z                    
        verts[self.N,self.N,3] = -self.hTildeSlopeX[0,0]
        verts[self.N,self.N,4] = 1.0
        verts[self.N,self.N,5] = -self.hTildeSlopeZ[0,0]
        
        # Last row of vertices - Reference first row of the displacement array
        # vertices(N,[0..N]) = original(N,[0..N]) + hTilde(0,[0..N]) * -1
        # Position X,Y,Z
        verts[self.N,0:self.N:,0] = v0[self.N,0:self.N:,0] + \
                                         self.hTildeDx[0,0:self.N:] * -1                        
        verts[self.N,0:self.N:,1] = self.hTilde[0,0:self.N:]
        verts[self.N,0:self.N:,2] = v0[self.N,0:self.N:,2] + \
                                         self.hTildeDz[0,0:self.N:] * -1
        # Normal X,Y,Z                          
        verts[self.N,0:self.N:,3] = -self.hTildeSlopeX[0,0:self.N:]
        verts[self.N,0:self.N:,4] = 1.0
        verts[self.N,0:self.N:,5] = -self.hTildeSlopeZ[0,0:self.N:]
        
        # Last col of vertices - Reference first col of the displacement array
        # vertices([0..N],N) = original([0..N],N) + hTilde([0..N],0) * -1
        # Position X,Y,Z
        verts[0:self.N:,self.N,0] = v0[0:self.N:,self.N,0] + \
                                         self.hTildeDx[0:self.N:,0] * -1 
        verts[0:self.N:,self.N,1] = self.hTilde[0:self.N:,0]
        verts[0:self.N:,self.N,2] = v0[0:self.N:,self.N,2] + \
                                         self.hTildeDz[0:self.N:,0] * -1
        # Normal X,Y,Z                          
        verts[0:self.N:,self.N,3] = -self.hTildeSlopeX[0:self.N:,0]
        verts[0:self.N:,self.N,4] = 1.0
        verts[0:self.N:,self.N,5] = -self.hTildeSlopeZ[0:self.N:,0]
        
    def evaluateWavesFFT(self, t):
        self.genHTilde(t)
        self.doFFT()
        
        
class OceanSurface():
    """
    The ocean surface is formed from a 2D tiled mesh where the vertices are 
    displaced according to a heightfield generated from a surface generator
    object.
    """
    def __init__(self,
                 shaderProgram,
                 camera,
                 N=64, 
                 scale=1.0, 
                 offset=Vector3(0.0,0.0,0.0),
                 wind=Vector2(0.0,0.0),
                 height=0.0005,
                 period=200.0):
                 
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
        self.period = period                  # The period of the surface anmim
        # Ocean Heightfield Generator
        self.heightfield = Heightfield(self.oceanTileSize,
                                       self.oceanWaveHeight, 
                                       self.oceanWind,
                                       self.oceanLength,
                                       self.period)

    def setupVAO(self):
        """
        Perform initial setup for this object's vertex array object, which
        stores the vertex VBO and indices VBO.
        """
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
    def setDepth(self, depth):
        """
        Set the depth of the ocean by modifying the Y offset which is ultimately
        applied to the Y translation component of the model matrix.
        """
        self.offset.y = depth
    def setHeightfieldParams(self, wind, waveHeight):
        """
        Adjust the generator parameters which govern how the ocean surface
        behaves.
        """
        self.oceanWind = wind
        self.oceanWaveHeight = waveHeight
        del self.heightfield
        self.heightfield = Heightfield(self.oceanTileSize,
                                       self.oceanWaveHeight, 
                                       self.oceanWind,
                                       self.oceanLength)
    def updateHeightfield(self, dt):
        """
        If deltaTime is not zero, perform an ocean surface update for time T.
        This update will run heightmap, diplacement and normal generation
        routines and then passes the updated values into the vertex array.
        """
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
        This ocean surface tile can be repeated in X and Z by increasing the
        value of tilesX and tilesZ respectively.
        """
        tilesX = 1 if tilesX < 1 else tilesX
        tilesZ = 1 if tilesZ < 1 else tilesZ
        
        # Update the ocean surface heightfield
        self.updateHeightfield(dt)
        
        glUseProgram(self.shader.id)             
        glUniformMatrix4fv(self.projMatrixHandle, 1, False, self.camera.getProjection())
        glUniformMatrix4fv(self.viewMatrixHandle, 1, False, self.camera.getModelView())
                
        glUniform1i(self.enableTexture, 0)
        
        glBindVertexArray(self.VAO)
        
        self.modelMatrix[13] = self.offset.y        # Translate Y 
                    
        for i in range(tilesX):
            self.modelMatrix[12] = self.offset.x + self.N * self.scale * i # Translate X
            for j in range(tilesZ):
                self.modelMatrix[14] = self.offset.z + self.N * self.scale * j # Translate Z
                glUniformMatrix4fv(self.modelMatrixHandle, 1, False, self.modelMatrix.elements)
                glDrawElements(GL_TRIANGLES, self.vertexCount, GL_UNSIGNED_INT, 0)        

        glBindVertexArray(0)
        glUseProgram(0)
        
class OceanFloor():
    """
    The ocean floor is formed from a 2D tiled mesh of equivalent size and 
    resolution to the ocean surface. The ocean floor is textured and forms a 
    canvas for painting an underwater caustics pattern.
    """
    def __init__(self,
                 shaderProgram,
                 refractionShader,
                 camera,
                 texture,
                 causticMapTexture,
                 oceanSurface,
                 oceanDepth,
                 N=64, 
                 scale=1.0, 
                 offset=Vector3(0.0,0.0,0.0)):
                 
        self.N = N                      # N - should be power of 2
        self.offset = offset            # World space offset
        self.scale = scale              # Size of each quad in world space
        self.shader = shaderProgram     # The GLSL shader program handle
        self.refractionShader = refractionShader
        self.camera = camera            # A camera object (provides MVP)
        self.surface = oceanSurface     # Maintain a reference to the ocean
                                        # surface
        self.oceanDepth = oceanDepth    # Ocean depth                                        
        
        # Initial camera orientation and position
        self.camera.setpos(-10.0, 5.0, -10.0)
        self.camera.orient(225.0,0.0,0.0)
        
        # Set up GLSL uniform and attribute handles
        self.positionHandle = glGetAttribLocation(self.shader.id, "vPosition")
        self.normalHandle = glGetAttribLocation(self.shader.id, "vNormal")
        self.texCoordHandle = glGetAttribLocation(self.shader.id, "vTexCoord")
        self.modelMatrixHandle = glGetUniformLocation(self.shader.id, "model")
        self.viewMatrixHandle = glGetUniformLocation(self.shader.id, "view")
        self.projMatrixHandle = glGetUniformLocation(self.shader.id, "projection")
        self.textureHandle = glGetUniformLocation(self.shader.id, "texture")
        self.causticMapHandle = glGetUniformLocation(self.shader.id, "causticMap")
        self.oceanDepthHandle = glGetUniformLocation(self.shader.id, "depth")
        
        self.texture = texture
        self.causticTexture = causticMapTexture
        
        # Photon Texture Shader Handles
        self.rsPositionHandle = glGetAttribLocation(
                                            self.refractionShader.id,
                                            "vPosition")
        self.rsNormalHandle = glGetAttribLocation(
                                            self.refractionShader.id,
                                            "vNormal")                                        
        self.rsLightPositionHandle = glGetUniformLocation(
                                            self.refractionShader.id,
                                            "vLightPosition")
        self.rsDepthHandle = glGetUniformLocation(
                                            self.refractionShader.id,
                                            "depth") 
        self.rsSizeHandle = glGetUniformLocation(
                                            self.refractionShader.id,
                                            "viewportSize") 
                       
                
        self.causticMap = image.DepthTexture.create_for_size(GL_TEXTURE_2D, 
                                                        self.N, 
                                                        self.N,
                                                        GL_RGBA)
                                                        
        self.causticMapO = image.DepthTexture.create_for_size(GL_TEXTURE_2D, 
                                                        self.N, 
                                                        self.N,
                                                        GL_RED)
        
        self.causticMapFBO = frameBuffer(self.causticMap)
        
        self.lightPosition = Vector3(32.0, 600.0, 32.0)
        
        
        glTexParameteri(self.causticTexture.target, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(self.causticTexture.target, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        
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
        
        self.buffer = (GLubyte * (self.N * self.N * 4))()
        
        
    def renderToFBO(self, frameBufferHandle, textureHandle):
        
        # Bind FBO A/B to set Texture A/B as the output texture
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, frameBufferHandle)
            
        # Set the viewport to the size of the texture 
        # (we are going to render to texture)
        glViewport(0,0, self.N, self.N)
            
        # Clear the output texture
        glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
             
        # Bind the refraction shader
        glUseProgram(self.refractionShader.id)
         
        # Need to create a view matrix for the light position.

        #self.lightPosition = self.camera.position
        
        glUniform3f(self.rsLightPositionHandle, *self.lightPosition.values())
        glUniform1f(self.rsDepthHandle, self.oceanDepth)
        glUniform1f(self.rsSizeHandle, self.N)    
        glBindVertexArray(self.VAO)

        glDrawElements(GL_TRIANGLES, self.vertexCount, GL_UNSIGNED_INT, 0)        

        # Unbind shader and FBO
        glBindVertexArray(0)
        glUseProgram(0)   
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, 0)  
        
        # Restore viewport
        glViewport(0, 0, self.camera.width, self.camera.height)
        
        
    def setDepth(self, depth):
        """
        Set the depth of the ocean. The ocean depth is passed to the caustics
        shader as a parameter and controls the focus of the caustics pattern.
        """
        self.oceanDepth = depth    
    def updateCaustics(self, dt):
        """
        Get the updated normal map from the ocean surface and use it to generate
        a new caustic pattern on the ocean floor
        """
        
        # Update the normals from the ocean surface
        # Normal Y does not change, so instead pass Position Y to the shader
        # as the height is useful for caustics generation.
        #self.verts[::,::,0] = self.surface.verts[::,::,0] # Position X
        #self.verts[::,::,1] = self.surface.verts[::,::,1] # Position Y
        #self.verts[::,::,2] = self.surface.verts[::,::,2] # Position Z
        self.verts[::,::,3] = self.surface.verts[::,::,3] # Normal X
        self.verts[::,::,4] = self.surface.verts[::,::,4] # Normal Y
        self.verts[::,::,5] = self.surface.verts[::,::,5] # Normal Z
                 
                
        # Update the vertex VBO
        glBindBuffer(GL_ARRAY_BUFFER, self.vertVBO)
        
        glBufferData(GL_ARRAY_BUFFER, 
                     self.verts.size*4, 
                     np.ctypeslib.as_ctypes(self.verts),
                     GL_STATIC_DRAW)

    def setupVAO(self):
        """
        Perform initial setup for this object's vertex array object, which
        stores the vertex VBO and indices VBO.
        """
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
        This ocean surface tile can be repeated in X and Z by increasing the
        value of tilesX and tilesZ respectively.
        """

        tilesX = 1 if tilesX < 1 else tilesX
        tilesZ = 1 if tilesZ < 1 else tilesZ
        
        self.updateCaustics(dt)
        
        # Generate Photon Map Data
        self.renderToFBO(self.causticMapFBO, self.causticMap)
        
        glBindTexture(GL_TEXTURE_2D, self.causticMap.id)
                
        glGetTexImage(GL_TEXTURE_2D, 0, GL_RGBA, GL_UNSIGNED_BYTE, self.buffer)

        #array = np.array(self.buffer,dtype=GLubyte)

        H,_,_ = np.histogram2d(self.buffer[0::4],
                               self.buffer[1::4],
                               weights=self.buffer[2::4],
                               bins=(self.N, self.N))
        #H[0][0] = 0
        #H = ((H+np.min(H))/(np.min(H)+np.max(H)))*np.max(H)
        #H = H.reshape(self.N*self.N)   
        H = H.astype(GLubyte)
        
        # narrayt = GLubyte * (self.N * self.N * 4)
        # narray = narrayt()
          
        # for i in range(self.N):
            # for j in range(self.N):
                # x = int((self.buffer[(i * self.N + j) * 4]/256.)*self.N)
                # y = int((self.buffer[(i * self.N + j) * 4 + 1]/256.)*self.N)
                # v = int((self.buffer[(i * self.N + j) * 4 + 2]/256.)*self.N)
                # narray[(x * self.N + y) * 4] += v
                # narray[(x * self.N + y) * 4 + 1] += v
                # narray[(x * self.N + y) * 4 + 2] += v
                # narray[(x * self.N + y) * 4 + 3] = 255
        
        glBindTexture(GL_TEXTURE_2D, self.causticMapO.id)
        
        glTexImage2D(GL_TEXTURE_2D,
                     0,
                     GL_RED,
                     self.N,
                     self.N,
                     0,
                     GL_RED,
                     GL_UNSIGNED_BYTE,
                     np.ctypeslib.as_ctypes(H))

        glUseProgram(self.shader.id)             
        glUniformMatrix4fv(self.projMatrixHandle, 1, False, self.camera.getProjection())
        glUniformMatrix4fv(self.viewMatrixHandle, 1, False, self.camera.getModelView())
        glUniform1f(self.oceanDepthHandle, self.oceanDepth)
        
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.texture.id)
        glUniform1i(self.textureHandle, 0)
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_2D, self.causticMapO.id)
        glUniform1i(self.causticMapHandle, 1)
                
        glBindVertexArray(self.VAO)
            
        for i in range(tilesX):
            self.modelMatrix[12] = self.offset.x + self.N * self.scale * i # Translate X
            for j in range(tilesZ):
                self.modelMatrix[14] = self.offset.z + self.N * self.scale * j # Translate Z
                glUniformMatrix4fv(self.modelMatrixHandle, 1, False, self.modelMatrix.elements)
                glDrawElements(GL_TRIANGLES, self.vertexCount, GL_UNSIGNED_INT, 0)        

        glBindVertexArray(0)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, 0)
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
        self.status.addParameter('Ocean depth')
        self.status.addParameter('Time')
        # Ocean Render Parameters
        self.oceanTilesX = 1
        self.oceanTilesZ = 1
        self.wireframe = False
        self.enableUpdates = True
        self.drawSurface = True               # Render the ocean surface
        self.drawFloor = True                 # Render the ocean floor
        # Ocean Parameters
        self.oceanWind = Vector2(32.0,32.0)     # Ocean wind in X,Z axis
        self.oceanWaveHeight = 0.0005         # The phillips spectrum parameter
        self.oceanTileSize = 128               # Must be a power of 2    
        self.oceanLength = 128                 # Ocean length parameter
        self.oceanDepth = 30.0
        self.period = 10.0                    # Period of ocean surface anim
        # OpenGL Shader
        self.oceanShader = ShaderProgram.open('shaders/ocean.shader')
        self.oceanFloorShader = ShaderProgram.open('shaders/ocean_caustics.shader')
        self.refractionShader = ShaderProgram.open('shaders/photon_texture.shader')
        # Textures
        self.oceanFloorTexture = pyglet.image.load('images/sand.png').get_texture() 
        self.causticMapTexture = pyglet.image.load('images/lightmap.png').get_texture() 
        # Ocean Surface Renderable
        self.oceanSurface = OceanSurface(
                            self.oceanShader,
                            self.camera,
                            self.oceanTileSize, 
                            1.0, 
                            Vector3(0.0,self.oceanDepth,0.0),
                            self.oceanWind,
                            self.oceanWaveHeight,
                            self.period) 
        # Ocean Floor Renderable
        self.oceanFloor = OceanFloor(
                            self.oceanFloorShader,
                            self.refractionShader,
                            self.camera,
                            self.oceanFloorTexture,
                            self.causticMapTexture,
                            self.oceanSurface,
                            self.oceanDepth,
                            self.oceanTileSize, 
                            1.0, 
                            Vector3(0.0,0.0,0.0))             

                            
    def statusUpdates(self, dt):
        """
        Called periodically by main loop for onscreen text updates
        """
        self.status.setParameter('Wind', self.oceanWind)
        self.status.setParameter('Wave height', self.oceanWaveHeight)
        self.status.setParameter('Ocean depth', self.oceanDepth)
        self.status.setParameter('Time', self.oceanSurface.time)
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
        self.oceanShader = ShaderProgram.open('shaders/waves.shader')
        self.oceanFloorShader = ShaderProgram.open('shaders/ocean_caustics.shader')
    def draw(self, dt):
        """ Alternative draw loop"""
        
        # Update camera orientation and position
        self.cameraUpdate(dt)
        
        if self.isKeyPressed(key.C):
            self.oceanDepth += 1
            self.oceanSurface.setDepth(self.oceanDepth)
            self.oceanFloor.setDepth(self.oceanDepth)
        elif self.isKeyPressed(key.V):
            self.oceanDepth -= 1
            self.oceanSurface.setDepth(self.oceanDepth)
            self.oceanFloor.setDepth(self.oceanDepth)
        
        # Draw ocean surface and floor
        
        glUseProgram(self.oceanShader.id)  
        
        if self.wireframe:
            glPolygonMode(GL_FRONT, GL_LINE)
        else:
            glPolygonMode(GL_FRONT, GL_FILL)
        
        if self.drawSurface:
            if self.enableUpdates:
                self.oceanSurface.draw(dt, self.oceanTilesX, self.oceanTilesZ)
            else:
                self.oceanSurface.draw(0.0, self.oceanTilesX, self.oceanTilesZ)
        else:
            if self.enableUpdates:
                # Update the surface pattern but dont draw
                self.oceanSurface.updateHeightfield(dt)
            
        glUseProgram(self.oceanFloorShader.id)
        
        if self.drawFloor:
            self.oceanFloor.draw(dt, self.oceanTilesX, self.oceanTilesZ)
            
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
            
        if symbol == key.Z:
            self.drawSurface = not self.drawSurface
        if symbol == key.X:
            self.drawFloor = not self.drawFloor
            
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
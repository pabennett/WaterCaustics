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
from vector import Vector2

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
    
class Ocean():
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
               

        """ 
        ------------------------------------------------------------------------
        Member Variables
        ------------------------------------------------------------------------
        """  
        # OpenGL structures      
        # Vertex arrays are 3-dimensional have have the following structure:
        # [[[v0x,v0y,v0z,n0x,n0y,n0z],[v1x,v1y,v1z,n1x,n1y,n1z]],
        #  [[v2x,v2y,v2z,n2x,n2y,n2z],[v3x,v3y,v3z,n3x,n3y,n3z]],
        #  [[v4x,v4y,v4z,n4x,n4y,n4z],[v5x,v5y,v5z,n5x,n5y,n5z]]]
        self.verts = np3DArray(0.0, 6, self.N1, self.N1, GLfloat)
        self.v0 = np3DArray(0.0, 6, self.N1, self.N1, GLfloat)
        # Indicies are grouped per quad (6 indices for each quad)
        # The wave mesh is composed of NxN quads
        self.indices = np3DArray(0,6,self.N,self.N,dtype='u4')
        
        # Initialise the ocean surface mesh
        self.build2DMesh()
        
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
                
    def build2DMesh(self):
        """
        Generate the vertex and index arrays necessary to draw a wave surface
        mesh of size N by N
        An additional row and column are introduced in order to be able to stitch
        ocean 'tiles' together seamlessly, so the final mesh dimensions are
        N+1*N+1
        """
        
        # Populate the index array
        for i in range(self.N):
            for j in range(self.N):
                idx = i * self.N1 + j
                self.indices[i][j][0] = idx
                self.indices[i][j][1] = idx + self.N1
                self.indices[i][j][2] = idx + 1
                self.indices[i][j][3] = idx + 1
                self.indices[i][j][4] = idx + self.N1
                self.indices[i][j][5] = idx + self.N1 + 1
                
        # Populate the initial positions and normals
        for mPrime in range(self.N+1):
            for nPrime in range(self.N+1):
                # Position X
                self.verts[mPrime][nPrime][0] = (nPrime - self.N / 2.0) * \
                                                self.length / float(self.N)
                # Position Y                        
                self.verts[mPrime][nPrime][1] = 0.0
                # Position Z
                self.verts[mPrime][nPrime][2] = (mPrime - self.N / 2.0) * \
                                                self.length / float(self.N) 
                # # Normal X
                self.verts[mPrime][nPrime][3] = 0.0
                # # Normal Y                        
                self.verts[mPrime][nPrime][4] = 1.0
                # # Normal Z
                self.verts[mPrime][nPrime][5] = 0.0 
                
        # Keep a copy of the initial positions (future positions are generated
        # by applying displacements to these initial positions)
        self.v0 = self.verts.copy()

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
         
    def updateVerts(self):
        """ 
        ------------------------------------------------------------------------
        Update Vertices
        ------------------------------------------------------------------------
        """
        
        # Update Normals
        self.hTildeSlopeX[::2,::2] = -self.hTildeSlopeX[::2,::2]
        self.hTildeSlopeZ[::2,::2] = -self.hTildeSlopeZ[::2,::2]
        self.hTildeSlopeX[1::2,1::2] = -self.hTildeSlopeX[1::2,1::2]
        self.hTildeSlopeZ[1::2,1::2] = -self.hTildeSlopeZ[1::2,1::2]
                                  
        self.verts[:self.N:,:self.N:,3] = -self.hTildeSlopeX
        self.verts[:self.N:,:self.N:,4] = 1.0
        self.verts[:self.N:,:self.N:,5] = -self.hTildeSlopeZ
        
        # Update Displacements
        self.hTilde[::2,::2] = -self.hTilde[::2,::2]
        self.hTildeDx[::2,::2] = -self.hTildeDx[::2,::2]
        self.hTildeDz[::2,::2] = -self.hTildeDz[::2,::2]
          
        self.hTilde[1::2,1::2] = -self.hTilde[1::2,1::2]
        self.hTildeDx[1::2,1::2] = -self.hTildeDx[1::2,1::2]
        self.hTildeDz[1::2,1::2] = -self.hTildeDz[1::2,1::2]
                   
        #Update the vertex list for all elements apart from max indices
        #Vertex X (Displacement)
        self.verts[:self.N:,:self.N:,0] = self.v0[:self.N:,:self.N:,0] + self.hTildeDx * -1
        # Vertex Y
        self.verts[:self.N:,:self.N:,1] = self.hTilde
        # Vertex Z (Displacement)
        self.verts[:self.N:,:self.N:,2] = self.v0[:self.N:,:self.N:,2]  + self.hTildeDz * -1
        
        # # Allow seamless tiling:

        # Top index of vertices - reference bottom index of displacement array
        # vertices(N,N) = original(N,N) + hTilde(0,0) * - 1
        # Vertex X  
        self.verts[self.N,self.N,0] = self.v0[self.N,self.N,0] + \
                                      self.hTildeDx[0,0] * -1
        # Vertex Y                           
        self.verts[self.N,self.N,1] = self.hTilde[0,0]
        # Vertex Z
        self.verts[self.N,self.N,2] = self.v0[self.N,self.N,2] + \
                                      self.hTildeDz[0,0] * -1
                                      
        self.verts[self.N,self.N,3] = -self.hTildeSlopeX[0,0]
        self.verts[self.N,self.N,4] = 1.0
        self.verts[self.N,self.N,5] = -self.hTildeSlopeZ[0,0]
        
        # Last row of vertices - Reference first row of the displacement array
        # vertices(N,[0..N]) = original(N,[0..N]) + hTilde(0,[0..N]) * -1
        # Vertex X  
        self.verts[self.N,0:self.N:,0] = self.v0[self.N,0:self.N:,0] + \
                                         self.hTildeDx[0,0:self.N:] * -1
        # Vertex Y                            
        self.verts[self.N,0:self.N:,1] = self.hTilde[0,0:self.N:]
        # Vertex Z
        self.verts[self.N,0:self.N:,2] = self.v0[self.N,0:self.N:,2] + \
                                         self.hTildeDz[0,0:self.N:] * -1
                                         
        self.verts[self.N,0:self.N:,3] = -self.hTildeSlopeX[0,0:self.N:]
        self.verts[self.N,0:self.N:,4] = 1.0
        self.verts[self.N,0:self.N:,5] = -self.hTildeSlopeZ[0,0:self.N:]
        
        # Last col of vertices - Reference first col of the displacement array
        # vertices([0..N],N) = original([0..N],N) + hTilde([0..N],0) * -1
        # Vertex X  
        self.verts[0:self.N:,self.N,0] = self.v0[0:self.N:,self.N,0] + \
                                         self.hTildeDx[0:self.N:,0] * -1
        # Vertex Y    
        self.verts[0:self.N:,self.N,1] = self.hTilde[0:self.N:,0]
        # Vertex Z
        self.verts[0:self.N:,self.N,2] = self.v0[0:self.N:,self.N,2] + \
                                         self.hTildeDz[0:self.N:,0] * -1
                                         
        self.verts[0:self.N:,self.N,3] = -self.hTildeSlopeX[0:self.N:,0]
        self.verts[0:self.N:,self.N,4] = 1.0
        self.verts[0:self.N:,self.N,5] = -self.hTildeSlopeZ[0:self.N:,0]
        
    def evaluateWavesFFT(self, t):
        self.genHTilde(t)
        self.doFFT()
        self.updateVerts()

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
        
        self.status = statusConsole
        
        self.status.addParameter('Wind')      
        self.status.addParameter('Wave height')

        # Animation Timer
        self.time = 0.0
        
        # Ocean Parameters
        self.oceanWindX = 32.0                # Ocean wind in X axis
        self.oceanWindZ = 32.0                # Ocean wind in Z axis
        self.oceanWaveHeight = 0.0005         # The phillips spectrum parameter
        self.oceanTileSize = 64               # Must be a power of 2    
        self.oceanLength = 64                 # Ocean length parameter
        # Ocean Render Parameters
        self.oceanTilesX = 10
        self.oceanTilesZ = 10
        self.wireframe = False
        
        # Ocean Surface Generator
        self.generator = Ocean( self.oceanTileSize,
                                self.oceanWaveHeight, 
                                Vector2(self.oceanWindX,self.oceanWindZ),
                                self.oceanLength)
                  
        self.enableUpdates = False
        
        
        self.mMainShader = ShaderProgram.open('shaders/waves.shader')
        
        # Shader handles (main shader)
        # Attributes
        self.positionHandle = glGetAttribLocation(self.mMainShader.id, "vPosition")
        self.normalHandle = glGetAttribLocation(self.mMainShader.id, "vNormal")
        self.texCoordHandle = glGetAttribLocation(self.mMainShader.id, "vTexCoord")
        # Uniforms
        self.offsetHandle = glGetUniformLocation(self.mMainShader.id, "offset")
        self.mMVPHandle = glGetUniformLocation(self.mMainShader.id, "MVP")
        self.mViewHandle = glGetUniformLocation(self.mMainShader.id, "view")
        self.mModelHandle = glGetUniformLocation(self.mMainShader.id, "model")
        self.mTextureUniformHandle = glGetUniformLocation(self.mMainShader.id, "texture")
        
        
        # Vertex Array Object for Position and Normal VBOs
        self.oceanVAO = GLuint()
        glGenVertexArrays(1,pointer(self.oceanVAO))
        glBindVertexArray(self.oceanVAO)
        
        # Vertex Buffer Objects (Positions Normals and Indices)
        self.vertVBO = GLuint()
        self.idxVBO = GLuint()
        glGenBuffers(1, pointer(self.vertVBO))
        glGenBuffers(1, pointer(self.idxVBO))
                
        self.indices = np.ctypeslib.as_ctypes(self.generator.indices)
        self.verts = np.ctypeslib.as_ctypes(self.generator.verts)
        
        self.vertexCount = self.generator.indices.size
        self.vertexSize = sizeof(GLfloat) * 6
        self.offsetNormals = sizeof(GLfloat) * 3
        
        # Set up vertices VBO (associated with oceanVAO)
        glBindBuffer(GL_ARRAY_BUFFER, self.vertVBO)      
        glBufferData(GL_ARRAY_BUFFER, sizeof(self.verts), self.verts, GL_STATIC_DRAW)
        # Positions
        glEnableVertexAttribArray(self.positionHandle) 
        glVertexAttribPointer(self.positionHandle, 3, GL_FLOAT, GL_FALSE, self.vertexSize, 0)
        # Normals
        glEnableVertexAttribArray(self.normalHandle) 
        glVertexAttribPointer(self.normalHandle, 3, GL_FLOAT, GL_FALSE, self.vertexSize, self.offsetNormals)
        
        # Set up indices VBO (associated with oceanVAO)
        # Indices
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.idxVBO)      
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, sizeof(self.indices), self.indices, GL_STATIC_DRAW)

        glBindVertexArray(0)
                                
        # Set up vertices
    def statusUpdates(self, dt):
        """
        Called periodically by main loop for onscreen text updates
        """
        wind = (self.oceanWindX,self.oceanWindZ)
        self.status.setParameter('Wind', wind)
        self.status.setParameter('Wave height', self.oceanWaveHeight)
    
    def resetOcean(self):
        """
        Recreate the ocean generator with new parameters
        """
        del self.generator
        
        self.generator = Ocean( self.oceanTileSize,
                                self.oceanWaveHeight, 
                                Vector2(self.oceanWindX,self.oceanWindZ),
                                self.oceanLength)

    def updateWave(self):
        # Time=0 Wavemap generation
        self.generator.evaluateWavesFFT(self.time)        
        # Positions
        glBindBuffer(GL_ARRAY_BUFFER, self.vertVBO)      
        # 4 Bytes per float
        glBufferData(GL_ARRAY_BUFFER, self.generator.verts.size*4, np.ctypeslib.as_ctypes(self.generator.verts), GL_STATIC_DRAW)
        
    def loadShaders(self):
        """ 
        Load the shaders
        Allow hotloading of shaders while the program is running
        """
        self.mMainShader = ShaderProgram.open('shaders/waves.shader')
    def render(self, dt):
        """ Alternative draw loop"""
        
        self.time += dt
        
        self.cameraUpdate(dt)
        
        if self.enableUpdates:
            self.updateWave()
        # Camera control

        
        glUseProgram(self.mMainShader.id)             
        glUniformMatrix4fv(self.mMVPHandle, 1, False, self.camera.getMVP()) 
        
        if self.wireframe:
            glPolygonMode(GL_FRONT, GL_LINE)
        else:
            glPolygonMode(GL_FRONT, GL_FILL)

            
        glBindVertexArray(self.oceanVAO)
        
        for i in range(self.oceanTilesX):
            for j in range(self.oceanTilesZ):
                glUniform2fv(self.offsetHandle, 1, (GLfloat*2)(self.oceanLength * i, self.oceanLength * -j)) 
                glDrawElements(GL_TRIANGLES, self.vertexCount, GL_UNSIGNED_INT, 0)
                
        glBindVertexArray(0)
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
            self.oceanWindX *= 2.0
            self.resetOcean()
        if symbol == key.NUM_2:
            self.oceanWindX /= 2.0
            self.resetOcean()
        if symbol == key.NUM_4:
            self.oceanWindZ *= 2.0
            self.resetOcean()
        if symbol == key.NUM_5:
            self.oceanWindZ /= 2.0
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
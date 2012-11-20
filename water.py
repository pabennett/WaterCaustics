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

def np3DArray(initialiser, points, rows, columns, dtype=np.float64):
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
        # [[[v0x,v0y,v0z],[v1x,v1y,v1z],[v2x,v2y,v2z]],
        #  [[v3x,v3y,v3z],[v5x,v5y,v5z],[v5x,v5y,v5z]],
        #  [[v6x,v6y,v6z],[v7x,v7y,v7z],[v8x,v8y,v8z]]]
        
        # When flattened, you get a packed vertex array: v0x,v0y,v0z,v1x,v1y....
        self.verts = np3DArray(0.0, 3, self.N+1, self.N+1, GLfloat)
        self.v0 = np3DArray(0.0, 3, self.N+1, self.N+1, GLfloat)
        self.indices = np.array(range(self.N1Sq*6),dtype=GLuint)
        
        # Wave surface arrays
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
                             
        # Generate initial vertex positions (N+1*N+1)
        for mPrime in range(self.N+1):
            for nPrime in range(self.N+1):
                # Vertex X
                self.verts[mPrime][nPrime][0] = (nPrime - self.N / 2.0) * \
                                                self.length / float(self.N)
                # Vertex Y                        
                self.verts[mPrime][nPrime][1] = 0.0
                # Vertex Z
                self.verts[mPrime][nPrime][2] = (mPrime - self.N / 2.0) * \
                                                self.length / float(self.N) 
                
                # Vertex X
                self.v0[mPrime][nPrime][0] = (nPrime - self.N / 2.0) * \
                                             self.length / float(self.N)
                # Vertex Y                     
                self.v0[mPrime][nPrime][1] = 0.0
                # Vertex Z
                self.v0[mPrime][nPrime][2] = (mPrime - self.N / 2.0) * \
                                             self.length / float(self.N) 
                                             
        # Build Lookup Tables and vertex indices list (N*N)        
        for mPrime in range(self.N):
            # Build k LUT for wave evaluation loop
            kz = pi * (2.0 * mPrime - self.N) / self.length
            for nPrime in range(self.N):
                kx = pi * (2.0 * nPrime - self.N) / self.length
                self.kxLUT[mPrime][nPrime] = kx
                self.kzLUT[mPrime][nPrime] = kz
                # Generate HTilde initial values
                self.hTilde0[mPrime][nPrime] = self.getHTilde0(nPrime, mPrime)
                self.hTilde0mk[mPrime][nPrime] = self.getHTilde0(-nPrime, mPrime)
            
                # Generate Indices for drawing triangles
                index = mPrime * (self.N + 1) + nPrime
                self.indices[index*6] = index
                self.indices[index*6+1] = index + self.N + 1
                self.indices[index*6+2] = index + self.N + 2
                self.indices[index*6+3] = index
                self.indices[index*6+4] = index + self.N + 2
                self.indices[index*6+5] = index + 1
                
                # Build a dispersion LUT
                self.dispersionLUT[mPrime][nPrime] = self.dispersion(nPrime, mPrime) 
                
                # Build a length LUT
                self.lenLUT[mPrime][nPrime] = sqrt(kx * kx + kz * kz)
                     
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
        
        self.hTilde[::2,::2] = -self.hTilde[::2,::2]
        self.hTildeDx[::2,::2] = -self.hTildeDx[::2,::2]
        self.hTildeDz[::2,::2] = -self.hTildeDz[::2,::2]
          
        self.hTilde[1::2,1::2] = -self.hTilde[1::2,1::2]
        self.hTildeDx[1::2,1::2] = -self.hTildeDx[1::2,1::2]
        self.hTildeDz[1::2,1::2] = -self.hTildeDz[1::2,1::2]
           
        #Update the vertex list for all elements in nonzero indices.
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

        # Texture size
        self.width = 32
        self.height = 32
        
        self.length = 64.0
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
        
        # Vertex Buffer Objects
        self.vboVerts = GLuint()
        self.vboIndices = GLuint()
        glGenBuffers(1, pointer(self.vboVerts))
        glGenBuffers(1, pointer(self.vboIndices))
        
        self.indices = np.ctypeslib.as_ctypes(self.generator.indices)
        
        # Vertices
        glBindBuffer(GL_ARRAY_BUFFER, self.vboVerts)      
        glBufferData(GL_ARRAY_BUFFER, self.generator.verts.size*4, np.ctypeslib.as_ctypes(self.generator.verts), GL_STATIC_DRAW)

        
        # Indices
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.vboIndices)      
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, sizeof(self.indices), self.indices, GL_STATIC_DRAW)
        
        # Texture creation
        self.image = image.create(self.width, self.height)
        self.mTextureHandle = image.DepthTexture.create_for_size(GL_TEXTURE_2D, 
                                                        self.width, 
                                                        self.height,
                                                        GL_RGBA)
                                                        
        # Set up vertices
        self.COORDS_PER_VERTEX = 3
                                                        
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
        #self.indices = (GLuint * len(self.generator.indices))(*self.generator.indices)
        
        # Vertices
        glBindBuffer(GL_ARRAY_BUFFER, self.vboVerts)      
        # 4 Bytes per float
        glBufferData(GL_ARRAY_BUFFER, self.generator.verts.size*4, np.ctypeslib.as_ctypes(self.generator.verts), GL_STATIC_DRAW)
        # Indices
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.vboIndices)  
        # 4 Bytes per uint
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, sizeof(self.indices), self.indices, GL_STATIC_DRAW)
        
    def loadShaders(self):
        """ 
        Load the shaders
        Allow hotloading of shaders while the program is running
        """
        self.mMainShader = ShaderProgram.open('shaders/waves.shader')
    def render(self, dt):
        """ Alternative draw loop"""
        
        self.time += dt
        
        if self.enableUpdates:
            self.updateWave()
        # Camera control
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
        
        glUseProgram(self.mMainShader.id)             
        glUniformMatrix4fv(self.mMVPHandle, 1, False, self.camera.getMVP()) 
        
        if self.wireframe:
            glPolygonMode(GL_FRONT, GL_LINE)
        else:
            glPolygonMode(GL_FRONT, GL_FILL)

        glBindBuffer(GL_ARRAY_BUFFER, self.vboVerts)
        glEnableVertexAttribArray(self.positionHandle)          
        glVertexAttribPointer(self.positionHandle, 3, GL_FLOAT, GL_FALSE, 0, 0)
        
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.vboIndices)
        
        for i in range(self.oceanTilesX):
            for j in range(self.oceanTilesZ):
                glUniform2fv(self.offsetHandle, 1, (GLfloat*2)(self.length * i, self.length * -j)) 
                glDrawElements(GL_TRIANGLES, len(self.indices), GL_UNSIGNED_INT, 0)
        
        glDisableVertexAttribArray(self.positionHandle)
        glPolygonMode(GL_FRONT, GL_FILL)
        glBindBuffer(GL_ARRAY_BUFFER, 0)  
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)  
        glUseProgram(0)

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
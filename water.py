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
         
def npArray(initialiser, rows, columns):
    """ Utility Function for generating numpy arrays """
    return np.array([[initialiser for i in range(columns)] for j in range(rows)])        

def np3Array(initialiser, points, rows, columns):
    """ Utility Function for generating numpy array of vertices """
    return np.array([[[initialiser for i in range(points)] for j in range(columns)] for k in range(rows)])    
    
class Ocean():
    def __init__(self, dimension=64, A=0.0005,w=Vector2(32.0, 32.0),length=64.0):
        """ 
        Dimension should be a power of 2
        """
        self.N = dimension              # Dimension - should be power of 2
        self.length = float(length)     # Length Parameter
        self.w = w                      # Wind Parameter
        self.a = A                      # Phillips spectrum parameter
                                        # affects heights of waves
                                           
        self.w0 = 2.0 * pi / 200.0      # Used by the dispersion function
        self.g = 9.81                   # Constant acceleration due to gravity
                       
        # OpenGL structures            
        self.vertices  = [0.0,0.0,0.0]*(self.N+1)**2
        self.verticeso = [0.0,0.0,0.0]*(self.N+1)**2
        
        self.NPvertices = np3Array(0.0, 3, self.N+1, self.N+1)
        self.NPverticesOrig = np3Array(0.0, 3, self.N+1, self.N+1)
        
        
        self.indices = []
        
        # Wave surface arrays
        self.hTilde0 = npArray(0.0+0j,self.N, self.N)
        self.hTilde0mk = npArray(0.0+0j,self.N, self.N)
        self.hTilde = npArray(0.0+0j,self.N, self.N)
        self.hTildeSlopeX = npArray(0.0+0j,self.N, self.N)
        self.hTildeSlopeZ = npArray(0.0+0j,self.N, self.N)
        self.hTildeDx = npArray(0.0+0j,self.N, self.N)
        self.hTildeDz = npArray(0.0+0j,self.N, self.N)
        
        # Lookup tables for code optimisation
        self.dispersionLUT = npArray(0.0, self.N, self.N)
        self.kLUTX = npArray(0.0, self.N, self.N)
        self.kLUTZ = npArray(0.0, self.N, self.N)
        self.lenLUT = npArray(0.0, self.N, self.N) 
        
        
        self.NPvertices
        
        
        for mPrime in range(self.N+1):
            for nPrime in range(self.N+1):
                index = mPrime * (self.N + 1) + nPrime

                
                self.vertices[index*3] = (nPrime - self.N / 2.0) * self.length / float(self.N)
                self.vertices[index*3+1] = 0.0
                self.vertices[index*3+2] = (mPrime - self.N / 2.0) * self.length / float(self.N) 
                
                self.NPvertices[mPrime][nPrime][0] = (nPrime - self.N / 2.0) * self.length / float(self.N)
                self.NPvertices[mPrime][nPrime][1] = 0.0
                self.NPvertices[mPrime][nPrime][2] = (mPrime - self.N / 2.0) * self.length / float(self.N) 
                
                self.NPverticesOrig[mPrime][nPrime][0] = (nPrime - self.N / 2.0) * self.length / float(self.N)
                self.NPverticesOrig[mPrime][nPrime][1] = 0.0
                self.NPverticesOrig[mPrime][nPrime][2] = (mPrime - self.N / 2.0) * self.length / float(self.N) 
                
                self.verticeso[index*3] = (nPrime - self.N / 2.0) * self.length / float(self.N)
                self.verticeso[index*3+1] = 0.0
                self.verticeso[index*3+2] = (mPrime - self.N / 2.0) * self.length / float(self.N)

        for mPrime in range(self.N):
            # Build k LUT for wave evaluation loop
            kz = pi * (2.0 * mPrime - self.N) / self.length
            for nPrime in range(self.N):
                kx = pi * (2.0 * nPrime - self.N) / self.length
                self.kLUTX[mPrime][nPrime] = kx
                self.kLUTZ[mPrime][nPrime] = kz
                # Generate HTilde initial values
                self.hTilde0[mPrime][nPrime] = self.getHTilde0(nPrime, mPrime)
                self.hTilde0mk[mPrime][nPrime] = self.getHTilde0(-nPrime, mPrime)
            
                # Generate Indices for drawing triangles
                index = mPrime * (self.N + 1) + nPrime
                self.indices.append(index)
                self.indices.append(index + self.N + 1)
                self.indices.append(index + self.N + 2)
                self.indices.append(index)
                self.indices.append(index + self.N + 2)
                self.indices.append(index + 1)
                
                # Build a dispersion LUT
                self.dispersionLUT[mPrime][nPrime] = self.dispersion(nPrime, mPrime) 
                
                # Build a length LUT
                kx = pi * (2 * nPrime - self.N) / self.length
                self.lenLUT[mPrime][nPrime] = sqrt(kx * kx + kz * kz)
                
        self.heightmap = np.zeros((self.N * self.N, 4), dtype="u1") #RGBA bytes
                
    def dbg_phillipsArray(self):
        """
        Return a 2D numpy array for display purposes
        """
        temp = []
        spectrum = zeros((self.N, self.N))
        pmax = 0
        for m in range(self.N):
            for n in range(self.N):
                p = self.phillips(n,m)
                if p > pmax:
                  pmax = p
                temp.append(p)
                spectrum[m][n] = p

        phillipsFreq = abs(fft.ifft2(spectrum))
        phillipsFreq = abs(log(phillipsFreq))
        
        # Scaling stuff for display
        mx = phillipsFreq.max()
        mn = phillipsFreq.min()
        phillipsFreq = ((phillipsFreq-mn)/mx) * 255
                        
        spectrum = zeros((self.N * self.N, 4), dtype="u1") #RGBA bytes
        
        for m in range(self.N):
            for n in range(self.N/2): 
                p = phillipsFreq[m][n]
                spectrum[m * self.N + n] = [p,p,p,255]
                # Mirrored half
                spectrum[m * self.N + self.N - 1 - n] = [p,p,p,255]
        
        return spectrum
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
   
        omegat = self.dispersionLUT[nPrime][mPrime] * t
        
        cos_ = cos(omegat)
        sin_ = sin(omegat)
        c0 = cos_ + (sin_ * 1j)
        c1 = cos_ + (-sin_ * 1j)
        
        
        return self.hTilde0[mPrime][nPrime] * c0 + self.hTilde0mk[mPrime][nPrime] * c1
          
    def genHTildeArray(self, t):
        """ 
        Use vectorised operations on np arrays to generate hTilde efficiently
        """

        omegat = self.dispersionLUT * t
        
        sin_ = np.sin(omegat)
        cos_ = np.cos(omegat)
        
        c0 = cos_ + (sin_ * 1j)
        c1 = cos_ + (-sin_ * 1j)
    
        self.hTilde = self.hTilde0 * c0 + self.hTilde0mk * c1 
        
    def evaluateWavesFFT(self, t):
    
        """ 
        ------------------------------------------------------------------------
        Generate hTilde for time t 
        ------------------------------------------------------------------------
        """
        
        # Update the hTilde values
        self.genHTildeArray(t)
        
        # Generate normals for X and Z
        self.hTildeSlopeX = self.hTilde * self.kLUTX * 1j
        self.hTildeSlopeZ = self.hTilde * self.kLUTZ * 1j
        
        # Generate a set of indices for which the length in the length 
        # look-up table is less than 0.000001
        zeros = self.lenLUT < 0.000001
        nonzeros = self.lenLUT >= 0.000001
        
        # If the length contained in the length look-up table (lenLUT) is 
        # greater than 0.000001 set the displacements in x and z to:
        # Dx = hTilde * complex(0.0,-kx/length)
        # Dz = hTilde * complex(0.0,-kz/length)
        # Otherwise, set the displacements to 0.0+0j
        self.hTildeDx = self.hTilde * 1j * -self.kLUTX / self.lenLUT
        self.hTildeDz = self.hTilde * 1j * -self.kLUTZ / self.lenLUT
        self.hTildeDx[zeros] = 0.0+0j
        self.hTildeDz[zeros] = 0.0+0j

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
         
        """ Update Vertices """
        
        self.hTilde[::2,::2] = -self.hTilde[::2,::2]
        self.hTildeDx[::2,::2] = -self.hTildeDx[::2,::2]
        self.hTildeDz[::2,::2] = -self.hTildeDz[::2,::2]
          
        self.hTilde[1::2,1::2] = -self.hTilde[1::2,1::2]
        self.hTildeDx[1::2,1::2] = -self.hTildeDx[1::2,1::2]
        self.hTildeDz[1::2,1::2] = -self.hTildeDz[1::2,1::2]
           
        # Update the vertex list for all elements in nonzero indices.
        # Vertex X (Displacement)
        self.NPvertices[1::,1::,0] = self.NPverticesOrig[1::,1::,0]  + self.hTildeDx * -1
        # Vertex Y
        self.NPvertices[1::,1::,1] = self.hTilde
        # Vertex Z (Displacement)
        self.NPvertices[1::,1::,2] = self.NPverticesOrig[1::,1::,2]  + self.hTildeDz * -1
        
        #self.vertices = self.NPvertices.flatten().tolist()
                   
        for mPrime in range(self.N):
            for nPrime in range(self.N):
                index = mPrime * (self.N + 1) + nPrime
                self.vertices[index*3] = self.verticeso[index*3] + (self.hTildeDx[mPrime][nPrime]) * -1
                self.vertices[index*3+1] = (self.hTilde[mPrime][nPrime])
                self.vertices[index*3+2] = self.verticeso[index*3+2] + (self.hTildeDz[mPrime][nPrime]) * -1
                # Allow seamless tiling
                if nPrime == 0 and mPrime == 0:
                    i = index + self.N + ((self.N+1)*self.N)
                    (ix,iy,iz) = (i*3,i*3+1,i*3+2)
                    self.vertices[iy] = (self.hTilde[mPrime][nPrime])
                    self.vertices[ix] = self.verticeso[ix] + (self.hTildeDx[mPrime][nPrime]) * -1
                    self.vertices[iz] = self.verticeso[iz] + (self.hTildeDz[mPrime][nPrime]) * -1
                if mPrime == 0:
                    i = index + (self.N + 1) * self.N
                    (ix,iy,iz) = (i*3,i*3+1,i*3+2)
                    self.vertices[iy] = (self.hTilde[mPrime][nPrime])
                    self.vertices[ix] = self.verticeso[ix] + (self.hTildeDx[mPrime][nPrime]) * -1
                    self.vertices[iz] = self.verticeso[iz] + (self.hTildeDz[mPrime][nPrime]) * -1
                if nPrime == 0:
                    i = index + self.N
                    (ix,iy,iz) = (i*3,i*3+1,i*3+2)
                    self.vertices[iy] = (self.hTilde[mPrime][nPrime])
                    self.vertices[ix] = self.verticeso[ix] + (self.hTildeDx[mPrime][nPrime]) * -1
                    self.vertices[iz] = self.verticeso[iz] + (self.hTildeDz[mPrime][nPrime]) * -1

   
class oceanRenderer():
    def __init__(self, window, camera):
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
        
        # Texture size
        self.width = 64
        self.height = 64
        
        self.length = 64.0
        self.time = 0.0
        
        # Ocean Surface Generator
        self.generator = Ocean(self.width, 0.0005, Vector2(32.0,32.0),self.length)
        self.updateCounter = 0
        
        self.enableUpdates = False
        
        # Vertex Buffer Objects
        self.vboVerts = GLuint()
        self.vboIndices = GLuint()
        glGenBuffers(1, pointer(self.vboVerts))
        glGenBuffers(1, pointer(self.vboIndices))
        
        self.vertices = (GLfloat * len(self.generator.vertices))(*self.generator.vertices)
        self.indices = (GLuint * len(self.generator.indices))(*self.generator.indices)
        
        # Vertices
        glBindBuffer(GL_ARRAY_BUFFER, self.vboVerts)      
        glBufferData(GL_ARRAY_BUFFER, sizeof(self.vertices), self.vertices, GL_STATIC_DRAW)
        
        # Indices
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.vboIndices)      
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, sizeof(self.indices), self.indices, GL_STATIC_DRAW);
        
        # Texture creation
        self.image = image.create(self.width, self.height)
        self.mTextureHandle = image.DepthTexture.create_for_size(GL_TEXTURE_2D, 
                                                        self.width, 
                                                        self.height,
                                                        GL_RGBA)
                                                        
               
        # Set up vertices
        self.COORDS_PER_VERTEX = 3
        self.COORDS_PER_TEXTURE = 2
                           
        self.mFullScreenQuad = (GLfloat * 24)(
            1.0,    -1.0,   0.0,
            1.0,    1.0,    0.0,
            -1.0,   1.0,    0.0,
            -1.0,   -1.0,   0.0,
            1.0,    -1.0,   0.0,
            1.0,    1.0,    0.0,
            -1.0,   1.0,    0.0,
            -1.0,   -1.0,   0.0)
            
        self.mGndIndices = (GLshort * 12)(
            0,  1,  2,
            2,  3,  0,
            4,  6,  5,
            6,  4,  7)
        
        self.mTexCoords = (GLfloat * 16)(
            1.0,    0.0,
            1.0,    1.0,
            0.0,    1.0,
            0.0,    0.0,
            1.0,    0.0,
            1.0,    1.0,
            0.0,    1.0,
            0.0,    0.0)
            
        self.ii = 0
                 
        self.mMainShader = ShaderProgram.open('shaders/passthru_jet.shader')
        
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

        
    def updateWave(self):
        # Time=0 Wavemap generation
        self.generator.evaluateWavesFFT(self.time)
        self.vertices = (GLfloat * len(self.generator.vertices))(*self.generator.vertices)
        self.indices = (GLuint * len(self.generator.indices))(*self.generator.indices)
        
        # Vertices
        glBindBuffer(GL_ARRAY_BUFFER, self.vboVerts)      
        glBufferData(GL_ARRAY_BUFFER, sizeof(self.vertices), self.vertices, GL_STATIC_DRAW)
        
        # Indices
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.vboIndices)      
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, sizeof(self.indices), self.indices, GL_STATIC_DRAW);
        
    def loadShaders(self):
        """ 
        Load the shaders
        Allow hotloading of shaders while the program is running
        """
        self.mMainShader = ShaderProgram.open('shaders/passthru_jet.shader')
    def createImage(self):

        data = self.generator.evaluateWavesFFT(self.time)
                                
        # set the GB (from RGBA) to 0
        data[ :, 1:-1 ] = 0
        
        # ensure alpha is 255
        data[ :, 3 ] = 255

        # we need to flatten the array
        data.shape = -1
                
        tex_data = (GLubyte * data.size)(*data.astype('u1'))
                
        im = image.ImageData(   self.width,
                                self.height,
                                "RGBA",
                                tex_data,
                                pitch = self.height * 4
                            )
        return im.get_texture()
        
    def triangles_v3f(self,scale):
        if scale < 1.0:
            return []
        else:
            data = self.triangles_v3f(scale / 2.0)
            data.extend([
                100 + scale, 100,           -0.1,
                100 + scale, 100 + scale,   -0.1,
                100,         100 + scale,   -0.1,
            ])
            return data
        
    def render(self, dt):
        """ Alternative draw loop"""
        
        self.time += dt
        
        #print self.time
        
        self.updateCounter += 1
        if self.enableUpdates and self.updateCounter >= 1:
            self.updateCounter = 0
            self.updateWave()
        # Camera control
        self.camera.update(dt)
        
        if self.isKeyPressed(key.W):
            self.camera.addVelocity(0.0, 0.0, 0.5)
        if self.isKeyPressed(key.S):
            self.camera.addVelocity(0.0, 0.0, -0.5)
        if self.isKeyPressed(key.A):
            self.camera.addVelocity(-0.5, 0.0, 0.0)
        if self.isKeyPressed(key.D):
            self.camera.addVelocity(0.5, 0.0, 0.0)
        if self.isKeyPressed(key.Q):
            self.camera.addAngularVelocity(0.0, 0.0, 2)
        if self.isKeyPressed(key.E):
            self.camera.addAngularVelocity(0.0, 0.0, -2)
        

        glUseProgram(self.mMainShader.id)             
        glUniformMatrix4fv(self.mMVPHandle, 1, False, self.camera.getMVP()) 
        
        #glPolygonMode(GL_FRONT, GL_LINE)

        glBindBuffer(GL_ARRAY_BUFFER, self.vboVerts)
        glEnableVertexAttribArray(self.positionHandle)          
        glVertexAttribPointer(self.positionHandle, 3, GL_FLOAT, GL_FALSE, 0, 0)

        #glDrawArrays(GL_TRIANGLES, 0, len(self.vertices)/3)
        
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.vboIndices)
        
        for i in range(10):
            for j in range(10):
                glUniform2fv(self.offsetHandle, 1, (GLfloat*2)(self.length * i, self.length * -j)) 
                glDrawElements(GL_TRIANGLES, len(self.indices), GL_UNSIGNED_INT, 0)
        
        glDisableVertexAttribArray(self.positionHandle)
        glBindBuffer(GL_ARRAY_BUFFER, 0)  
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)  
        glUseProgram(0)
               
    def draw(self, dt):          
        """ Main draw loop """
        
        if self.isKeyPressed(key.W):
            self.camera.addVelocity(0.0, 0.0, 0.1)
        if self.isKeyPressed(key.S):
            self.camera.addVelocity(0.0, 0.0, -0.1)
        if self.isKeyPressed(key.A):
            self.camera.addVelocity(-0.1, 0.0, 0.0)
        if self.isKeyPressed(key.D):
            self.camera.addVelocity(0.1, 0.0, 0.0)
        if self.isKeyPressed(key.Q):
            self.camera.addAngularVelocity(0.0, 0.0, 2)
        if self.isKeyPressed(key.E):
            self.camera.addAngularVelocity(0.0, 0.0, -2)
        
        
        self.mVertices = (GLfloat * len(self.generator.vertices))(*self.generator.vertices)
        
        self.time += 0.1

        glViewport(0, 0, self.width, self.height)
        # Clear screen
        glClear(GL_COLOR_BUFFER_BIT)
        # Use the caustics shader
        glUseProgram(self.mMainShader.id)
        
        glPolygonMode(GL_FRONT, GL_LINE)
        
        # Set texture register 0 as active
        glActiveTexture(GL_TEXTURE0)
        # Bind the texture as the input
        glBindTexture(GL_TEXTURE_2D, self.mTextureHandle.id)
        # Tell the texture uniform sampler to use this texture in the shader by 
        # binding to texture unit 0.
        glUniform1i(self.mTextureUniformHandle, 0)
        
        # Set up the vertex attributes                              
        glVertexAttribPointer(self.mTextureCoordinateHandle, 
                              2, 
                              GL_FLOAT, 
                              False, 
                              0, 
                              self.mTexCoords )
                              
        # Draw a full screen quad.
        glVertexAttribPointer(self.positionHandle, 
                              self.COORDS_PER_VERTEX, 
                              GL_FLOAT, 
                              False, 
                              12, 
                              self.mVertices )
                              
        # Camera control
        self.camera.update(dt)
        glUniformMatrix4fv(self.mMVPHandle, 1, False, self.camera.getMVP())
          
        # Enable vertex attribute arrays
        glEnableVertexAttribArray(self.positionHandle)
        glEnableVertexAttribArray(self.mTextureCoordinateHandle)
             
        frig = range(3)
        frig = (GLshort * len(frig))(*frig)
             
        # Draw triangles
        glDrawElements(GL_TRIANGLES, 
                       len(frig), 
                       GL_UNSIGNED_SHORT, 
                       frig)
             
        # Disable arrays
        glDisableVertexAttribArray(self.positionHandle)
        glDisableVertexAttribArray(self.mTextureCoordinateHandle)
        # Unbind shader
        glActiveTexture(GL_TEXTURE0) # Reset the active texture
        glUseProgram(0)
    def on_key_press(self, symbol, modifiers):
        """ Handle key press events"""
        
        # Set the pressedKeys dict to allow us to have while-key-pressed actions
        self.pressedKeys[symbol] = True
        
        if symbol == key.P:
            self.loadShaders()
        if symbol == key.SPACE:
            self.enableUpdates = not self.enableUpdates
            
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
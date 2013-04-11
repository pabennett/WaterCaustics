from utilities import *

from math import *
import numpy as np
from vector import Vector2, Vector3

from ctypes import pointer, sizeof
from gletools import ShaderProgram

class Tessendorf():
    def __init__(self, 
                 dimension=64, 
                 A=0.0005,
                 w=Vector2(32.0, 32.0),
                 length=64,
                 period=200.0):

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
        '''
        The phillips spectrum
        '''
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
        r = gaussianRandomVariable()
        return r * sqrt(self.phillips(nPrime, mPrime) / 2.0)
        
    def genHTildeArray(self, t):
        ''' 
        Generate array of wave height values for time t 
        '''
        omegat = self.dispersionLUT * t
        
        sin_ = np.sin(omegat)
        cos_ = np.cos(omegat)
        
        c0 = cos_ + (sin_ * 1j)
        c1 = cos_ + (-sin_ * 1j)
    
        self.hTilde = self.hTilde0 * c0 + self.hTilde0mk * c1 

    def genHTilde(self, t):
        ''' 
        Generate hTilde for time t 
        '''
        
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
        ''' 
        Compute FFT
        '''
                                
        # Heights
        self.hTilde = np.fft.fft2(self.hTilde)
        # Displacements
        self.hTildeDx = np.fft.fft2(self.hTildeDx)
        self.hTildeDz = np.fft.fft2(self.hTildeDz)
        # Normals
        self.hTildeSlopeX = np.fft.fft2(self.hTildeSlopeX)
        self.hTildeSlopeZ = np.fft.fft2(self.hTildeSlopeZ)
         
    def evaluateWavesFFT(self, t):
        self.genHTilde(t)
        self.doFFT()
         
    def update(self, time, verts, v0):
        '''
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
        '''
        
        # First, do a surface update
        self.evaluateWavesFFT(time)

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

        
class Ripples():
    '''
    Creates concentric ripples that bounce off the edge of the heightfield.
    
    This technique is based on the method covered here:
    http://freespace.virgin.net/hugo.elias/graphics/x_water.htm
    
    This heightfield generator makes use of the GPU to compute the ripples:
    
    FBO ping-pong buffers are required, three buffers are used in
    the following fashion:
    
    Buffer A,B = PingPong Buffers
    Buffer C = CurrentBuffer (Lets us read a snapshot of the current destination
                              buffer as it is written)
    
                               A = Cycle - 1         B = Cycle - 1     
                               C = Current           C = Current
                     
     B ----> Shader -+--> A --+-> Shader -+--> B --+-> Shader -+--> A  .. Repeat
                     |        |           |        |           |
                     +--> C --+           +--> C --+           +--> C
                          |                    |                    |
                          +-----> Display      +-----> Display      +--> Display
    
    The display texture is used to displace the heightfield vertices.
    '''
    
    def __init__(self, camera, dimension=64):
    
        self.N = dimension              # Dimension - should be power of 2
        self.camera = camera

        # Set up vertices for rendering a fullscreen quad
        self.vertices, self.indices, self.vertexSize = fullscreenQuad()
        
        # Vertex Buffer Objects (Positions Texcoords and Indices)
        self.vertVBO = GLuint()
        self.indexVBO = GLuint()
        glGenBuffers(1, pointer(self.vertVBO))
        glGenBuffers(1, pointer(self.indexVBO))       
        self.offsetTexcoords = sizeof(GLfloat) * 3
        
       
        self.tapPosition = Vector2(0.0,0.0)

       
        self.rippleShader = ShaderProgram.open('shaders/ripples.shader')
        self.copyShader = ShaderProgram.open('shaders/passthru.shader')
        
 
        self.textureA = image.DepthTexture.create_for_size(GL_TEXTURE_2D, 
                                                        self.N, 
                                                        self.N,
                                                        GL_RGBA)
                                                        
        self.textureB = image.DepthTexture.create_for_size(GL_TEXTURE_2D, 
                                                        self.N, 
                                                        self.N,
                                                        GL_RGBA)
                                                        
        self.textureC = image.DepthTexture.create_for_size(GL_TEXTURE_2D, 
                                                        self.N, 
                                                        self.N,
                                                        GL_RGBA)
                                         
        self.frameBufferA = frameBuffer(self.textureA)
        self.frameBufferB = frameBuffer(self.textureB)
        self.frameBufferC = frameBuffer(self.textureC)
        
        self.mBufferSelect = False

        # Shader handles (water ripple shader)
        self.rippleTextureHandle = glGetUniformLocation(
                                                        self.rippleShader.id,
                                                        "texture")
                                                        
        self.rippleCopyTextureHandle = glGetUniformLocation(
                                                        self.rippleShader.id,
                                                        "currentTexture")
                                        
        self.rippleTapPosHandle = glGetUniformLocation(
                                                        self.rippleShader.id,
                                                        "tapPos")
        self.rippleTapHandle = glGetUniformLocation(
                                                        self.rippleShader.id,
                                                        "tapped")
        

        self.ripplePositionHandle = glGetAttribLocation(self.rippleShader.id,
                                                        "vPosition")
        self.rippleTexcoordHandle = glGetAttribLocation(self.rippleShader.id,
                                                        "vTexCoord")
        
        # Shader handles (passthru copy shader)
        self.copyTextureHandle = glGetUniformLocation(  self.copyShader.id,
                                                        "texture")
        self.copyPositionHandle = glGetAttribLocation(  self.copyShader.id,
                                                        "vPosition")
        self.copyTexcoordHandle = glGetAttribLocation(  self.copyShader.id,
                                                        "vTexCoord")
        
        # Ripple shader variables
        self.tapped = False
                
        # Texbuffer
        self.buffer = (GLubyte * (self.N * self.N * 4))()

    def update(self, time, verts, v0):          

        if self.mBufferSelect:
            self.renderToFBO(self.frameBufferA, 
                        self.textureA, 
                        self.textureB)
        else:
            self.renderToFBO(self.frameBufferB, 
                        self.textureB, 
                        self.textureA)
   
        self.mBufferSelect = not self.mBufferSelect
        
        # Use the values in textureC to update the vertices
        glBindTexture(GL_TEXTURE_2D, self.textureC.id)      
        glGetTexImage(GL_TEXTURE_2D, 0, GL_RGBA, GL_UNSIGNED_BYTE, self.buffer)
        
        # Channel R maps to the values 0 - 1 in steps of 2**-8
        # Channel G maps to the values 1 - 256 in steps of 1
        # Channel B denotes the sign of the pixel, where 0.0 is positive and 1.0 is negative.
        R = np.array(self.buffer[0::4]).reshape(self.N,self.N)
        G = np.array(self.buffer[1::4]).reshape(self.N,self.N)
        B = np.array(self.buffer[2::4]).reshape(self.N,self.N)
        
        negatives = B >= 1.0
        
        V = (G)/64.
        V[negatives] = -V[negatives]
        
        verts[:self.N:,:self.N:,1] = V
        
        # Restore viewport
        glViewport(0, 0, self.camera.width, self.camera.height)
        
    def tap(self, tapPosition):
        self.tapped = True
        self.tapPosition = tapPosition/self.N
        
    def renderToFBO(self,frameBufferHandle, textureHandleA, textureHandleB):
        # Use the ping-pong FBO technique.
        # Terminology:
        # frameBufferHandle is the FBO of the current output texture.
        # textureHandleA is the handle of the texture currently set as output.
        # textureHandleB is the handle of the texture currently set as input.
        # textureCHandle is a handle to a texture that is a copy of A, which will
        # allow us to access A's while it is bound as an output.
        
        # First copy the timestep-2 (current buffer) texture to buffer C so that
        # it may be read by the shader as it writes to the current buffer.
        self.renderToCopy(textureHandleA)
        
        # Bind FBO A/B to set Texture A/B as the output texture
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, frameBufferHandle)
            
        # Set the viewport to the size of the texture 
        # (we are going to render to texture)
        glViewport(0,0, self.N, self.N)
            
        # Clear the output texture
        glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
             
        # Bind the automata shader
        glUseProgram(self.rippleShader.id)
            
        # Make texture register 0 active and bind texture B/A as the input
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, textureHandleB.id)     
        # Tell the texture uniform sampler to use this texture in the shader by
        #binding to texture unit 0.
        glUniform1i(self.rippleTextureHandle, 0)
        
        glActiveTexture(GL_TEXTURE2)
        glBindTexture(GL_TEXTURE_2D, self.textureC.id)
        glUniform1i(self.rippleCopyTextureHandle, 2)
             
        # Update the 'tapped' uniform for user interaction
        if self.tapped:
            self.tapped = False
            glUniform1i(self.rippleTapHandle, 1)
            glUniform2fv(   self.rippleTapPosHandle,
                            1,
                            self.tapPosition.elements())
        else:
            glUniform1i(self.rippleTapHandle, 0)
            glUniform2fv(   self.rippleTapPosHandle,
                            1,
                            self.tapPosition.elements())

        # Set up vertices VBO
        glBindBuffer(GL_ARRAY_BUFFER, self.vertVBO)  
        
        glBufferData(   GL_ARRAY_BUFFER,
                        sizeof(self.vertices),
                        self.vertices,
                        GL_STATIC_DRAW)
    
        # Set up vertex attributes
        glEnableVertexAttribArray(self.ripplePositionHandle)
        glVertexAttribPointer(  self.ripplePositionHandle,
                                3,
                                GL_FLOAT,
                                GL_FALSE,
                                self.vertexSize,
                                0)
                                
        glEnableVertexAttribArray(self.rippleTexcoordHandle)          
        glVertexAttribPointer(  self.rippleTexcoordHandle,
                                2,
                                GL_FLOAT,
                                GL_FALSE,
                                self.vertexSize,
                                self.offsetTexcoords)

        # Draw fullscreen quad
        glDrawElements(GL_TRIANGLES,
                       len(self.indices), 
                       GL_UNSIGNED_SHORT,
                       self.indices)
                                                            
        # Disable arrays
        glDisableVertexAttribArray(self.ripplePositionHandle)
        glDisableVertexAttribArray(self.rippleTexcoordHandle)
        # Unbind shader and FBO
        glUseProgram(0)   
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, 0)                          
    def renderToCopy(self, textureToCopy):
        # Bind FBO C to set Texture C as the output texture
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, self.frameBufferC)

        # Set the viewport to the size of the texture 
        # (we are going to render to texture)
        glViewport(0,0, self.N, self.N)
            
        # Clear the output texture
        glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
             
        # Bind the passthru shader
        glUseProgram(self.copyShader.id)
            
        # Make texture register 0 active and bind texture B/A as the input
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, textureToCopy.id)     
        # Tell the texture uniform sampler to use this texture in the shader by
        #binding to texture unit 0.
        glUniform1i(self.copyTextureHandle, 0)
        
        
        # Set up vertices VBO
        glBindBuffer(GL_ARRAY_BUFFER, self.vertVBO)  
        
        glBufferData(   GL_ARRAY_BUFFER,
                        sizeof(self.vertices),
                        self.vertices,
                        GL_STATIC_DRAW)
    
        # Set up vertex attributes
        glEnableVertexAttribArray(self.copyPositionHandle)
        glVertexAttribPointer(  self.copyPositionHandle,
                                3,
                                GL_FLOAT,
                                GL_FALSE,
                                self.vertexSize,
                                0)
                                
        glEnableVertexAttribArray(self.copyTexcoordHandle)          
        glVertexAttribPointer(  self.copyTexcoordHandle,
                                2,
                                GL_FLOAT,
                                GL_FALSE,
                                self.vertexSize,
                                self.offsetTexcoords)

        # Draw fullscreen quad
        glDrawElements(GL_TRIANGLES,
                       len(self.indices), 
                       GL_UNSIGNED_SHORT,
                       self.indices)
                       
        # Disable arrays
        glDisableVertexAttribArray(self.copyPositionHandle)
        glDisableVertexAttribArray(self.copyTexcoordHandle)
        # Unbind shader and FBO
        glUseProgram(0)                
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, 0)  
 
    
__author__ = "Peter Bennett"
__copyright__ = "Copyright 2012, Peter A Bennett"
__license__ = "LGPL"
__version__ = "0.1"
__maintainer__ = "Peter Bennett"
__email__ = "pab850@gmail.com"
__contact__ = "www.bytebash.com"

# Pyglet provides the OpenGL context and control input
from pyglet import *
from pyglet.gl import *
from pyglet.window import key, mouse
# gletools ShaderProgram is required to compile GLSL shaders, this can
# be replaced with a standalone shader class if preferred
# For example: 
# http://swiftcoder.wordpress.com/2008/12/19/simple-glsl-wrapper-for-pyglet/
from gletools import ShaderProgram
from math import *
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
    return fbo


class Renderer():

    """ 
    The renderer class has two render modes:
    
    Standard Renderer (mRenderMode = True)
    
    The standard renderer uses a combination of wave functions to model the water
    surface. The water surface changes over time and does not allow for user
    interraction. Use the ripple renderer below if user interraction is required.

    Ripple Renderer: (mRenderMode = False)
    
    The ripple renderer simulates water ripples and allows user interraction with
    the mouse. Press and hold mouse 1 to disturb the water surface at the current
    cursor location.
    
    This technique is based on the method covered here:
    http://freespace.virgin.net/hugo.elias/graphics/x_water.htm
    
    FBO ping-pong buffers are required for this mode, three buffers are used in
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

    """

    def __init__(self, window):
        """ Constructor """
        # Register the renderer for control input
        self.keys = key.KeyStateHandler()
        self.window = window
        self.window.push_handlers(self.on_key_press)
        self.window.push_handlers(self.on_key_release)
        self.window.push_handlers(self.keys)
        self.window.push_handlers(self.on_mouse_motion)
        self.window.push_handlers(self.on_mouse_drag)
        self.window.push_handlers(self.on_mouse_press)
        self.window.push_handlers(self.on_mouse_release)        
        
        # Window size
        (szx, szy) = self.window.get_size()
        self.width = szx
        self.height = szy
        
        # Texture size
        self.texWidth = 512
        self.texHeight = 512
        
        
        # Set up vertices
        self.COORDS_PER_VERTEX = 3
        self.COORDS_PER_TEXTURE = 2
        
        self.mGndVertices = (GLfloat * 24)(
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
            
        self.mMainShader = ShaderProgram.open('shaders/caustics.shader')
        self.mRippleShader = ShaderProgram.open('shaders/ripples.shader')
        self.mCopyShader = ShaderProgram.open('shaders/passthru.shader')
        
        self.mBGTextureHandle = pyglet.image.load('images/tiles.png').get_texture()                                  
                                                        
                                                        
        self.mEnvTextureHandle = pyglet.image.load('images/lightmap.png').get_texture()   

        self.mTextureAHandle = image.DepthTexture.create_for_size(GL_TEXTURE_2D, 
                                                        self.texWidth, 
                                                        self.texHeight,
                                                        GL_RGBA)
                                                        
        self.mTextureBHandle = image.DepthTexture.create_for_size(GL_TEXTURE_2D, 
                                                        self.texWidth, 
                                                        self.texHeight,
                                                        GL_RGBA)
                                                        
        self.mTextureCHandle = image.DepthTexture.create_for_size(GL_TEXTURE_2D, 
                                                        self.texWidth, 
                                                        self.texHeight,
                                                        GL_RGBA)
                                         
        self.mFrameBufferAHandle = frameBuffer(self.mTextureAHandle)
        self.mFrameBufferBHandle = frameBuffer(self.mTextureBHandle)
        self.mFrameBufferCHandle = frameBuffer(self.mTextureCHandle)
        self.mBufferSelect = False
        
        
        # Shader handles (caustic shader)

        self.mPositionHandle = glGetAttribLocation(self.mMainShader.id, "vPosition")
        self.mTextureCoordinateHandle = glGetAttribLocation(self.mMainShader.id, "vTexCoord")
        self.mTextureUniformHandle = glGetUniformLocation(self.mMainShader.id, "texture")
        self.mBGTextureUniformHandle = glGetUniformLocation(self.mMainShader.id, "bgTexture")
        self.mRippleTextureUniformHandle = glGetUniformLocation(self.mMainShader.id, "ripples")
        self.mRenderModeUniformHandle = glGetUniformLocation(self.mMainShader.id, "uRenderMode")

        # Shader handles (water ripple shader)
        self.mWaterTextureUniformHandle = glGetUniformLocation(self.mRippleShader.id, "texture")
        self.mCWaterTextureUniformHandle = glGetUniformLocation(self.mRippleShader.id, "currentTexture")
        self.mWaterTapPosHandle = glGetUniformLocation(self.mRippleShader.id, "tapPos")
        self.mWaterTappedHandle = glGetUniformLocation(self.mRippleShader.id, "tapped")
        self.mWaterFloodHandle = glGetUniformLocation(self.mRippleShader.id, "flood")
        self.mWaterPositionHandle = glGetAttribLocation(self.mRippleShader.id, "vPosition")
        self.mWaterTextureCoordinateHandle = glGetAttribLocation(self.mRippleShader.id, "vTexCoord")
        
        # Shader handles (passthru copy shader)
        self.mCopyTextureUniformHandle = glGetUniformLocation(self.mCopyShader.id, "texture")
        self.mCopyPositionHandle = glGetAttribLocation(self.mCopyShader.id, "vPosition")
        self.mCopyTextureCoordinateHandle = glGetAttribLocation(self.mCopyShader.id, "vTexCoord")
        
        # Ripple shader variables
        self.mTapped = False
        self.mFlood = False
        
        # Tweakables
        self.mWaveFrequency = 10.0
        self.mWaveFactor = 1.0
        self.mWaterDepth = 1.0
        self.mShowWaveFunc = False
        self.mShowBumpMap = False
        self.mEnableRefraction = False
        
        self.mRenderMode = False    ## False -> Wave surface is generated from 
                                    ##          composite sombrero wave function.
                                    ## True ->  Wave surface is generated from a 
                                    ##          water ripple algorithm, user
                                    ##          interraction creates ripples that
                                    ##          distort the light.
        
        
        
        self.mWaterDepthHandle = glGetUniformLocation(self.mMainShader.id, "depth")
        self.mWaveSizeHandle = glGetUniformLocation(self.mMainShader.id, "uWaveSize")
        self.mFactorHandle = glGetUniformLocation(self.mMainShader.id, "uFactor")
        self.mCausticBrightnessHandle = glGetUniformLocation(self.mMainShader.id, "uCausticBrightness")
        self.mLightPosHandle = glGetUniformLocation(self.mMainShader.id, "uLightPos")
        self.mShowWaveFuncHandle = glGetUniformLocation(self.mMainShader.id, "uShowWaveFunc")
        self.mShowBumpMapHandle = glGetUniformLocation(self.mMainShader.id, "uShowBumpMap")
        self.mEnableRefractionHandle = glGetUniformLocation(self.mMainShader.id, "uEnableRefraction")
        
        # Animation
        self.mOffsetHandle = glGetUniformLocation(self.mMainShader.id, "offset")
        self.mTimerHandle = glGetUniformLocation(self.mMainShader.id, "Timer")
        self.mOffsetTimerEnabled = True
        self.mTimer = 0.0
        self.mOffsetTimer = 0.0
        self.mOffsetTimerStep = 0.0001
        self.mOffset = [0.0, 0.0]
        self.mTimerRewind = False
        self.mTimerStep = 0.004
        self.mCausticBrightness = 1.0;    
        self.mLightPos = [0.5, 0.5]                
    def draw(self):          
        """ Main draw loop """
        
        if self.mBufferSelect:
            self.renderToFBO(self.mFrameBufferAHandle, 
                        self.mTextureAHandle, 
                        self.mTextureBHandle)
        else:
            self.renderToFBO(self.mFrameBufferBHandle, 
                        self.mTextureBHandle, 
                        self.mTextureAHandle)
        
        glViewport(0, 0, self.width, self.height)
        # Clear screen
        glClear(GL_COLOR_BUFFER_BIT)
        # Use the caustics shader
        glUseProgram(self.mMainShader.id)
        # Set texture register 0 as active
        glActiveTexture(GL_TEXTURE0)
        # Bind the background texture as the input
        glBindTexture(GL_TEXTURE_2D, self.mBGTextureHandle.id)
        # Tell the texture uniform sampler to use this texture in the shader by 
        # binding to texture unit 0.
        glUniform1i(self.mBGTextureUniformHandle, 0)
        # Set texture register 1 as active
        glActiveTexture(GL_TEXTURE1)
        # Bind the environment map texture as the input
        glBindTexture(GL_TEXTURE_2D, self.mEnvTextureHandle.id)
        # Tell the texture uniform sampler to use this texture by binding it to unit 1
        glUniform1i(self.mTextureUniformHandle, 1)
        
        
        # Set texture register 0 as active
        glActiveTexture(GL_TEXTURE2)
        # Bind texture C as the input texture
        glBindTexture(GL_TEXTURE_2D, self.mTextureCHandle.id)
        glUniform1i(self.mRippleTextureUniformHandle, 2)
        
        
        # Set up the vertex attributes
        glVertexAttribPointer(self.mPositionHandle, 
                              self.COORDS_PER_VERTEX, 
                              GL_FLOAT, 
                              False, 
                              12, 
                              self.mGndVertices )
                                                            
        glVertexAttribPointer(self.mTextureCoordinateHandle, 
                              2, 
                              GL_FLOAT, 
                              False, 
                              0, 
                              self.mTexCoords )
    		 
        # Set tweakables
        glUniform1f(self.mWaterDepthHandle, -0.8)
        glUniform1f(self.mWaterDepthHandle, self.mWaterDepth)
        glUniform1f(self.mWaveSizeHandle, self.mWaveFrequency)
        glUniform1f(self.mFactorHandle, self.mWaveFactor)
        glUniform1f(self.mCausticBrightnessHandle, self.mCausticBrightness)
        glUniform1f(self.mShowWaveFuncHandle, self.mShowWaveFunc)
        glUniform1f(self.mShowBumpMapHandle, self.mShowBumpMap)
        glUniform1f(self.mEnableRefractionHandle, self.mEnableRefraction)
        glUniform2fv(self.mLightPosHandle, 1,(GLfloat*2)(self.mLightPos[0], self.mLightPos[1]))
        glUniform1f(self.mRenderModeUniformHandle, self.mRenderMode)
        
        
        # Set animation timers
        glUniform1f(self.mTimerHandle, self.mTimer * 2 * pi)
        self.mOffset = [sin(2*pi*self.mOffsetTimer),cos(2*pi*self.mOffsetTimer)]
        glUniform2fv(self.mOffsetHandle, 1, (GLfloat*2)(self.mOffset[0],self.mOffset[1]))

        # Enable vertex attribute arrays
        glEnableVertexAttribArray(self.mPositionHandle)
        glEnableVertexAttribArray(self.mTextureCoordinateHandle)
    				 
        # Draw triangles
        glDrawElements(GL_TRIANGLES, 
                       len(self.mGndIndices), 
                       GL_UNSIGNED_SHORT, 
                       self.mGndIndices)
    		 
        # Disable arrays
        glDisableVertexAttribArray(self.mPositionHandle)
        glDisableVertexAttribArray(self.mTextureCoordinateHandle)
        # Unbind shader
        glUseProgram(0)
        
        # Update animation timers
        if self.mOffsetTimer >= 1.0:
            self.mOffsetTimer = 0.0
        elif self.mOffsetTimerEnabled:
            self.mOffsetTimer += self.mOffsetTimerStep

        if self.mTimer >= 1.0:
            self.mTimer = 0.0
        else:
            self.mTimer += self.mTimerStep
            
        self.mBufferSelect = not self.mBufferSelect
        
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
        glViewport(0,0, self.texWidth, self.texHeight)
    		
        # Clear the output texture
        glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    		 
        # Bind the automata shader
        glUseProgram(self.mRippleShader.id)
    		
        # Make texture register 0 active and bind texture B/A as the input
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, textureHandleB.id)	 
        # Tell the texture uniform sampler to use this texture in the shader by
        #binding to texture unit 0.
        glUniform1i(self.mWaterTextureUniformHandle, 0)
        
        glActiveTexture(GL_TEXTURE2)
        glBindTexture(GL_TEXTURE_2D, self.mTextureCHandle.id)
        glUniform1i(self.mCWaterTextureUniformHandle, 2)
    	     
        # Update the 'tapped' uniform for user interaction
        if self.mTapped:
            self.mTapped = False
            glUniform1i(self.mWaterTappedHandle, 1)
            glUniform2fv(self.mWaterTapPosHandle, 1, (GLfloat*2)(self.mLightPos[0], self.mLightPos[1]))
        else:
            glUniform1i(self.mWaterTappedHandle, 0)
            glUniform2fv(self.mWaterTapPosHandle, 1, (GLfloat*2)(self.mLightPos[0], self.mLightPos[1]))
        if self.mFlood:
            self.mFlood = False
            glUniform1i(self.mWaterFloodHandle, 1)
        else:
            glUniform1i(self.mWaterFloodHandle, 0)
    
        # Set up vertex attributes
        glVertexAttribPointer(self.mWaterPositionHandle, 
                              self.COORDS_PER_VERTEX, 
                              GL_FLOAT, 
                              False, 
                              12, 
                              self.mGndVertices)
                              
        glVertexAttribPointer(self.mWaterTextureCoordinateHandle, 
                              2, 
                              GL_FLOAT, 
                              False, 
                              0, 
                              self.mTexCoords)
                                                            
        # Enable vertex attribute arrays
        glEnableVertexAttribArray(self.mWaterPositionHandle)
        glEnableVertexAttribArray(self.mWaterTextureCoordinateHandle)
        # Draw fullscreen quad
        glDrawElements(GL_TRIANGLES,
                       len(self.mGndIndices), 
                       GL_UNSIGNED_SHORT,
                       self.mGndIndices)
        # Disable arrays
        glDisableVertexAttribArray(self.mPositionHandle)
        glDisableVertexAttribArray(self.mTextureCoordinateHandle)
        # Unbind shader and FBO
        glUseProgram(0)				
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, 0)             
    def renderToCopy(self, textureToCopy):
        # Bind FBO C to set Texture C as the output texture
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, self.mFrameBufferCHandle)

        # Set the viewport to the size of the texture 
        # (we are going to render to texture)
        glViewport(0,0, self.texWidth, self.texHeight)
    		
        # Clear the output texture
        glClear (GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    		 
        # Bind the passthru shader
        glUseProgram(self.mCopyShader.id)
    		
        # Make texture register 0 active and bind texture B/A as the input
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, textureToCopy.id)	 
        # Tell the texture uniform sampler to use this texture in the shader by
        #binding to texture unit 0.
        glUniform1i(self.mCopyTextureUniformHandle, 0)
    
        # Set up vertex attributes
        glVertexAttribPointer(self.mCopyPositionHandle, 
                              self.COORDS_PER_VERTEX, 
                              GL_FLOAT, 
                              False, 
                              12, 
                              self.mGndVertices)
                              
        glVertexAttribPointer(self.mCopyTextureCoordinateHandle, 
                              2, 
                              GL_FLOAT, 
                              False, 
                              0, 
                              self.mTexCoords)
                                                            
        # Enable vertex attribute arrays
        glEnableVertexAttribArray(self.mCopyPositionHandle)
        glEnableVertexAttribArray(self.mCopyTextureCoordinateHandle)
        # Draw fullscreen quad
        glDrawElements(GL_TRIANGLES,
                       len(self.mGndIndices), 
                       GL_UNSIGNED_SHORT,
                       self.mGndIndices)
        # Disable arrays
        glDisableVertexAttribArray(self.mPositionHandle)
        glDisableVertexAttribArray(self.mTextureCoordinateHandle)
        # Unbind shader and FBO
        glUseProgram(0)				
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, 0)  
            
    def on_key_press(self, symbol, modifiers):
        """ Handle key press events"""
        # Display mode control
        if symbol == key.NUM_3:
            self.mShowBumpMap = not self.mShowBumpMap 
            self.mShowWaveFunc = False
        if symbol == key.NUM_2:
            self.mShowWaveFunc = not self.mShowWaveFunc 
            self.mShowBumpMap = False
        if symbol == key.NUM_1:
            self.mOffsetTimerEnabled = not self.mOffsetTimerEnabled   
        if symbol == key.NUM_4:
            self.mEnableRefraction = not self.mEnableRefraction
        if symbol == key.NUM_5:
            self.mRenderMode = not self.mRenderMode
        # Caustic brightness control
        if symbol == key.J:
            self.mCausticBrightness += 0.1
        if symbol == key.K:
            self.mCausticBrightness -= 0.1    
        # Depth Control
        if symbol == key.H:
            self.mWaterDepth -= 0.1    
            print "Depth: " + str(self.mWaterDepth)
        if symbol == key.G:
            if self.mWaterDepth <= 0.9:
                self.mWaterDepth += 0.1
            else:
                print "Depth is clamped to <= 1.0!"
            print "Depth: " + str(self.mWaterDepth)
        # Wave function control 
        if symbol == key.E:
            self.mWaveFrequency += 0.05    
        if symbol == key.R:
            self.mWaveFrequency -= 0.05    
        if symbol == key.T:
            self.mWaveFactor += 0.5
        if symbol == key.Y:
            self.mWaveFactor -= 0.5
        
    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        """ Handle mouse drag events """
        (szx, szy) = self.window.get_size()
        self.mLightPos = [x/float(szx),
                          y/float(szy)]
        self.mTapped = True             
    def on_mouse_press(self, x, y, button, modifiers):
        """ Handle mouse press events """
        if button == mouse.LEFT:
            self.mTapped = True
        if button == mouse.RIGHT:
            self.mFlood = True
    def on_mouse_release(self, x, y, button, modifiers):
        """ Handle mouse release events """
        pass        
    def on_key_release(self, symbol, modifiers):
        """ Handle key release events """
        pass
    def on_mouse_motion(self, x, y, dx, dy):
        """ Handle mouse motion events """
        (szx, szy) = self.window.get_size()
        self.mLightPos = [x/float(szx),
                          y/float(szy)]

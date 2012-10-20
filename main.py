""" 
The aim of this project is to emulate the light patterns known as water caustics
typically seen on on the bottom of a swimming pool. 
"""

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
from pyglet.window import key
# gletools ShaderProgram is required to compile GLSL shaders, this can
# be replaced with a standalone shader class if preferred
# For example: 
# http://swiftcoder.wordpress.com/2008/12/19/simple-glsl-wrapper-for-pyglet/
from gletools import ShaderProgram
from math import *

# Global constants
kScreenWidth = 864          ## Window width
kScreenHeight= 864          ## Window height
kFullScreenMode = False     ## Fulscreen mode
kMouseFocus = False         ## Window holds mouse focus
kDesiredFPS = 120           ## Desired FPS (not guaranteed)
# Derived constants
kFPS = 1/float(kDesiredFPS) ## Loop period ms

class Renderer():
    def __init__(self, window):
        """ Constructor """
        # Register the renderer for control input
        self.keys = key.KeyStateHandler()
        window.push_handlers(self.on_key_press)
        window.push_handlers(self.on_key_release)
        window.push_handlers(self.keys)
        window.push_handlers(self.on_mouse_motion)
        window.push_handlers(self.on_mouse_drag)
        window.push_handlers(self.on_mouse_press)
        window.push_handlers(self.on_mouse_release)        
        
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

        self.mBGTextureHandle = pyglet.image.load('images/sand.png').get_texture()                                  
                                                        
                                                        
        self.mEnvTextureHandle = pyglet.image.load('images/lightmap.png').get_texture()               
                
        # Shader handles		

        self.mPositionHandle = glGetAttribLocation(self.mMainShader.id, "vPosition")
        self.mTextureCoordinateHandle = glGetAttribLocation(self.mMainShader.id, "vTexCoord")
	    
        self.mTextureUniformHandle = glGetUniformLocation(self.mMainShader.id, "texture")
        self.mBGTextureUniformHandle = glGetUniformLocation(self.mMainShader.id, "bgTexture")
	   		
        # Tweakables
        self.mWaveFrequency = 10.0
        self.mWaveFactor = 1.0
        self.mWaterDepth = 1.0
        self.mShowWaveFunc = False
        self.mShowBumpMap = False
        
        self.mWaterDepthHandle = glGetUniformLocation(self.mMainShader.id, "depth")
        self.mWaveSizeHandle = glGetUniformLocation(self.mMainShader.id, "uWaveSize")
        self.mFactorHandle = glGetUniformLocation(self.mMainShader.id, "uFactor")
        self.mCausticBrightnessHandle = glGetUniformLocation(self.mMainShader.id, "uCausticBrightness")
        self.mLightPosHandle = glGetUniformLocation(self.mMainShader.id, "uLightPos")
        self.mShowWaveFuncHandle = glGetUniformLocation(self.mMainShader.id, "uShowWaveFunc")
        self.mShowBumpMapHandle = glGetUniformLocation(self.mMainShader.id, "uShowBumpMap")
        
        # Animation
        self.mOffsetHandle = glGetUniformLocation(self.mMainShader.id, "offset")
        self.mTimerHandle = glGetUniformLocation(self.mMainShader.id, "Timer")
        self.mOffsetTimerEnabled = True
        self.mTimer = 0.0
        self.mOffsetTimer = 0.0
        self.mOffsetTimerStep = 0.0001
        self.mOffset = [0.0, 0.0]
        self.mTimerRewind = False
        self.mTimerStep = 0.001
        self.mCausticBrightness = 1.0;    
        self.mLightPos = [0.5, 0.5]                
    def draw(self):          
        """ Main draw loop """
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
        
        glUniform2fv(self.mLightPosHandle, 1,(GLfloat*2)(self.mLightPos[0], self.mLightPos[1]))

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
        pass                
    def on_mouse_press(self, x, y, button, modifiers):
        """ Handle mouse press events """
        pass
    def on_mouse_release(self, x, y, button, modifiers):
        """ Handle mouse release events """
        pass        
    def on_key_release(self, symbol, modifiers):
        """ Handle key release events """
        pass
    def on_mouse_motion(self, x, y, dx, dy):
        """ Handle mouse motion events """
        self.mLightPos = [x/float(kScreenWidth),y/float(kScreenHeight)]

# Setup        
config = Config(buffers=2, samples=4)
window = pyglet.window.Window(caption='Caustics', 
                              width=kScreenWidth, 
                              height=kScreenHeight, 
                              config=config, 
                              vsync=False, 
                              fullscreen=kFullScreenMode)
                              
window.set_exclusive_mouse(kMouseFocus)
renderer = Renderer(window)    
                          
# Main Render Loop
def on_draw(dt):
    window.clear()
    renderer.draw()
    
# Initialisation
if __name__ == '__main__':
    glClearColor(0.0, 0.2, 0.0, 1.0);
    glViewport(0, 0, kScreenWidth, kScreenHeight)
  
clock.schedule_interval(on_draw, kFPS)
pyglet.app.run()



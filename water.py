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
from numpy import *
from vector import Vector2

g = 9.81    # Constant acceleration due to gravity

""" Renderer Imports """
from pyglet import *
from pyglet.gl import *
from pyglet.window import key, mouse
from gletools import ShaderProgram

class Ocean():
    #cOcean ocean(64, 0.0005f, vector2(32.0f,32.0f), 64, false);
    def __init__(self, dimension=64, A=0.0005,w=Vector2(32.0, 32.0),length=64):
        """ 
        Dimension should be a power of 2
        """
        self.N = dimension                  # Dimension - should be power of 2
        self.length = length                # Length Parameter
        self.w = w                          # Wind Parameter
        self.a = A                          # Phillips spectrum parameter
                                            # affects heights of waves
                                            
    def dbg_phillipsArray(self):
        """
        Return a 2D numpy array for display purposes
        """
        temp = []
        spectrum = zeros((self.N * self.N, 4), dtype="u1") #RGBA bytes
        
        pmax = 0
        for m in range(self.N):
            for n in range(self.N):
                p = self.phillips(n,m)
                if p > pmax:
                  pmax = p
                temp.append(p)
                
        if pmax == 0: return 0
        for m in range(self.N):
            for n in range(self.N):  
                p = (temp[m * self.N + n] / pmax) * 255
                spectrum[m * self.N + n] = [p,p,p,255]
                
                
        return spectrum
                
    def phillips(self, n_prime, m_prime):
        """
        The phillips spectrum
        """
        k = Vector2(pi * (2 * n_prime - self.N) / self.length, \
                    pi * (2 * m_prime - self.N) / self.length)

        k_length = k.magnitude()
        
        if(k_length < 0.000001): return 0.0
        
        k_length2 = k_length * k_length
        k_length4 = k_length2 * k_length2
        
        k_dot_w = k.normalise().dot(self.w.normalise())
        k_dot_w2 = k_dot_w * k_dot_w
        
        w_length = self.w.magnitude()
        L = w_length * w_length / g
        l2 = L*L

        damping = 0.001
        ld2 = l2 * damping * damping
        
        return self.a * exp(-1.0 / (k_length2 * l2)) / k_length4 * k_dot_w2 * \
               exp(-k_length2 * ld2);

                        
                        
class oceanRenderer():

    """ 
    A simple class to display a texture heightmap as a fullscreen quad
    """

    def __init__(self, window, camera):
        """ Constructor """
        # Register the renderer for control input
        self.keys = key.KeyStateHandler()
        self.pressedKeys = {}
        self.window = window
        self.window.push_handlers(self.on_key_press)
        self.window.push_handlers(self.on_key_release)
        self.window.push_handlers(self.keys)   
        
        # Window size
        (szx, szy) = self.window.get_size()
        self.width = szx
        self.height = szy
        self.camera = camera
        
        # Texture size
        self.texWidth = 128
        self.texHeight = 128
        
        
        # Ocean Surface Generator
        # def values Ocean(64, 0.0005, Vector2(32.0,32.0),64.0)
        self.generator = Ocean(self.texWidth, 0.0005, Vector2(1.0,1.0),16.0)
        
        
        # Texture creation
        self.image = image.create(self.texWidth, self.texHeight)
        self.mTextureHandle = image.DepthTexture.create_for_size(GL_TEXTURE_2D, 
                                                        self.texWidth, 
                                                        self.texHeight,
                                                        GL_RGBA)
        
        self.mTextureHandle = self.createImage()
        
        
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
            
        self.mMainShader = ShaderProgram.open('shaders/passthru_jet.shader')
        
        # Shader handles (main shader)
        self.mPositionHandle = glGetAttribLocation(self.mMainShader.id, "vPosition")
        self.mTextureCoordinateHandle = glGetAttribLocation(self.mMainShader.id, "vTexCoord")
        self.mMVPHandle = glGetUniformLocation(self.mMainShader.id, "MVP")
        self.mTextureUniformHandle = glGetUniformLocation(self.mMainShader.id, "texture")

    def loadShaders(self):
        """ 
        Load the shaders
        Allow hotloading of shaders while the program is running
        """
        self.mMainShader = ShaderProgram.open('shaders/passthru_jet.shader')
    def createImage(self):
        #data = array([1, 2, 3], dtype='u1')
        data = random.random_integers(low=0, high=1, size=(self.texWidth * self.texHeight, 4))
        data *= 255

        data = self.generator.dbg_phillipsArray()
                
        # set the GB (from RGBA) to 0
        data[ :, 1:-1 ] = 0
        
        # ensure alpha is 255
        data[ :, 3 ] = 255

        # we need to flatten the array
        data.shape = -1
                
        tex_data = (GLubyte * data.size)(*data.astype('u1'))
                
        im = image.ImageData(   self.texWidth,
                                self.texHeight,
                                "RGBA",
                                tex_data,
                                pitch = self.texHeight * 4
                            )
        return im.get_texture()
                        
    def draw(self, dt):          
        """ Main draw loop """

        glViewport(0, 0, self.width, self.height)
        # Clear screen
        glClear(GL_COLOR_BUFFER_BIT)
        # Use the caustics shader
        glUseProgram(self.mMainShader.id)
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
        glVertexAttribPointer(self.mPositionHandle, 
                              self.COORDS_PER_VERTEX, 
                              GL_FLOAT, 
                              False, 
                              12, 
                              self.mFullScreenQuad )
             
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
        glActiveTexture(GL_TEXTURE0) # Reset the active texture
        glUseProgram(0)
    def on_key_press(self, symbol, modifiers):
        """ Handle key press events"""
        
        # Set the pressedKeys dict to allow us to have while-key-pressed actions
        self.pressedKeys[symbol] = True
        
        if symbol == key.P:
            self.loadShaders()
            
    def isKeyPressed(self, symbol):
        if symbol in self.pressedKeys:
            return self.pressedKeys[symbol]
        return False
          
    def on_key_release(self, symbol, modifiers):
        """ Handle key release events """
        self.pressedKeys[symbol] = False
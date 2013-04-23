from pyglet import *
from pyglet.gl import *

import numpy as np
from math import *
import ctypes
'''
Collection of utility functions for OpenGL pyglet projects
'''

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
    
def np2DArray(initialiser, rows, columns, dtype=np.float32):
    ''' Utility Function for generating numpy arrays '''
    rows = int(rows)
    columns = int(columns)
    return np.array([[initialiser for i in range(columns)] for j in range(rows)])        

def np3DArray(initialiser, points, rows, columns, dtype=np.float32):
    ''' Utility Function for generating numpy array of vertices '''
    points = int(points)
    rows = int(rows)
    columns = int(columns)
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

def fullscreenQuad():
    '''
    Generate vertices and indices for drawing a fullscreen quad.
    
    The vertices are of the format:
    [v0x, v0y, v0z, t0x, t0y]
    [v1x, v1y, v1z, t1x, t1y]
              ...
    [v7x, v7y, v7z, t7x, t7y]
    
    '''
    
    # The vertices are of the format:
    vertexSize = ctypes.sizeof(GLfloat) * 5
    vertices = (GLfloat * 40)(
        1.0,    -1.0,   0.0,    1.0,    0.0,
        1.0,    1.0,    0.0,    1.0,    1.0,
        -1.0,   1.0,    0.0,    0.0,    1.0,
        -1.0,   -1.0,   0.0,    0.0,    0.0,
        1.0,    -1.0,   0.0,    1.0,    0.0,
        1.0,    1.0,    0.0,    1.0,    1.0,
        -1.0,   1.0,    0.0,    0.0,    1.0,
        -1.0,   -1.0,   0.0,    0.0,    0.0)
            
    indices = (GLshort * 12)(
        0,  1,  2,
        2,  3,  0,
        4,  6,  5,
        6,  4,  7)
        
    
    return vertices, indices, vertexSize
    
def SkyboxVerts():
    '''
    Generate vertices and indices for drawing a skybox
    '''
    vertexSize = ctypes.sizeof(GLfloat) * 3
    vertices = (GLfloat * 24) (
        -1.0,   1.0,    1.0,
        -1.0,   -1.0,   1.0,
        1.0,    -1.0,   1.0,
        1.0,    1.0,    1.0,
        -1.0,   1.0,    -1.0,
        -1.0,   -1.0,   -1.0,
        1.0,    -1.0,   -1.0,
        1.0,    1.0,    -1.0)
        
    indices = (GLshort * 24) (
        0,  1,  2,  3,
        3,  2,  6,  7,
        7,  6,  5,  4,
        4,  5,  1,  0,  
        0,  3,  7,  4,  
        1,  2,  6,  5)
        
    return vertices, indices, vertexSize
    
    
    
def Pointfield2D(dimension=64, scale=1.0):
    '''
    Generate vertices for GL_POINT drawing
    
    The vertices are of the format:
    [v0x, v0y, v0z, t0x, t0y]
    [v1x, v1y, v1z, t1x, t1y]
              ...
    [v7x, v7y, v7z, t7x, t7y]
    
    '''
    N = dimension
    
    vertexSize = ctypes.sizeof(GLfloat) * 8                  
    vertices = (GLfloat * (N * N * 8))(*range(N * N * 8)) 
    
    
    #indices = np2DArray(0, N, N, GLshort)
               
    # Populate the initial positions
    for i in range(N):
        for j in range(N):
            idx = (i * N + j) * 8  
            # # Index
            # indices[i][j] = i * N + j
            # Position X
            vertices[idx] = ((j-N/2.0) * scale) / (N / 2.)
            # Position Y                        
            vertices[idx + 1] = ((i-N/2.0) * scale) / (N / 2.)
            # Position Z
            vertices[idx + 2] = -1.0
            # Normal X
            vertices[idx] = 0.0
            # Normal Y                        
            vertices[idx + 1] = 1.0
            # Normal Z
            vertices[idx + 2] = 0.0
            # # Texture X
            vertices[idx + 3] = i/float(N)
            # # Texture Y                        
            vertices[idx + 4] = j/float(N)
            
    indices = (GLshort * (N * N))(*range(N * N))   
    
    return vertices, indices, vertexSize
    
def Mesh2DSurface(dimension=64, scale=1.0):
    '''
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
    '''
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
            verts[i][j][0] = j * scale
            # Position Y                        
            verts[i][j][1] = 0.0
            # Position Z
            verts[i][j][2] = i * scale
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
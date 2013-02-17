from utilities import *

class Mesh():
    '''
    A 2D surface mesh holding position, normal and texcoord information
    '''
    
    def __init__(self, dimension=64):
        self.N = dimension
        # Check that N is a power of 2.
        assert self.N != 0 and ((self.N & (self.N - 1)) == 0)
        
        # Create a 3D array of vertices of 8 elements
        self.verts = np3DArray(0.0, 8, self.N + 1, self.N + 1, GLfloat)
        # Indicies are grouped per quad (6 indices for each quad)
        # The mesh is composed of NxN quads
        self.indices = np3DArray(0,6,self.N,self.N,dtype='u4')
        # Construct the mesh information
        self.Mesh2DSurface()
        
        self.vertexCount = self.indices.size 
        
        self.vertexSize = 8
        self.indexSize = 6
        self.offsetNormals = 3
        self.offsetTexture = 5
        
    def Mesh2DSurface(self):
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
                                                                     
        Vertex arrays are 3-dimensional have have the following structure:
        [[[v0x,v0y,v0z,n0x,n0y,n0z,t0x,t0y],[v1x,v1y,v1z,n1x,n1y,n1z,t1x,t1y]],
         [[v2x,v2y,v2z,n2x,n2y,n2z,t2x,t2y],[v3x,v3y,v3z,n3x,n3y,n3z,t3x,t3y]],
         [[v4x,v4y,v4z,n4x,n4y,n4z,t4x,t4y],[v5x,v5y,v5z,n5x,n5y,n5z,t5x,t5y]]]
         
        '''
                 
        # Initialise the surface mesh
        # Populate the index array
        for i in range(self.N):
            for j in range(self.N):
                idx = i * self.N + 1 + j
                self.indices[i][j][0] = idx
                self.indices[i][j][1] = idx + self.N + 1
                self.indices[i][j][2] = idx + 1
                self.indices[i][j][3] = idx + 1
                self.indices[i][j][4] = idx + self.N + 1
                self.indices[i][j][5] = idx + self.N + 1 + 1
                
        # Populate the initial positions and normals
        for i in range(self.N + 1):
            for j in range(self.N + 1):
                # Position X
                self.verts[i][j][0] = (j-self.N/2.0) * scale
                # Position Y                        
                self.verts[i][j][1] = 0.0
                # Position Z
                self.verts[i][j][2] = (i-self.N/2.0) * scale
                # # Normal X
                self.verts[i][j][3] = 0.0
                # # Normal Y                        
                self.verts[i][j][4] = 1.0
                # # Normal Z
                self.verts[i][j][5] = 0.0 
                # # Texture X
                self.verts[i][j][6] = i/float(self.N)
                # # Texture Y                        
                self.verts[i][j][7] = j/float(self.N)
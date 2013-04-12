__author__ = "Peter Bennett"
__copyright__ = "Copyright 2012, Peter A Bennett"
__license__ = "LGPL"
__maintainer__ = "Peter Bennett"
__email__ = "pab850@gmail.com"
__contact__ = "www.bytebash.com"

""" 
A simple 16-element Matrix class implementing functions required by a 
free-look camera system.
"""
from math import sqrt, tan, pi
from ctypes import c_float
from vector import Vector3

class Matrix16():
    def __init__(self, *elements):
        if elements:
            assert len(elements) == 16
            self.elements = (c_float*16)(*elements)
        else:
            self.elements = (c_float*16)(
                1.0, 0.0, 0.0, 0.0, \
                0.0, 1.0, 0.0, 0.0, \
                0.0, 0.0, 1.0, 0.0, \
                0.0, 0.0, 0.0, 1.0
            )
    def __repr__(self):
        return "Matrix16(" + str(list(self.elements)) + ")"
    def __str__(self):
        return "Matrix16(" + str(list(self.elements)) + ")"
    def __getitem__(self, i):
        return self.elements[i]
    def __setitem__(self, i, value):
        self.elements[i] = value
    def __mul__(self, other):
        """ 
        Perform Left hand multiplication on this matrix, the result is:
        result = this * other
        """
        if isinstance(other, Matrix16):
            # Matrix * Matrix            
            res = [0]*16
            for y in range(4):
                for x in range(4):
                    for k in range(4):
                        res[(y*4)+x] += self.row(y)[k] * other.col(x)[k]    
            return Matrix16(*res)
        else:
            # TODO: Add support for vector multiplication when needed
            return NotImplemented        
    def __rmul__(self, other):
        """ 
        Perform Right hand multiplication on this matrix, the result is:
        result = other * this
        """
        if isinstance(other, Matrix16):
            # Matrix * Matrix
            res = [0]*16
            for y in range(4):
                for x in range(4):
                    for k in range(4):
                        res[(y*4)+x] += other.row(y)[k] * self.col(x)[k]  
            return Matrix16(*res)
        else:
            # TODO: Add support for vector multiplication when needed
            return NotImplemented   
    def col(self, i):    
        """ Return column i of the matrix """
        return([self.elements[i],    \
                self.elements[i+4],  \
                self.elements[i+8],  \
                self.elements[i+12]])
                
    def row(self, i):
        """ Return row i of the matrix """
        return([self.elements[(i*4)],    \
                self.elements[(i*4)+1],  \
                self.elements[(i*4)+2],  \
                self.elements[(i*4)+3]])
    def cvalues(self):
        return self.elements
                
    @classmethod
    def perspective(self, vFOV, aspect, fzNear, fzFar):
        # f = 1/tan(vFOV*pi/360.)
        # p = float(aspect)
        # a = (fzFar+fzNear)/(fzNear-fzFar)
        # b = (2*fzFar*fzNear)/(fzNear-fzFar)
        # return Matrix16( f/p, 0.0, 0.0,  0.0, \
                         # 0.0, f,   0.0,  0.0, \
                         # 0.0, 0.0, a,    b,   \
                         # 0.0, 0.0, -1.0, 0.0)
                         
                         
                         
        f = 1/tan(vFOV*pi/360.)
        p = float(aspect)
        a = (fzFar+fzNear)/(fzNear-fzFar)
        b = (2*fzFar*fzNear)/(fzNear-fzFar)
        return Matrix16( f/p, 0.0, 0.0,  0.0, \
                         0.0, f,   0.0,  0.0, \
                         0.0, 0.0, a,    -1.0,   \
                         0.0, 0.0, b,    0.0)        
                         
                         

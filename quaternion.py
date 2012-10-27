__author__ = "Peter Bennett"
__copyright__ = "Copyright 2012, Peter A Bennett"
__license__ = "LGPL"
__maintainer__ = "Peter Bennett"
__email__ = "pab850@gmail.com"
__contact__ = "www.bytebash.com"

""" 
A simple Quaternion class
"""

from ctypes import c_float
from math import *
from matrix16 import Matrix16

class Quaternion():
    def __init__(self, w=1.0, x=0.0, y=0.0, z=0.0):
        self.w = w
        self.x = x
        self.y = y
        self.z = z
    def __repr__(self):
        return ("Quaternion( w=" + str(self.w) +
                        ", x=" + str(self.x) +
                        ", y=" + str(self.y) +
                        ", z=" + str(self.z) + ")")
    def __str__(self):
        return ("Quaternion( w=" + str(self.w) +
                        ", x=" + str(self.x) +
                        ", y=" + str(self.y) +
                        ", z=" + str(self.z) + ")")
    def __mul__(self, other):
        """ 
        Perform right hand multiplication of this quaternion with the input.
        The result is:
        result = this * other
        """
        xn = (self.w * other.x) + (self.x * other.w) + (self.y * other.z) - (self.z * other.y)
        yn = (self.w * other.y) + (self.y * other.w) + (self.z * other.x) - (self.x * other.z)
        zn = (self.w * other.z) + (self.z * other.w) + (self.x * other.y) - (self.y * other.x)
        wn = (self.w * other.w) - (self.x * other.x) - (self.y * other.y) - (self.z * other.z)
        return Quaternion(wn, xn, yn,zn)
                
    def __div__(self, f):
        return Quaternion(self.w / f,self.x / f,self.y / f,self.z / f)
    def __add__(self, other):
        return Quaternion(self.w + other.w,self.x + other.x,self.y + other.y,self.z + other.z)
        
    def __eq__(self, other):
        if self.x == other.x and self.y == other.y and self.z == other.z and self.w == other.w:
            return True
        else:
            return False
    def __ne__(self, other):
        if self.x != other.x or self.y != other.y or self.z != other.z or self.w != other.w:
            return True
        else:
            return False
    def magnitude(self):
        return sqrt(self.x * self.x + 
                    self.y * self.y +
                    self.z * self.z +
                    self.w * self.w)
    def normalise(self):
        mag = self.magnitude()
        return Quaternion(self.w / mag,self.x / mag,self.y / mag,self.z / mag)
    def setRotationDeg(self, axis, degrees):
        halfTheta = (degrees * (pi / 180.)) / 2.
        s = sin(halfTheta)
        self.w = cos(halfTheta)
        self.x = axis.x * s
        self.y = axis.y * s
        self.z = axis.z * s
    def scaleThis(self, scale):
        self.w *= scale
        self.x *= scale
        self.y *= scale
        self.z *= scale
    def dot(self, other):
        return (self.x * other.x + 
                self.y * other.y + 
                self.z * other.z + 
                self.w * other.w)
    def matrix(self):
        """ 
        Return a 16 element array representing a matrix formed from this 
        quaternion.
        """
        
        qy2 = self.y * self.y
        qx2 = self.x * self.x
        qz2 = self.z * self.z
        
        qxqy = self.x * self.y
        qxqz = self.x * self.z
        
        qyqx = self.y * self.x
        qyqz = self.y * self.z
        
        qzqx = self.z * self.x
        qzqy = self.z * self.y
        
        qwqx = self.w * self.x
        qwqz = self.w * self.z
        qwqy = self.w * self.y
        
        return Matrix16(    1.0 - (2.0 * qy2) - (2.0 * qz2),    \
                            2.0 * (qxqy - qwqz),                \
                            2.0 * (qxqz + qwqy),                \
                            0.0,                                \
                            2.0 * (qxqy + qwqz),                \
                            1.0 - (2.0 * qx2) - (2.0 * qz2),    \
                            2.0 * (qyqz - qwqx),                \
                            0.0,                                \
                            2.0 * (qxqz - qwqy),                \
                            2.0 * (qyqz + qwqx),                \
                            1.0 - (2.0 * qx2) - (2.0 * qy2),    \
                            0.0,                                \
                            0.0,                                \
                            0.0,                                \
                            0.0,                                \
                            1.0,                                \
                        )
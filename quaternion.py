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
        Perform Left hand multiplication on this quaternion, the result is:
        result = this * other
        """
        wn = (self.w * other.w) - (self.x * other.x) - (self.y * other.y) - (self.z * other.z)
        xn = (self.w * other.x) + (self.x * other.w) - (self.y * other.z) + (self.z * other.y)
        yn =(self.w * other.y) + (self.x * other.z) + (self.y * other.w) - (self.z * other.x)
        zn = (self.w * other.z) - (self.x * other.y) + (self.y * other.x) + (self.z * other.w)
        
        return Quaternion(wn, xn, yn,zn)
        
    def __rmul__(self, other):
        """
        Perform multiplication on this Quaternion such that:
        result = other * this;
        """
    
        wn = (other.w * self.w) - (other.x * self.x) - (other.y * self.y) - (other.z * self.z)
        xn = (other.w * self.x) + (other.x * self.w) - (other.y * self.z) + (other.z * self.y)
        yn = (other.w * self.y) + (other.x * self.z) + (other.y * self.w) - (other.z * self.x)
        zn  = (other.w * self.z) - (other.x * self.y) + (other.y * self.x) + (other.z * self.w)
        
        return Quaternion(wn,xn,yn,zn)
        
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
    def interpolate(self, other, t):
        qx = 0.
        qy = 0.
        qz = 0.
        qw = 0.
        d = 0.
        f0 = 0.
        f1 = 0.
        if(self != other):
            d = other.dot()
            if(d < 0.):
                qx = -other.x
                qy = -other.y
                qz = -other.z
                qw = -other.w
                d = -d
            else:
                qx = other.x
                qy = other.y
                qz = other.z
                qw = other.w
            if((1. - d) > 0.1):
                angle = acos(d)
                s = sin(angle)
                tAngle = t * angle
                f0 = sin(angle - tAngle) / s
                f1 = sin(tAngle) / s
            else:
                f0 = 1. - t
                f1 = t
        return Quaternion
        (
            f0 * self.w + f1 * qw,
            f0 * self.x + f1 * qx,
            f0 * self.y + f1 * qy,
            f0 * self.z + f1 * qz,
        )
    def matrix(self):
        """ 
        Return a 16 element array representing a matrix formed from this quaternion
        """
        return (c_float*16)(
            (1.0 - (2.0 * ((self.y * self.y) + (self.z * self.z)))),
            (2.0 * ((self.x * self.y) - (self.z * self.w))),
            (2.0 * ((self.x * self.z) + (self.y * self.w))),
            0.0,
            (2.0 * ((self.x * self.y) + (self.z * self.w))),
            (1.0 - (2.0 * ((self.x * self.x) + (self.z * self.z)))),
            (2.0 * ((self.y * self.z) - (self.x * self.w))),
            0.0,
            (2.0 * ((self.x * self.z) - (self.y * self.w))),
            (2.0 * ((self.y * self.z) + (self.w * self.w))),
            (1.0 - (2.0 * ((self.x * self.x) + (self.y * self.y)))),
            0.0,
            0.0,
            0.0,
            0.0,
            1.0
        )
        
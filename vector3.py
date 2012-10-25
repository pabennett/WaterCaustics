__author__ = "Peter Bennett"
__copyright__ = "Copyright 2012, Peter A Bennett"
__license__ = "LGPL"
__maintainer__ = "Peter Bennett"
__email__ = "pab850@gmail.com"
__contact__ = "www.bytebash.com"

""" 
A simple 3-element Vector class implementing common functions
"""
from math import sqrt

class Vector3():
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = x
        self.y = y
        self.z = z
    def __repr__(self):
        return "Vector3(" + str(self.x) + "," + str(self.y) + "," + str(self.z) + ")"
    def __str__(self):
        return "Vector3(" + str(self.x) + "," + str(self.y) + "," + str(self.z) + ")"
    def __mul__(self, f):
        return Vector3(self.x * f,self.y * f,self.z * f)
    def __div__(self, f):
        return Vector3(self.x / f,self.y / f,self.z / f)
    def __add__(self, other):
        return Vector3(self.x + other.x,self.y + other.y,self.z + other.z)
    def __sub__(self, other):
        return Vector3(self.x - other.x,self.y - other.y,self.z - other.z)
    def __neg__(self):
        return Vector3(-self.x, -self.y, -self.z)
    def magnitude(self):
        return sqrt(self.x*self.x + self.y*self.y + self.z*self.z)
    def dot(self, other):
        return ((self.x * other.x) + (self.y * other.y) + (self.z * other.z))
    def cross(self, other):
        return Vector3((self.y * other.z) - (self.z * other.y),(self.z * other.x) - (self.x * other.z),(self.x * other.y) - (self.y * other.x))
    def normalise(self):
        mag = self.magnitude()
        return Vector3(self.x / mag,self.y / mag,self.z / mag)
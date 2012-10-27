__author__ = "Peter Bennett"
__copyright__ = "Copyright 2012, Peter A Bennett"
__license__ = "LGPL"
__maintainer__ = "Peter Bennett"
__email__ = "pab850@gmail.com"
__contact__ = "www.bytebash.com"

""" 
A class to provide a quaternion based first person or freelook
camera. Provides functions to allow the camera to be moved
around a 3D scene.
"""

from vector3 import *
from quaternion import *
from matrix16 import *

WORLD_XAXIS = Vector3(1.0, 0.0, 0.0)
WORLD_YAXIS = Vector3(0.0, 1.0, 0.0) # World 'UP'
WORLD_ZAXIS = Vector3(0.0, 0.0, 1.0) # World 'FORWARD'

class Camera():
    def __init__(self, width, height, vFOV, fzNear, fzFar):
        """ 
        Create an instance of the camera class with the following parameters:
        width   : The width of the viewport
        height  : The height of the viewport
        vFOV    : The desired vertical field of view in degrees
        fzNear  : The near clipping plane of the view frustrum in world units 
                  (Minimum view distance) 
        fzFar   : The far clipping plane of the view frustrum in world units 
                  (Maximum view distance)
        """
        
        # Parameters
        self.width = width if width > 0 else 1
        self.height = height if height > 0 else 1
        self.aspect = self.width / float(self.height)
        self.FOV = vFOV
        self.fzNear = fzNear
        self.fzFar = fzFar
        self.flightMode = True
        
        # Vectors
        self.position = Vector3(0.0, 0.0, 0.0)
        self.xAxis = Vector3(1.0, 0.0, 0.0)
        self.yAxis = Vector3(0.0, 1.0, 0.0)
        self.zAxis = Vector3(0.0, 0.0, 1.0)
        self.flightForward = Vector3(0.0, 0.0, 0.0)
        self.forward = Vector3(0.0, 0.0, 0.0)
        self.moveVelocity = Vector3(0.0, 0.0, 0.0)
        self.angularVelocity = Vector3(0.0, 0.0, 0.0)
        
        # Quaternions
        self.orientation = Quaternion()
        
        # Matrices
        self.projection = Matrix16.perspective(self.FOV, 
                                             self.aspect, 
                                             self.fzNear, 
                                             self.fzFar)
        self.view = Matrix16()
        self.MVP = Matrix16()
        
    def perspective(self, width, height, vFOV, fzNear, fzFar):
        """
        Update the projection matrix
        width   : The width of the viewport, cannot be zero
        height  : The height of the viewport, cannot be zero
        vFOV    : The desired vertical field of view in degrees
        fzNear  : The near clipping plane of the view frustrum in world units 
                  (Minimum view distance)
        fzFar   : The far clipping plane of the view frustrum in world units
                  (Maximum view distance)
        """
        
        if width <= 0 or height <= 0:
            return

        self.fzFar = fzFar
        self.fzNear = fzNear
        self.FOV = vFOV
        self.width = width
        self.height = height
        self.aspect = self.width / float(self.height)
        
        self.projection = Matrix16.perspective(self.FOV, 
                                             self.aspect, 
                                             self.fzNear, 
                                             self.fzFar)
        
        # Update MVP
        self.MVP = self.projection * self.view
    def update(self, yaw, pitch, roll, dx, dy, dz, dt):
        """
        Update the camera velocity
        yaw     :   The angle in degrees by which the camera should rotate 
                    horizontally
        pitch   :   The angle in degrees by which the camera should rotate 
                    vertically
        roll    :   The angle in degrees by which the camera should rotate about
                    its view axis  
        dx      :   The x axis delta
        dy      :   The y axis delta
        dz      :   The z axis delta    
        dt      :   Time delta since last call
        """
        dt = 0.03 if dt < 0.03 else dt
        dt = 1.0 if dt > 1.0 else dt
        
        self.angularVelocity += Vector3(yaw * dt, pitch * dt, roll * dt)
        self.angularVelocity -= self.angularVelocity * dt
        
        if(self.angularVelocity.magnitude() != 0.0):
            orient(self.angularVelocity)
        
        self.addVelocity(dx, dy, dz)
        self.moveVelocity -= self.moveVelocity * dt
        self.position += self.moveVelocity * dt
        self.updateViewMatrix()
    def addVelocity(self, dx, dy, dz):
        self.moveVelocity += self.xAxis * dx
        self.moveVelocity += self.yAxis * dy
        if(self.flightMode):
            self.moveVelocity += self.flightForward * dz
        else:
            self.moveVelocity += self.forward * dz
    def orient(self, yaw, pitch, roll):
        """
        Apply the given yaw, pitch and roll to the current camera orientation.
        yaw     :   The angle in degrees by which the camera should rotate
                    horizontally
        pitch   :   The angle in degrees by which the camera should rotate
                    vertically
        roll    :   The angle in degrees by which the camera should rotate about
                    its view axis  
        """
        rotation = Quaternion()
        
        """ 
            Apply the y-axis delta to the quaternion.
            Pitch causes the camera to rotate around the CAMERA's X-axis.
            We need to right multiply the quaternions because the pitch
            rotation is about the CAMERA X-Axis 
        """
        if(pitch != 0):
            rotation.setRotationDeg(WORLD_XAXIS, pitch)
            self.orientation = self.orientation * rotation
        
        """
            Apply the x-axis delta to the quaternion.
            Yaw causes the camera to rotate around the WORLD's Y-axis.
            We need to left multiply the quaternions because the yaw
            rotation is about the WORLD Y-Axis.
        """
        if(yaw != 0):
            rotation.setRotationDeg(WORLD_YAXIS, yaw)
            self.orientation = rotation * self.orientation
        
        """
            Apply the z-axis delta to the quaternion.
            Roll causes the camera to rotate around the camera's Z-axis
            We need to right multiply the quaternions because the roll
            rotation is about the CAMERA Z-Axis
        """
        if(roll != 0):
            if(self.flightMode):
                #rotation.setRotationDeg(self.flightForward, roll)
                rotation.setRotationDeg(WORLD_ZAXIS, roll)
            else:
                #rotation.setRotationDeg(self.forward, roll)
                rotation.setRotationDeg(WORLD_ZAXIS, roll)
            self.orientation = self.orientation * rotation
            
        self.updateViewMatrix()
        
        
    def move(self, dx, dy, dz):
        """
        * Move the camera by the specified value in all three axis.
        * @param dx
        *    The x axis delta
        * @param dy
        *    The y axis delta
        * @param dz
        *    The z axis delta    
        """
        if(self.flightMode):
            # This is flight mode so we need to move along the forward axis.
            # Move left or right along the camera's x-axis.
            self.position += self.xAxis * dx
            # Move up or down along the world's y-axis.
            self.position += WORLD_YAXIS * dy
            # Move forward along the camera's z-axis.
            self.position += self.flightForward * dz
        else:
            # Determine the 'forwards' direction (where we are looking). If the
            # camera z-axis is used we will move slower forward as the camera
            # tilts upwards, we instead need to use the axis perpendicular to
            # camera xaxis and world yaxis.
            # Move left or right along the camera's x-axis.
            self.position += self.xAxis * dx
            # Move up or down along the world's y-axis.
            self.position += self.yAxis * dy
            # Move forward along the camera's z-axis.    
            self.position += self.forward * dz
        self.positionUpdateViewMatrix()  
    def setpos(self, x, y, z):
        """
        Position the camera at the given world x, y, z coords
        """
        self.position = Vector3(x,y,z)
        self.positionUpdateViewMatrix()
    def updateViewMatrix(self):
        """
        Generate a view matrix from the camera orientation and position and 
        update the camera axis information.
            
        OpenGL Matrix Format (Column Major):
        
        +-----+-----+-----+-----+
        | m0  | m4  | m8  | m12 | 
        +-----+-----+-----+-----+
        | m1  | m5  | m9  | m13 |
        +-----+-----+-----+-----+
        | m2  | m6  | m10 | m14 |
        +-----+-----+-----+-----+
        | m3  | m7  | m11 | m15 |
        +-----+-----+-----+-----+
        
        View Matrix Format (OpenGL column major notation):
        
        +-----+-----+-----+-----+    x = x-axis scale and rotation vector3
        | x0  | y0  | z0  | 0   |    y = y-axis scale and rotation vector3
        +-----+-----+-----+-----+    z = z-axis scale and rotation vector3
        | x1  | y1  | z1  | 0   |    t = translation vector3
        +-----+-----+-----+-----+
        | x2  | y2  | z2  | 0   |     
        +-----+-----+-----+-----+           
        | t0  | t1  | t2  | 1   |            
        +-----+-----+-----+-----+            
                                         
        t = Vector3(-dot(XAXIS,eye),-dot(YAXIS,eye),-dot(ZAXIS,eye))

        """

        # Reconstruct the view matrix.
        self.orientation.normalise()
        self.view = self.orientation.matrix()
                
        # Load the axis vectors
        self.xAxis = Vector3(self.view[0], self.view[4], self.view[8])
        self.yAxis = Vector3(self.view[1], self.view[5], self.view[9])
        self.zAxis = Vector3(self.view[2], self.view[6], self.view[10])
        
        # Apply translation component.
        self.view[12] = -(self.xAxis.dot(self.position))
        self.view[13] = -(self.yAxis.dot(self.position))
        self.view[14] = -(self.zAxis.dot(self.position))
        
                
        # Determine the 'forwards' direction (where we are looking).
        self.flightForward = -self.zAxis
        self.forward = WORLD_YAXIS.cross(self.xAxis)
        self.forward = self.forward.normalise()
        
        # Reconstruct the MVP matrix.
        # Projection is row major, view is row major
        # OpenGL uses column major operator on left            Ie: P*V*M*V1 = V2
        # This is the same as row major operator on the right. Ie: V1*M*V*P = V2
        self.MVP = self.view * self.projection
        
                           
    def positionUpdateViewMatrix(self):
        """
        Apply the current camera position to the view matrix. 
        Only use if there has been no change in orientation since the last update.
        """
        # Apply translation component.
        self.view[12] = -(self.xAxis.dot(self.position))
        self.view[13] = -(self.yAxis.dot(self.position))
        self.view[14] = -(self.zAxis.dot(self.position))
        # Reconstruct the MVP matrix.
        self.MVP = self.view * self.projection
    def getInverseProjection(self):
        """
        Get the inverse projection matrix for converting from clip space back to
        camera space in the vertex shader.
        """
        return self.projection.inverse_perspective( self.width, 
                                                    self.height,
                                                    self.FOV, 
                                                    self.fzNear,
                                                    self.fzFar).elements
    def getModelView(self):
        """ 
        Get the model-viw matrix.
        The model-view matrix 4x4 matrix is used to transform from world/object
        space to eye/camera space.
        """
        return self.view.elements
    def getMVP(self):
        """
        Get the model-view-projection (MVP) matrix.
        The MVP matrix is used to transform from world/object space to clip space.
        """
        return self.MVP.elements
    def getProjection(self):
        """
        Get the projection matrix.
        The projection matrix is used to translate from camera/eye space to clip space.
        """
        return self.projection.elements
        
        
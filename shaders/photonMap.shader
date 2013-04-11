vertex:

// Input Attributes
attribute vec3 vPosition;
attribute vec3 vNormal;

// Input Uniforms
uniform vec3 vLightPosition;
uniform float depth;
uniform float tileSize;
uniform float photonIntensity;
uniform float photonScale;

// To Fragment Shader
varying float intensity;

// Indices of refraction
const float kRefractionAir = 1.0; // Real world: 1.000293
const float kRefractionWater = 1.333;
const float kAir2Water = kRefractionAir/kRefractionWater;

void main(){

    // Render mesh grid as full screen quad
    gl_Position = vec4(vPosition.x/(tileSize/2.0),
                       vPosition.z/(tileSize/2.0), -1.0, 1.0);

    vec3 position =  vPosition;
    
    // gl_Position is the ocean surface position vector
    // vNormal is the normal of the ocean surface at gl_Position
    // vLightPosition is the position of the light source in world space
    
    // Refract the light ray direction vector from the light source to the 
    // ocean surface position vector and determine the intersection position
    // of the refracted ray on a flat ocean floor at depth D.
    
    // Required elements:
    // Light Position
    // Light Direction Vector (from Ocean Position to Light Position)
    // Ocean Normal
    // Depth
    
    // Get the light direction vector    
    vec3 vLightDirection = vLightPosition - position;
    vLightDirection = normalize(vLightDirection);
    
    vec3 normal = normalize(vNormal);
    vec3 vRefract = refract(vLightDirection, normal, kAir2Water);

    // Calculate the distance along the Refraction ray from the ocean surface
    // to the interception point on the ocean floor.
    float distance = (depth - position.y) / vRefract.y;
    
    // Calculate the interception point of the ray on the ocean floor.
    vec3 vIntercept = ((position + vRefract * distance)/tileSize)+0.5;
    
    // Make the caustic texture tileable by using wrap-around co-ordinates
    vIntercept.x = mod(vIntercept.x, 1.0);
    vIntercept.z = mod(vIntercept.z, 1.0);     
    if (vIntercept.x < 0.0) {
        vIntercept.x = 1.0 - (abs(vIntercept.x));
    }
    if (vIntercept.z < 0.0) {
        vIntercept.z = 1.0 - (abs(vIntercept.z));
    }
      
    // Pass values to fragment shader
    intensity = photonIntensity/256.0; // Intensity contribution
    gl_Position.x = (vIntercept.x*2.0)-1.0;
    gl_Position.y = (vIntercept.z*2.0)-1.0;
    gl_Position.z = 0.0;
    gl_PointSize = photonScale;
}

fragment:

import: colourmaps

varying float intensity;

void main()
{
  gl_FragColor = vec4(vec3(1.0,1.0,1.0),intensity);
}

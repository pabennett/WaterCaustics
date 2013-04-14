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
    // Input positions are in the range (-0.5 to 0.5), offset these to 0 to 1.0
    position.x += 0.5;
    position.z += 0.5;
    
    // gl_Position is the ocean surface position vector
    // vNormal is the normal of the ocean surface at gl_Position
    // vLightPosition is the position of the light source in world space
    
    // Refract the light ray direction vector from the light source to the 
    // ocean surface position vector and determine the intersection position
    // of the refracted ray on a flat ocean floor at depth D.
        
    // Get the light direction vector    
    vec3 vLightDirection = vLightPosition - position;
    vLightDirection = normalize(vLightDirection);
    // Obtain the refracted light ray vector
    vec3 normal = normalize(vNormal);
    vec3 vRefract = refract(vLightDirection, normal, kAir2Water);
    // Calculate the distance along the Refraction ray from the ocean surface
    // to the interception point on the ocean floor.
    float distance = (depth - position.y) / vRefract.y;
    // Calculate the interception point of the ray on the ocean floor.
    vec3 vIntercept = ((position + vRefract * distance)/tileSize);

    // Make the caustic texture tileable by using wrap-around co-ordinates
    // Rays that are wrapped around will appear to have originated from a
    // neighbouring ocean tile.
    vIntercept.x = mod(vIntercept.x, 1.0);
    vIntercept.z = mod(vIntercept.z, 1.0);     
    if (vIntercept.x < 0.0) {
        vIntercept.x = 1.0 - (abs(vIntercept.x));
    }
    if (vIntercept.z < 0.0) {
        vIntercept.z = 1.0 - (abs(vIntercept.z));
    }
      
    // The intensity of the photon is controlled via a uniform
    intensity = photonIntensity/256.0; // Intensity contribution
    // Set the position of the GL_POINT according to the interception point
    gl_Position.x = (vIntercept.x*2.0)-1.0;
    gl_Position.y = (vIntercept.z*2.0)-1.0;
    // The ray always strikes the ocean floor to create a planar field of points
    gl_Position.z = 0.0;
    // The point size is controlled via a uniform
    gl_PointSize = photonScale;
}

fragment:

varying float intensity;

void main()
{
    // The intensity of the photon is controlled via a uniform
    gl_FragColor = vec4(vec3(1.0,1.0,1.0),intensity);
}

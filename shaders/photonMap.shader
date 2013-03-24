vertex:

// Input Attributes
attribute vec3 vPosition;
attribute vec3 vNormal;

// Input Uniforms
uniform vec3 vLightPosition;
uniform float depth;
uniform float viewportSize;
uniform float photonIntensity;
uniform float photonScale;

uniform float offsetX;
uniform float offsetY;

// To Fragment Shader
varying float intensity;


////////////////////////////////////////////////////////////////////////////////
// Write to a photon texture which holds the intersection points of refracted
// light rays with the ocean floor due to the surface of the ocean

// Indices of refraction
const float kRefractionAir = 1.0; //1.000293
const float kRefractionWater = 1.333;
const float kAir2Water = kRefractionAir/kRefractionWater;

void main(){

    // Render mesh grid as full screen quad
    gl_Position = vec4(vPosition.x/(viewportSize/2.0),
                       vPosition.z/(viewportSize/2.0), -1.0, 1.0);
           
    
    
    vec3 position =  vPosition;
    position.x += offsetX;
    position.y += offsetY;
    
    // gl_Position is the ocean surface position vector
    // vNormal is the normal of the ocean surface at gl_Position
    // lightPosition is the position of the light source in world space
    
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
    float depth2 = (depth + position.y) / 50.0;
    depth2 *= 10;
    float distance = (depth2 - position.y) / vRefract.y;
    
    // Calculate the interception point of the ray on the ocean floor.
    vec3 vIntercept = ((position + vRefract * distance)+(viewportSize/2.0))/viewportSize;
    
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

varying float intensity;

void main()
{
  gl_FragColor = vec4(1.0,1.0,1.0,intensity);
}

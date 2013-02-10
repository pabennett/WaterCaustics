vertex:

// Input Attributes
attribute vec3 vPosition;
attribute vec3 vNormal;

// Input Uniforms
uniform vec3 vLightPosition;
uniform float depth;
uniform float viewportSize;

// To Fragment Shader
varying vec3 vIntercept;


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
    vec3 vLightDirection = vLightPosition - vPosition;
    
    vLightDirection = normalize(vLightDirection);
    vNormal = normalize(vNormal);
    
    vec3 vRefract = refract(vLightDirection, vNormal, kAir2Water);
    
    // Calculate the distance along the Refraction ray from the ocean surface
    // to the interception point on the ocean floor.
    float depth2 = (depth + vPosition.y) / 50.0;
    float distance = (depth2 - vPosition.y) / vRefract.y;
    
    // Calculate the interception point of the ray on the ocean floor.
    
    vIntercept = ((vPosition + vRefract * distance)+(viewportSize/2.0))/viewportSize;
    
    //vIntercept = abs(vPosition + vRefract * distance)/(viewportSize/2.0);
    
    //vIntercept = clamp(vIntercept, vec3(0.0), vec3(1.0));
    //vIntercept = vec3((vPosition.x+64.0)/128,0.0,(vPosition.z+64.0)/128);    
}

fragment:

varying vec3 vIntercept;

void main()
{
  gl_FragColor = vec4(vIntercept.x, vIntercept.z, vIntercept.y, 1.0);
}


// Refract the light direction vector using Snell's law and the ocean
// surface normal.
// vNormal = normalize(vNormal);

// float cosTheta1 = dot(vNormal, -vLightDirection);
// float cosTheta2 = sqrt(1.0f - (kAir2Water**2) * (1.0 - cosTheta1**2));

// if cosTheta1 < 0.0
// {
    // vRefract = kAir2Water * vLightDirection 
      // - (kAir2Water * cosTheta1 - cosTheta2) * vNormal;
// }
// else
// {
    // vRefract = kAir2Water * vLightDirection 
      // + (kAir2Water * cosTheta1 - cosTheta2) * vNormal;
// }

// Now that the refraction direction vector is obtained, calculate the
// interception position for the given depth. (line-plane intersection)

// Get the length of the light ray to the intersection point
// float d = depth / cosTheta2;
// float B = sqrt(d**2 - depth**2)
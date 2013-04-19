vertex:

attribute vec3 vPosition;
attribute vec3 vNormal;
attribute vec2 vTexCoord;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;

varying vec2 texCoord;

varying vec3 lightVector;
varying vec3 normal;
varying vec3 surfaceNormal;
varying vec3 halfAngleVector;
varying float fogFactor;
varying vec3 worldPosition;

varying vec3 lightDirection;

const vec3 lightPosition = vec3(1000.0, 600.0, 300.0);

void main(){

    //OpenGL uses column-major operator on left (P*V*M * v1 = v2) convention. 
    // (MVP * position)
    //Same as row-major operator on right (v1 * M*V*P = v2)
    gl_Position = view * model * vec4(vPosition,1.0);
    
    worldPosition = (model * vec4(vPosition,1.0)).xyz;
        
    fogFactor = min(-gl_Position.z/700.0, 1.0);
    gl_Position = projection * gl_Position;

	vec4 v = view * model * vec4(vPosition,1.0);
	vec3 normal1 = normalize(vNormal);
    
	lightVector = normalize((view * vec4(lightPosition, 1.0)).xyz - v.xyz);
    lightDirection = normalize(lightPosition - worldPosition);
	normal = normalize((inverse(transpose(view * model)) * vec4(normal1, 0.0)).xyz);
    surfaceNormal = normal1;
    halfAngleVector = normalize(lightVector + normalize(-v.xyz));
    
    texCoord = vTexCoord;
    
}

fragment:

import: colourmaps

// Indices of refraction
const float kRefractionAir = 1.0; //1.000293
const float kRefractionWater = 1.333;
const float kAir2Water = kRefractionAir/kRefractionWater;
// Fresnel tweaks
const float kFresnelBias = 0.2;
const float kFresnelScale = 1.0;
const float kFresnelPower = 5.0;
// Surface Lighting
const vec4 kAmbientColour  = vec4(0.0, 0.53, 1.0 , 1.0);
const vec4 kReflectedColour = vec4(0.0, 0.53, 1.0 , 1.0);
const vec4 kSpecularColour = vec4(1.0, 1.0, 1.0,  1.0);
const vec4 kDiffuseColour = vec4(0.4, 0.8, 0.95, 1.0);
const vec4 kFogColour = vec4(0.0, 0.49, 1.0 ,1.0);
// Input for Beer's law (light attenuation through water)
const float absorptionCoefficient = pow(20,-3);
// Light contributions
const float kEmissiveContrib = 1.0;
const float kAmbientContrib  = 0.2;
const float kDiffuseContrib  = 0.3;
const float kSpecularContrib = 1.0;

varying vec2 texCoord;

varying vec3 lightVector;
varying vec3 normal;
varying vec3 surfaceNormal;
varying vec3 halfAngleVector;
varying float fogFactor;
varying vec3 worldPosition;
varying vec3 lightDirection;

uniform sampler2D texture; 
uniform sampler2D caustics; 
uniform vec3 eyePosition;
uniform vec3 eye;

uniform float tileSize;   // The size of a single surface tile
uniform vec2 tileCount;  // The total number of tiles composing the surface
uniform vec2 tileOffset; // The position of this tile relative to the others

void main()
{
    vec4 fragColour = vec4(0.0);
    vec3 normal1 = normalize(normal);
    vec3 halfAngleVector1  = normalize(halfAngleVector);
    
    // Create a refraction effect on the water surface by tracing rays from
    // the eye through the water's surface to the sea floor.
    // Get the direction to the eye from the vertex position   
    vec3 vEyeDirection = normalize(worldPosition-eyePosition);
    // Distance from the eye to surface point
    float eyeDistance = distance(eyePosition,worldPosition);
    // Refracted eye ray through ocean surface
    vec3 vRefract = refract(vEyeDirection, surfaceNormal, kAir2Water);
    
    // Calculate the distance along the Refraction ray from the ocean surface
    // to the interception point on the ocean floor.
    float depth = worldPosition.y;
    float distance = abs(depth / vRefract.y);
    // Calculate the interception point of the ray on the ocean floor.
    vec3 vIntercept = ((worldPosition + vRefract * distance)/tileSize);
    
    // If the ray strikes the ocean floor sample the floor texture, otherwise
    // return the 'out of bounds' color - in this case the glclearcolour
    vec4 refractedColour = vec4(0.0, 0.49, 1.0 ,1.0); 
    // TODO: The reflected colour will be sourced from a cubemap in the future.
    vec4 reflectedColour = kReflectedColour;
    
    if ((vIntercept.x < tileCount.x) && (vIntercept.x > 0) &&
        (vIntercept.z < tileCount.y) && (vIntercept.z > 0)) {
        refractedColour = texture2D(texture, vIntercept.zx) + 
                            texture2D(caustics, vIntercept.zx);
    }
    
    // Apply ambient, emissive, diffuse and specular terms to the surface
    
    // Calculate transmitted light absorbtion using Beer's law
    // Note: This has been hacked slightly to factor in distance from the 
    // viewer to create an attenuation effect on distant water patches.
    vec4 absorbtion = exp(-absorptionCoefficient * (2*distance+(50*eyeDistance)));
    // Apply the transmitted light absorbtion
    refractedColour *= absorbtion;
    
    // Calculate the fresnel term for mixing between reflected and refracted
    // light on the water's surface
    float fresnel = max(0,
                       min(1,
                         kFresnelBias +
                         kFresnelScale *
                         pow(1 + dot(vEyeDirection,surfaceNormal),kFresnelPower)
                       )
                    );
    // Apply the fresnel term
    fragColour = fresnel * reflectedColour 
                 + (1 - fresnel) * refractedColour * kEmissiveContrib;
                        
	float facing = dot(normal1, lightVector);
    // Check that the vertex is not facing away from the light
    if (facing > 0.0)
    {
        // Apply specular term
        fragColour +=   kSpecularColour *
                        kSpecularContrib *
                        max(pow(dot(normal1, halfAngleVector1), 120.0), 0.0);
        // Apply diffuse light
        fragColour += kDiffuseColour  * kDiffuseContrib  * facing;
    }
    
    // Apply ambient light
	fragColour += kAmbientColour  * kAmbientContrib;
    
    // Apply distance fogging
	fragColour = fragColour * (1.0-fogFactor) + kFogColour * (fogFactor);
    
    // Output the colour
    gl_FragColor = fragColour;
}
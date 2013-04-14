vertex:

attribute vec3 vPosition;
attribute vec3 vNormal;
attribute vec2 vTexCoord;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;

uniform float tileSize;   // The size of a single surface tile
uniform vec2 tileCount;  // The total number of tiles composing the surface
uniform vec2 tileOffset; // The position of this tile relative to the others

varying vec2 texCoord;

varying vec3 lightVector;
varying vec3 normal;
varying vec3 surfaceNormal;
varying vec3 halfAngleVector;
varying float fogFactor;
varying vec3 position;
varying float vTileSize;
varying vec2 vTileCount;
varying vec2 vTileOffset;

const vec3 lightPosition = vec3(1000.0, 600.0, 300.0);

void main(){

    //OpenGL uses column-major operator on left (P*V*M * v1 = v2) convention. 
    // (MVP * position)
    //Same as row-major operator on right (v1 * M*V*P = v2)
    gl_Position = view * model * vec4(vPosition,1.0);
    
    position.x = vPosition.x + (tileOffset.x * tileSize) + (tileSize/2.0);
    position.z = vPosition.z + (tileOffset.y * tileSize) + (tileSize/2.0);
    position.y = vPosition.y + model[3][1]; // Get the vertical offset (depth)

    vTileSize = tileSize;
    vTileCount = tileCount;
    vTileOffset = tileOffset;
    
    fogFactor = min(-gl_Position.z/500.0, 1.0);
    gl_Position = projection * gl_Position;

	vec4 v = view * model * vec4(vPosition,1.0);
	vec3 normal1 = normalize(vNormal);
    
	lightVector = normalize((view * vec4(lightPosition, 1.0)).xyz - v.xyz);
	normal = (inverse(transpose(view * model)) * vec4(normal1, 0.0)).xyz;
    surfaceNormal = normal1;
    halfAngleVector = lightVector + normalize(-v.xyz);
    
    texCoord = vTexCoord;
}

fragment:

import: colourmaps

varying vec2 texCoord;

varying vec3 lightVector;
varying vec3 normal;
varying vec3 surfaceNormal;
varying vec3 halfAngleVector;
varying float fogFactor;
varying vec3 position;
varying float vTileSize;
varying vec2 vTileCount;
varying vec2 vTileOffset;

uniform sampler2D texture; 
uniform sampler2D caustics; 

uniform vec3 eyePosition;
uniform vec3 eye;

  
vec4 fog(vec4 color, vec4 fcolor, float depth, float density)
{
   float f=pow(e, -pow(depth*density, 2));
   return mix(fcolor, color, f);
}

// Indices of refraction
const float kRefractionAir = 1.0; //1.000293
const float kRefractionWater = 1.333;
const float kAir2Water = kRefractionAir/kRefractionWater;

void main()
{
    vec4 fragColour;
	vec3 normal1 = normalize(normal);
	vec3 lightVector1 = normalize(lightVector);
	vec3 halfAngleVector1  = normalize(halfAngleVector);
    
    /*
        Create a refraction effect on the water surface by tracing rays from
        the eye through the water's surface to the sea floor
    */
    
    // Get the direction to the eye from the vertex position   
    vec3 vEyeDirection = normalize(position-eyePosition);
    // Distance from the eye to surface point
    float eyeDistance = distance(eyePosition,position);
    // Refracted eye ray through ocean surface
    vec3 vRefract = refract(vEyeDirection, surfaceNormal, kAir2Water);
    // Calculate the distance along the Refraction ray from the ocean surface
    // to the interception point on the ocean floor.
    float depth = position.y;
    float distance = abs(depth / vRefract.y);

    // Calculate the interception point of the ray on the ocean floor.
    vec3 vIntercept = ((position + vRefract * distance)/vTileSize);

    // If the ray strikes the ocean floor sample the floor texture, otherwise
    // return the 'out of bounds' color - in this case the glclearcolour
    vec4 emissive_colour = vec4(0.0, 0.49, 1.0 ,1.0); 
    
    if ((vIntercept.x < vTileCount.x) && (vIntercept.x > 0) &&
        (vIntercept.z < vTileCount.y) && (vIntercept.z > 0)) {
        emissive_colour = texture2D(texture, vIntercept.zx) + texture2D(caustics, vIntercept.zx);
    }
    
    // Apply ambient, emissive, diffuse and specular terms to the surface
    vec4 c = vec4(1.0);
    vec4 ambient_colour  = vec4(0.0, 0.53, 1.0 , 1.0);
    vec4 specular_colour = vec4(1.0, 1.0, 1.0,  1.0);
    vec4 diffuse_colour = vec4(120.0/255.0, 226.0/255.0, 252.0/255.0, 1.0);//vec4(0.11, 0.24, 0.59, 1.0);

    // The emissive contribution is reduced as the water gets deeper, this
    // makes the water appear darker and the sea floor obscured by scattering.
    // Rework this at some point.
    float emissive_contribution = min(pow(e, -pow((distance)/200, 2)), 0.6);
    float ambient_contribution  = 0.2;
    float diffuse_contribution  = 0.3;
    float specular_contribution = 1.00;
	float d = dot(normal1, lightVector1);
    
	bool facing = d > 0.0;
	fragColour = emissive_colour * emissive_contribution +
		    ambient_colour  * ambient_contribution  * c +
		    diffuse_colour  * diffuse_contribution  * c * max(d, 0) +
                    (facing ?
			specular_colour * specular_contribution * c * max(pow(dot(normal1, halfAngleVector1), 120.0), 0.0) :
			vec4(0.0, 0.0, 0.0, 0.0));

    // Apply distance fogging
	fragColour = fragColour * (1.0-fogFactor) + vec4(0.0, 0.49, 1.0 ,1.0) * (fogFactor);
    // Output the colour
	fragColour.a = 1.0;
    gl_FragColor = fragColour;
}
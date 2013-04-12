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

const vec3 lightPosition = vec3(1000.0, 600.0, 1000.0);

void main(){

    //OpenGL uses column-major operator on left (P*V*M * v1 = v2) convention. 
    // (MVP * position)
    //Same as row-major operator on right (v1 * M*V*P = v2)
    gl_Position = view * model * vec4(vPosition,1.0);
    
    position.x = vPosition.x + (tileOffset.x * tileSize);
    position.z = vPosition.z + (tileOffset.y * tileSize);
    position.y = model[3][1];
    vTileSize = tileSize;
    
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

const float e = 2.71828182845904523536028747135266249;

varying vec2 texCoord;

varying vec3 lightVector;
varying vec3 normal;
varying vec3 surfaceNormal;
varying vec3 halfAngleVector;
varying float fogFactor;
varying vec3 position;
varying float vTileSize;

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
    
    // Get the direction of the eye       
    vec3 vEyeDirection = normalize(eyePosition-position);
    vec3 vRefract = refract(vEyeDirection, surfaceNormal, kAir2Water);
    // Calculate the distance along the Refraction ray from the ocean surface
    // to the interception point on the ocean floor.
    float depth = position.y;
    float distance = depth / vRefract.y;
    
    // Calculate the interception point of the ray on the ocean floor.
    vec3 vIntercept = ((mod(position,vTileSize) + vRefract * distance)/vTileSize);
        
    // Wrap-around co-ordinates
    vIntercept.x = mod(vIntercept.x, 1.0);
    vIntercept.z = mod(vIntercept.z, 1.0);     
    if (vIntercept.x < 0.0) {
        vIntercept.x = 1.0 - (abs(vIntercept.x));
    }
    if (vIntercept.z < 0.0) {
        vIntercept.z = 1.0 - (abs(vIntercept.z));
    }
    
    vec4 c = texture2D(texture, vIntercept.xz) + texture2D(caustics, vIntercept.xz);
    
    /* Apply ambient, emissive, diffuse and specular terms to the surface */

    vec4 emissive_color = vec4(1.0, 1.0, 1.0,  1.0);
    vec4 ambient_color  = vec4(0.0, 0.53, 1.0 , 1.0);
    vec4 diffuse_color  = vec4(1.0, 1.0, 1.0,  1.0);
    vec4 specular_color = vec4(1.0, 1.0, 1.0,  1.0);

    float emissive_contribution = 0.20;
    float ambient_contribution  = 0.20;
    float diffuse_contribution  = 0.80;
    float specular_contribution = 1.20;

	float d = dot(normal1, lightVector1);
	bool facing = d > 0.0;

	fragColour = emissive_color * emissive_contribution +
		    ambient_color  * ambient_contribution  * c +
		    diffuse_color  * diffuse_contribution  * c * max(d, 0) +
                    (facing ?
			specular_color * specular_contribution * c * max(pow(dot(normal1, halfAngleVector1), 120.0), 0.0) :
			vec4(0.0, 0.0, 0.0, 0.0));

	fragColour = fragColour * (1.0-fogFactor) + vec4(0.0, 0.49, 1.0 ,1.0) * (fogFactor);

	fragColour.a = 1.0;
    gl_FragColor = fragColour;
}
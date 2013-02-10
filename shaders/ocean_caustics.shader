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
varying vec3 halfAngleVector;
varying vec3 position;
varying float fogFactor;

const vec3 lightPosition = vec3(0.0,500.0,-0.0);

void main(){

    //OpenGL uses column-major operator on left (P*V*M * v1 = v2) convention. 
    // (MVP * position)
    //Same as row-major operator on right (v1 * M*V*P = v2)
    position = vPosition;
    gl_Position = view * model * vec4(vPosition,1.0);
    fogFactor = min(-gl_Position.z/100.0, 1.0);
    gl_Position = projection * gl_Position;
    //gl_Position = vec4(position.x/256.0, position.z/256.0, -1.0, 1.0);
	vec4 v = view * model * vec4(vPosition,1.0);
	vec3 normal1 = normalize(vNormal);
    
	lightVector = normalize((view * vec4(lightPosition, 1.0)).xyz - v.xyz);
	normal = (inverse(transpose(view * model)) * vec4(normal1, 0.0)).xyz;
    halfAngleVector = lightVector + normalize(-v.xyz);
    
    texCoord = vTexCoord;
    
    normal = vNormal;
}

fragment:

const float e = 2.71828182845904523536028747135266249;
const vec4 skyColour = vec4(0.0, 0.49, 1.0, 1.0);

varying vec2 texCoord;

varying vec3 lightVector;
varying vec3 normal;
varying vec3 halfAngleVector;
varying vec3 position;
varying float fogFactor;

uniform sampler2D texture; 
uniform sampler2D causticMap; 

uniform float depth; 

// Produce from the float input x (range 0.0 to 1.0) a vec4 colour using the
// common 'Jet' colour mapping.
vec4 jet(float x)
{
   x = 4*x;
   float red = clamp(min(x - 1.5, -x + 4.5),0.0,1.0);
   float green = clamp(min(x - 0.5, -x + 3.5),0.0,1.0);
   float blue  = clamp(min(x + 0.5, -x + 2.5),0.0,1.0);
   
   return vec4(red, green, blue, 1.0);
}
  
vec4 fog(vec4 color, vec4 fcolor, float depth, float density)
{
   float f=pow(e, -pow(depth*density, 2));
   return mix(fcolor, color, f);
}

vec3 line_plane_intercept(vec3 pl,vec3 vl,vec3 npl,float  depth)
{
    // Calculate the line-plane-intercept of a ray cast from the ground plane
    // through a wave surface to a light map.
    // http://http.developer.nvidia.com/GPUGems/gpugems_ch02.html
    
    // ------------------------------o-(d)----------------------- Light Map
    //                              /
    //                             / vl (Refracted light vector) 
    //                            /     
    // .''._o''._.''._.''._.''._.^'._.''._.''._.''._.''._.''._.'' Wave Function
    //      |                    |
    //      | dpl (depth)        | npl (ground plane normal)
    //      |                    |     (assumed to be vertical)
    // -----o---------------(pl)-o------------------------------- Ground Plane
    //
    // vl (the refracted light vector) is effectively along the wave
    // surface normal.
    //

    
    // Unoptimized

    // float distance = (depth - dot(npl, pl)) /

    //                    dot(vl, npl);

    // Optimized (assumes npl always points up)
    float distance = (depth - dot(npl, pl)) / dot(vl, npl);
    //float distance = (depth - pl.y) / vl.y;
    return pl + vl * distance;
}

void main()
{
    vec4 fragColour;
	vec3 normal1 = normalize(normal);
    float depth1 = (depth + normal1.y);

    vec4 waterColour = vec4(0.0, 0.49, 1.0 ,1.0);    

    // Caustics
    vec3 position1 = vec3(0.5,0.0,0.5);
    vec3 intercept = line_plane_intercept(  position1,
                                            vec3(normal1.x,1.0,normal1.z), 
                                            vec3(0, 1, 0), 
                                            -depth1);
    
    intercept.xz *= depth1;
    
    fragColour = jet(texture2D(texture, texCoord).r*4.0);
	//fragColour = fragColour * (1.0-fogFactor) + waterColour * (fogFactor);
    
    // Cheating caustics
    //fragColour += vec4(abs(normal1.x)/4.0 + abs(normal1.z)/4.0)  * (1.0-fogFactor);
    // Computed caustics
    //fragColour += texture2D(causticMap, intercept.xz) * (1.0-fogFactor);
    
	fragColour.a = 1.0;
    gl_FragColor = fragColour;
}
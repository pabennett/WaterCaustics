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
varying float fogFactor;

const vec3 lightPosition = vec3(1000.0, 600.0, 1000.0);

void main(){

    //OpenGL uses column-major operator on left (P*V*M * v1 = v2) convention. 
    // (MVP * position)
    //Same as row-major operator on right (v1 * M*V*P = v2)
    gl_Position = view * model * vec4(vPosition,1.0);
    fogFactor = min(-gl_Position.z/500.0, 1.0);
    gl_Position = projection * gl_Position;

	vec4 v = view * model * vec4(vPosition,1.0);
	vec3 normal1 = normalize(vNormal);
    
	lightVector = normalize((view * vec4(lightPosition, 1.0)).xyz - v.xyz);
	normal = (inverse(transpose(view * model)) * vec4(normal1, 0.0)).xyz;
    halfAngleVector = lightVector + normalize(-v.xyz);
    
    texCoord = vTexCoord;
}

fragment:

const float e = 2.71828182845904523536028747135266249;
const vec4 skyColour = vec4(0.0, 0.49, 1.0, 1.0);

varying vec2 texCoord;

varying vec3 lightVector;
varying vec3 normal;
varying vec3 halfAngleVector;
varying float fogFactor;

uniform sampler2D texture; 
uniform int texEnable;

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

void main()
{
    vec4 fragColour;
	vec3 normal1 = normalize(normal);
	vec3 lightVector1 = normalize(lightVector);
	vec3 halfAngleVector1  = normalize(halfAngleVector);

    vec4 c = vec4(1,1,1,1);//texture(water, texCoord);

    vec4 emissive_color = vec4(1.0, 1.0, 1.0,  1.0);
    vec4 ambient_color  = vec4(0.0, 0.49, 1.0 , 1.0);
    vec4 diffuse_color  = vec4(1.0, 1.0, 1.0,  1.0);
    vec4 specular_color = vec4(1.0, 1.0, 1.0,  1.0);

    float emissive_contribution = 0.00;
    float ambient_contribution  = 0.30;
    float diffuse_contribution  = 0.30;
    float specular_contribution = 1.80;

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
vertex:

attribute vec3 vPosition;
attribute vec3 vNormal;
attribute vec2 vTexCoord;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;

varying vec2 texCoord;

varying vec3 normal;
varying vec3 position;
varying float fogFactor;

void main(){

    //OpenGL uses column-major operator on left (P*V*M * v1 = v2) convention. 
    // (MVP * position)
    //Same as row-major operator on right (v1 * M*V*P = v2)
    position = vPosition;
    normal = vNormal;
    gl_Position = view * model * vec4(vPosition,1.0);
    fogFactor = min(-gl_Position.z/500.0, 1.0);
    gl_Position = projection * gl_Position;

    texCoord = vTexCoord;
}

fragment:

import: colourmaps

const vec4 waterColour = vec4(0.0, 0.49, 1.0, 1.0);

varying vec2 texCoord;
varying float fogFactor;

uniform sampler2D texture; 
uniform sampler2D caustics; 

uniform float depth; 

void main()
{
    vec4 fragColour;
    
    // Sample the ocean floor texture
    fragColour = texture2D(texture, texCoord);
    // Apply distance fog
	fragColour = fragColour * (1.0-fogFactor) + waterColour * (fogFactor);
    // Sample the caustic texture
    vec4 caustic = vec4(texture2D(caustics, texCoord)) * (1.0-fogFactor);
    // Apply the caustic texture
    fragColour += caustic;
    fragColour.a = 1.0;
    // Output the colour
    gl_FragColor = fragColour;
}
vertex:

attribute vec3 vPosition;
attribute vec3 vNormal;
attribute vec2 vTexCoord;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;

varying vec3 position;
varying vec3 normal;
varying vec2 texcoord;

void main(){

    //OpenGL uses column-major operator on left (P*V*M * v1 = v2) convention. 
    // (MVP * position)
    //Same as row-major operator on right (v1 * M*V*P = v2)
    position = vPosition;
    gl_Position = view * model * vec4(vPosition,1.0);
    gl_Position = projection * gl_Position;
    normal = vNormal;
    texcoord = vTexCoord;
    

}

fragment:

varying vec3 position;

precision highp float;

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

void main()
{

  vec4 outputColour = jet(abs(position.y));
  
  gl_FragColor = outputColour;
}
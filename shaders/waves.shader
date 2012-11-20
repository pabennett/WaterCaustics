vertex:

attribute vec4 vPosition;
uniform mat4 MVP;
uniform vec2 offset;
varying float h;
varying float fogFactor;

void main(){
	gl_Position = MVP * (vPosition + vec4(offset.x, 0.0, offset.y, 0.0));
    fogFactor = min(-gl_Position.z/50.0, 1.0);
    h = vPosition.y;
}

fragment:

const float e = 2.71828182845904523536028747135266249;
const vec4 skyColour = vec4(0.0, 0.49, 1.0, 1.0);

varying float h;
varying float fogFactor;

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
  vec4 outputColour = jet(abs(h/5));
  
  gl_FragColor = outputColour;
  gl_FragColor = fog(gl_FragColor, skyColour, fogFactor, 0.2);
}
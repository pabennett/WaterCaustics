vertex:

attribute vec4 vPosition;
attribute vec2 vTexCoord;
varying vec2 texCoord;

void main(){
	gl_Position = vPosition;
	texCoord = vTexCoord;
}

fragment:

precision highp float;
varying vec2 texCoord;
uniform sampler2D texture;        //the input texture


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
  vec4 texSamplep = texture2D(texture, vec2(texCoord.x, texCoord.y)); 
  
  vec4 outputColour = jet(texSamplep.r);
  
  gl_FragColor = outputColour;
}
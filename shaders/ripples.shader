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
uniform sampler2D currentTexture; //the destination texture
uniform vec2 tapPos;
uniform int tapped;
uniform int flood;

float kEPSILON = pow(2.0,-8.0);
float kDamping = 0.99; // Damping minimum is 2**-8 (the resolution of our float)

float kTexSize = 512.0;
float kPixSize = 1.0 / kTexSize;

vec3 unpackRG(float f) {
  // F was generated using formula R + G * 256.0
  // Where R and G lie in the range 0 - 1 with steps of 2**-8
  vec3 colour = vec3(0.0);
  // The blue channel signifies sign
  colour.b = f < 0.0 ? 1.0 : 0.0;
  f = abs(f);
  colour.g = floor(f);
  colour.r = (f - colour.g);
  colour.g /= 256.0;
  return colour;
}

float packColour(vec4 colour) {
  if(colour.b != 0.0)
  {
    return -(colour.r + colour.g * 256.0);
  }
  else
  {
    return (colour.r + colour.g * 256.0);
  }
}

void main()
{
  
  float result = 0.0;
  vec4 outputColour = vec4(0.0, 0.0, 0.0, 1.0);

  // Channel R maps to the values 0 - 1 in steps of 2**-8
  // Channel G maps to the values 1 - 256 in steps of 1
  // Channel B denotes the sign of the pixel, where 0.0 is positive and 1.0 is negative.
  
  vec4 texSample0 = texture2D(texture, vec2(texCoord.x - kPixSize, texCoord.y)); //Previous state x-1
  vec4 texSample1 = texture2D(texture, vec2(texCoord.x + kPixSize, texCoord.y)); //Previous state x+1
  vec4 texSample2 = texture2D(texture, vec2(texCoord.x, texCoord.y - kPixSize)); //Previous state y-1
  vec4 texSample3 = texture2D(texture, vec2(texCoord.x, texCoord.y + kPixSize)); //Previous state y+1
  vec4 texSamplep = texture2D(currentTexture, vec2(texCoord.x, texCoord.y));     //Current state x,y
  
  // Combine the R and G channels into a single float range -257 - 257.0, resolution of 1.0/256.0 (2^-8)
  float sample0 = packColour(texSample0);
  float sample1 = packColour(texSample1);
  float sample2 = packColour(texSample2);
  float sample3 = packColour(texSample3);
  float samplep = packColour(texSamplep);
  	
  if(texCoord.x > kPixSize && texCoord.x < 1.0 - kPixSize && texCoord.y > kPixSize && texCoord.y < 1.0 - kPixSize){
    result = ((sample0 + sample1 + sample2 + sample3) / 2.0) - samplep;
    // Apply damping
    // If velocity AND height are almost zero, set it to zero.
    result = result * kDamping;
    result = abs(result) <= kEPSILON ? 0.0 : result;
    // Split the result float (0.0 to 257.0 with a resolution of 2^-8) into R and G channels (0 to 1.0 with a resolution of 2^-8)
    outputColour = vec4(unpackRG(result),1.0);
  }
  
  if(tapped == 1)
  {
    if(pow((texCoord.x - tapPos.x),2.0) + pow((texCoord.y - tapPos.y),2.0) < pow(0.05,2.0))
    {
      outputColour = vec4(1.0, 1.0, 0.0, 1.0);
    }
  }
  
  if(flood == 1)
  {
    if(pow((texCoord.x - tapPos.x),2.0) + pow((texCoord.y - tapPos.y),2.0) < pow(0.8,2.0))
    {
      outputColour = vec4(1.0, 0.0, 0.0, 1.0);
    }
  }
  
  gl_FragColor = outputColour;
}
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
void main()
{
  vec4 texSamplep = texture2D(texture, vec2(texCoord.x, texCoord.y)); 
  gl_FragColor = texSamplep;
}
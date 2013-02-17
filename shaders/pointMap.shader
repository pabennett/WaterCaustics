vertex:

attribute vec3 vPosition;
attribute vec2 vTexcoord;

varying vec3 position;
varying vec2 texcoord;

uniform sampler2D texture;

void main(){

    // Read positions from the position texture and draw points.
    //position.xy = (texture2D(texture, vTexcoord)-0.5)*2.0;
    position = vPosition;
    texcoord = vTexcoord;
    position.xy = (texture2D(texture, texcoord)*2.0)-1.0;
    position.z = -1.0;
    



    gl_Position = vec4(position, 1.0);
    
}

fragment:

varying vec3 position;
varying vec2 texcoord;

void main()
{
  //gl_FragColor = vec4(position.x,position.y,0.0,0.1);
  gl_FragColor = vec4(position.x,position.y,0.9,0.1);
}
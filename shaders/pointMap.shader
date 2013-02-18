vertex:

attribute vec3 vPosition;
attribute vec2 vTexcoord;

varying vec3 position;
varying vec2 texcoord;
varying float intensity;

uniform sampler2D texture;

void main(){

    // Read positions from the position texture and draw points.
    //position.xy = (texture2D(texture, vTexcoord)-0.5)*2.0;
    position = vPosition;
    texcoord = vTexcoord;
    // Position X,Y is stored in the red and green channels.
    position = texture2D(texture, texcoord);
    // The photon contribution is stored in the blue channel.
    intensity = position.z;
    // Scale X and Y
    position.xy = (position.xy*2.0)-1.0;
    // Set point position to far clip plane
    position.z = -1.0;
    
    gl_Position = vec4(position, 1.0);
    gl_PointSize = 4.0;
}

fragment:

varying vec3 position;
varying vec2 texcoord;
varying float intensity;

void main()
{
  //gl_FragColor = vec4(position.x,position.y,0.0,0.1);
  gl_FragColor = vec4(1.0,1.0,1.0,intensity);

}
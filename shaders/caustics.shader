#version 400

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
varying vec3 worldSpacePosition;
uniform sampler2D texture; 
uniform sampler2D bgTexture;
uniform float depth;
varying vec2 texCoord;  
uniform float Timer;

uniform float uWaveSize;    // Frequency
uniform float uFactor;
uniform float uCausticBrightness;
uniform float uShowWaveFunc;
uniform float uShowBumpMap;
uniform vec2 uLightPos;

uniform vec2 offset;

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
    // Axis format:
    //  Z
    //  |  Y    
    //  | /
    //  |/____X 
    //
    
    // Unoptimized

    // float distance = (depth - dot(npl, pl)) /

    //                    dot(vl, npl);

    // Optimized (assumes npl always points up)
  
    float distance = (depth - pl.z) / vl.z;
    return pl + vl * distance;
}

vec4 jet(float x)
{
   x = 4*x;
   float red = clamp(min(x - 1.5, -x + 4.5),0.0,1.0);
   float green = clamp(min(x - 0.5, -x + 3.5),0.0,1.0);
   float blue  = clamp(min(x + 0.5, -x + 2.5),0.0,1.0);
   
   return vec4(red, green, blue, 1.0);
}

vec2 sombreroWave(float f, float x, float y, float timer) {
    vec2 wave = vec2(0.0);
    vec2 cPos = -1.0 + 2.0 * vec2(x, y); 
    float cLength = length(cPos);
    //wave = (vec2(1.0, 1.0) + (cPos/cLength)*cos(cLength*f-timer*4.0))*0.5;
    wave = vec2(x, y) + (vec2(1.0, 1.0) + (cPos/cLength)*cos(cLength*0.9-timer*4.0) * 0.5);
    return wave;
}
    
float sombrero(float x, float y, float timer, vec2 offset){
    // Sombrero
    //f(x,y) = cos(sqrt(x**2 + y**2))
    float phase = timer * 4.0;

    vec2 cpos = -1.0 + 2.0 * vec2(x+0.25 ,y + 0.3);
    float c = length(cpos);
    float f = cos(c * 2.5 * uWaveSize - timer * 2.0);

    cpos = -1.0 + 2.0 * vec2(x+0.3,y+0.2);
    c = length(cpos);
    f += cos(c * 2.5* uWaveSize - timer * 2.0);
    
    cpos = -1.0 + 2.0 * vec2(x+2.5,y+2.5);
    c = length(cpos);
    f += cos(c * 1.0 * uWaveSize - timer * 2.0) * 8.0;
    
    // Normalise
    f *= 10.0 * uFactor;
    return f;
}

vec4 bumpSombrero(float x, float y, float timer, vec2 offset) {    
    // Use a composite of multiple sombrero waves to generate a bump map
    //The result is a bump vector: xyz=normal, a=height
    //  Y
    //  |  Z    
    //  | /
    //  |/____X 
    //
    float s = 1.0 / 512.0;
    
    float s11 = (sombrero(x,   y,   timer, offset));
    float s01 = (sombrero(x-s, y+s, timer, offset));
    float s21 = (sombrero(x,   y+s, timer, offset));
    float s10 = (sombrero(x+s, y-s, timer, offset));
    float s12 = (sombrero(x+s, y,   timer, offset));
    
    vec3 va = normalize(vec3(2.0, 0.0, s21-s01)); 
    vec3 vb = normalize(vec3(0.0, -2.0, s12-s10));
    vec4 bump = vec4( cross(va,vb), abs(s11) );
    return bump;
}

void main()
{
    const float kPixStepSize = 1.0;
    vec3 vertPos = vec3(texCoord.x, texCoord.y, 0.0);
    vertPos *= kPixStepSize;
  
  
    // Wave Functions

    vec4 bump = bumpSombrero(texCoord.x, texCoord.y, Timer, offset);
    float D = bump.w;
    vec2 dxdy = bump.xy;
    
    // Diffraction 
    float rIndex = 2.0;
    float xDiff = (sombreroWave(35.0, (texCoord.x + offset.x) * kPixStepSize * 2.0, texCoord.y * kPixStepSize, Timer)
                - sombreroWave(35.0, (texCoord.x + offset.x) * kPixStepSize, texCoord.y * kPixStepSize, Timer)).x;
                
    float yDiff = (sombreroWave(35.0, (texCoord.x + offset.x) * kPixStepSize, texCoord.y * kPixStepSize * 2.0, Timer)
                - sombreroWave(35.0, (texCoord.x + offset.x) * kPixStepSize, texCoord.y * kPixStepSize, Timer)).y;

                
    yDiff *= 0.2;
    xDiff *= 0.2;    
                
    float xAngle = atan(xDiff);
    float xRefraction = asin(sin(xAngle) / rIndex);
    float xDisplace = tan(xRefraction) * xDiff;

    float yAngle = atan(yDiff);
    float yRefraction = asin(sin(yAngle) / rIndex);
    float yDisplace = tan(yRefraction) * yDiff;

    // Caustics
    vec3 intercept = line_plane_intercept(  vertPos.xyz,
                                            vec3(dxdy, 1.0), 
                                            vec3(0, 0, 1), 
                                            -depth);
    intercept.xy *= depth;
    
    // Generate output
    vec4 colour;
        
    // Apply Refraction
    if (xDiff < 0.0) {
      if (yDiff < 0.0) {
        colour = texture2D(bgTexture, vec2((texCoord.x * 4.0) - xDisplace , (texCoord.y * 4.0) - yDisplace));
      }
      else
      {
        colour = texture2D(bgTexture, vec2((texCoord.x * 4.0) - xDisplace , (texCoord.y * 4.0) + yDisplace));
      }
    }
    else
    {
      if (yDiff < 0.0){
        colour = texture2D(bgTexture, vec2((texCoord.x * 4.0) + xDisplace , (texCoord.y * 4.0)- yDisplace));
      }
      else
      {
        colour = texture2D(bgTexture, vec2((texCoord.x * 4.0) + xDisplace , (texCoord.y * 4.0) + yDisplace));
      }
    }
    
    // Apply caustics & positional light
    colour += 0.25*(1.0 - abs(uLightPos.y - texCoord.y)) * (1.0 - abs(uLightPos.x - texCoord.x));
    colour += ((1.0 - abs(uLightPos.y - texCoord.y)) * (1.0 - abs(uLightPos.x - texCoord.x))) * uCausticBrightness * texture2D(texture, intercept.xy * depth);
    
    if(uShowWaveFunc == 1.0){
        colour = jet(bump.a);
    }
    
    if(uShowBumpMap == 1.0){
        colour = vec4(bump.x, bump.y, bump.z, 1.0);
    }
    colour.a = 1;
    gl_FragColor = colour;
}
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
uniform sampler2D ripples;
uniform float depth;
varying vec2 texCoord;  
uniform float Timer;

uniform float uWaveSize;    // Frequency
uniform float uFactor;
uniform float uCausticBrightness;
uniform float uShowWaveFunc;
uniform float uShowBumpMap;
uniform float uEnableRefraction;
uniform vec2 uLightPos;
uniform float uRenderMode;

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

vec4 binary(float x)
{
   if(x > 0.0){
     return vec4(1.0);
   }
   else
   {
     return vec4(0.0);
   }
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

    cpos = -1.0 + 2.0 * vec2(x-0.3,y-0.2);
    c = length(cpos);
    f += cos(c * 2.5* uWaveSize - timer * 2.0);
    
    cpos = -1.0 + 2.0 * vec2(x+0.3,y-0.2);
    c = length(cpos);
    f += cos(c * 2.5* uWaveSize - timer * 2.0);
    
    cpos = -1.0 + 2.0 * vec2(x-0.3,y+0.2);
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
    const vec3 off = vec3(-s,0.0,s);
    const vec2 size = vec2(2.0,0.0);
        
    float s11 = (sombrero(x,   y,   timer, offset));
    float s01 = (sombrero(x + off.x,   y + off.y,   timer,  offset));
    float s21 = (sombrero(x + off.z,   y + off.y,   timer,  offset));
    float s10 = (sombrero(x + off.y,   y + off.x,   timer,  offset));
    float s12 = (sombrero(x + off.y,   y + off.z,   timer,  offset));

    vec3 va = normalize(vec3(size.xy,s21-s11));
    vec3 vb = normalize(vec3(size.yx,s12-s10));
    vec4 bump = vec4( cross(va,vb), s11 );

    return bump;
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

vec4 bumpRipples(float x, float y, float timer, vec2 offset) { 
    // Use a composite of multiple sombrero waves to generate a bump map
    //The result is a bump vector: xyz=normal, a=height
    //  Y
    //  |  Z    
    //  | /
    //  |/____X 
    //
    float s = 1.0 / 512.0;
    const vec3 off = vec3(-s,0.0,s);
    const vec2 size = vec2(128.0,0.0);
        
    float s11 = packColour(texture2D(ripples, vec2(x,y)));
    float s01 = packColour(texture2D(ripples, vec2(x + off.x,y + off.y)));
    float s21 = packColour(texture2D(ripples, vec2(x + off.z,y + off.y)));
    float s10 = packColour(texture2D(ripples, vec2(x + off.y,y + off.x)));
    float s12 = packColour(texture2D(ripples, vec2(x + off.y,y + off.z)));

    vec3 va = normalize(vec3(size.xy,s21-s01));
    vec3 vb = normalize(vec3(size.yx,s12-s10));
    vec4 bump = vec4( cross(va,vb), s11 );

    return bump;  
}

void main()
{
    const float kPixStepSize = 1.0;
    vec3 vertPos = vec3(texCoord.x, texCoord.y, 0.0);
    vertPos *= kPixStepSize;
  
  
    // Wave Functions
    // Use either a wave function or the input 'ripples' texture as a source
    // of the wave surface.
    // Notes:
    // bumpSombrero will produce a bumpmap from a composite of sombrero functions
    // bumpRipples will use the 'ripples' texture input as the wave surface source.
    
    vec4 bump = vec4(0.0);
    if(uRenderMode == 0.0){
        // User interraction mode.
        bump = bumpRipples(texCoord.x, texCoord.y, Timer, offset);
    }
    else if(uRenderMode == 1.0){
        // Simulated waves mode.
        bump = bumpSombrero(texCoord.x, texCoord.y, Timer, offset);
    }
    
    float D = bump.w;
    vec2 dxdy = bump.xy;
    
    // Caustics
    vec3 intercept = line_plane_intercept(  vertPos.xyz,
                                            vec3(dxdy, 1.0), 
                                            vec3(0, 0, 1), 
                                            -depth);
    intercept.xy *= depth;
    
    // Generate output
    vec4 colour;
        
    // Apply Refraction
    if (uEnableRefraction == 1.0) {
    // Diffraction 
        float rIndex = 2.0;
        float xDiff = dxdy.x * 1.0;
                    
        float yDiff = dxdy.y * 1.0;
                    
        float xAngle = atan(xDiff);
        float xRefraction = asin(sin(xAngle) / rIndex);
        float xDisplace = tan(xRefraction) * xDiff;

        float yAngle = atan(yDiff);
        float yRefraction = asin(sin(yAngle) / rIndex);
        float yDisplace = tan(yRefraction) * yDiff;
                
        if (xDiff < 0.0) {
          if (yDiff < 0.0) {
            colour = texture2D(bgTexture, vec2((texCoord.x * 2.0) - xDisplace , (texCoord.y * 2.0) - yDisplace));
          }
          else
          {
            colour = texture2D(bgTexture, vec2((texCoord.x * 2.0) - xDisplace , (texCoord.y * 2.0) + yDisplace));
          }
        }
        else
        {
          if (yDiff < 0.0){
            colour = texture2D(bgTexture, vec2((texCoord.x * 2.0) + xDisplace , (texCoord.y * 2.0)- yDisplace));
          }
          else
          {
            colour = texture2D(bgTexture, vec2((texCoord.x * 2.0) + xDisplace , (texCoord.y * 2.0) + yDisplace));
          }
        }
    }
    else
    {
        colour = texture2D(bgTexture, vec2(texCoord.x * 2.0, texCoord.y * 2.0));
    }
    
    // Apply caustics & positional light
    //colour += 0.25*(1.0 - abs(uLightPos.y - texCoord.y)) * (1.0 - abs(uLightPos.x - texCoord.x));
    colour += ((1.0 - abs(uLightPos.y - texCoord.y)) * (1.0 - abs(uLightPos.x - texCoord.x))) * uCausticBrightness * texture2D(texture, intercept.xy * depth);
    colour *= 0.7;
    
    // Toggle to show the heightmap of the wave function.
    if(uShowWaveFunc == 1.0){
        colour = jet((bump.a + 256.0)/512.0);
    }
    
    // Toggle to display the bump map.
    if(uShowBumpMap == 1.0){
        colour = vec4(bump.x, bump.y, bump.z, 1.0);
    }
    colour.a = 1;
    gl_FragColor = colour;
}
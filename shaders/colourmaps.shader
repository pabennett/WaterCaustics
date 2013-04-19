const float pi = 3.141592653589793238462643383279;
const float e = 2.71828182845904523536028747135266249;

float getHelixChannel(float x, float p0, float p1)
{
   /* Based on implementation from MatPlotLib's colourmap module. */
   
   // Gamma factor to emphasise either low intensity values (gamma < 1)
   // or high intensity values (gamma > 1)
   float gamma = 1.0;
   // Start colour (purple)
   float s = 0.5;
   // Number of r,g,b rotations in colour that are made from start to end.
   float r = -1.5;
   // Hue (colour saturation) 0 = greyscale.
   float h = 1.0;
   // Apply gamma factor to emphasise low or high intensity values
   float xg = pow(x,gamma);
   
   // Calculate amplitude and angle of deviation from the black
   // to white diagonal in the plane of constant perceived intensity
   float a = h * xg * (1 - xg) / 2;
   float phi = 2 * pi * (s / 3 + r * x);
   
   return xg + a * (p0 * cos(phi) + p1 * sin(phi));
}

vec3 cubeHelix(float x)
{
   // Implement D.A. Green's cubehelix colour scheme
   
   // Input X ranges from 0 to 1.

   float red, green, blue;

   red = getHelixChannel(x, -0.14861, 1.78277);
   green = getHelixChannel(x, -0.29227, -0.90649);
   blue = getHelixChannel(x, -1.97294, 0.0);
   
   return vec3(red, green, blue);
}

vec3 jet(float x)
{
   x = 4*x;
   float red = clamp(min(x - 1.5, -x + 4.5),0.0,1.0);
   float green = clamp(min(x - 0.5, -x + 3.5),0.0,1.0);
   float blue  = clamp(min(x + 0.5, -x + 2.5),0.0,1.0);   
   
   return vec3(red, green, blue);
}

vec3 thermal(float x)
{
   // Thermal colourmap LUT
   const vec3 THERMAL_MAP[5] = vec3[]
   (
      vec3(0, 0, 0),
      vec3(0.3, 0, 0.7),
      vec3(1, 0.2, 0),
      vec3(1, 1, 0),
      vec3(1, 1, 1)
   );
   
   // Compute LUT index and lerp value
   int i = int(floor(x / 0.25));
   float lerp = fract(x / 0.25);

   // R,G,B Output
   float red;
   float green;
   float blue;
   
   if (x != 1.0)
   {
      // Lerp between LUT entries for input values < 1.0
      red = mix(THERMAL_MAP[i].x, THERMAL_MAP[i+1].x, lerp); 
      green = mix(THERMAL_MAP[i].y, THERMAL_MAP[i+1].y, lerp); 
      blue = mix(THERMAL_MAP[i].z, THERMAL_MAP[i+1].z, lerp); 
   }
   else
   {
      // If the input is maximum just return the upper LUT entry.
      red = THERMAL_MAP[4].x;
      green = THERMAL_MAP[4].y;
      blue = THERMAL_MAP[4].z;
   }
   return vec3(red, green, blue);
}
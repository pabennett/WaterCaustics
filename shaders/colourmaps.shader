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

vec3 sea(float x)
{
    float red = (0.00000385 * pow(x,2)) + (-0.00468 * x);// + 0.975;
    float green = (-0.00002132 * pow(x,2)) + (0.002442 * x);// + 0.9482;
    float blue = (-0.00001596 * pow(x,2)) + (0.002605 * x);// + 0.9185;
    
   
    if(x > 0.588)
    {
       blue = 1.4 - x;
    }
    else
    {
       blue = 1.0;
    }

    if(x > 0.45)
    {
       green = 1.2 - x;
    }
    else
    {
       green = 1.0;
    }

    red = 1.0 - x;
    
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

uniform vec3 EARTH_MAP_R[7] = vec3[] 
( 
   vec3(0.0, 0.0, 0.0000),
   vec3(0.2824, 0.1882, 0.1882),
   vec3(0.4588, 0.2714, 0.2714),
   vec3(0.5490, 0.4719, 0.4719),
   vec3(0.6980, 0.7176, 0.7176),
   vec3(0.7882, 0.7553, 0.7553),
   vec3(1.0000, 0.9922, 0.9922)
);

                              
uniform vec3 EARTH_MAP_G[23] = vec3[] 
( 
   vec3(0.0, 0.0, 0.0000),
   vec3(0.0275, 0.0000, 0.0000),
   vec3(0.1098, 0.1893, 0.1893),
   vec3(0.1647, 0.3035, 0.3035),
   vec3(0.2078, 0.3841, 0.3841),
   vec3(0.2824, 0.5020, 0.5020),
   vec3(0.5216, 0.6397, 0.6397),
   vec3(0.6980, 0.7171, 0.7171),
   vec3(0.7882, 0.6392, 0.6392),
   vec3(0.7922, 0.6413, 0.6413),
   vec3(0.8000, 0.6447, 0.6447),
   vec3(0.8078, 0.6481, 0.6481),
   vec3(0.8157, 0.6549, 0.6549),
   vec3(0.8667, 0.6991, 0.6991),
   vec3(0.8745, 0.7103, 0.7103),
   vec3(0.8824, 0.7216, 0.7216),
   vec3(0.8902, 0.7323, 0.7323),
   vec3(0.8980, 0.7430, 0.7430),
   vec3(0.9412, 0.8275, 0.8275),
   vec3(0.9569, 0.8635, 0.8635),
   vec3(0.9647, 0.8816, 0.8816),
   vec3(0.9961, 0.9733, 0.9733),
   vec3(1.0000, 0.9843, 0.9843)
);

uniform vec3 EARTH_MAP_B[11] = vec3[] 
( 
   vec3(0.0, 0.0, 0.0000),
   vec3(0.0039, 0.1684, 0.1684),
   vec3(0.0078, 0.2212, 0.2212),
   vec3(0.0275, 0.4329, 0.4329),
   vec3(0.0314, 0.4549, 0.4549),
   vec3(0.2824, 0.5004, 0.5004),
   vec3(0.4667, 0.2748, 0.2748),
   vec3(0.5451, 0.3205, 0.3205),
   vec3(0.7843, 0.3961, 0.3961),
   vec3(0.8941, 0.6651, 0.6651),
   vec3(1.0000, 0.9843, 0.9843)
);


//Each row in the table for a given color is a sequence of x, y0, y1 tuples. 
//In each sequence, x must increase monotonically from 0 to 1. 
//For any input value z falling between x[i] and x[i+1], the output value of a 
//given color will be linearly interpolated between y1[i] and y0[i+1]:

// Helper function for reading channel LUTs and interpolating values.
// float getChannelValue(const vec3[] lut, float x)
// {
   // float x0, x1, y0, y1;
   // int i;
   // // Find x entry in lut closest to x input.
   // for (i=1; i<lut.length(); i=i+1)
   // { 
      // x0 = lut[i-1].x;
      // x1 = lut[i].x;
      // y0 = lut[i].y;
      // y1 = lut[i-1].z;
      
      // if (x1 == x)
      // {
         // return lut[i].z;
      // }
      // else if x1 > x
      // {
         // // Lerp between y0 and y1 intensities using the position of x between
         // // x0 and x1 as a fraction.
         // return mix(y0, y1, ((x-x0)/(x1-x0)));
      // }
   // }
// }

vec3 earth(float x)
{
   float red, green, blue;
   float x0, x1, y0, y1;
   int i;
   
   // Find x entry in lut closest to x input.
   for (i=1; i<EARTH_MAP_R.length(); i=i+1)
   { 
      x0 = EARTH_MAP_R[i-1].x;
      x1 = EARTH_MAP_R[i].x;
      y0 = EARTH_MAP_R[i].y;
      y1 = EARTH_MAP_R[i-1].z;
      
      if (x1 == x)
      {
         red = EARTH_MAP_R[i].z;
         break;
      }
      else if (x1 > x)
      {
         // Lerp between y0 and y1 intensities using the position of x between
         // x0 and x1 as a fraction.
         red = mix(y1, y0, ((x-x0)/(x1-x0)));
         break;
      }
   }
   
   // Find x entry in lut closest to x input.
   for (i=1; i<EARTH_MAP_G.length(); i=i+1)
   { 
      x0 = EARTH_MAP_G[i-1].x;
      x1 = EARTH_MAP_G[i].x;
      y0 = EARTH_MAP_G[i].y;
      y1 = EARTH_MAP_G[i-1].z;
      
      if (x1 == x)
      {
         green = EARTH_MAP_G[i].z;
         break;
      }
      else if (x1 > x)
      {
         // Lerp between y0 and y1 intensities using the position of x between
         // x0 and x1 as a fraction.
         green = mix(y1, y0, ((x-x0)/(x1-x0)));
         break;
      }
   }
   
   // Find x entry in lut closest to x input.
   for (i=1; i<EARTH_MAP_B.length(); i=i+1)
   { 
      x0 = EARTH_MAP_B[i-1].x;
      x1 = EARTH_MAP_B[i].x;
      y0 = EARTH_MAP_B[i].y;
      y1 = EARTH_MAP_B[i-1].z;
      
      if (x1 == x)
      {
         blue = EARTH_MAP_B[i].z;
         break;
      }
      else if (x1 > x)
      {
         // Lerp between y0 and y1 intensities using the position of x between
         // x0 and x1 as a fraction.
         blue = mix(y1, y0, ((x-x0)/(x1-x0)));
         break;
      }
   }
   
   return vec3(red, green, blue);
}


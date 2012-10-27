WaterCaustics - Rendering Experiments
==============================

![WaterCaustics](http://www.bytebash.com/files/watercaustics.png "Water Caustics")

Description
-----------

The aim of this project is to emulate the light patterns known as water caustics
typically seen on on the bottom of a swimming pool. 

Dependencies
------------

This code has been written in Python 2.7 with the following additional modules:

[Pyglet](http://www.pyglet.org/ "Pyglet") for OpenGL and windowing + controls

[Gletools](http://codeflow.org/entries/2009/jul/31/gletools-advanced-pyglet-utilities/ "Gletools") to allow compilation of GLSL shaders

Controls
--------

A listing of the controls is provided below:

+   **P** Reload the shaders. Shader hotloading is handy for debugging and tweaking.
+   **H** Lower the height of the water plane
+   **G** Raise the height of the water plane (maximum of 1.0)
+   **T** Raise the wave factor (wave function mode only)
+   **Y** Lower the wave factor (wave function mode only)
+   **J** Raise the brightness of the water caustics
+   **K** Lower the brightness of the water caustics
+   **NUM_2** Enable/Disable display of the wave function heightmap
+   **NUM_3** Enable/Disable display of the wave function bumpmap
+   **NUM_4** Enable/Disable Refraction
+   **NUM_5** Toggle render mode between ripple and wave function mode
+   **MOUSE** Left click when in ripple mode to cause ripples at the mouse cursor
+   **SPACE** Enable or disable the camera system
+   **WSAD**  Move around in camera mode
+   **QE**    Change roll in camera mode

Acknowledgements
----------------

The caustics generator is based an Nvidia GPU Gems article on caustics, which can be found [here](http://http.developer.nvidia.com/GPUGems/gpugems_ch02.html "GPU Gems")  
The sand and tile textures are by Patrick Hoesly on [Flickr](http://www.flickr.com/photos/zooboing/ "Zooboing") 

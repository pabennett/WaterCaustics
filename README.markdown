WaterCaustics - Rendering Experiments
==============================

Description
-----------

The aim of this project is to emulate the light patterns known as water caustics
typically seen on on the bottom of a swimming pool. I investigate various
methods of simulating water surfaces and associated caustics.

The engine is able to render various scenes at interractive framerates:

Swimming pool
-------------

![PoolCaustics](http://www.bytebash.com/files/caustics/swimmingPoolPreview.png "Pool Caustics")

Sea
-------------

![Sea](http://www.bytebash.com/files/caustics/seaPreview.png "Sea")

Tropical Water
--------------

![Tropical](http://www.bytebash.com/files/caustics/tropicalPreview.png "Tropical Caustics")

Dependencies
------------

This code has been written in Python 2.7 with the following additional modules:

[Numpy](http://numpy.scipy.org/ "Numpy") for fast array operations

[Pyglet](http://www.pyglet.org/ "Pyglet") for OpenGL and windowing + controls

[Gletools](http://codeflow.org/entries/2009/jul/31/gletools-advanced-pyglet-utilities/ "Gletools") to allow compilation of GLSL shaders

Features
--------

Currently three methods of simulating water surfaces have been implemented,
these are:

+ FBO ping-pong for shallow water ripples with user interraction via the mouse.
+ Sombrero function (a composite creates something resembling a water surface).
+ Tessendorf's FFT synthesis technique.

The scene instance in main.py uses the Tessendorf ocean surface simulator by
default.

Caustic generation is performed by tracing the path of refracted light rays
through the water's surface and then calculating the interception point on the
sea bed at a user specified depth. The interception points are recorded in a
"Photon map" which is then passed to a shader that draws GL_POINTS at the photon
positions; the accumulation of photons at the same position on the sea bed
creates a caustic pattern.

How to Run
----------

Install the required dependencies and then run **main.py**!

Controls
--------

A listing of the controls is provided below, these depend on which renderer is
in use:

Tessendorf FFT synthesis renderer:

+   **M** Enable or Disable the Caustics Engine
+   **V** Lower the height of the water plane
+   **C** Raise the height of the water plane
+   **U** Increase the scale of the caustic photons
+   **J** Decrease the scale of the caustic photons
+   **Y** Increase the intensity of the caustics
+   **H** Decrease the intensity of the caustics
+   **Z** Toggle drawing ocean surface
+   **X** Toggle drawing ocean floor
+   **MOUSE** Look
+   **WSAD**  Move
+   **QE**    Change roll
+   **SPACE** Toggle timer (pauses surface animations)
+   **NUM_4/NUM_5** Double/halve Z wind component
+   **NUM_1/NUM_2** Double/halve X wind component
+   **NUM_7/NUM_8** Double/halve phillips spectrum factor (affects wave height)
+   **L** Toggle wireframe

Acknowledgements
----------------

Thanks to Keith Lantz for his [excellent guide](http://www.keithlantz.net/2011/10/ocean-simulation-part-one-using-the-discrete-fourier-transform/ "Ocean Simulation")
on Tessendorf's ocean simulation technique

The sand and tile textures are by Patrick Hoesly on [Flickr](http://www.flickr.com/photos/zooboing/ "Zooboing") 

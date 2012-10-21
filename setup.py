from distutils.core import setup

import glob

# The main entry point of the program
script_file = 'main.py'

# Create a list of data files.          
image_files = glob.glob('images/*.*')
        
# Create a list of data files.          
shader_files = glob.glob('shaders/*.shader')
        
mydata_files = [('images', image_files),('shaders', shader_files)]

# Setup args that apply to all setups, including ordinary distutils.
setup_args = dict(
    data_files=mydata_files)
    
# py2exe options
try:
    import py2exe
    setup_args.update(dict(
        windows=[dict(
            script=script_file
        )],
        options={"py2exe": {
                            'bundle_files':1,
                            'ascii':False}}))
except ImportError:
    pass

# py2app options
# try:
#     import py2app
#     setup_args.update(dict(
#         app=[script_file],
#         options=dict(py2app=dict(
#             argv_emulation=True,
#             iconfile='assets/app.icns',
#         )),
#     ))
# except ImportError:
#     pass

setup(**setup_args)
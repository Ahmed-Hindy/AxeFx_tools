node = kwargs['node']

# set defaults:
node.parm('picture').set('$RENDER/$HIPNAME/$OS/$OS.$F4.exr')
node.parm('dcmfilename').set('$RENDER/$HIPNAME/$OS/$OS.deep.$F4.exr')
node.parm('camera').set('/Scene/CAM/camera1')




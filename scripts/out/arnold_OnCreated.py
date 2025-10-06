import traceback


node = kwargs['node']

# set defaults:
# /Properties/Output
node.parm('ar_picture').set('$RENDER/$HIPNAME/$OS/$OS.$F4.exr')
node.parm('ar_exr_half_precision').set(1)
node.parm('ar_exr_multipart').set(1)
node.parm('ar_exr_preserve_layer_name').set(1)

# /Properties/Samples
node.parm('ar_enable_progressive_render').set(1)

# /Properties/Textures
node.parm('ar_texture_auto_maketx').set(0)


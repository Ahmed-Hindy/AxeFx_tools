node = kwargs['node']

node.parm('vm_picture').set('$RENDER/$HIPNAME/$OS/$OS.$F4.exr')
node.parm('vm_dcmfilename').set('$RENDER/$HIPNAME/$OS/$OS.deep.$F4.exr')
node.parm('vm_renderengine').set('pbrraytrace')
node.parm('vm_verbose').set(1)

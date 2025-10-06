# print('configuring sopcrowdimport lop')
HOUDINI_MAJOR_RELEASE, HOUDINI_MINOR_RELEASE, HOUDINI_BUILD_VERSION = hou.applicationVersion()
node = kwargs['node']


node.parm("f1").deleteAllKeyframes()
node.parm("f1").set(1001)

node.parm("pathprefix").set("/Scene/geo/crowd/$OS")
node.parm("enable_animsavepath").set(1)
node.parm("animsavepath").set(r"layers/$OS.anim.usdc")
node.parm("enable_geosavepath").set(1)
node.parm("geosavepath").set(r"layers/$OS.usdc")

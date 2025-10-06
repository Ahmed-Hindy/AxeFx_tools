node = kwargs['node']
node.parm('enable_pathprefix').set(1)
node.parm('pathprefix').set('/geo/$OS')
node.parm('enable_packedprims').set(1)
node.parm('enable_pathattr').set(1)
node.parm('enable_setdefaultprim').set(1)
node.parm('enable_topology').set(1)
node.parm('enable_staticattribs').set(1)


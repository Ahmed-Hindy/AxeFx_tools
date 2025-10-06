node = kwargs['node']
node.parm('pathprefix').set("/Scene/GEO/$OS")
node.parm('enable_savepath').set("1")
node.parm('savepath').set("layers/$OS.usdc")

node.parm('enable_prefixabsolutepaths').set(1)
node.parm('prefixabsolutepaths').set(1)

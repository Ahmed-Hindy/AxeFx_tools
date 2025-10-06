node = kwargs['node']

node.parm("setsavepath").set(1)
node.parm("savepath").set(r"layers/$OS.usd")

node.parm("startnewlayer").set(1)


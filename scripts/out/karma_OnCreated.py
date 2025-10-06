# print('configuring Karma Node! rops')
node = kwargs['node']

# /Common Settings
node.parm('picture').set('$RENDER/$HIPNAME/$OS/$OS.$F4.exr')
# /Deep Output
node.parm('dcmfilename').set('$RENDER/$HIPNAME/$OS/$OS.deep.$F4.exr')

# /Advanced/Buckets and Caching
node.parm("dosnapshot").set(0)

# /Advanced/Driver
node.parm('alfprogress').set(1)
node.parm("reportnetwork").set(1)
node.parm("soho_foreground").set(1)


# /Advanced/Options/USD Options
node.parm("complexity").set("low")

# /Advanced/Profiling
node.parm("husk_debug").set(1)
node.parm("verbosity").set(3)
node.parm("log").set(1)
node.parm("logappend").set(1)
node.parm("husk_stdout").set(r"$HIP/logs/$HIPNAME.$RENDERID_logs.txt")
node.parm("husk_stderr").set(r"$HIP/logs/$HIPNAME.$RENDERID_errors.txt")


# print('configuring Karma Node! rops')
node = kwargs['node']


node.parm('renderer').set('BRAY_HdKarmaXPU')
node.parm('rendersettings').set('/Render/rendersettings')

node.parm('enableoutputprocessor_savepathsrelativetooutput').set(1)
node.parm('clearhoudinicustomdata').set(1)

# /Output
node.parm('alfprogress').set(1)
node.parm("reportnetwork").set(1)
node.parm("soho_foreground").set(1)

# /Husk/Statistics
node.parm("husk_debug").set(1)
node.parm("verbosity").set(3)
node.parm("log").set(1)
node.parm("logappend").set(1)
node.parm("husk_stdout").set(r"$HIP/logs/$HIPNAME.$RENDERID_logs.txt")
node.parm("husk_stderr").set(r"$HIP/logs/$HIPNAME.$RENDERID_errors.txt")


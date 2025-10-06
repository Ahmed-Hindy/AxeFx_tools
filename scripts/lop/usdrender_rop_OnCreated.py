# print('configuring usdrender_rop lop')
HOUDINI_MAJOR_RELEASE, HOUDINI_MINOR_RELEASE, HOUDINI_BUILD_VERSION = hou.applicationVersion()
node = kwargs['node']

node.parm("rendersettings").set(r"/Render/rendersettings")


# /Husk/Rendering
node.parm("husk_complexity").set("low")
node.parm("dosnapshot").set(0)

# /Husk/Statistics
node.parm("husk_debug").set(1)
if HOUDINI_MAJOR_RELEASE == 19 and HOUDINI_MINOR_RELEASE == 5:
    node.parm("verbosity").set("3")
elif HOUDINI_MAJOR_RELEASE >= 20:
    node.parm("verbose").set(3)
else:
    print("WARNING: usdrender_rop_OnCreated: Unsupported Houdini version")

node.parm("husk_log").set(1)
node.parm("husk_logappend").set(1)
node.parm("husk_stdout").set(r"$HIP/logs/$HIPNAME.$OS.$RENDERID.`$F4`_logs.txt")
node.parm("husk_stderr").set(r"$HIP/logs/$HIPNAME.$OS.$RENDERID.`$F4`_errors.txt")

# /Output
node.parm("enableoutputprocessor_simplerelativepaths").set(0)
node.parm("enableoutputprocessor_matchoutputextension").set(0)
node.parm("soho_foreground").set(1)
node.parm("alfprogress").set(1)
node.parm("reportnetwork").set(1)

# /Scripts
## following script doesn't work on deadline. Skipping!
# node.parm('prerender').set("""
# import os
# import traceback
# try:
#     folder_path = f"{os.environ['HIP']}/logs"
#     if not os.path.exists(folder_path):
#         os.makedirs(folder_path, exist_ok=True)
# except:
#     traceback.print_exc()
#     """)
# node.parm('lprerender').set('python')



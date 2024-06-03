import hou

keyword = "HIP_FOLDER_NAME"  # "explosion" for example
drive = "Drive letter"  # "D:" for example

nodes = hou.node("/").allSubChildren()

tempPath = ""

for node in nodes:

    parms = node.parms()

    for x in parms:
        if x.parmTemplate().type().name() == "String":

            tempPath = x.eval()

            if tempPath.startswith(drive):
                x.set("$HIP" + tempPath.split(keyword)[1])

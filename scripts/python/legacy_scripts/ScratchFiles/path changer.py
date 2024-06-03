import hou
import os

origVar = "$HIP"  # orig string to replace
newVar = "$BLDG"  # replace with this


obj = hou.node("/obj")
nodes = hou.selectedNodes()[0].children()
origStringEval = ""

for node in nodes:

    parms = node.parms()

    for x in parms:
        if x.parmTemplate().name() == "file":
            origstring = x.unexpandedString()
            print("original String is: " + origstring)

            origStringEval = x.eval()
            print("original String Evaluated is: " + origStringEval)

            if origstring.startswith(origVar):
                sec_part_of_orig_string = origstring.split(origVar)[1]
                newString = newVar + sec_part_of_orig_string
                print("new String is: " + newString)

                x.set(newString)
                print("new x is: " + x.unexpandedString())


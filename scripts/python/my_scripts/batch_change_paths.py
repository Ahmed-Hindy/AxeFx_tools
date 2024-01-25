import hou
import os

origVar = "$HIP"  # orig string to replace
newVar = "$ASSETS"  # replace with this


obj = hou.node("/obj")



for MaterialBuilders in hou.selectedNodes():
    MaterialBuilderContents = MaterialBuilders.children()
    for child in MaterialBuilderContents:
        childTypeName = child.type().name()
        if childTypeName == "principledshader::2.0":
            # print(f"principled shaders found in {MaterialBuilders.name()} and it is called: {child.name()}")


            ### for each principled shader found, lets check the parameters if they contain "_texture"  ###
            parametersAll = child.parms()
            for parameter in parametersAll:

                try:
                    origstring = parameter.unexpandedString()
                    ###  now we have all parameters in every principled shader that has a "origVar" string in it ###
                    ###  we will now replace the origVar with the "newVar" ###
                    if origVar in origstring:
                        # print(f"parameter is {parameter.unexpandedString()}")
                        sec_part_of_orig_string = origstring.split(origVar)[1]
                        newString = newVar + sec_part_of_orig_string
                        parameter.set(newString)
                        print("new String is: " + newString)
                except:
                    pass


















# for node in MaterialBuilderContents:
#     print(node.name())
#     if node.name() == "principledshader":
#         print(node.name())

    # parms = PrincipledShader.parms()

origStringEval = ""


# for node in nodes:
#
#     parms = node.parms()
#
#     for x in parms:
#         if x.parmTemplate().name() == "file":
#             origstring = x.unexpandedString()
#             print("original String is: " + origstring)
#
#             origStringEval = x.eval()
#             print("original String Evaluated is: " + origStringEval)
#
#             if origstring.startswith(origVar):
#                 sec_part_of_orig_string = origstring.split(origVar)[1]
#                 newString = newVar + sec_part_of_orig_string
#                 print("new String is: " + newString)
#
#                 x.set(newString)
#                 print("new x is: " + x.unexpandedString())


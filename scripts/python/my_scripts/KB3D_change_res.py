import hou

origVar = "4k"  # orig string to replace
newVar = """`chs("../../res")`"""  # replace with this

obj = hou.node("/obj")
nodes = hou.selectedNodes()


# matnet = hou.node('/obj/KB3D_EveryCityEmergencyResponse/matnet') #I disabled it but didnt test it yet, enable if problematic


def getPrincipledShaders(kwargs):
    principledShadersList = []
    for matnet in nodes:
        matnetChildren = matnet.children()
        for child in matnetChildren:
            childTypeName = child.type().name()
            if childTypeName == "materialbuilder":
                # print(f"material builder nodes found in {matnet.name()} and it is called: {child.name()}")
                materialbuilderChildren = child.children()
                for materialbuilderChild in materialbuilderChildren:
                    if materialbuilderChild.type().name() == "principledshader::2.0":
                        # print(f"I found a principled shader called {materialbuilderChild.name()}")
                        principledShader = materialbuilderChild
                        principledShadersList.append(principledShader)
                        # print(f"principledShadersList: {principledShadersList}")
    return principledShadersList


def changeRes(kwargs):
    for principledShader in getPrincipledShaders(kwargs):
        ### for each principled shader found, lets check the parameters if they contain "_texture"  ###
        parametersAll = principledShader.parms()
        parameterTexture = []
        for parameter in parametersAll:
            if parameter.name().endswith("_texture"):
                parameterTexture.append(parameter)
                # print(f"parameters found = {parameterTexture.name()}")

        ###  now we have all parameters in every principled shader that has a "origVar" string in it ###
        ###  we will now replace the origVar with the "newVar" ###
        for x in parameterTexture:
            origString = x.unexpandedString()
            print(f"origString before was {origString}")
            print(f"newvar is {newVar} and its type is")
            if origVar in origString:
                print(f"origVar is {origVar}")
                origString = origString.replace(origVar, newVar)
                print(f"origString after is {origString}")
                x.set(origString)
                # print("new String is: " + newString)


def changeRough(kwargs):
    for principledShader in getPrincipledShaders(kwargs):
        # print(f"principledShader: {principledShader}")
        parametersAll = principledShader.parms()
        principledShader.parm("rough").set(1)
        print(f"changed roughness !!!!!!!")


# available functions to call from shelf tool :)

if __name__ == '__main__':
    print('name is main')

# changeRes(kwargs)
# changeRough(kwargs)

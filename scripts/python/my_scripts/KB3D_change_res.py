import hou

origVar = "4k"  # orig string to replace
newVar  = """`chs("../../res")`"""  # replace with this
obj     = hou.node("/obj")


# def


def add_str_res_parm_to_node(node, param_name='parm_name', label='parm_label', default_value="4k") -> None:
    """
    function: adds a string parameter for a node.
    need to make sure the input is a valid node object and not a list, currently this is hardcoded in the next 3 lines,
    maybe a seperate validator function?
    """
    print(f'//{node.type().name()=}')
    if node.type().name() != 'matnet':
        raise ValueError("Invalid hou.Node object provided.")

    # Create a string parameter template with a default value
    parm_template = hou.StringParmTemplate(param_name, label, 1, default_value=[default_value])
    # Get the existing parameter group from the node
    parm_group = node.parmTemplateGroup()
    # Append the new parameter template to the group
    parm_group.append(parm_template)
    # Update the node with the new parameter group
    node.setParmTemplateGroup(parm_group)


def getPrincipledShaders(kwargs, node):
    principledShadersList = []
    matnetChildren = node.children()
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


def changeRes(kwargs, nodes):
    for principledShader in getPrincipledShaders(kwargs, nodes):
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
            # print(f"origString before was {origString}")
            # print(f"newvar is {newVar} and its type is")
            if origVar in origString:
                # print(f"origVar is {origVar}")
                origString = origString.replace(origVar, newVar)
                # print(f"origString after is {origString}")
                x.set(origString)
                # print("new String is: " + newString)


def changeRough(kwargs, nodes):
    for principledShader in getPrincipledShaders(kwargs, nodes):
        # print(f"principledShader: {principledShader}")
        parametersAll = principledShader.parms()
        principledShader.parm("rough").set(1)
        print(f"changed roughness !!!!!!!")


# available functions to call from shelf tool :)

if __name__ == '__main__':
    print('name is main')

# changeRes(kwargs)
# changeRough(kwargs)

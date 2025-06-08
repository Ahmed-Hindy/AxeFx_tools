import hou
""" execute KB3DProcessor().run() on the matnet in a KB3D provided hipfile """


class KB3DProcessor:
    def __init__(self):
        self.orig_string = "4k"  # orig string to replace
        self.new_string  = r'`chs("../../res")`'  # replace with this
        self.obj = hou.node("/obj")
        self.matnet_node = None

        selected_nodes = hou.selectedNodes()
        if not selected_nodes:
            hou.ui.displayMessage(text='No node selected!')
            return
        if not isinstance(selected_nodes[0], hou.ShopNode):
            hou.ui.displayMessage("Please select a valid Material Network")
            return

        self.matnet_node = selected_nodes[0]

    def add_str_res_parm_to_node(self, node, param_name='parm_name', label='parm_label', default_value="4k"):
        """
        function: adds a string parameter for a node.
        need to make sure the input is a valid node object and not a list, currently this is hardcoded in the next 3 lines,
        maybe a seperate validator function?
        """
        if node.parm(param_name):
            print("WARNING: Material Network already modified.")
            return

        # Create a string parameter template with a default value
        parm_template = hou.StringParmTemplate(param_name, label, 1, default_value=[default_value])
        # Get the existing parameter group from the node
        parm_group = node.parmTemplateGroup()
        # Append the new parameter template to the group
        parm_group.append(parm_template)
        # Update the node with the new parameter group
        node.setParmTemplateGroup(parm_group)


    def get_principled_shaders(self):
        """
        :return: a list of all found principled shaders nested in
                 <matnet>/<materialbuilder>nodes/<principledshader::2.0>
        """
        matnet_children = self.matnet_node.children()
        material_builders_list = [child for child in matnet_children if child.type().name() == "materialbuilder"]

        principled_shaders_list = []
        for material_builder in material_builders_list:
            material_builder_children = material_builder.children()
            principled_shaders_list.extend([child for child in material_builder_children if child.type().name() == "principledshader::2.0"])

        # print(f"\n{principled_shaders_list=}\n")
        return principled_shaders_list


    def change_resolution(self, principled_shader):
        ### for each principled shader found, lets check the parameters if they contain "_texture"  ###
        all_parameters = principled_shader.parms()
        texture_parameters = [parameter for parameter in all_parameters if parameter.name().endswith("_texture")]

        ###  now we have all parameters in every principled shader that has a "origVar" string in it ###
        ###  we will now replace the origVar with the "newVar" ###
        for x in texture_parameters:
            original_string = x.unexpandedString()
            if self.orig_string not in original_string:
                continue
            original_string = original_string.replace(self.orig_string, self.new_string)
            x.set(original_string)


    def change_rough(self, principled_shader):
        principled_shader.parm("rough").set(1)
        # print(f"changed roughness for {principled_shader.parent().path()}")

    def run(self):
        """
        Main function to run from shelf. runs on a matnet
        """
        if not self.matnet_node:
            return

        self.add_str_res_parm_to_node(node=self.matnet_node, param_name='res', label='res', default_value="4k")
        for principledShader in self.get_principled_shaders():
            self.change_resolution(principledShader)
            self.change_rough(principledShader)

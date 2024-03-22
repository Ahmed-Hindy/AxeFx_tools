"""
copyright Ahmed Hindy. please mention the original author if you used this any part of this code
"""

import hou
from typing import Dict
# from pprint import pprint


def get_selected_nodes():
    return hou.selectedNodes()

class MaterialProcessor():
    def __init__(self):
        global mysel
        # mysel = hou.selectedNodes()
        # self.safetycheck()

    @staticmethod
    def get_current_directory():
        current_tab = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor, 0)
        current_tab_parent = current_tab.pwd()
        print(f"current_tab_parent.type().name() is {current_tab_parent.type().name()}")
        return current_tab_parent

    ###### SAFETY TO CHECK THE CURRENT SELECTION, IF NOTHING OR IF NOT A PRINCIPLE SHADER THEN SHOW A MESSAGE
    def safetycheck(self):
        acceptable_material_node =  ["principledshader::2.0", "arnold_materialbuilder", "rs_materialbuilder"]

        if mysel==():
            hou.ui.displayMessage("Please select a principleShader to convert")
        else :
            type = mysel[0].type()
            if type.name() in acceptable_material_node:
                pass

            else:
                hou.ui.displayMessage("Current selected node is a : " + type.description() + """
                
                You need to select a node of type PrincipledShader""")
                return

    @staticmethod
    def get_principled_texture_nodes():
        """
        Get all Principled texture nodes in the current scene.
        """
        texture_nodes = []
        for node in hou.node("/").allSubChildren():
            if node.type().name() == "principledshader::2.0":
                texture_nodes.append(node)
        return texture_nodes

    @staticmethod
    def get_enabled_texture_parms_for_principled_shader(node) -> list:
        """returns all parameters on a node that have '<tex_name>_useTexture' enabled"""
        input_tex_parm_list = []
        for parm in node.parms():
            if '_useTexture' in parm.name():
                if parm.eval() == 1:
                    input_tex_str  = parm.name().split('_useTexture')[0] + '_texture'
                    input_tex_parm = node.parm(input_tex_str)
                    # print(f'{input_tex_parm=}')
                    input_tex_parm_list.append(input_tex_parm)
        return input_tex_parm_list

    @staticmethod
    def get_texture_maps_from_parms(input_parms: hou.parm) -> Dict[str, str]:
        """
        takes input parameters list and returns a dict containing {parm.name() : parm.value())
        if there is '$F4' or '<UDIM>' included in the parameter value they won't be evaluated
        """
        textures_dict = {}
        for parm in input_parms:
            textures_dict[parm.name()] = parm.unexpandedString()
            print(f'{textures_dict=}')
        return textures_dict
    
    from typing import Dict

    @staticmethod
    def normalize_texture_map_keys(texture_dict: Dict[str, str]) -> Dict[str, str]:
        """
        takes in dictionary from 'get_texture_maps_from_parms()'
        Normalizes the dictionary keys related to the names of the texture parameters,
        for example if [key] = 'basecolor_texture' like in 'principledshader::2.0 then it will rename it to 'albedo'
        note to self: added 'albedo' and 'rough' for now, need to add the rest of the input textures.
        """
        normalized_dict = {}

        for key, value in texture_dict.items():
            if any(k in key for k in ['albedo', 'diffuse', 'basecolor']):
                normalized_dict['albedo'] = value
            elif any(k in key for k in ['rough']):
                normalized_dict['rough'] = value
            else:
                print(f'/// {key=} is {value=}')
                normalized_dict[key] = value

        return normalized_dict


class NotUsed():
    @staticmethod
    def convert_texture_node_to_arnold(texture_node):
        """
        Convert a Principled texture node to Arnold Standard Surface.
        """
        # Create a new Arnold Standard Surface node
        arnold_node = hou.node("/").createNode("arnold_surface")

        # Copy parameters from the Principled texture node to the Arnold Standard Surface node
        for param in texture_node.params():
            arnold_node.setParam(param.name(), param.evalAsString())

        # Connect the new node to the same inputs as the Principled texture node
        for input_name in texture_node.inputs():
            input_node = texture_node.input(input_name).node()
            arnold_node.setInput(input_name, input_node)


    @staticmethod
    def create_mat_arnold_material(name, texture_node, parent_node):
        """
        Create an Arnold material with a Standard Surface node and connected image nodes.
        """
        # Create an Arnold material builder node
        arnold_material = parent_node.createNode("arnold_material")
        arnold_material.setName(name)

        # Create an Arnold Standard Surface node
        arnold_surface = arnold_material.createNode("arnold_surface")

        # Copy parameters from the texture node to the Arnold Standard Surface node
        for param in texture_node.params():
            arnold_surface.setParam(param.name(), param.evalAsString())

        # Connect the texture nodes to the Arnold Standard Surface node
        for input_name in texture_node.inputs():
            input_node = texture_node.input(input_name).node()
            arnold_surface.setInput(input_name, input_node)

        # Connect the Arnold Standard Surface node to the output of the Arnold material builder node
        arnold_material.setOutput(0, arnold_surface)

        return arnold_material


    def create_mat_usdpreview(self, path):

            matcontext = hou.node(path)
            #mysel = hou.selectedNodes()[0]
            usdmat = matcontext.createNode("usdpreviewsurface", mysel.name() + "_previewUSD")

            albedo = matcontext.createNode("usduvtexture::2.0", "USD_albedo")
            rough = matcontext.createNode("usduvtexture::2.0", "USD_roughness")
            primvar = matcontext.createNode("usdprimvarreader","usd_primvar_ST")

            primvar.parm("signature").set("float2")
            primvar.parm("varname").set("st")

            #connect USD MAT with textures
            usdmat.setInput(0, albedo,4 )
            usdmat.setInput(5, rough,4 )

            #connect USD textures with primvar
            albedo.setInput(1, primvar, 0)
            rough.setInput(1, primvar, 0)

            #set albedo path
            path = mysel.parm("basecolor_texture").eval()
            albedo.parm("file").set(path)

            #set roughness path
            path = mysel.parm("rough_texture").eval()
            rough.parm("file").set(path)

            #create opacity if exists
            if mysel.parm("opaccolor_useTexture").eval() == 1:
                path = mysel.parm("opaccolor_texture").eval()
                opacity = matcontext.createNode("usduvtexture::2.0", "USD_opacity")
                opacity.parm("file").set(path)
                opacity.setInput(1, primvar, 0)
                usdmat.setInput(8, opacity, 0)

            #set USDpreview settings
            usdmat.parm("opacityThreshold").set(0.2)
            usdmat.parm("useSpecularWorkflow").set(1)
            matcontext.layoutChildren()

            test = matcontext.outputs()
            if len(test)>0:
                if (test[0].type().description()) == "Component Material":
                    #setting component material - materialpath with mtlX
                    test[0].parm("matspecpath1").set("/ASSET/mtl/" + matsubnet.name()  )

                    #creating assign material within componentMaterial
                    edit = test[0].node("edit")
                    assign = edit.createNode("assignmaterial")
                    output = edit.node("output0")
                    subinputs = edit.indirectInputs()[0]
                    assign.setInput(0, subinputs)
                    output.setInput(0, assign)
                    edit.layoutChildren()
                    #setting assign material
                    assign.parm("matspecpath1").set("/ASSET/mtl/" + usdmat.name())
                    assign.parm("primpattern1").set("/*")

                    purpose = assign.parm("bindpurpose1")
                    purpose.set(purpose.menuItems()[-1])


    @staticmethod
    def convert_principled_textures_to_arnold():
        """
        Convert all Principled texture nodes in the current scene to Arnold Standard Surface.
        """
        texture_nodes = get_principled_texture_nodes()
        for texture_node in texture_nodes:
            convert_texture_node_to_arnold(texture_node)

    # convert_principled_textures_to_arnold()

class Convert():
    @staticmethod
    def create_mtlx_shader(mat_context, node_name='', input_tex_maps_list=[]):
        matsubnet  = mat_context.createNode("subnet", node_name + "_materialX")

        ## DEFINE OUTPUT SURFACE
        surfaceoutput = matsubnet.createNode("subnetconnector", "surface_output")
        surfaceoutput.parm("parmname").set("surface")
        surfaceoutput.parm("parmlabel").set("Surface")
        surfaceoutput.parm("parmtype").set("surface")
        surfaceoutput.parm("connectorkind").set("output")

        ## DEFINE OUTPUT DISPLACEMENT
        dispoutput = matsubnet.createNode("subnetconnector", "displacement_output")
        dispoutput.parm("parmname").set("displacement")
        dispoutput.parm("parmlabel").set("Displacement")
        dispoutput.parm("parmtype").set("displacement")
        dispoutput.parm("connectorkind").set("output")

        # CREATE MATERIALX STANDARD
        mtlx = matsubnet.createNode("mtlxstandard_surface", "surface_mtlx")
        surfaceoutput.setInput(0, mtlx)

        # CREATE ALBEDO
        path = mysel.parm("basecolor_texture").eval()
        albedo = matsubnet.createNode("mtlximage", "ALBEDO")
        albedo.parm("file").set(path)
        mtlx.setInput(1, albedo)

        # CREATE METALLIC
        if mysel.parm("metallic_useTexture").eval() == 1:
            path = mysel.parm("metallic_texture").eval()
            metal = matsubnet.createNode("mtlximage", "METALLIC")
            metal.parm("signature").set("0")
            metal.parm("file").set(path)
            mtlx.setInput(3, metal)

        # CREATE ROUGHNESS
        path = mysel.parm("rough_texture").eval()
        rough = matsubnet.createNode("mtlximage", "ROUGHNESS")
        rough.parm("file").set(path)
        rough.parm("signature").set("0")
        mtlx.setInput(6, rough)

        # CREATE SPECULAR
        if mysel.parm("reflect_useTexture").eval() == 1:
            path = mysel.parm("reflect_texture").eval()
            spec = matsubnet.createNode("mtlximage", "REFLECT")
            spec.parm("file").set(path)
            mtlx.setInput(5, spec)

        # CREATE OPACITY IF NEEDED
        if mysel.parm("opaccolor_useTexture").eval() == 1:
            path = mysel.parm("opaccolor_texture").eval()
            opac = matsubnet.createNode("mtlximage", "OPACITY")
            opac.parm("file").set(path)
            mtlx.setInput(38, opac)

        # CREATE NORMAL
        if mysel.parm("baseBumpAndNormal_enable").eval() == 1:
            path = mysel.parm("baseNormal_texture").eval()
            normal = matsubnet.createNode("mtlximage", "NORMAL")
            normal.parm("signature").set("vector3")
            plugnormal = matsubnet.createNode("mtlxnormalmap")
            normal.parm("file").set(path)
            mtlx.setInput(40, plugnormal)
            plugnormal.setInput(0, normal)

        # CREATE DISPLACEMENT
        if mysel.parm("dispTex_enable").eval() == 1:
            # GETTING THE PARAMETERS VALUE
            path = mysel.parm("dispTex_texture").eval()
            offset = mysel.parm("dispTex_offset").eval()
            scale = mysel.parm("dispTex_scale").eval()
            # CREATING DISPLACE NODES
            displace = matsubnet.createNode("mtlximage", "DISPLACE")
            plugdisplace = matsubnet.createNode("mtlxdisplacement")
            remapdisplace = matsubnet.createNode("mtlxremap", "OFFSET_DISPLACE")
            # SETTING PARAMETERS DISPLACE
            # set remap
            remapdisplace.parm("outlow").set(offset)
            remapdisplace.parm("outhigh").set(1 + offset)
            # set scale displace
            plugdisplace.parm("scale").set(scale)
            # set image displace
            displace.parm("file").set(path)
            displace.parm("signature").set("0")

            # SETTING INPUTS
            dispoutput.setInput(0, plugdisplace)
            plugdisplace.setInput(0, remapdisplace)
            remapdisplace.setInput(0, displace)

        matsubnet.layoutChildren()
        return matsubnet



    @staticmethod
    def convert_to_mtlx(input_mat_node, mat_context):
        """takes a material VOP node and converts it to MTLX mat builder"""
        input_node_name = input_mat_node.name()
        mtlx_subnet     = Convert.create_mtlx_shader(mat_context, input_node_name, input_tex_maps_list=[])
        return mtlx_subnet




def run():
    selected_nodes = get_selected_nodes()
    mat_context    = hou.node('/mat')
    for input_node in selected_nodes:
        enabled_tex_parms = MaterialProcessor.get_enabled_texture_parms_for_principled_shader(input_node)
        # print(f'{enabled_tex_parms=}')
        input_textures_dict = MaterialProcessor.get_texture_maps_from_parms(enabled_tex_parms)
        normalized_input_tex_dict = MaterialProcessor.normalize_texture_map_keys(input_textures_dict)
        # now we need to input the texture dictionary into the newly created MTLX subnet...
        Convert.convert_to_mtlx(input_node, mat_context)

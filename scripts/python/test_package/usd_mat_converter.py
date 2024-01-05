
"""
Author : Mahmoud Kamal 2022-2023

This script to extracting information about shaders from usd sublayer node, specifically their type, properties, and connections to other nodes.

The script gets the stage from the usdz file.
then iterates through all the prims (basic building blocks that make up a scene) in the stage using TraverseAll().

For each prim, if it is a shader, the script extracts its name, type, and properties.
It also checks if the shader has a material:binding relationship, which indicates that it is assigned to a mesh.

For each property of the shader, the script extracts its name, type, and value.
It also checks if the property is connected to another node, and if so, it extracts the name, type, and connected attribute of the other node.
This information is stored in a dictionary called shader_data.


"""

import os
import pprint
import json
import pxr.Usd as Usd
import pxr.UsdGeom as UsdGeom
import hou
from importlib import reload

class SolarisMaterialOverride:
    def init_data(self,input_usd_file=None, target_stage=None):

        stage = None
        prims = None
        if not input_usd_file:
            if target_stage:

                stage = target_stage.stage()
            else:
                raise Exception("Sorry, You need to set input usd file path or set stage node")
                return stage, prims
        else:
            if not target_stage:
                stage = Usd.Stage.Open(input_file)

            else:
                raise Exception("Sorry, You need to set input usd file path or set stage node")
                return stage, prims

        prims = stage.TraverseAll()
        print(f'init_data()----- {prims=} \n')
        return stage, prims


    def collect_data_Arnold(self, input_usd_file=None, target_stage=None):              ### this is currently limited to Arnold usd shaders, need to refactor for usdPreviewSurface
        stage, prims = self.init_data(input_usd_file, target_stage)
        shader_data = {}
        assign_data = {}

        if not stage and not prims:
            return shader_data,assign_data

        for prim in prims:
            if prim:
                prim_name = prim.GetName()
                if prim.GetTypeName() != 'Material':
                    if prim.HasRelationship('material:binding'):
                        # Get assigned material to the mesh
                        material_binding = prim.GetRelationship('material:binding').GetTargets()
                        if material_binding[0].GetPrimPath() not in assign_data:
                            assign_data[material_binding[0].GetPrimPath()] = []
                        assign_data[material_binding[0].GetPrimPath()].append(prim.GetPrimPath())

                if prim.GetTypeName() == 'Material':
                    print(f'collect_Arnold_data()----- {prim=} \n')

                    material_path = str(prim.GetPrimPath()).split(prim.GetName())[0]
                    # print(f'collect_Arnold_data()----- {material_path=} \n')
                    shader_data[prim.GetName()] = {}
                    shader_data[prim.GetName()]["path"] = material_path
                    shader_data[prim.GetName()]["children"] = {}
                    print(f'collect_Arnold_data()----- {shader_data=} \n')

                    if prim.HasRelationship('material:binding'):
                        ### Get assigned material to the mesh
                        material_binding = prim.GetRelationship('material:binding').GetTargets()
                        print(f'collect_Arnold_data()----- {material_binding=} \n')

                    for shader_node in prim.GetChildren():

                        shader_node_type = shader_node.GetAttribute("info:id").Get()
                        shader_node_name = shader_node.GetName()
                        shader_data[prim.GetName()]["children"][shader_node_name] = {}
                        shader_data[prim.GetName()]["children"][shader_node_name]["node_type"] = shader_node_type
                        shader_data[prim.GetName()]["children"][shader_node_name]["attributes"] = {}
                        print(f'collect_Arnold_data()----- {shader_data[prim.GetName()]["children"]=}')
                        for attribute in shader_node.GetProperties():  ### gets all shader primvars
                            attribute_name = attribute.GetName()
                            if "info" in attribute_name:
                                continue

                            attribute_value = shader_node.GetAttribute(attribute_name).Get()

                            if attribute_name != "material:binding":
                                print(f'collect_Arnold_data()----- {attribute_name=}')
                                if "inputs" in attribute_name:
                                    shader_data[prim.GetName()]["children"][shader_node_name]["attributes"][attribute_name] = {}
                                    shader_data[prim.GetName()]["children"][shader_node_name]["attributes"][attribute_name]["value"] = attribute_value
                                    print(f'collect_Arnold_data()----- {shader_data[prim.GetName()]["children"][shader_node_name]["attributes"][attribute_name]=}')

                                    if attribute.GetConnections():
                                        shader_data[prim.GetName()]["children"][shader_node_name]["attributes"][attribute_name]["connections"] = {}
                                        connected_node_path = shader_node.GetProperty(attribute_name).GetConnections()[0].GetPrimPath()
                                        connected_node = stage.GetPrimAtPath(connected_node_path)
                                        connected_node_type = connected_node.GetAttribute("info:id").Get()
                                        connected_node_name = connected_node.GetName()
                                        connected_node_attrib = str(shader_node.GetProperty(attribute_name).GetConnections()[0]).split(".")[1]

                                        shader_data[prim.GetName()]["children"][shader_node_name]["attributes"][attribute_name]["connections"][connected_node_name] = {}
                                        shader_data[prim.GetName()]["children"][shader_node_name]["attributes"][attribute_name]["connections"][connected_node_name]["node_type"] = connected_node_type
                                        shader_data[prim.GetName()]["children"][shader_node_name]["attributes"][attribute_name]["connections"][connected_node_name]["connected_node_attribute"] = connected_node_attrib

        # def print_nested_dictionaries(dictionary):
        #     for key, value in dictionary.items():
        #         if isinstance(value, dict):
        #             print_nested_dictionaries(value)
        #         else:
        #             print(f"{key}: {value}")
        # print_nested_dictionaries(shader_data)
        return shader_data, assign_data


    def collect_data_USDPreview(self, input_usd_file=None, target_stage=None):              ### this is currently limited to Arnold usd shaders, need to refactor for usdPreviewSurface
        stage, prims = self.init_data(input_usd_file, target_stage)
        shader_data = {}
        assign_data = {}

        if not stage and not prims:
            return shader_data,assign_data

        for prim in prims:
            if prim:
                prim_name = prim.GetName()
                if prim.GetTypeName() != 'Material':
                    if prim.HasRelationship('material:binding'):
                        # Get assigned material to the mesh
                        material_binding = prim.GetRelationship('material:binding').GetTargets()
                        if material_binding[0].GetPrimPath() not in assign_data:
                            assign_data[material_binding[0].GetPrimPath()] = []
                        assign_data[material_binding[0].GetPrimPath()].append(prim.GetPrimPath())

                if prim.GetTypeName() == 'Material':
                    print(f'collect_data_USDPreview()----- {prim=} \n')

                    material_path = str(prim.GetPrimPath()).split(prim.GetName())[0]
                    # print(f'collect_data_USDPreview()----- {material_path=} \n')
                    shader_data[prim.GetName()] = {}
                    shader_data[prim.GetName()]["path"] = material_path
                    shader_data[prim.GetName()]["children"] = {}
                    print(f'collect_data_USDPreview()----- {shader_data=} \n')

                    if prim.HasRelationship('material:binding'):
                        ### Get assigned material to the mesh
                        material_binding = prim.GetRelationship('material:binding').GetTargets()
                        print(f'collect_data_USDPreview()----- {material_binding=} \n')

                    for shader_node in prim.GetChildren():

                        shader_node_type = shader_node.GetAttribute("info:id").Get()
                        shader_node_name = shader_node.GetName()
                        shader_data[prim.GetName()]["children"][shader_node_name] = {}
                        shader_data[prim.GetName()]["children"][shader_node_name]["node_type"] = shader_node_type
                        shader_data[prim.GetName()]["children"][shader_node_name]["attributes"] = {}
                        # print(f'collect_data_USDPreview()----- {shader_data[prim.GetName()]["children"]=}')
                        for attribute in shader_node.GetProperties():                   ### gets all shader primvars
                            attribute_name = attribute.GetName()
                            if "info" in attribute_name:
                                continue

                            attribute_value = shader_node.GetAttribute(attribute_name).Get()

                            if attribute_name != "material:binding":
                                print(f'collect_data_USDPreview()----- {attribute_name=}')
                                if "inputs" in attribute_name:
                                    shader_data[prim.GetName()]["children"][shader_node_name]["attributes"][attribute_name] = {}
                                    shader_data[prim.GetName()]["children"][shader_node_name]["attributes"][attribute_name]["value"] = attribute_value
                                    print(f'collect_data_USDPreview()----- {shader_data[prim.GetName()]["children"][shader_node_name]["attributes"][attribute_name]=}')

                                    if attribute.GetConnections():
                                        shader_data[prim.GetName()]["children"][shader_node_name]["attributes"][attribute_name]["connections"] = {}
                                        connected_node_path = shader_node.GetProperty(attribute_name).GetConnections()[0].GetPrimPath()
                                        connected_node = stage.GetPrimAtPath(connected_node_path)
                                        connected_node_type = connected_node.GetAttribute("info:id").Get()
                                        connected_node_name = connected_node.GetName()
                                        connected_node_attrib = str(shader_node.GetProperty(attribute_name).GetConnections()[0]).split(".")[1]

                                        shader_data[prim.GetName()]["children"][shader_node_name]["attributes"][attribute_name]["connections"][connected_node_name] = {}
                                        shader_data[prim.GetName()]["children"][shader_node_name]["attributes"][attribute_name]["connections"][connected_node_name]["node_type"] = connected_node_type
                                        shader_data[prim.GetName()]["children"][shader_node_name]["attributes"][attribute_name]["connections"][connected_node_name]["connected_node_attribute"] = connected_node_attrib

        # def print_nested_dictionaries(dictionary):
        #     for key, value in dictionary.items():
        #         if isinstance(value, dict):
        #             print_nested_dictionaries(value)
        #         else:
        #             print(f"{key}: {value}")
        # print_nested_dictionaries(shader_data)
        return shader_data, assign_data


    def create_shaders_Arnold(self, input_usd_file=None, target_stage=None):
        """
        Extract data from usd and start build material networks
        """
        shader_data, assign_data = self.collect_data_Arnold(input_usd_file, target_stage)
        if not shader_data and not assign_data:
            return shader_data, assign_data
        stage = hou.node("/stage")
        mat_lib = stage.createNode("materiallibrary")
        mat_lib.moveToGoodPosition()
        counter = 0
        # print(f'create_override_shaders()----- {shader_data=} \n')
        for shader in shader_data:
            # print(f'create_override_shaders()----- {shader=} \n')
            arnold_net = mat_lib.createNode("arnold_materialbuilder", shader)
            mat_lib.parm("materials").set(counter)
            if counter == 0:
                mat_lib.parm("matpathprefix").set(shader_data[shader]["path"])
                # mat_lib.parm("fillmaterials").pressButton()
            counter += 1

        for node in shader_data[shader]["children"]:                                                ###gets all nodes inside shader networks like Standard Surf
            """
            Create all shader nodes
            """
            # print(f'create_override_shaders()----- {node=} \n')
            # print(f'create_override_shaders()----- {shader_data[shader]["children"][node]["node_type"]=} \n')
            node_type = shader_data[shader]["children"][node]["node_type"].split(":")[1]            ### gets node_type of eg. stnd Surf, remove splitting for usdPreviewSurface

            shader_node = arnold_net.createNode(node_type, node)
            if shader_node.type().name() == "arnold::standard_surface":                             ### need a similar loop for usdPreviewSurface
                """
                If the node is material node
                connect it with 'out node(shading group)' and set material lib node parameter
                """
                mat_lib.parm("materials").set(counter)
                mat_lib.parm("matpath{}".format(counter)).set(shader_data[shader]["path"]+shader)
                mat_lib.parm("matnode{}".format(counter)).set(shader)
                out_material_node = arnold_net.node("OUT_material")
                out_material_node.setInput(0,shader_node,0)

        # for node in shader_data[shader]["children"]:                                                        ### this is a duplicate for loop, why?
            shader_node = arnold_net.node(node)                                                             ### gets the hou.node shader e.g. Std Surf
            # print(f'create_override_shaders()----- {shader_node=} \n')

            for attribute in shader_data[shader]["children"][node]["attributes"]:                           ### loops over all attribs on shader
                """
                Set parameter values and parameters connections with other nodes
                """
                # print(f'create_override_shaders()----- {attribute=}')                                       ### returns e.g. 'inputs:specular_roughness'
                attribute_value = shader_data[shader]["children"][node]["attributes"][attribute]["value"]   ### gets all attribs values
                # print(f'create_override_shaders()----- {attribute_value=}')                                 ### returns 0.095
                attribute_name = "{}".format(attribute.split(":")[1])
                # print(f'create_override_shaders()----- {attribute_name=} \n')                               ### returns e.g. 'specular_roughness'
                if attribute_name:
                    # print( shader_node,attribute_name,attribute_value)

                    if "connections" not in shader_data[shader]["children"][node]["attributes"][attribute]:
                        """
                        Set parameter values  
                        """
                        if shader_node.parm(attribute_name):                                                ### checks if the created shader e.g. std surf has the attribute_name we are looping over
                            parm_type = type(shader_node.parm(attribute_name).eval())
                            # if "@" in attribute_value:                                                    ### gives me errors so I disabled it
                            #     attribute_value = attribute_value.strip("@")
                            shader_node.parm(str(attribute_name)).set(parm_type(attribute_value))           ### sets that parameter to be attribute_value we have
                    else:
                        """
                        Set parameter connections with other nodes
                        """
                        for connected_node in shader_data[shader]["children"][node]["attributes"][attribute]["connections"]:
                            connected_node_name = arnold_net.node(connected_node)

                            output_connected_attribute = shader_data[shader]["children"][node]["attributes"][attribute]["connections"][connected_node]["connected_node_attribute"]

                            input_index = shader_node.inputIndex(attribute_name)

                            output_index = connected_node_name.outputIndex(output_connected_attribute.split(":")[1])

                            inputs = shader_node.input(input_index)
                            if not inputs:
                                shader_node.insertInput(input_index, connected_node_name, output_index)

                # shader_node.parm("{}".format(attribute.split(":")[1])).set(attribute_value)
        print('\n \n')
        return shader_data, assign_data, mat_lib

    def create_shaders_USDPreview(self, input_usd_file=None, target_stage=None):
        """
        Extract data from usd and start build material networks
        """
        shader_data, assign_data = self.collect_data_USDPreview(input_usd_file, target_stage)
        if not shader_data and not assign_data:
            return shader_data, assign_data
        stage = hou.node("/stage")
        mat_lib = stage.createNode("materiallibrary")
        mat_lib.moveToGoodPosition()
        counter = 0
        # print(f'create_override_shaders()----- {shader_data=} \n')
        for shader in shader_data:
            # print(f'create_override_shaders()----- {shader=} \n')
            subnetwork = mat_lib.createNode('subnet', shader)
            mat_lib.parm("materials").set(counter)
            if counter == 0:
                mat_lib.parm("matpathprefix").set(shader_data[shader]["path"])
                # mat_lib.parm("fillmaterials").pressButton()
            counter += 1

        for node in shader_data[shader]["children"]:                                                ###gets all nodes inside shader networks like Standard Surf
            """
            Create all shader nodes
            """
            # print(f'create_override_shaders()----- {node=} \n')
            # print(f'create_override_shaders()----- {shader_data[shader]["children"][node]["node_type"]=} \n')
            node_type = shader_data[shader]["children"][node]["node_type"]                          ### gets node_type of eg. stnd Surf, remove splitting for usdPreviewSurface
            print(f'create_shaders_USDPreview()----- {node_type=}')

            shader_node = subnetwork.createNode(node_type.lower(), node)
            if shader_node.type().name() == "arnold::standard_surface":                             ### need a similar loop for usdPreviewSurface
                """
                If the node is material node
                connect it with 'out node(shading group)' and set material lib node parameter
                """
                mat_lib.parm("materials").set(counter)
                mat_lib.parm("matpath{}".format(counter)).set(shader_data[shader]["path"]+shader)
                mat_lib.parm("matnode{}".format(counter)).set(shader)
                out_material_node = subnetwork.node("OUT_material")
                out_material_node.setInput(0, shader_node, 0)

        # for node in shader_data[shader]["children"]:                                                      ### this is a duplicate for loop, why?
            shader_node = subnetwork.node(node)                                                             ### gets the hou.node shader e.g. Std Surf
            # print(f'create_override_shaders()----- {shader_node=} \n')

            for attribute in shader_data[shader]["children"][node]["attributes"]:                           ### loops over all attribs on shader
                """
                Set parameter values and parameters connections with other nodes
                """
                # print(f'create_override_shaders()----- {attribute=}')                                       ### returns e.g. 'inputs:specular_roughness'
                attribute_value = shader_data[shader]["children"][node]["attributes"][attribute]["value"]   ### gets all attribs values
                # print(f'create_override_shaders()----- {attribute_value=}')                                 ### returns 0.095
                attribute_name = "{}".format(attribute.split(":")[1])
                # print(f'create_override_shaders()----- {attribute_name=} \n')                               ### returns e.g. 'specular_roughness'
                if attribute_name:
                    # print( shader_node,attribute_name,attribute_value)

                    if "connections" not in shader_data[shader]["children"][node]["attributes"][attribute]:
                        """
                        Set parameter values  
                        """
                        if shader_node.parm(attribute_name):                                                ### checks if the created shader e.g. std surf has the attribute_name we are looping over
                            parm_type = type(shader_node.parm(attribute_name).eval())
                            # if "@" in attribute_value:                                                    ### gives me errors so I disabled it
                            #     attribute_value = attribute_value.strip("@")
                            shader_node.parm(str(attribute_name)).set(parm_type(attribute_value))           ### sets that parameter to be attribute_value we have
                    else:
                        """
                        Set parameter connections with other nodes
                        """
                        for connected_node in shader_data[shader]["children"][node]["attributes"][attribute]["connections"]:
                            connected_node_name = subnetwork.node(connected_node)
                            output_connected_attribute = shader_data[shader]["children"][node]["attributes"][attribute]["connections"][connected_node]["connected_node_attribute"]
                            input_index = shader_node.inputIndex(attribute_name)
                            output_index = connected_node_name.outputIndex(output_connected_attribute.split(":")[1])
                            inputs = shader_node.input(input_index)
                            if not inputs:
                                shader_node.insertInput(input_index, connected_node_name, output_index)

                # shader_node.parm("{}".format(attribute.split(":")[1])).set(attribute_value)
        return shader_data, assign_data, mat_lib


    def assign_materials(self, assign_data):
        """
        Create necessary nodes to assign materials to the objects
        using collection node and material assign node
        """
        stage = hou.node("/stage")
        collection_node = stage.createNode("collection")
        collection_node.moveToGoodPosition()
        collection_node.parm("collectioncount").set(len(assign_data))
        material_assign_node =  stage.createNode("assignmaterial")
        material_assign_node.moveToGoodPosition()
        material_assign_node.parm("nummaterials").set(len(assign_data))
        counter = 1
        for material in assign_data:
            material_name = str(material).split("/")[-1]
            material_path = str(material).split(str(material).split("/")[-1])[0]
            collection_node.parm("collectionname{}".format(counter)).set(material_name)
            if counter == 1:
                path = material_path + "collections"
                collection_node.parm("defaultprimpath").set(path)
            for object in assign_data[material]:
                collection_val = collection_node.parm("includepattern{}".format(counter)).eval()
                collection_val = collection_val + "\n" + str(object.GetPrimPath())
                collection_node.parm("includepattern{}".format(counter)).set(collection_val)
                #/Asset/collections.collection:big_robot_steel_Shader
            material_assign_node.parm("primpattern{}".format(counter)).set("{}.collection:{}".format(path,material_name))
            material_assign_node.parm("matspecpath{}".format(counter)).set(material_path+material_name)

            counter += 1
        return collection_node,material_assign_node

    def run_override(self, input_usd_file=None, target_stage=None):
        # import trend_importer
        # reload(trend_importer)
        # importer = trend_importer.TrendImporter(None, None)

        shader_data, assign_data, mat_lib  = self.create_shaders_Arnold(input_usd_file, target_stage)
        collection_node, material_assign_node = self.assign_materials(assign_data)
        if target_stage:
            mat_lib.setInput(0, target_stage)
        if collection_node and material_assign_node:
            collection_node.setInput(0,mat_lib)
            material_assign_node.setInput(0, collection_node)
            # importer.create_network_box([collection_node,material_assign_node,mat_lib], "Material_Override")


    def run_debug(self, input_usd_file=None, target_stage=None):
        # import trend_importer
        # reload(trend_importer)
        # importer = trend_importer.TrendImporter(None, None)

        shader_data, assign_data, mat_lib  = self.create_shaders_USDPreview(input_usd_file, target_stage)
        collection_node, material_assign_node = self.assign_materials(assign_data)
        if target_stage:
            mat_lib.setInput(0, target_stage)
        if collection_node and material_assign_node:
            collection_node.setInput(0,mat_lib)
            material_assign_node.setInput(0, collection_node)
            # importer.create_network_box([collection_node,material_assign_node,mat_lib], "Material_Override")




node = hou.node('/stage/x')

data = SolarisMaterialOverride().run_debug(target_stage=node)


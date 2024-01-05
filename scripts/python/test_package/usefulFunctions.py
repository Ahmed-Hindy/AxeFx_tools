# -*- coding: utf-8 -*-
"""
Documentation:
credits unknown, fetched from github
"""
import hou
import loputils
from pxr import Usd, Sdf, UsdShade, UsdGeom, Gf


def get_bound_geoms(material_prim: Usd.Prim):
    """
    To get all bound geom with specific material prim

    @parm prim: pxr.Prim
    return list(pxr.Prim)
    """

    prim_type = material_prim.GetTypeName()

    if prim_type != 'Material':
        return []

    material_path = material_prim.GetPath()
    stage = material_prim.GetStage()

    geom_prims = []
    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.Imageable):
            continue

        material, material_rel = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial(
            UsdShade.Tokens.full)
        # material_rel = prim.GetRelationship('material:binding')

        if not material_rel.IsValid():
            continue

        if material_path in material_rel.GetTargets():
            geom_prims.append(prim)

    return geom_prims


def add_primvar_to_prim(stage: Usd.Stage,
                        prim_path: Sdf.Path,
                        primvar_name: str,
                        primvar_value=Sdf.ValueTypeNames.String):
    prim = stage.GetPrimAtPath(prim_path)
    primvar = UsdGeom.PrimvarsAPI(prim).CreatePrimvar(primvar_name, Sdf.ValueTypeNames.String)
    primvar.SetInterpolation(UsdGeom.Tokens.constant)
    primvar.Set(primvar_value)

    return primvar


def create_usd_material(stage: Usd.Stage,
                        material_path: Sdf.Path,
                        material_id="UsdPreviewSurface",
                        namespace=None):
    material = UsdShade.Material.Define(stage, material_path)
    shader_path = material_path.AppendChild("surface_shader")
    shader = UsdShade.Shader.Define(stage, shader_path)
    shader.CreateIdAttr(material_id)

    if namespace:
        material.CreateSurfaceOutput(namespace).ConnectToSource(shader.ConnectableAPI(), "surface")
    else:
        material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")

    return material, shader


def add_usd_texture(surface_shader: UsdShade.Shader,
                    shader_path: Sdf.Path,
                    input_name="diffuseColor",
                    input_type=Sdf.ValueTypeNames.Color3f,
                    texture_path="",
                    primvars=None):
    stage = surface_shader.GetPrim().GetStage()

    surface_shader_input = surface_shader.GetInput(input_name)
    if not surface_shader_input:
        surface_shader_input = surface_shader.CreateInput(input_name, input_type)

    # texture file prim
    texture_shader = UsdShade.Shader.Define(stage, shader_path)
    texture_shader.CreateIdAttr('UsdUVTexture')

    # outputs
    texture_output = texture_shader.CreateOutput('rgb', Sdf.ValueTypeNames.Float3)

    # inputs
    texture_tex_input = texture_shader.CreateInput('file', Sdf.ValueTypeNames.Asset)
    texture_st_input = texture_shader.CreateInput("st", Sdf.ValueTypeNames.Float2)

    # connections
    surface_shader_input.ConnectToSource(texture_output)
    # surface_shader_input.ConnectToSource(shader.ConnectableAPI(), "rgb")

    # Set textures
    texture_tex_input.Set(texture_path)

    # st shader
    st_shader = UsdShade.Shader.Define(stage, shader_path.AppendChild("st_reader"))
    st_shader.CreateIdAttr("UsdPrimvarReader_float2")
    st_shader.CreateInput("varname", Sdf.ValueTypeNames.String).Set("st")
    st_output = st_shader.CreateOutput("result", Sdf.ValueTypeNames.Float2)
    texture_st_input.ConnectToSource(st_output)

    # primvars
    if primvars:
        primvar_reader_shader = UsdShade.Shader.Define(stage,
                                                       shader_path.AppendChild("primvar_reader"))
        primvar_reader_shader.CreateIdAttr("UsdPrimvarReader_string")
        primvar_reader_shader.CreateInput("varname", Sdf.ValueTypeNames.String).Set(primvars)
        reader_output = primvar_reader_shader.CreateOutput("result", Sdf.ValueTypeNames.String)
        texture_tex_input.ConnectToSource(reader_output)


def add_preview_attrs(preview_shader: UsdShade.Shader):
    preview_shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(
        Gf.Vec3f(1.0, 0.0, 0.0))

    add_usd_texture(preview_shader,
                    preview_shader.GetPath().GetParentPath().AppendChild("diffuse"),
                    input_name="diffuseColor",
                    input_type=Sdf.ValueTypeNames.Color3f,
                    texture_path="foo/bar.ext"
                    )


def add_mtlx_attrs(preview_shader: UsdShade.Shader):
    preview_shader.CreateInput("base_color", Sdf.ValueTypeNames.Color3f).Set(
        Gf.Vec3f(0.0, 1.0, 0.0))

    add_usd_texture(preview_shader,
                    preview_shader.GetPath().GetParentPath().AppendChild("diffuse"),
                    input_name="base_color",
                    input_type=Sdf.ValueTypeNames.Color3f,
                    # primvars="foo:bar"
                    )


def bind_material(stage: Usd.Stage, prim: Usd.Prim, mtl_path: Sdf.Path, purpose=UsdShade.Tokens.full):
    material = UsdShade.Material.Define(stage, mtl_path)

    if prim.GetTypeName() == 'GeomSubset':
        prim.GetAttribute("familyName").Set("materialBind")

    UsdShade.MaterialBindingAPI(prim).Bind(material, materialPurpose=purpose)


def create_material(stage: Usd.Stage, material_path: Sdf.Path, geo_path: Sdf.Path):
    preview_path = material_path.AppendChild("__preview")
    mtlx_path = material_path.AppendChild("__mtlx")

    mtlx_mtl, mtlx_shader = create_usd_material(
        stage,
        mtlx_path,
        material_id="ND_standard_surface_surfaceshader",
        namespace="mtlx"
    )
    preview_mtl, preview_shader = create_usd_material(
        stage,
        preview_path,
        material_id="UsdPreviewSurface"
    )

    add_preview_attrs(preview_shader)
    add_mtlx_attrs(mtlx_shader)

    geo_prim = stage.DefinePrim(geo_path)
    UsdShade.MaterialBindingAPI(geo_prim).Bind(mtlx_mtl, materialPurpose=UsdShade.Tokens.full)
    UsdShade.MaterialBindingAPI(geo_prim).Bind(preview_mtl, materialPurpose=UsdShade.Tokens.preview)



# example usage:
# print('start')
# node        = hou.pwd()     ### node type: <hou.OpNodeType for Lop pythonscript>
# stage       = node.editableStage()
# geo_path    = Sdf.Path('/shaderball/Geometry/PreviewSurface')
# mat_path    = Sdf.Path('/shaderball/Materials')
# print(f'geo_path: {geo_path}, mat_path: {mat_path}')
# create_material(stage, mat_path, geo_path)

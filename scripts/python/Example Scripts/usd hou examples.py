# LOP python example to create some stuff

import hou
from pxr import Usd, UsdShade, Sdf, UsdGeom, Gf, Kind



modelRoot = UsdGeom.Xform.Define(stage, "/TexModel")
Usd.ModelAPI(modelRoot).SetKind(Kind.Tokens.component)
billboard = UsdGeom.Mesh.Define(stage, "/TexModel/card")
billboard.CreatePointsAttr([(0,0,0),(9.6,0,0), (9.6,5.4,0),(0,5.4,0)])
billboard.CreateFaceVertexCountsAttr([4])
billboard.CreateFaceVertexIndicesAttr([0,1,2,3])
billboard.CreateExtentAttr([(0,0, 0), (9.6,5.4, 0)])
texCoords = UsdGeom.PrimvarsAPI(billboard).CreatePrimvar("st",
                                    Sdf.ValueTypeNames.TexCoord2fArray,
                                    UsdGeom.Tokens.varying)
texCoords.Set([(0, 0), (1, 0), (1,1), (0, 1)])

# Now make a Material that contains a PBR preview surface, a texture reader,
# and a primvar reader to fetch the texture coordinate from the geometry
material = UsdShade.Material.Define(stage, '/TexModel/boardMat')
stInput = material.CreateInput('frame:stPrimvarName', Sdf.ValueTypeNames.Token)
stInput.Set('st')
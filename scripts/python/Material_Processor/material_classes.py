from dataclasses import dataclass, field
from typing import Optional, Dict, List

@dataclass
class NodeInfo:
    node_type: str
    traversal_path: str
    connected_input_index: Optional[int] = None

    def __str__(self):
        return f"NodeInfo(node_type={self.node_type}, traversal_path={self.traversal_path}, connected_input_index={self.connected_input_index})"

@dataclass
class TextureInfo:
    file_path: str
    nodes: List[NodeInfo] = field(default_factory=list)

    def __str__(self):
        return f"TextureInfo(file_path={self.file_path}, nodes={self.nodes})"

@dataclass
class MaterialData:
    material_name: str
    material_path: Optional[str] = None
    textures: Dict[str, TextureInfo] = field(default_factory=dict)

    def __str__(self):
        return self._pretty_print()

    def __repr__(self):
        return self._pretty_print()

    def _pretty_print(self):
        return f"MaterialData(material_name={self.material_name}, textures={self.textures})"

from dataclasses import dataclass, field
from typing import Optional, Dict, List

@dataclass
class NodeParameter:
    name: str
    value: any
    standardized_name: Optional[str] = None  # Add a standardized name attribute

    def __str__(self):
        return f""
        # return f"NodeParameter(name={self.name}, value={self.value}, standardized_name={self.standardized_name})"

@dataclass
class NodeInfo:
    node_type: str
    node_name: str
    parameters: List[NodeParameter] = field(default_factory=list)
    traversal_path: str = ""
    connected_input_index: Optional[int] = None
    child_nodes: List['NodeInfo'] = field(default_factory=list)  # Added to store child nodes

    # New attributes specific to output nodes
    is_output_node: bool = False
    output_type: Optional[str] = None  # Could be 'surface', 'displacement', etc.

    def __str__(self):
        b = "Not Output"
        if self.is_output_node:
            b = f"{self.is_output_node}, output_type = {self.output_type})"
        return(f"NodeInfo(node_type={self.node_type}, node_name={self.node_name},"
                f"traversal_path={self.traversal_path}, connected_input_index={self.connected_input_index},"
                f"child_nodes={self.child_nodes}, {b})")

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
    nodes: List[NodeInfo] = field(default_factory=list)

    def __str__(self):
        return self._pretty_print()

    def __repr__(self):
        return self._pretty_print()

    def _pretty_print(self):
        return f"MaterialData(material_name={self.material_name}, textures={self.textures}, nodes={self.nodes})"

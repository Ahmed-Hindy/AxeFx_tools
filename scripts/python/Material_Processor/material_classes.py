from dataclasses import dataclass, field
from typing import Optional, Dict, List

@dataclass
class NodeParameter:
    """
    Represents a parameter of a node in a material network.

    Attributes:
        name (str): The name of the parameter.
        value (any): The value of the parameter.
        standardized_name (Optional[str]): A standardized name for the parameter, if applicable.
    """
    name: str
    value: any
    standardized_name: Optional[str] = None  # Add a standardized name attribute

    def __str__(self):
        return f""
        # return f"NodeParameter(name={self.name}, value={self.value}, standardized_name={self.standardized_name})"

@dataclass
class NodeInfo:
    """
    Represents a node in a material network.

    Attributes:
        node_type (str): The type of the node.
        node_name (str): The name of the node.
        parameters (List[NodeParameter]): A list of parameters associated with the node.
        node_path (str): The path to the node within the network.
        connected_input_index (Optional[int]): The index of the input this node is connected to, if any.
        child_nodes (List['NodeInfo']): A list of child nodes connected to this node.
        is_output_node (bool): Whether this node is an output node.
        output_type (Optional[str]): The type of output, e.g., 'surface', 'displacement', etc.
    """
    node_type: str
    node_name: str
    parameters: List[NodeParameter] = field(default_factory=list)
    node_path: str = ""
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
                f"node_path={self.node_path}, connected_input_index={self.connected_input_index},"
                f"child_nodes={self.child_nodes}, {b})")
    def __repr__(self):
        b = "Not Output"
        if self.is_output_node:
            b = f"{self.is_output_node}, output_type = {self.output_type})"
        return(f"NodeInfo(node_type={self.node_type}, node_name={self.node_name},"
                f"node_path={self.node_path}, connected_input_index={self.connected_input_index},"
                f"child_nodes={self.child_nodes}, {b})")

@dataclass
class TextureInfo:
    """
    Represents texture information in a material network.

    Attributes:
        file_path (str): The file path to the texture.
        nodes (List[NodeInfo]): A list of nodes associated with this texture.
    """
    file_path: str
    nodes: List[NodeInfo] = field(default_factory=list)

    def __str__(self):
        return f"TextureInfo(file_path={self.file_path}, nodes={self.nodes})"

@dataclass
class MaterialData:
    """
    Represents the data for a material, including its textures and nodes.

    Attributes:
        material_name (str): The name of the material.
        material_path (Optional[str]): The path to the material within the network.
        textures (Dict[str, TextureInfo]): A dictionary of texture information associated with the material.
        nodes (List[NodeInfo]): A list of nodes that make up the material network.
    """
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

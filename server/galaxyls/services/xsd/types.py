""" Type definitions for XSD processing.
"""

from lxml import etree
from anytree import NodeMixin, RenderTree, findall, Resolver, ResolverError
from typing import List, Dict, Optional
from pygls.types import MarkupContent, MarkupKind
from .constants import MSG_NO_DOCUMENTATION_AVAILABLE


class XsdBase:
    """Base class that encapsulates an element from the XSD schema.

    It contains common information and functionality shared by
    XML nodes and attributes.
    """

    def __init__(self, name: str, element):
        super(XsdBase, self).__init__()
        self.name: str = name
        self.xsd_element = element

    def __repr__(self) -> str:
        return self.name

    def get_doc(self, lang: str = "en") -> MarkupContent:
        """Gets the Markdown documentation associated with this element
        from the XSD schema.

        If there is no documentation in the schema for the element,
        a message indicating this will be returned instead.

        Args:
            lang (str, optional): The language code of the documentation
            to retrieve. Defaults to "en" (English).

        Returns:
            [str]: The documentation text or a message indicating
            there is no documentation.
        """
        try:
            doc = self.xsd_element.xpath(
                "./xs:annotation/xs:documentation[@xml:lang=$lang]/text()", namespaces=self.xsd_element.nsmap, lang=lang,
            )
            return MarkupContent(MarkupKind.Markdown, doc[0].strip())
        except BaseException:
            return MarkupContent(MarkupKind.Markdown, MSG_NO_DOCUMENTATION_AVAILABLE)


class XsdAttribute(XsdBase):
    """Represents an attribute in an XML tag.

    It contains information about the attribute extracted
    from the XSD schema.

    Args:
        XsdBase: Inherits base functionality from XsdBase.
    """

    def __init__(
        self, name: str, element: etree.Element, type_name: Optional[str] = None, is_required: bool = False,
    ):
        super(XsdAttribute, self).__init__(name, element)
        self.type_name: str = type_name
        self.is_required: bool = is_required
        self.enumeration: List[str] = []


class XsdNode(XsdBase, NodeMixin):
    """Represents a particular XML tag.

    The node contains information extracted from the XSD schema
    about the XML tag, possible descendants, attributes, etc.

    Args:
        XsdBase: Inherits base functionality from XsdBase.
        NodeMixin: Inherits tree node functionality from NodeMixin.
    """

    def __init__(self, name: str, element: etree.Element, parent: NodeMixin = None):
        super(XsdNode, self).__init__(name, element)
        self.parent: NodeMixin = parent
        self.attributes: Dict[str, XsdAttribute] = {}
        self.min_occurs: int = 1  # required by default
        self.max_occurs: int = -1  # unbounded by default

    def render(self) -> str:
        """Gets an ascii representation of this node.

        Returns:
            str: An ascii representation of the node.
        """
        return str(RenderTree(self).by_attr(lambda node: f"[{node.name}] {' '.join(node.attributes)}"))


class XsdTree:
    """Represents a tree structure containing the important
    XSD information for all the elements and attributes.
    """

    def __init__(self, root: XsdNode):
        self.root: XsdNode = root
        self.node_resolver = Resolver("name")

    def find_node_by_name(self, name: str) -> Optional[XsdNode]:
        """Finds node in the tree that matches the given name.

        Args:
            name (str): The name of the node to find.

        Returns:
            XsdNode: The node that matches the name or None if
            not found.
        """
        nodes = findall(self.root, lambda node: node.name == name)
        if len(nodes) == 0:
            return None
        return nodes[0]

    def find_node_by_stack(self, node_stack: List[str]) -> Optional[XsdNode]:
        """Finds the node definition in the tree that matches the given stack of tags.

        Args:
            node_stack (List[str]): The stack of tag names composing a tree branch.
            Like: ['root', 'node', 'subnode', 'leaf']

        Returns:
            Optional[XsdNode]: The node definition matching the leaf in the path or
            None if the node could not be found.
        """
        result_node = None
        if node_stack:
            try:
                path = self._get_path_from_stack(node_stack)
                result_node = self.node_resolver.get(self.root, path)
            except ResolverError as e:
                print(e)
        return result_node

    def render(self) -> str:
        """Gets an ascii representation of this tree.

        Returns:
            str: An ascii representation of the tree.
        """
        return self.root.render()

    def _get_path_from_stack(self, node_stack: List[str]) -> str:
        if node_stack[0] == self.root.name:
            node_stack[0] = "."
        return "/".join(node_stack)

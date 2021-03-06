"""Utilities to validate Galaxy xml tool wrappers and extract
information from the XSD schema.
"""

from typing import List
from lxml import etree

from pygls.workspace import Document
from pygls.types import Diagnostic, MarkupContent, MarkupKind

from .constants import TOOL_XSD_FILE, MSG_NO_DOCUMENTATION_AVAILABLE
from .parser import GalaxyToolXsdParser
from .validation import GalaxyToolValidationService
from ..context import XmlContext


class GalaxyToolXsdService:
    """Galaxy tool Xml Schema Definition service.

    This service provides functionality to extract information from
    the XSD schema and validate XML files against it.
    """

    def __init__(self, server_name: str):
        """Initializes the validator by loading the XSD."""
        self.server_name = server_name
        self.xsd_doc = etree.parse(str(TOOL_XSD_FILE))
        self.xsd_schema = etree.XMLSchema(self.xsd_doc)
        self.xsd_parser = GalaxyToolXsdParser(self.xsd_doc.getroot())
        self.validator = GalaxyToolValidationService(server_name, self.xsd_schema)

    def validate_document(self, document: Document) -> List[Diagnostic]:
        """Validates the Galaxy tool xml using the XSD schema and returns a list
        of diagnotics if there are any problems.
        """
        return self.validator.validate_document(document)

    def get_documentation_for(self, context: XmlContext) -> MarkupContent:
        """Gets the documentation annotated in the XSD about the
        given element name (node or attribute).
        """
        tree = self.xsd_parser.get_tree()
        node = tree.find_node_by_stack(context.node_stack)
        element = None
        if context.is_tag():
            element = node
        if context.is_attribute_key():
            element = node.attributes.get(context.token_name)
        if element is None:
            return MarkupContent(MarkupKind.Markdown, MSG_NO_DOCUMENTATION_AVAILABLE)
        return element.get_doc()

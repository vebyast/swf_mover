#!/usr/bin/env python

import dataclasses
from os import path

from absl import app
from absl import flags
from lxml import etree
import sh

FLAGS = flags.FLAGS

_SWF = flags.DEFINE_string("swf", None, "Path to to the SWF to edit.")

SWFMILL = sh.Command("swfmill")


@dataclasses.dataclass
class Point(object):
    x: float
    y: float

    @classmethod
    def FromElement(cls, elem: etree.Element, fx: str = "x", fy: str = "y"):
        return cls(x=float(elem.get(fx) or 0), y=float(elem.get(fy) or 0))

    @classmethod
    def min(cls, a, b):
        return cls(x=min(a.x, b.x), y=min(a.y, b.y))

    def __add__(self, other):
        return Point(x=self.x + other.x, y=self.y + other.y)


HUGE_POINT = Point(float("+inf"), float("+inf"))


class MoveRootPositionVisitor(object):
    def __init__(self, dx, dy):
        self.dx = dx
        self.dy = dy

    def Visit(self, element, path=()):
        if path == ("Header", "size", "Rectangle"):
            element.set("left", str(float(element.get("left")) + self.dx))
            element.set("right", str(float(element.get("right")) + self.dx))
            element.set("top", str(float(element.get("top")) + self.dy))
            element.set("bottom", str(float(element.get("bottom")) + self.dy))
        else:
            for child in element:
                self.Visit(child, path + (child.tag,))


class GetTopLeftVisitor(object):
    def __init__(self):
        self.tree_origin = None
        self.shape_origin = None
        self._current_pt = None

        self.top_left = HUGE_POINT

    def RegisterPoint(self, pt):
        self.top_left = Point.min(self.top_left, pt)

    @property
    def current_pt(self):
        return self._current_pt

    @current_pt.setter
    def current_pt(self, value):
        self.RegisterPoint(value)
        self._current_pt = value

    def Visit(self, element, path=()):
        if path == ("Header", "size", "Rectangle"):
            self.tree_origin = Point.FromElement(element, "left", "top")
            self.top_left = Point.min(self.top_left, self.tree_origin)
        elif path == ("Header", "tags", "DefineShape", "bounds", "Rectangle"):
            pt_rel_to_origin = Point.FromElement(element, "left", "top")
            self.shape_origin = pt_rel_to_origin + self.tree_origin
        elif path == (
            "Header",
            "tags",
            "DefineShape",
            "shapes",
            "Shape",
            "edges",
            "ShapeSetup",
        ):
            pt_rel_to_shape = Point.FromElement(element)
            self.current_pt = pt_rel_to_shape + self.shape_origin
        elif path == (
            "Header",
            "tags",
            "DefineShape",
            "shapes",
            "Shape",
            "edges",
            "LineTo",
        ):
            self.current_pt += Point.FromElement(element)
        elif path == (
            "Header",
            "tags",
            "DefineShape",
            "shapes",
            "Shape",
            "edges",
            "CurveTo",
        ):
            self.current_pt += Point.FromElement(element, "x2", "y2")

        elif path == ("Header", "tags", "DefineShape2", "bounds", "Rectangle"):
            pt_rel_to_origin = Point.FromElement(element, "left", "top")
            self.shape_origin = pt_rel_to_origin + self.tree_origin
        elif path == (
            "Header",
            "tags",
            "DefineShape2",
            "shapes",
            "Shape",
            "edges",
            "ShapeSetup",
        ):
            pt_rel_to_shape = Point.FromElement(element)
            self.current_pt = pt_rel_to_shape + self.shape_origin
        elif path == (
            "Header",
            "tags",
            "DefineShape2",
            "shapes",
            "Shape",
            "edges",
            "LineTo",
        ):
            self.current_pt += Point.FromElement(element)
        elif path == (
            "Header",
            "tags",
            "DefineShape2",
            "shapes",
            "Shape",
            "edges",
            "CurveTo",
        ):
            self.current_pt += Point.FromElement(element, "x2", "y2")

        else:
            for child in element:
                self.Visit(child, path + (child.tag,))


def main(argv):
    del argv  # Unused.

    # Decompile SWF
    xml_path = path.splitext(_SWF.value)[0] + ".xml"
    SWFMILL.swf2xml(_SWF.value, xml_path)

    # Load XML
    with open(xml_path, "rb") as xml_file:
        xml = etree.parse(xml_file)

    # Find top-left corner
    top_left_visitor = GetTopLeftVisitor()
    top_left_visitor.Visit(xml.getroot())

    # Update root position to place everything in positive x, y
    move_visitor = MoveRootPositionVisitor(
        -top_left_visitor.top_left.x, -top_left_visitor.top_left.y
    )
    move_visitor.Visit(xml.getroot())

    # Recompile SWF
    with open(xml_path, "wb") as xml_file:
        xml.write(xml_file)
    SWFMILL.xml2swf(xml_path, _SWF.value)


if __name__ == "__main__":
    app.run(main)
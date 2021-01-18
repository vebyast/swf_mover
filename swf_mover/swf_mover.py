#!/usr/bin/env python

import dataclasses
from os import path

from absl import app
from absl import flags
from absl import logging
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

    def __mul__(self, other):
        return Point(x=self.x * other, y=self.y * other)


HUGE_POINT = Point(float("+inf"), float("+inf"))
NEGATIVE_HUGE_POINT = HUGE_POINT * -1

HEADER = (
    "swf",
    "Header",
)
ROOT_POS = HEADER + ("size", "Rectangle")
TAGS = HEADER + ("tags",)
DEFSHAPE = TAGS + ("DefineShape",)
DEFSHAPE2 = TAGS + ("DefineShape2",)
SHAPE_POS = ("bounds", "Rectangle")
EDGES = ("shapes", "Shape", "edges")
SHAPESETUP = ("ShapeSetup",)
LINETO = ("LineTo",)
CURVETO = ("CurveTo",)


class MoveRootPositionVisitor(object):
    def __init__(self, movement):
        self.movement = movement

    def Visit(self, element, parent_path=()):
        path = parent_path + (element.tag,)

        if (
            path == ROOT_POS
            or path == DEFSHAPE + SHAPE_POS
            or path == DEFSHAPE2 + SHAPE_POS
        ):
            old_tl = Point.FromElement(element, "left", "top")
            old_br = Point.FromElement(element, "right", "bottom")
            new_tl = old_tl + self.movement
            new_br = old_br + self.movement
            element.set("left", str(new_tl.x))
            element.set("right", str(new_br.x))
            element.set("top", str(new_tl.y))
            element.set("bottom", str(new_br.y))

        if (
            path == DEFSHAPE + EDGES + SHAPESETUP
            or path == DEFSHAPE2 + EDGES + SHAPESETUP
        ):
            old = Point.FromElement(element)
            new = old + self.movement
            if element.get("x") is not None:
                element.set("x", str(new.x))
            if element.get("y") is not None:
                element.set("y", str(new.y))

        else:
            for child in element:
                self.Visit(child, path)


class GetBoundsVisitor(object):
    def __init__(self):
        self.tree_origin = None
        self.shape_origin = None
        self._current_pt = Point(0, 0)

        self.top_left = HUGE_POINT
        self.bottom_left = NEGATIVE_HUGE_POINT

    def RegisterPoint(self, pt):
        self.top_left = Point.min(self.top_left, pt)

    @property
    def current_pt(self):
        return self._current_pt

    @current_pt.setter
    def current_pt(self, value):
        self.RegisterPoint(value)
        self._current_pt = value

    def Visit(self, element, parent_path=()):
        path = parent_path + (element.tag,)

        if path == ROOT_POS:
            self.tree_origin = Point.FromElement(element, "left", "top")
            self.top_left = Point.min(self.top_left, self.tree_origin)

        elif path == DEFSHAPE + SHAPE_POS or path == DEFSHAPE2 + SHAPE_POS:
            self.shape_origin = Point.FromElement(element, "left", "top")
            self.current_pt = self.shape_origin

        elif (
            path == DEFSHAPE + EDGES + SHAPESETUP
            or path == DEFSHAPE2 + EDGES + SHAPESETUP
        ):
            pt = Point.FromElement(element)
            self.current_pt = pt + self.shape_origin

        elif (
            path == DEFSHAPE + EDGES + LINETO
            or path == DEFSHAPE2 + EDGES + LINETO
        ):
            self.current_pt += Point.FromElement(element)

        elif (
            path == DEFSHAPE + EDGES + CURVETO
            or path == DEFSHAPE2 + EDGES + CURVETO
        ):
            self.current_pt += Point.FromElement(element, "x2", "y2")

        else:
            for child in element:
                self.Visit(child, path)


def main(argv):
    del argv  # Unused.

    # Decompile SWF
    swf_in_path = _SWF.value
    xml_in_path = path.splitext(_SWF.value)[0] + ".xml"
    SWFMILL.swf2xml(swf_in_path, xml_in_path)

    # Load XML
    with open(xml_in_path, "rb") as xml_in_file:
        xml = etree.parse(xml_in_file)

    # Find top-left corner
    bounds_visitor = GetBoundsVisitor()
    bounds_visitor.Visit(xml.getroot())
    logging.info(f"top_left: {bounds_visitor.top_left}")

    # Update root position to place everything in positive x, y
    movement = bounds_visitor.top_left * -1
    logging.info(f"movement: {movement}")
    move_visitor = MoveRootPositionVisitor(movement)
    move_visitor.Visit(xml.getroot())

    # Recompile SWF
    xml_out_path = path.splitext(_SWF.value)[0] + ".moved.xml"
    with open(xml_out_path, "wb") as xml_out_file:
        xml.write(xml_out_file)
    swf_out_path = path.splitext(_SWF.value)[0] + ".moved.swf"
    SWFMILL.xml2swf(xml_out_path, swf_out_path)


if __name__ == "__main__":
    app.run(main)

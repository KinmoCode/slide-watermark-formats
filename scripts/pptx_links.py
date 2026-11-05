#!/usr/bin/env python3
"""List hyperlink relationships and the objects that use them in a .pptx.

Read-only: the archive is read in memory; nothing is extracted or written.
Standard library only. Run with:  python3 -I pptx_links.py deck.pptx [--domain gamma.app]

SPDX-License-Identifier: MIT
"""

import argparse
import posixpath
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
R_ID = "{%s}id" % NS["r"]
HYPERLINK_TYPE = NS["r"] + "/hyperlink"
PART_RE = re.compile(r"^ppt/(slides|slideLayouts|slideMasters)/[A-Za-z]+\d+\.xml$")
OBJECT_TAGS = {"sp", "pic", "grpSp", "cxnSp", "graphicFrame"}
MAX_PART_BYTES = 50 * 1024 * 1024  # refuse absurdly large XML parts


def read_xml(zf, name):
    info = zf.getinfo(name)
    if info.file_size > MAX_PART_BYTES:
        raise ValueError("%s is too large to inspect" % name)
    return ET.fromstring(zf.read(name))


def rels_path(part):
    folder, base = posixpath.split(part)
    return posixpath.join(folder, "_rels", base + ".rels")


def read_rels(zf, part):
    path = rels_path(part)
    if path not in zf.namelist():
        return {}
    rels = {}
    for el in read_xml(zf, path).findall("rel:Relationship", NS):
        rels[el.get("Id")] = {
            "type": el.get("Type", ""),
            "target": el.get("Target", ""),
            "external": el.get("TargetMode") == "External",
        }
    return rels


def slide_size(zf):
    root = read_xml(zf, "ppt/presentation.xml")
    size = root.find("p:sldSz", NS)
    if size is None:
        return 12192000, 6858000
    return int(size.get("cx")), int(size.get("cy"))


def text_of(node):
    return " ".join(t.text or "" for t in node.iter("{%s}t" % NS["a"])).strip()


def box_of(node):
    xfrm = node.find(".//a:xfrm", NS)
    if xfrm is None:
        xfrm = node.find("p:xfrm", NS)  # graphicFrame
    if xfrm is None:
        return None
    off, ext = xfrm.find("a:off", NS), xfrm.find("a:ext", NS)
    if off is None or ext is None:
        return None
    return tuple(int(v) for v in (off.get("x"), off.get("y"), ext.get("cx"), ext.get("cy")))


def objects(tree):
    for node in tree.iter():
        tag = node.tag.split("}")[-1]
        if node.tag.startswith("{%s}" % NS["p"]) and tag in OBJECT_TAGS:
            yield tag, node


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pptx")
    parser.add_argument("--domain", help="only show links whose target contains this text")
    args = parser.parse_args()

    with zipfile.ZipFile(args.pptx) as zf:
        if "ppt/presentation.xml" not in zf.namelist():
            sys.exit("Not a .pptx: ppt/presentation.xml is missing")
        cx, cy = slide_size(zf)
        print("slide size: %d x %d EMU (%.2f x %.2f in)" % (cx, cy, cx / 914400, cy / 914400))
        parts = sorted(n for n in zf.namelist() if PART_RE.match(n))
        for part in parts:
            rels = read_rels(zf, part)
            links = {
                rid: rel for rid, rel in rels.items()
                if rel["type"] == HYPERLINK_TYPE
                and (not args.domain or args.domain.lower() in rel["target"].lower())
            }
            if not links:
                continue
            print("\n== %s" % part)
            for rid, rel in links.items():
                print("  rel %-6s %s%s" % (rid, rel["target"], "  (external)" if rel["external"] else ""))
            root = read_xml(zf, part)
            for tag, node in objects(root):
                used = [h.get(R_ID) for h in node.iter()
                        if h.tag in ("{%s}hlinkClick" % NS["a"], "{%s}hlinkHover" % NS["a"])
                        and h.get(R_ID) in links]
                if not used:
                    continue
                props = node.find(".//p:cNvPr", NS)
                name = props.get("name", "") if props is not None else ""
                descr = props.get("descr", "") if props is not None else ""
                box = box_of(node)
                where = ""
                if box:
                    x, y, w, h = box
                    where = " at x=%.2f y=%.2f w=%.2f h=%.2f" % (x / cx, y / cy, w / cx, h / cy)
                print("  %-12s name=%r descr=%r text=%r uses %s%s"
                      % (tag, name, descr, text_of(node)[:60], ",".join(sorted(set(used))), where))


if __name__ == "__main__":
    main()

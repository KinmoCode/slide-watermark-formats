# PowerPoint (.pptx): where a badge lives

A .pptx file is an Office Open XML package as defined by ECMA-376
(PresentationML for slides, DrawingML for shapes and pictures, Open Packaging
Conventions for the container). The container is a plain ZIP archive, so any
unzip tool can open it.

## Package layout

```
[Content_Types].xml              content type of every part
_rels/.rels                      package relationships (points to ppt/presentation.xml)
ppt/presentation.xml             slide list, slide size (<p:sldSz>)
ppt/_rels/presentation.xml.rels  presentation -> slides, masters, theme
ppt/slides/slide1.xml            one part per slide
ppt/slides/_rels/slide1.xml.rels relationships of slide 1 (layout, images, hyperlinks)
ppt/slideLayouts/slideLayoutN.xml        layouts (inherit from a master)
ppt/slideLayouts/_rels/slideLayoutN.xml.rels
ppt/slideMasters/slideMasterN.xml        masters (shared by many layouts)
ppt/slideMasters/_rels/slideMasterN.xml.rels
ppt/media/imageN.png|jpeg        embedded pictures
ppt/notesSlides/                 speaker notes
ppt/theme/                       colours and fonts
```

Inheritance runs master -> layout -> slide. An object placed on a master or a
layout appears on every slide that uses it, but it **cannot be selected on the
slide** in PowerPoint; you have to open View -> Slide Master to reach it. That
is why a corner badge sometimes "can't be clicked".

## Coordinates

Positions are in EMU (English Metric Units): 914400 EMU = 1 inch,
12700 EMU = 1 point. The slide size comes from `ppt/presentation.xml`:

```xml
<p:sldSz cx="12192000" cy="6858000"/>   <!-- 13.333 x 7.5 in, 16:9 -->
```

Each shape carries its box in `a:xfrm`:

```xml
<a:xfrm><a:off x="10287000" y="6324600"/><a:ext cx="1752600" cy="381000"/></a:xfrm>
```

Here `x / cx_slide = 0.84` and `y / cy_slide = 0.92`: bottom-right corner.

Groups (`p:grpSp`) have their own `a:off`/`a:ext` plus a child coordinate
space `a:chOff`/`a:chExt`. To get a nested shape's slide position, map its box
from the child space to the group's box:

```
scale_x = group.ext.cx / group.chExt.cx
slide_x = group.off.x + (child.off.x - group.chOff.x) * scale_x
```

and the same for y, recursively for nested groups.

## Shape tree

Objects live in `<p:cSld><p:spTree>`. The element types that can hold a badge:

| Element | What it is |
|---|---|
| `p:sp` | Shape or text box (text in `p:txBody/a:p/a:r/a:t`) |
| `p:pic` | Picture; the image is `p:blipFill/a:blip/@r:embed` |
| `p:grpSp` | Group of the above |
| `p:cxnSp` | Connector |
| `p:graphicFrame` | Table, chart, SmartArt |

Every object has non-visual properties with a name and optional alt text:

```xml
<p:nvPicPr>
  <p:cNvPr id="7" name="Picture 6" descr="Made with Gamma">
    <a:hlinkClick r:id="rId4"/>
  </p:cNvPr>
  ...
</p:nvPicPr>
```

Hyperlinks appear as `a:hlinkClick` (or `a:hlinkHover`) either on `p:cNvPr`
(click on the whole object) or on a text run's `a:rPr` (click on the words).

## Relationships

`r:id` and `r:embed` are keys into the part's own `.rels` file. For
`ppt/slides/slide3.xml` that is `ppt/slides/_rels/slide3.xml.rels`:

```xml
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout"
    Target="../slideLayouts/slideLayout2.xml"/>
  <Relationship Id="rId3"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
    Target="../media/image5.png"/>
  <Relationship Id="rId4"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"
    Target="https://gamma.app/?utm_source=made-with-gamma" TargetMode="External"/>
</Relationships>
```

(The URL above is illustrative; check the `Target` in your own file.)

Relative targets resolve against the folder of the owning part, not the
`_rels` folder: `../media/image5.png` from `ppt/slides/slide3.xml` is
`ppt/media/image5.png`.

## What a Gamma badge looks like

In Gamma exports made on the Free plan, the "Made with Gamma" badge is a small
object in the bottom-right corner: a picture and/or a shape (often grouped)
with a hyperlink relationship whose target is on gamma.app. Depending on the
export it is placed on each `ppt/slides/slideN.xml`, or once on a
`ppt/slideLayouts/` or `ppt/slideMasters/` part.

A reliable way to identify it:

1. Find `Relationship` elements with `TargetMode="External"` and a gamma.app
   target in any `slides`, `slideLayouts` or `slideMasters` `.rels` file.
2. In the matching part, find the object whose `a:hlinkClick/@r:id` uses that
   Id.
3. Confirm it is small and in the bottom-right corner (offset beyond ~60% of
   width and ~80% of height), or that its name, alt text or only text is a
   phrase like "Made with Gamma".

Removing it losslessly means deleting that object node (or its whole group)
from the part, then deleting the now-unused hyperlink relationship and, if no
other relationship uses it, the badge image in `ppt/media/`. Nothing is
re-rendered, so every other object stays editable.

Be careful with two look-alikes:

- A normal paragraph that happens to link to the same site. Drop only the
  `a:hlinkClick` element and keep the text.
- Your own logo on the master. Do not match pictures by position alone.

## What a NotebookLM slide looks like

NotebookLM Slide Deck exports store most of each slide as one full-slide
picture: a `p:pic` whose `a:ext` covers (nearly) the whole slide, pointing via
`r:embed` to `ppt/media/imageN.png`. Some slides also carry a few editable
text boxes on top. The NotebookLM mark is part of that picture's pixels, so
there is no XML node to delete; the picture itself has to be decoded, its
bottom-right corner rebuilt (see [inpainting.md](inpainting.md)), and the
image written back under the same name. PNG stays lossless if re-encoded as
PNG.

A quick test for "raster slide": the slide has a `p:pic` whose
`cx * cy >= 0.85 * slide_cx * slide_cy`. A slide background picture
(`p:bg/p:bgPr/a:blipFill`) counts too.

## Inspect a deck from the shell

```sh
# List the parts
unzip -l deck.pptx | grep -E 'ppt/(slides|slideLayouts|slideMasters)/'

# All external relationships, with the part they belong to
for f in $(unzip -Z1 deck.pptx | grep -E '_rels/.*\.rels$'); do
  unzip -p deck.pptx "$f" \
    | grep -o '<Relationship [^>]*TargetMode="External"[^>]*>' \
    | sed "s|^|$f: |"
done

# Which parts mention a given domain
unzip -Z1 deck.pptx | while read -r f; do
  unzip -p deck.pptx "$f" 2>/dev/null | grep -q -i 'gamma\.app' && echo "$f"
done

# Shape names and alt text on slide 1
unzip -p deck.pptx ppt/slides/slide1.xml | grep -o '<p:cNvPr [^>]*>'

# Picture sizes on slide 1 (compare with <p:sldSz> in ppt/presentation.xml)
unzip -p deck.pptx ppt/slides/slide1.xml | grep -o '<a:ext cx="[0-9]*" cy="[0-9]*"/>'
unzip -p deck.pptx ppt/presentation.xml | grep -o '<p:sldSz [^>]*>'
```

`unzip -p` prints a member to stdout without extracting anything to disk.
The same commands are collected in [../scripts/pptx_inspect.sh](../scripts/pptx_inspect.sh).

## Inspect a deck with Python (read-only)

[../scripts/pptx_links.py](../scripts/pptx_links.py) uses only the standard
library (`zipfile`, `xml.etree.ElementTree`). It reads the archive in memory,
never extracts or writes, and prints, per slide/layout/master:

- every hyperlink relationship (Id, target, whether it is external),
- every object that uses one of them, with its name, alt text, text and
  position as a fraction of the slide.

```sh
python3 -I scripts/pptx_links.py deck.pptx
python3 -I scripts/pptx_links.py deck.pptx --domain gamma.app
```

`-I` runs Python in isolated mode, so nothing in the current directory is
imported by accident. Note that the script does not apply group transforms;
positions of shapes nested in groups are in the group's child space.

## Legacy .ppt

The binary .ppt format (PowerPoint 97-2003) is not a ZIP of XML and none of
the above applies. Open it in PowerPoint and save as .pptx first.

## Reference

- ECMA-376 Office Open XML, Part 1 (PresentationML, DrawingML) and Part 2
  (Open Packaging Conventions):
  https://ecma-international.org/publications-and-standards/standards/ecma-376/
- Gamma help, exporting: https://help.gamma.app/en/articles/8022861-how-do-i-export-my-gamma
- NotebookLM help, Slide Deck downloads: https://support.google.com/notebooklm/answer/16757456

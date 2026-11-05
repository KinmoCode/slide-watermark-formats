# slide-watermark-formats

Technical notes on where AI presentation tools put their visible corner marks
inside exported files, and how to inspect them yourself: PowerPoint (.pptx),
PDF, and MP4 video.

The notes cover two common cases:

- **Vector badges** stored as separate objects in the file structure, such as
  the "Made with Gamma" badge in Gamma .pptx and .pdf exports. These can be
  found (and removed) without touching a single pixel.
- **Baked-in marks** that are part of an image or video frame, such as the
  NotebookLM mark on Slide Deck pictures, infographics and Video Overviews.
  These live in pixels and can only be changed by decoding the image or video.

Everything here is about reading and understanding the formats. The snippets
are read-only: they list and print, they never modify your files.

## Contents

| File | What it covers |
|---|---|
| [notes/pptx-ooxml.md](notes/pptx-ooxml.md) | The .pptx package: slides, layouts, masters, `_rels`, pictures, hyperlinks; how to unzip and grep for a badge |
| [notes/pdf.md](notes/pdf.md) | Link annotations, image XObjects vs vector pages, inspecting with `qpdf --qdf`, `mutool show` and pdf-lib |
| [notes/mp4.md](notes/mp4.md) | Why marks in video are baked into frames, decode/re-encode with WebCodecs, audio passthrough |
| [notes/inpainting.md](notes/inpainting.md) | Rebuilding a mark on a calm slide margin from its background, instead of blurring |
| [scripts/pptx_links.py](scripts/pptx_links.py) | List hyperlink relationships and badge-like shapes in a .pptx (Python standard library only) |
| [scripts/pptx_inspect.sh](scripts/pptx_inspect.sh) | Shell one-liners for the same, using `unzip` and `grep` |

## Quick start

```sh
# What is inside a deck?
unzip -l deck.pptx | grep -E 'ppt/(slides|slideLayouts|slideMasters|media)/'

# Which parts link to an external site?
python3 -I scripts/pptx_links.py deck.pptx

# Which PDF pages carry link annotations?
qpdf --qdf --object-streams=disable deck.pdf - | grep -a -n '/URI'
```

## Summary of findings

| Source | Format | How the mark is stored | Lossless removal possible? |
|---|---|---|---|
| Gamma (Free plan) | .pptx | Small shape/picture/group in the bottom-right corner, with `a:hlinkClick` to a gamma.app relationship; on slides or on a slide layout/master | Yes: delete the XML node and its relationship |
| Gamma (Free plan) | .pdf | Drawn badge in the page content plus a `/Link` annotation with a gamma.app `/URI` | Link: yes. Drawn badge: needs a pixel patch or content-stream edit |
| NotebookLM Slide Deck | .pptx | Each slide is a full-slide picture in `ppt/media/`; the mark is in its pixels | No: the picture has to be decoded and edited |
| NotebookLM Slide Deck | .pdf | Each page is one full-page image XObject; the mark is in its pixels | No: the image has to be decoded and edited |
| NotebookLM infographic | .png | Pixels | No |
| NotebookLM Video Overview | .mp4 | Pixels of every frame | No: decode and re-encode the video stream; audio can be copied |

On a 16:9 NotebookLM slide, the mark sits at roughly 82–99% across and 91–99%
down. Gamma's badge sits in a similar bottom-right zone (about 78–99% across,
88–99% down).

Invisible watermarks such as Google SynthID are a different thing: they are
spread through the content, are not visible, and nothing in these notes finds
or changes them.

## Official documentation

- Gamma help, exporting (badge on Free-plan PDF/PPTX exports):
  https://help.gamma.app/en/articles/8022861-how-do-i-export-my-gamma
- Gamma help, pricing (plans that remove the badge):
  https://help.gamma.app/en/articles/8077107-gamma-pricing
- NotebookLM help, plan features and the "Visible watermarking" setting:
  https://support.google.com/notebooklm/answer/16206866
- NotebookLM help, downloading a Slide Deck as PDF or .pptx:
  https://support.google.com/notebooklm/answer/16757456
- ECMA-376 Office Open XML:
  https://ecma-international.org/publications-and-standards/standards/ecma-376/
- ISO 32000-2 (PDF 2.0): https://www.iso.org/standard/75839.html
- W3C WebCodecs: https://www.w3.org/TR/webcodecs/

## A browser tool built on these notes

[Slide Watermark Remover](https://slidewatermarkremover.com) applies the
techniques described here entirely in the browser, with no upload:

- [Gamma watermark remover](https://slidewatermarkremover.com/gamma-watermark-remover)
  for .pptx and .pdf
- [NotebookLM watermark remover](https://slidewatermarkremover.com/notebooklm-watermark-remover)
  for slide decks, infographics and Video Overviews

## Disclaimer

These notes are independent and are not affiliated with, endorsed by or
sponsored by Gamma Tech, Inc. or Google LLC. Gamma and NotebookLM are
trademarks of their owners and are named only to describe file formats.
Export layouts can change at any time; check your own files. You are
responsible for complying with the terms of your own plan.

## License

MIT, see [LICENSE](LICENSE).

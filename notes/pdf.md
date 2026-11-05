# PDF: link annotations, page images and drawn badges

PDF is defined by ISO 32000 (PDF 1.7 is ISO 32000-1, PDF 2.0 is ISO 32000-2).
A page is a dictionary with a content stream (drawing operators), a
`/Resources` dictionary (fonts, images, forms used by that stream) and an
optional `/Annots` array (interactive things laid on top: links, comments,
form widgets).

A corner mark in an exported slide PDF can be stored in up to three places,
and each needs a different fix.

## 1. Link annotations (the clickable part)

A clickable badge is a link annotation in the page's `/Annots` array:

```
12 0 obj
<< /Type /Annot
   /Subtype /Link
   /Rect [ 1180 26 1352 62 ]
   /Border [ 0 0 0 ]
   /A << /S /URI /URI (https://gamma.app/...) >>
>>
endobj
```

- `/Rect` is `[x1 y1 x2 y2]` in PDF user space: points (1/72 in), origin at
  the **bottom-left** of the page. To get a top-left fraction of the page:
  `x = (x1 - box.x) / box.width`, `y = (box.y + box.height - y2) / box.height`.
- The annotation is not drawn; it only makes that rectangle clickable.
  Deleting it removes the link but not the visible badge.
- Removing it is lossless: drop the entry from `/Annots` (and the `/Annots`
  key itself if the array is now empty).

## 2. Vector pages with a drawn badge

On pages made of real text and vector shapes (Gamma PDF exports, for
example), the visible badge is drawn by the page content: text operators
(`BT ... ET`), paths, and/or a small image or form XObject, near the
bottom-right of the page.

Options to remove the visible part:

- Edit the content stream and delete the operators that draw the badge. This
  is exact, but fragile: content streams are free-form, the badge may share a
  graphics state with other objects, and the operators differ between
  exporters.
- Render the page corner, rebuild the badge pixels from the background (see
  [inpainting.md](inpainting.md)), and draw the clean patch as a small image
  over exactly the badge rectangle. The rest of the page stays vector and
  text stays selectable. The link rectangle from step 1 is a good hint for
  where to put the patch. At 2.5x render scale (72 x 2.5 = 180 dpi) the patch
  is indistinguishable at normal zoom.

## 3. Raster pages (one full-page image)

Many AI slide exports, including NotebookLM Slide Deck PDFs, store each slide
as one image covering the page, with no text objects. The page content is
just:

```
q
1365.33 0 0 768 0 0 cm
/Im0 Do
Q
```

`cm` sets the transform (here: scale the unit square to 1365.33 x 768 pt,
the full page), and `/Im0 Do` paints the image XObject named `Im0` from
`/Resources /XObject`. The image itself is a stream:

```
<< /Type /XObject /Subtype /Image
   /Width 2730 /Height 1536
   /ColorSpace /DeviceRGB /BitsPerComponent 8
   /Filter /FlateDecode
   /DecodeParms << /Predictor 15 /Colors 3 /Columns 2730 >>
   /Length ... >>
stream ... endstream
```

The mark is part of those pixels. To remove it without blurring the slide:

1. Detect the page: no `BT` in the content stream, and the largest image is
   drawn axis-aligned over (almost) the whole page (follow `q`/`Q`/`cm` to the
   `Do`, or compare aspect ratios).
2. Decode the image at its native resolution:
   - `/DCTDecode` is a JPEG file; decode it as JPEG.
   - `/FlateDecode` is zlib; inflate it, then undo PNG row predictors if
     `/DecodeParms /Predictor` is 10 or higher (each row starts with a filter
     byte: 0 None, 1 Sub, 2 Up, 3 Average, 4 Paeth).
   - Check `/ColorSpace` (`/DeviceRGB`, `/DeviceGray`, or `[/ICCBased ...]`
     with `/N 3` or `/N 1`) and `/BitsPerComponent 8`. Other encodings
     (CMYK, JBIG2, JPX, 16-bit, indexed) need more work.
3. Rebuild the corner pixels.
4. Write the stream back into the **same object**: Flate stays Flate
   (lossless); JPEG is re-encoded at high quality. Every page that references
   the object sees the change; nothing else in the file moves.

Re-rendering the whole page instead (print to PDF, screenshot, export as
images) softens text inside the slide image and often changes the page size.

## Inspecting a PDF

### qpdf

```sh
# Uncompressed, human-readable copy (QDF mode) for reading in an editor
qpdf --qdf --object-streams=disable deck.pdf deck-qdf.pdf

# Find link annotations and their targets
grep -a -n -E '/Subtype /Link|/URI' deck-qdf.pdf

# Find image XObjects and their encoding
grep -a -n -E '/Subtype /Image|/Filter|/Width|/Height|/ColorSpace' deck-qdf.pdf

# Page count, and a JSON dump of the object structure
qpdf --show-npages deck.pdf
qpdf --json deck.pdf > deck.json
```

QDF output also places `%% Page N` comments before each page dictionary,
which makes the per-page structure easy to follow.

### MuPDF (mutool)

```sh
mutool info deck.pdf                      # per-page fonts and images (sizes, filters)
mutool show deck.pdf trailer              # the trailer dictionary
mutool show deck.pdf pages                # list of page objects
mutool show deck.pdf 'trailer/Root/Pages/Kids/0/Annots'   # annotations of page 1
mutool show deck.pdf 12                   # object 12
mutool show -b deck.pdf 15 > content.txt  # decoded stream of object 15
mutool extract deck.pdf                   # writes images and fonts to the current directory
```

### pdf-lib (JavaScript, also runs in the browser)

```js
import { PDFDocument, PDFName, PDFDict, PDFArray } from 'pdf-lib';

const doc = await PDFDocument.load(bytes, { updateMetadata: false });
doc.getPages().forEach((page, index) => {
  const annots = page.node.lookupMaybe(PDFName.of('Annots'), PDFArray);
  for (let i = 0; annots && i < annots.size(); i++) {
    const annot = annots.lookupMaybe(i, PDFDict);
    if (annot?.lookup(PDFName.of('Subtype')) !== PDFName.of('Link')) continue;
    const action = annot.lookupMaybe(PDFName.of('A'), PDFDict);
    const uri = action?.lookup(PDFName.of('URI'));
    console.log(`page ${index + 1}:`, uri?.decodeText?.(), annot.lookup(PDFName.of('Rect')).toString());
  }
  const xobjects = page.node.Resources()?.lookupMaybe(PDFName.of('XObject'), PDFDict);
  for (const [name, ref] of xobjects?.entries() ?? []) {
    const stream = doc.context.lookup(ref);
    const dict = stream?.dict;
    if (dict?.lookup(PDFName.of('Subtype')) !== PDFName.of('Image')) continue;
    console.log(`  image ${name.decodeText()}`,
      dict.lookup(PDFName.of('Width')).toString(), 'x',
      dict.lookup(PDFName.of('Height')).toString(),
      dict.lookup(PDFName.of('Filter'))?.toString());
  }
});
```

This only reads. To remove a link, call `annots.remove(i)` and
`doc.save()`.

## Things that block editing

- **Encryption.** A password-protected PDF (`/Encrypt` in the trailer) must be
  decrypted before its objects can be rewritten. With the password,
  `qpdf --decrypt --password=... in.pdf out.pdf` produces an unprotected copy.
  Easier: export again from the source app without a password.
- **Rotated pages.** `/Rotate 90` changes how user space maps to the screen;
  account for it when converting `/Rect` or placing a patch.
- **Crop box vs media box.** Measure against `/CropBox` (what viewers show),
  falling back to `/MediaBox`.
- **Shared images.** One image object can be used by several pages; edit it
  once.

## Reference

- ISO 32000-2 (PDF 2.0): https://www.iso.org/standard/75839.html
  (sections on annotations, link annotations, image XObjects, filters)
- NotebookLM help, downloading a Slide Deck as PDF:
  https://support.google.com/notebooklm/answer/16757456
- Gamma help, exporting: https://help.gamma.app/en/articles/8022861-how-do-i-export-my-gamma

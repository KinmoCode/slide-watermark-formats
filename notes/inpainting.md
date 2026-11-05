# Rebuilding a corner mark from its background

Slide exports almost always put the corner mark on a calm margin: a flat
colour, a soft gradient, or the edge of a card. On such a background the
"true" pixels under the mark can be estimated very accurately from the pixels
around it. This is better than the common shortcuts:

- **Blur / smudge:** spreads the mark into a grey patch.
- **Crop:** changes the slide size and cuts content.
- **Paint a rectangle:** visible as a patch on any gradient.

## A simple, robust method

Given an RGBA image and a box around the mark:

1. **Fit the background.** Take a thin ring of pixels just outside the box
   (a few pixels wide). For each colour channel, fit a smooth surface by least
   squares, for example a quadratic
   `c(u, v) = a0 + a1 u + a2 v + a3 u² + a4 uv + a5 v²`
   with `u, v` the normalised coordinates around the box centre. A tiny ridge
   term keeps the fit stable on thin rings.
2. **Drop outliers and refit.** Slide content touching the ring would skew
   the fit. Compute each ring pixel's residual, drop those above something like
   `max(6, 4 × median)`, and fit again.
3. **Find the mark.** A pixel inside the box belongs to the mark if any
   channel differs from the fitted background by more than a threshold (about
   20 levels out of 255 works well). Grow that mask by 1–2 pixels to catch
   anti-aliased edges. Pixels that do not stand out are left exactly as they
   are: this is what keeps nearby text sharp.
4. **Rebuild the marked pixels.** For each marked pixel, walk left, right, up
   and down to the nearest unmarked pixel, and interpolate linearly along each
   axis; weight each axis by `1 / span` so the shorter span counts more. This
   is exact on flat colours and on linear gradients.
5. **Relax.** A few dozen Gauss–Seidel passes of the Laplace equation over the
   marked pixels (each pixel becomes the mean of its four neighbours) remove
   the faint cross-shaped seams left by axis interpolation, while keeping
   linear ramps exact.
6. **Busy-box fallback.** If most of the box (say more than 85%) "stands out",
   the box is over busy content rather than a margin; rebuild the whole box
   instead of leaving fragments, or ask for a tighter box.

On flat and linear-gradient backgrounds the result is within a couple of
colour levels of the true background. Over photos and textures, the rebuilt
area is smooth and can look softer than its surroundings.

## Where the box goes

As fractions of the slide or frame (top-left origin), observed in typical
16:9 exports:

| Mark | x | y | width | height |
|---|---|---|---|---|
| NotebookLM (slides, PDF pages, video) | 0.82 | 0.91 | 0.17 | 0.08 |
| Gamma badge (generous) | 0.78 | 0.88 | 0.215 | 0.115 |

Boxes can be generous because step 3 only rebuilds the pixels that stand out.
Always check your own file; layouts change.

## Applying it per format

- **Image (PNG/JPEG/WebP):** decode, rebuild, encode in the same format. PNG
  stays lossless.
- **PPTX raster slide:** rebuild the picture in `ppt/media/` and write it back
  under the same name; see [pptx-ooxml.md](pptx-ooxml.md).
- **PDF page image:** decode the image XObject at native resolution and write
  it back into the same object; see [pdf.md](pdf.md).
- **Video:** compute the mask from several frames, then apply the same
  rebuild plan to every decoded frame; see [mp4.md](mp4.md).

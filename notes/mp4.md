# MP4 video: marks baked into frames

## Why there is nothing to "delete"

An MP4 file is an ISO Base Media File Format container (ISO/IEC 14496-12):
boxes such as `ftyp`, `moov` (track metadata, sample tables) and `mdat`
(the compressed samples). A typical slide-style video has two tracks:

- a video track, usually H.264/AVC (`avc1`), sometimes HEVC, VP9 or AV1;
- an audio track, usually AAC (`mp4a`).

There is no overlay layer in MP4. A corner logo such as the NotebookLM mark on
a Video Overview is drawn into the picture before encoding, so it is part of
the pixels of every frame. Removing it means changing those pixels, and
changing pixels means:

1. **decode** the compressed video into raw frames,
2. **edit** the corner of each frame,
3. **encode** the frames again,
4. **mux** the new video samples (plus the audio) into a new MP4.

You can see this with ffprobe:

```sh
ffprobe -hide_banner -show_streams -select_streams v deck-overview.mp4 | grep -E 'codec_name|width|height|r_frame_rate|bit_rate'
ffprobe -hide_banner -show_streams -select_streams a deck-overview.mp4 | grep -E 'codec_name|sample_rate|channels'
```

and look at the corner of a frame:

```sh
ffmpeg -hide_banner -ss 30 -i deck-overview.mp4 -frames:v 1 frame.png
```

## Finding the mark once, from several frames

A corner logo is static while the slides behind it change. That makes it easy
to tell apart from slide content:

1. Sample a handful of frames spread over the clip (for example at 12%, 30%,
   50%, 70% and 88% of the duration).
2. In each frame, find the pixels inside the corner box that stand out from
   the local background (see [inpainting.md](inpainting.md)).
3. Keep only pixels that stand out in most frames (for example at least 3 of
   5). Slide text that passes through the corner in one scene is voted out.

Because the mask is the same for every frame, the "which neighbours does each
pixel copy from" plan can be computed once and applied to every frame cheaply.

## Re-encoding in the browser with WebCodecs

WebCodecs (W3C) exposes the browser's own hardware/software codecs to
JavaScript:

- `VideoDecoder` takes `EncodedVideoChunk`s (from a demuxer such as MP4Box.js)
  and outputs `VideoFrame`s.
- A `VideoFrame` can be drawn to an `OffscreenCanvas` (or copied with
  `copyTo`) to get RGBA pixels, edited, and turned back into a `VideoFrame`.
- `VideoEncoder` takes `VideoFrame`s and outputs `EncodedVideoChunk`s, which a
  muxer (such as mp4-muxer) writes into a new MP4.

Minimal shape of the loop:

```js
const encoder = new VideoEncoder({
  output: (chunk, meta) => muxer.addVideoChunk(chunk, meta),
  error: console.error,
});
encoder.configure({
  codec: 'avc1.42001f',          // H.264 baseline; match the source where possible
  width, height,
  bitrate: 8_000_000,
  framerate: fps,
});

const decoder = new VideoDecoder({
  output: (frame) => {
    ctx.drawImage(frame, 0, 0);
    const image = ctx.getImageData(0, 0, width, height);
    rebuildCorner(image.data);    // apply the precomputed plan
    ctx.putImageData(image, 0, 0);
    const clean = new VideoFrame(canvas, { timestamp: frame.timestamp });
    encoder.encode(clean);
    clean.close();
    frame.close();
  },
  error: console.error,
});
decoder.configure(configFromDemuxer);   // codec string + avcC description from MP4Box.js
// feed decoder.decode(new EncodedVideoChunk(...)) for each sample, then flush both
```

Practical notes:

- Feature-detect: `'VideoEncoder' in window && 'VideoDecoder' in window`.
  Recent Chrome and Edge on desktop support both; support for encoding in
  Safari and on phones varies.
- Close every `VideoFrame` you receive or create, or the decoder stalls.
- Keep the source resolution and frame rate. Re-encoding always costs some
  quality; aiming a little above the source bitrate (for example 1.3x,
  clamped to a sane range such as 2–16 Mbps) keeps generational loss low.
- Respect the encoder's back-pressure (`encodeQueueSize`) on long clips.
- Everything happens in the tab; the file never needs to leave the device.

## Audio passthrough

The mark is only in the video track, so the audio does not need to be
decoded. Copy the compressed audio samples (data, timestamp, duration,
key flag) from the demuxer straight into the new file's audio track with the
same codec, sample rate and channel count. The narration comes out bit for
bit identical, and there is no second round of AAC loss.

The ffmpeg equivalent of "re-encode video, copy audio" is:

```sh
ffmpeg -i in.mp4 -vf "<your filter>" -c:v libx264 -crf 18 -c:a copy out.mp4
```

## What re-encoding does not fix

- **End screens / intro cards.** A full branded scene is content, not a
  corner overlay. Trim it with any video editor.
- **Invisible watermarks** such as SynthID, embedded in the content itself,
  are not visible and are not affected by editing a corner.
- **Busy backgrounds.** If the corner shows a moving photo or video, a
  background-fit rebuild looks smoother than its surroundings.

## Reference

- W3C WebCodecs: https://www.w3.org/TR/webcodecs/
- NotebookLM help, plan features and the "Visible watermarking" setting:
  https://support.google.com/notebooklm/answer/16206866

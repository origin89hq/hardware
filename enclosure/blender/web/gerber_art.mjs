// Derive the website's Gerber artwork and the web model's board texture from the layer masks.
//
// Input: the directory written by gerber_layers.mjs (top-*.png, top-layers.json).
// Output, all in --out:
//   gerber-u7.webp         blue artwork around U7 (x -4..44 mm, y -22..22 mm), 1000 px wide
//   trace-mask-u7.webp     white, alpha = copper or pads, same crop and size
//   gerber-board-dim.webp  whole board, 1600 x 2000, dim copper/pads/silk on transparent
//   trace-mask-board.webp  white, alpha = copper or pads, 1600 x 2000
//   board-albedo.jpg       2048 x 2560 solder-mask colour texture for export_glb.py
//
//   npx --yes --package sharp@0.35.3 -- \
//     node enclosure/blender/web/gerber_art.mjs --layers /tmp/home-media/gerber-layers \
//     --out /tmp/home-media/gerber-art
//
// Colours are mixed per pixel in the order copper, pads, silkscreen, truncated to
// 8 bits. The U7 crop and both trace masks are mixed at mask resolution and then
// scaled; the dimmed board and the albedo scale the masks first (sharp's default
// Lanczos 3). Keep both orders: they reproduce the published files byte for byte.
import assert from "node:assert/strict";
import { mkdir, readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { parseArgs } from "node:util";
import { npxRequire } from "./npx_require.mjs";

const sharp = npxRequire("sharp", "sharp@0.35.3");

const { values } = parseArgs({ options: { layers: { type: "string" }, out: { type: "string" } } });
assert.ok(values.layers && values.out, "Usage: gerber_art.mjs --layers DIR --out DIR");
const record = JSON.parse(await readFile(resolve(values.layers, "top-layers.json"), "utf8"));
const ppm = record.px_per_mm;
const [minX, minY, spanX, spanY] = record.view_box.map((v) => v / 1000);

// Board mm to mask pixels; the masks put +Y at the top.
function region([x0, x1], [y0, y1]) {
  return {
    left: Math.round((x0 - minX) * ppm),
    top: Math.round((minY + spanY - y1) * ppm),
    width: Math.round((x1 - x0) * ppm),
    height: Math.round((y1 - y0) * ppm),
  };
}
const U7 = region([-4, 44], [-22, 22]);
const BOARD = { left: 0, top: 0, width: Math.round(spanX * ppm), height: Math.round(spanY * ppm) };

// Mask coverage for a crop, at mask resolution or scaled to width x height.
async function masks(crop, width, height) {
  const read = (name) => {
    const image = sharp(resolve(values.layers, `top-${name}.png`), { limitInputPixels: false })
      .extract(crop)
      .extractChannel(0);
    return (width ? image.resize(width, height) : image).raw().toBuffer();
  };
  const [copper, pads, silk] = await Promise.all([read("copper"), read("pads"), read("silk")]);
  return { copper, pads, silk };
}

const mix = (a, b, t) => a + (b - a) * t;
const rgb = (hex) => [1, 3, 5].map((i) => Number.parseInt(hex.slice(i, i + 2), 16));

// Mix per pixel; paint returns [r, g, b] or [r, g, b, a] from coverage in 0..1.
function paint(layers, channels, colour) {
  const out = Buffer.alloc(layers.copper.length * channels);
  for (let i = 0; i < layers.copper.length; i++) {
    const pixel = colour(layers.copper[i] / 255, layers.pads[i] / 255, layers.silk[i] / 255);
    for (let c = 0; c < channels; c++) out[i * channels + c] = Math.floor(pixel[c]);
  }
  return out;
}

function encode(pixels, width, height, channels) {
  return sharp(pixels, { raw: { width, height, channels }, limitInputPixels: false });
}

const out = (name) => resolve(values.out, name);
await mkdir(values.out, { recursive: true });

const traceMask = (c, p) => [255, 255, 255, Math.max(c, p) * 255];

// U7 close-up: mixed on the crop, then scaled to 1000 px wide.
{
  const layers = await masks(U7);
  const [bg, copper, pads, silk] = ["#0d1116", "#1a2c56", "#3f61b3", "#9aa5b1"].map(rgb);
  const art = paint(layers, 3, (c, p, s) =>
    [0, 1, 2].map((k) => mix(mix(mix(bg[k], copper[k], c), pads[k], p), silk[k], s * 0.85)),
  );
  await encode(art, U7.width, U7.height, 3)
    .resize(1000)
    .webp({ quality: 88 })
    .toFile(out("gerber-u7.webp"));
  await encode(paint(layers, 4, traceMask), U7.width, U7.height, 4)
    .resize(1000)
    .webp({ quality: 85, alphaQuality: 80 })
    .toFile(out("trace-mask-u7.webp"));
}

// Whole board, 1600 x 2000: the dimmed artwork scales the masks first, the trace mask after.
{
  const [width, height] = [1600, 2000];
  const layers = await masks(BOARD, width, height);
  const [copper, pads, silk] = [
    [22, 36, 70],
    [40, 62, 120],
    [70, 80, 95],
  ];
  const dim = paint(layers, 4, (c, p, s) => {
    const t = s * 0.8;
    const colour = [0, 1, 2].map((k) => mix(mix(mix(0, copper[k], c), pads[k], p), silk[k], t));
    return [...colour, Math.max(c, p, t) * 255];
  });
  await encode(dim, width, height, 4)
    .webp({ quality: 80, alphaQuality: 80 })
    .toFile(out("gerber-board-dim.webp"));
  const full = await masks(BOARD);
  await encode(paint(full, 4, traceMask), BOARD.width, BOARD.height, 4)
    .resize(width, height)
    .webp({ quality: 80, alphaQuality: 70 })
    .toFile(out("trace-mask-board.webp"));
}

// Board texture for the GLB: green mask, lighter over copper, gold pads, white silk.
{
  const [width, height] = [2048, 2560];
  const layers = await masks(BOARD, width, height);
  const [bare, copper, pads, silk] = [
    [16, 64, 38],
    [30, 96, 56],
    [214, 170, 102],
    [228, 230, 226],
  ];
  const albedo = paint(layers, 3, (c, p, s) =>
    [0, 1, 2].map((k) => mix(mix(mix(bare[k], copper[k], c), pads[k], p), silk[k], s)),
  );
  await encode(albedo, width, height, 3)
    .jpeg({ quality: 86, mozjpeg: true })
    .toFile(out("board-albedo.jpg"));
}
console.log("gerber art written to", values.out);

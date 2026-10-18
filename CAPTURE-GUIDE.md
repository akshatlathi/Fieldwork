# How to film garments for Fieldwork (≈3 minutes per garment)

For the unresolved issues in the supplied real captures, use the [targeted 05/06 follow-up packet](fieldwork-ai/data/capture-kit/defect-followup/README.md). A video and additional close-up photos can now be submitted together. The already inspected organized garments are development data; use separate unseen garments for the final test.

These captures support the real-world seller → buyer → human-review evaluation. Split by garment **before running models**: for an initial 30-garment pilot, use 10 development, 10 calibration, and 10 final-test garments. Keep final-test captures unseen until settings are frozen. All takes of one garment, and deliberate look-alike pairs, belong in the same split. See [evaluation protocol](fieldwork-ai/eval/EVALUATION-PLAN.md).

A [starter kit](fieldwork-ai/data/capture-kit/README.md) now contains 30 planned garment folders and annotation templates. Splits alternate by garment ID so a smaller initial collection includes each split. These are empty templates outside the active evaluation dataset. Complete the media and independent annotations before moving a folder into `data/garments/`. During development, run only development/calibration captures; keep test garments unevaluated until configuration is frozen.

## What you need
- Your phone and a plain surface (bed sheet, floor, table). Daylight or a bright room; no flash.
- A sticky note and a pen (for the one-time code).
- A notebook or phone notes, to record each garment's real flaws.

## Folder layout
Make one folder per garment inside `ai-builder-cup/fieldwork-ai/data/garments/`:
```
garment-01/
  take.mp4        the 12-second listing video
  photo-1.jpg     front
  photo-2.jpg     back
  photo-3.jpg     label (brand + size + care label)
  notes.txt       e.g. "Uniqlo navy jacket, M. Small stain left cuff. Pilling on right sleeve."
  split.txt       development, calibration, or test
  truth.json      structured annotations, copied and completed from the example below
```

## Session 1: the listing take (per garment)
1. Write any 4 characters on the sticky note (e.g. `K7Q2`); write the same code in notes.txt.
2. Lay the garment flat, front up. Put the sticky note beside it.
3. **Record 12 seconds:** slowly move over the front (1–2 s per area), flip it over, slowly over the back, then hold close on the label for 2 s. Keep the code in frame at least once.
4. Take the 3 photos (front, back, label).
5. In notes.txt write: brand, size, colour, and **every real flaw you know of** (where and how big). This is our "truth" for testing.

Aim for **15 garments** in session 1: a mix of jackets, jeans, shirts, hoodies, dresses. **At least 5 with real flaws** (stains, pilling, small holes, fading) are the most valuable.

## Session 2: the unboxing take (same garments, next day)
For each garment from session 1, make a folder `garment-01/unbox/`:
1. **Plant a small removable change on about half of them** and write exactly what and where in `unbox/changes.txt`:
   - a dot with a **washable marker** (stain), or
   - a tuft of **lint or a thread** stuck on (snag/fluff), or
   - a **safety pin** through the fabric (looks like a small hole/snag).
   For the other half, change nothing and write "no change".
2. Fold the garment differently, move to a different room or light, and film a 12-second "unboxing" take the same way → `unbox/take.mp4`.

Record what is actually visible, its location, approximate size, and severity before seeing model output. Distinguish removable proxies from real defects: lint is not a tear, and a safety pin is not automatically a hole. For final-test cases, have a second person independently inspect the evidence where possible and resolve disagreements. Missing or hidden areas remain unknown.

Use unchanged, changed, similar-but-different, blurry, incomplete-view and replay cases. Record ground truth separately from system-generated reports. Multiple attempts on the same garment remain correlated; report distinct garment counts as well as case counts.

Copy [the truth-file example](fieldwork-ai/eval/capture-truth.example.json) into each garment folder as `truth.json` and replace its example observations. This records the split, comparison group, physical changes, expected evidence assessment, and buyer question references. `truth.json` is the authoritative split for the evaluation; keep `split.txt` consistent. Validate files before calling models:

```bash
cd fieldwork-ai
python eval/capture_schema.py --root data/garments
```

## Bonus (very useful)
- **Look-alike pairs:** two very similar garments (two plain white tees, two similar jeans): film both. Name them `garment-20a`, `garment-20b`.
- More garments are better: the target is **30 garments** and **100 planted changes** in total (several changes per garment is fine, one at a time).

## Don'ts
- No people's faces, home addresses, or documents in the frame.
- Don't use filters or beauty modes.
- Don't edit the videos.

# Real garment capture kit

Thirty planned garment IDs: 10 development, 10 calibration, 10 test, assigned in alternating order so a smaller pilot still contains each split. No images, observations or results have been generated. These folders are not the active evaluation dataset.

1. Use the root CAPTURE-GUIDE.md to record each real garment, its front/back/label photos and received take.
2. Fill truth.template.json from independent observations BEFORE viewing model output. Replace FILL_ME with consistent/differs/cant_tell, fill the reference notes/reviewers and describe all known flaws/physical changes. Empty flaw lists do not assert a clean garment until independently inspected.
3. Keep the split fixed. Any deliberate look-alike pair must share a comparison group AND a split before models see either garment.
4. Once complete, save as truth.json and place the garment folder under data/garments/. Keep received video at unbox/take.mp4. Unrecorded templates must remain in capture-kit.
5. Validate: python eval/capture_schema.py --root data/garments

The raw templates intentionally fail truth validation. Do not fabricate observations or use digitally altered stress-test images as real captures. Start with three garments (one per split); 30 is a small pilot, not production proof. Questions in the template are examples: add garment-specific answerable and unanswerable questions with independent reference answers.

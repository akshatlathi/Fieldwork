# Targeted follow-up for garments 05 and 06

This packet requests new evidence. It contains no recorded media or completed ground truth. Keep the original `data/organized-garments/` media unchanged. These already inspected garments belong to development, not a final unseen test split.

For each issue, take three photos in this folder's garment subfolder:

1. A wide front/back view with the issue pointed out and a nearby pocket, seam or waistband visible.
2. A sharp close-up with the issue centered. Use diffuse light; avoid flash/glare and digital zoom.
3. Another close-up under slightly different light, with a ruler alongside if size matters. Do not stretch or alter the fabric to manufacture the reported defect.

Complete the corresponding `annotation.template.json` with wearer’s left/right, front/back, exact location, visibility and actual filenames **before** looking at new model predictions. A second person should check the photographs where possible. Leave unknown details unknown.

- **Garment 05:** locate the reported back hole and red hip stain separately. Also show the front dark spots; their cause is not established by a photograph. Do not treat model-reported fading or label wear as confirmation of the hole/stain.
- **Garment 06:** locate the reported hip hole. The owner notes do not yet identify side, front/back position or size. Both wide and close views are necessary to establish which part is being inspected.

In the app, select a recorded video, choose these supplementary photos, then make the Pass. Photos now supplement a video in the same submission. These same-session close-ups help diagnose seller inspection; they do not replace a separately recorded received/unboxing session.

For delivery evaluation, follow the root CAPTURE-GUIDE.md. Keep owner annotations independent of model outputs, distinguish physical changes from removable proxies, and record changed/unchanged/look-alike cases on different backgrounds and lighting. Avoid reusing the same code card as an identity shortcut. Only completed validated `truth.json` captures belong in the active workflow evaluation dataset.

"""Local side-by-side evidence gallery; predictions are not reference labels."""
import argparse
import html
import json
from pathlib import Path
from PIL import Image


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('folder', type=Path)
    folder = ap.parse_args().folder.resolve()
    report = json.loads((folder/'report.json').read_text())
    esc = html.escape
    parts = ['<!doctype html><meta charset="utf-8"><title>Defect inspection comparison</title>',
             '<style>body{font:16px system-ui;margin:2rem;color:#202020}section{border-top:1px solid #aaa;margin:2rem 0} '
             '.arms{display:grid;grid-template-columns:1fr 1fr;gap:2rem}img{max-width:100%;max-height:300px;object-fit:contain} '
             'article{padding:1rem;background:#f4f4f4;margin:1rem 0}small{display:block}h1,h2,h3{line-height:1.2}</style>',
             '<h1>Overview versus regional inspection</h1><p>Development predictions; independent per-image reference review is pending. More boxes do not imply better accuracy. Crops retain source pixels; zooming cannot establish hidden defects.</p>']
    for row in report['cases']:
        parts.append(f'<section><h2>{esc(row["garment"])}</h2><div class="arms">')
        for arm in ['baseline', 'regional']:
            parts.append(f'<div><h3>{arm}</h3>')
            for photo in row['photos']:
                findings = ([{**f, 'source_box_2d': e['box_2d']} for f in row.get('baseline', {}).get('findings', [])
                             for e in f['evidence'] if e['frame_id'] == photo['photo']] if arm == 'baseline' else
                            photo.get('candidate', {}).get('findings', []))
                parts.append(f'<h4>{esc(photo["photo"])}</h4>')
                if not findings:
                    parts.append('<p>No saved finding (check report.json for call errors).</p>')
                for n, f in enumerate(findings):
                    path = folder/'review-crops'/row['garment']/f'{arm}-{Path(photo["photo"]).stem}-{n}.jpg'
                    path.parent.mkdir(parents=True, exist_ok=True)
                    y0, x0, y1, x1 = f['source_box_2d']
                    with Image.open(photo['views'][0]['path']) as im:
                        w, h = im.size
                        # Include context around each returned box without altering pixels.
                        py, px = max(5, (y1-y0)*.2), max(5, (x1-x0)*.2)
                        im.crop((max(0, int((x0-px)*w/1000)), max(0, int((y0-py)*h/1000)),
                                 min(w, round((x1+px)*w/1000)), min(h, round((y1+py)*h/1000)))).save(path, quality=95)
                    parts.append(f'<article><b>{esc(f["code"])} · {esc(f.get("status", "baseline shown"))} · {esc(f["severity"])}</b>'
                                 f'<p>{esc(f["note"])}</p><a href="{esc(path.relative_to(folder).as_posix())}"><img src="{esc(path.relative_to(folder).as_posix())}"></a>'
                                 f'<small>Source box: {f["source_box_2d"]}</small></article>')
            parts.append('</div>')
        parts.append('</div></section>')
    (folder/'review.html').write_text('\n'.join(parts))
    print(folder/'review.html')


if __name__ == '__main__':
    main()

"""Static evidence gallery for the experimental sequence, not a product UI."""
import argparse
import html
import json
import os
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('folder', type=Path)
    folder = ap.parse_args().folder.resolve()
    report = json.loads((folder/'report.json').read_text())
    esc = html.escape
    def relative(path):
        return esc(os.path.relpath(path, folder))
    parts = ['<!doctype html><meta charset="utf-8"><title>Defect sequence evidence</title>',
             '<style>body{font:16px system-ui;margin:2rem;color:#222}section{border-top:1px solid #999;margin-top:2rem}'
             '.items{display:flex;gap:1rem;flex-wrap:wrap}article{background:#f4f4f4;padding:1rem;max-width:350px}'
             'img{max-width:320px;max-height:220px;object-fit:contain}small{display:block}code{font-size:.85em}</style>',
             '<h1>Overview → regional proposals → contextual confirmation</h1>'
             '<p>Supported means a second model opinion. It is not independent truth. Rejected proposals remain saved; no-proposal images are not certified clean.</p>']
    for photo in report['photos']:
        parts.append(f'<section><h2>{esc(photo["garment"])} · {esc(photo["photo"])}</h2>')
        if not photo['proposals']:
            parts.append('<p>No detector proposal; context model skipped. This does not establish absence.</p>')
        parts.append('<div class="items">')
        for p in photo['proposals']:
            initial = ', '.join(f'{o["origin"]}: {o["initial_status"]}' for o in p['origins'])
            parts.append(f'<article><b>{esc(p["code"])} · {esc(p["context"]["status"])}</b>'
                         f'<p>{esc(p["context"]["reason"])}</p><small>{esc(initial)}</small>'
                         f'<small>Conservative policy: {esc(p.get("agreement_policy_status", "not yet computed"))}</small>')
            if p.get('crop'):
                parts.append(f'<a href="{relative(p["crop"])}"><img src="{relative(p["crop"])}"></a>')
            parts.append(f'<small>Source box: {p["box"]}</small></article>')
        parts.append('</div></section>')
    (folder/'review.html').write_text('\n'.join(parts))
    print(folder/'review.html')


if __name__ == '__main__':
    main()

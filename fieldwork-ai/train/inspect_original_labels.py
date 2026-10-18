"""Inspect annotation metadata via HTTP ranges, without downloading the image archive.

Refuses servers that do not honour partial responses. Does not extract archive files.
"""
import io
import argparse
import json
from pathlib import Path
import zipfile
import requests
import truststore
truststore.inject_into_ssl()

URL = "https://zenodo.org/records/13788681/files/clothing_v3.zip"
OUT = Path(__file__).resolve().parent.parent / "data/audit/original"


class RangeFile(io.RawIOBase):
    def __init__(self):
        self.position = 0
        self.downloaded = 0
        with requests.get(URL, headers={"Range": "bytes=0-0"}, stream=True, timeout=40) as response:
            if response.status_code != 206:
                raise RuntimeError(f"Server refused partial reads (HTTP {response.status_code}); archive was not downloaded")
            self.length = int(response.headers["Content-Range"].rsplit("/", 1)[1])

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        self.position = offset if whence == 0 else self.position + offset if whence == 1 else self.length + offset
        return self.position

    def read(self, size=-1):
        if size < 0:
            size = self.length - self.position
        size = min(size, self.length - self.position)
        if size <= 0:
            return b""
        if size > 32 * 1024 * 1024 or self.downloaded + size > 64 * 1024 * 1024:
            raise RuntimeError("Metadata read exceeded the 64 MiB inspection budget")
        end = self.position + size - 1
        with requests.get(URL, headers={"Range": f"bytes={self.position}-{end}"}, stream=True, timeout=60) as response:
            if response.status_code != 206:
                raise RuntimeError("Server stopped honouring partial reads; refusing full download")
            content_range = response.headers.get("Content-Range", "")
            if not content_range.startswith(f"bytes {self.position}-"):
                raise RuntimeError(f"Wrong partial response: {content_range}")
            data = response.raw.read(size)
        self.position += len(data)
        self.downloaded += len(data)
        return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe-null", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    with RangeFile() as remote, zipfile.ZipFile(remote) as archive:
        files = [i for i in archive.infolist() if i.filename.endswith((".json", ".py", ".csv"))]
        (OUT / "annotation-files.json").write_text(json.dumps([{"name": i.filename, "size": i.file_size,
            "offset": i.header_offset, "compressed_size": i.compress_size} for i in files], indent=2))
        print("Annotation files:", len(files), "archive bytes:", remote.length, flush=True)
        print("First names:", [i.filename for i in files[:15]], flush=True)
        jsons = sorted([i for i in files if i.filename.endswith(".json")], key=lambda i: i.header_offset)
        clusters = []
        for info in jsons:
            start, end = info.header_offset, info.header_offset + info.compress_size + len(info.filename.encode()) + 200
            if clusters and start - clusters[-1][1] < 1024:
                clusters[-1][1] = max(clusters[-1][1], end)
            else:
                clusters.append([start, end])
        print("Annotation range groups:", len(clusters), "bytes:", sum(b-a for a,b in clusters), flush=True)
        chosen = [i for i in files if i.filename.endswith("labels.py")]
        chosen += [i for i in files if "labels_" in i.filename and i.filename.endswith(".json")][:3]
        for index, info in enumerate(chosen[:5]):
            if info.file_size > 2 * 1024 * 1024:
                continue
            blob = archive.read(info)
            target = OUT / f"sample-{index}-{Path(info.filename).name}"
            target.write_bytes(blob)
            print("Saved annotation sample:", info.filename, len(blob), flush=True)
        if args.probe_null:
            manifest = list(map(json.loads, (OUT.parent / "manifest.jsonl").read_text().splitlines()))
            lookup = {}
            for info in jsons:
                lookup.setdefault(Path(info.filename).name, []).append(info)
            chosen_rows = []
            for split in ("train", "test"):
                candidates = [r for r in manifest if r["split"] == split and (r["labels"]["stains"] is None or r["labels"]["holes"] is None)]
                chosen_rows.extend(candidates[i] for i in sorted(set([0, len(candidates)//4, len(candidates)//2, 3*len(candidates)//4, len(candidates)-1])))
            samples = []
            for row in chosen_rows:
                filename = Path(row["source_image_path"]).stem.replace("front_", "labels_", 1) + ".json"
                matched = lookup.get(filename, [])
                if len(matched) != 1:
                    samples.append({"row_id": row["row_id"], "matches": len(matched)})
                    continue
                original = json.loads(archive.read(matched[0]))
                samples.append({"row_id": row["row_id"], "source": matched[0].filename,
                                "mirror": row["labels"], "original": original})
                print("Null probe:", row["row_id"], "stains=", original.get("stains", "<MISSING>"),
                      "holes=", original.get("holes", "<MISSING>"), flush=True)
            (OUT / "null-probes.json").write_text(json.dumps(samples, indent=2))
        print("Downloaded bytes:", remote.downloaded, flush=True)


if __name__ == "__main__":
    main()

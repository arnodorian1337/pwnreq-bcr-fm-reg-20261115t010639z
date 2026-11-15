#!/usr/bin/env python3
import hashlib, io, json, pathlib, subprocess, sys, tarfile, urllib.request

base, output = sys.argv[1:]
changed = subprocess.check_output(["git", "diff", "--name-only", f"{base}...HEAD"], text=True).splitlines()
sources = [pathlib.Path(name) for name in changed if name.startswith("modules/") and name.endswith("/source.json")]
if len(sources) != 1:
    raise SystemExit(f"expected exactly one new source.json, got {sources}")
path = sources[0]
source = json.loads(path.read_text())
url = source.get("docs_url", "")
if not url.startswith("https://"):
    raise SystemExit(f"unsupported docs_url: {path}")
request = urllib.request.Request(url, headers={"User-Agent": "bcr-first-materialization-review", "Cache-Control": "no-cache"})
with urllib.request.urlopen(request, timeout=120) as response:
    payload = response.read()
with tarfile.open(fileobj=io.BytesIO(payload), mode="r:*") as archive:
    members = [item for item in archive.getmembers() if item.isfile() and item.name.endswith(".binaryproto")]
    if [item.name for item in members] != ["proof.binaryproto"]:
        raise SystemExit(f"unexpected documentation members: {[item.name for item in members]}")
    if not archive.extractfile(members[0]).read():
        raise SystemExit("empty reviewed binaryproto")
receipt = {"docs_url": url, "head_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "sha256": hashlib.sha256(payload).hexdigest()}
pathlib.Path(output).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print(f"PASS reviewed docs {path}: sha256={receipt['sha256']}")

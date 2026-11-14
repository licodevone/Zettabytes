"""Publicação manual com código versionado em pacote e dependências do uv.lock.

Usado quando a integração GitHub/CLI não tem acesso. Nunca inclui o .env.
"""
import base64
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

payload = "".join(os.environ[f"APP_SOURCE_{i}"] for i in range(int(os.environ["APP_SOURCE_PARTS"])))
compressed = base64.b64decode(payload)
if hashlib.sha256(compressed).hexdigest() != os.environ["APP_SOURCE_SHA256"]:
    raise RuntimeError("Source checksum mismatch")
root = Path("/repo/apps/api")
root.mkdir(parents=True, exist_ok=True)
for name, content in json.loads(gzip.decompress(compressed)).items():
    target = (root / name).resolve()
    if not target.is_relative_to(root):
        raise RuntimeError("Invalid source path")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
os.chdir(root)
subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "--no-cache-dir", "--require-hashes", "-r", "requirements.railway.txt"], check=True)
os.setgid(1001)
os.setuid(1001)
subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
os.execv(sys.executable, [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", os.environ.get("PORT", "8100"), "--proxy-headers"])

"""Gera pacotes reproduzíveis sem segredos para a publicação manual."""
import base64
import gzip
import hashlib
import json
from pathlib import Path

repo = Path(__file__).resolve().parents[1]
out = repo / ".local" / "railway"
out.mkdir(parents=True, exist_ok=True)
api = repo / "apps" / "api"
api_files = [*api.glob("app/**/*.py"), *api.glob("alembic/**/*.py"), api / "alembic.ini", api / "requirements.railway.txt"]
web_files = [repo / name for name in ("package.json", "pnpm-lock.yaml", "pnpm-workspace.yaml", ".npmrc", "apps/api/package.json")]
for directory in ("apps/web", "packages/api-client", "packages/typescript-config"):
    web_files.extend(p for p in (repo / directory).rglob("*") if p.is_file() and not any(part in {"node_modules", ".next", ".turbo"} for part in p.relative_to(repo / directory).parts) and p.suffix not in {".tsbuildinfo"})
for name, files, root, bootstrap in (("api", api_files, api, "railway-api-bootstrap.py"), ("web", web_files, repo, "railway-web-bootstrap.cjs")):
    data = {p.relative_to(root).as_posix(): p.read_text(encoding="utf-8") for p in files}
    compressed = gzip.compress(json.dumps(data, ensure_ascii=False).encode(), mtime=0)
    encoded = base64.b64encode(compressed).decode()
    variables = {f"APP_SOURCE_{i//16000}": encoded[i:i+16000] for i in range(0, len(encoded), 16000)}
    variables.update(APP_SOURCE_PARTS=str((len(encoded)+15999)//16000), APP_SOURCE_SHA256=hashlib.sha256(compressed).hexdigest(), APP_BOOTSTRAP=base64.b64encode((repo / "infra" / bootstrap).read_bytes()).decode())
    (out / f"{name}-variables.json").write_text(json.dumps(variables), encoding="utf-8")
    print(f"{name}: {len(data)} files, {len(compressed)} compressed bytes, {variables['APP_SOURCE_PARTS']} parts")

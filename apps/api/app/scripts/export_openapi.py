"""Exporta o schema OpenAPI para arquivo (sem subir servidor). Usado pelo codegen do frontend."""

import json
import sys
from pathlib import Path

from app.main import app


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("openapi.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n", "utf-8")
    print(f"OpenAPI exportado para {target}")


if __name__ == "__main__":
    main()

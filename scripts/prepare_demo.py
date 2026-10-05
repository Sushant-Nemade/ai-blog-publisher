import argparse
from pathlib import Path
import shutil

from blogboard.services.storage import DOMAINS, Draft, LocalStorageService


def main():
    parser = argparse.ArgumentParser(description="Build an isolated synthetic test site")
    parser.add_argument("--output", type=Path, default=Path("build/demo/ai-blog-publisher"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    web = root / "blogboard" / "web"
    output = args.output.resolve()
    if output == web.resolve() or output.is_relative_to(web.resolve()):
        raise ValueError("demo output must be separate from the published site")
    shutil.copytree(web, output, dirs_exist_ok=True, ignore=shutil.ignore_patterns("blogs"))
    storage = LocalStorageService(output)
    for domain in DOMAINS:
        storage.put_object(f"blogs/{domain}/articles.json", "[]")
    draft = Draft.model_validate_json((root / "examples" / "reviewed-draft.json").read_text(encoding="utf-8"))
    storage.publish(draft, draft.digest())
    print(f"Synthetic fixture site verified: {storage.verify()} article at {output}")


if __name__ == "__main__":
    main()
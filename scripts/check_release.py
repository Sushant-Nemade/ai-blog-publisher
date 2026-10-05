from pathlib import Path
import re
import subprocess

from blogboard.services.storage import LocalStorageService


def main():
    root = Path(__file__).resolve().parents[1]
    names = subprocess.check_output(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                                    cwd=root).decode().split("\0")
    rules = [re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"),
             re.compile(r"github_pat_[A-Za-z0-9_]{50,}"),
             re.compile(r"gsk_[A-Za-z0-9]{30,}"),
             re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")]
    problems = []
    for name in filter(None, names):
        path = root / name
        if not path.is_file():
            continue
        if path.name == ".env" or name.startswith("drafts/"):
            problems.append(name)
        elif path.stat().st_size < 1000000:
            text = path.read_bytes().decode("utf-8", errors="ignore")
            if any(rule.search(text) for rule in rules):
                problems.append(name)
    if problems:
        raise ValueError("Possible private material in release files: " + ", ".join(problems))
    print(f"Release file screening passed; {LocalStorageService().verify()} site articles verified.")


if __name__ == "__main__":
    main()
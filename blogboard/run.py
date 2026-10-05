import argparse
import json
from pathlib import Path
import sys
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4


def today_ist() -> str:
    return datetime.now(timezone(timedelta(hours=5, minutes=30))).date().isoformat()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="AI Blog Publisher: generate a draft, never auto-publish")
    parser.add_argument("--date", default=today_ist(), help="Publication date in YYYY-MM-DD format")
    parser.add_argument("--dry-run", action="store_true", help="Offline preview: no network or output files")
    parser.add_argument("--ainews", action="store_true", help="Use the opt-in news research track")
    parser.add_argument("--fixture", action="store_true", help="Save the labeled synthetic example draft")
    parser.add_argument("--domain", choices=("ml", "dl", "nlp", "cv", "genai", "statistics"), default="ml")
    parser.add_argument("--topic", default=None, help="Tutorial topic, up to 300 characters")
    parser.add_argument("--draft", type=Path, help="Inspect a saved draft; does not publish by default")
    parser.add_argument("--approve", help="Publish --draft only if this SHA-256 matches its inspected digest")
    parser.add_argument("--verify-site", action="store_true", help="Validate local article indexes and files")
    parser.add_argument("--site-root", type=Path, help="Override the local static site directory")
    parser.add_argument("--draft-root", type=Path, help="Override the private draft directory")
    args = parser.parse_args(argv)
    try:
        date.fromisoformat(args.date)
    except ValueError:
        parser.error("--date must be a valid ISO date")
    if args.approve and not args.draft:
        parser.error("--approve requires --draft")
    if sum(bool(flag) for flag in (args.draft, args.fixture, args.verify_site)) > 1:
        parser.error("choose only one of --draft, --fixture, --verify-site")
    if args.topic and not 1 <= len(args.topic.strip()) <= 300:
        parser.error("--topic must contain 1 to 300 characters")
    if args.dry_run:
        print(json.dumps({"date": args.date, "domain": "ainews" if args.ainews else "ml",
                          "status": "preview", "network_calls": 0, "published": False}))
        return 0

    try:
        from blogboard.config.settings import app_settings
        from blogboard.services.storage import Draft, LocalStorageService, save_draft

        if args.site_root:
            app_settings.SITE_ROOT = args.site_root.resolve()
        if args.draft_root:
            app_settings.DRAFT_ROOT = args.draft_root.resolve()
        if args.verify_site:
            print(json.dumps({"verified_articles": LocalStorageService().verify()}))
        elif args.draft:
            if args.draft.stat().st_size > 100000:
                raise ValueError("draft exceeds size limit")
            draft = Draft.model_validate_json(args.draft.read_text(encoding="utf-8"))
            if args.approve:
                path = LocalStorageService().publish(draft, args.approve)
                print(json.dumps({"published": True, "file": path, "source": draft.source}))
            else:
                print(json.dumps({"digest": draft.digest(), "published": False, "draft": draft.model_dump()}, indent=2))
        elif args.fixture:
            example = Path(__file__).resolve().parents[1] / "examples" / "reviewed-draft.json"
            draft = Draft.model_validate_json(example.read_text(encoding="utf-8"))
            print(json.dumps({"draft": save_draft(draft), "digest": draft.digest(),
                              "source": "fixture", "published": False}))
        else:
            from blogboard.graph.graph import graph

            final_state = graph.invoke(
                {"date": args.date, "dry_run": False, "domain": "ainews" if args.ainews else args.domain,
                 **({"topic": args.topic} if args.topic else {})},
                config={"configurable": {"thread_id": str(uuid4())}, "recursion_limit": 20},
            )
            print(json.dumps({"draft": final_state["draft_path"], "published": False}))
        return 0
    except Exception as error:
        print(f"Operation failed ({type(error).__name__}). No publication reported; inspect configuration and retry.",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

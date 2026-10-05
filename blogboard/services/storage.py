from contextlib import contextmanager
from datetime import date
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from blogboard.config.settings import app_settings


Domain = Literal["ml", "dl", "nlp", "cv", "genai", "ainews", "statistics"]
DOMAINS = ("ml", "dl", "nlp", "cv", "genai", "ainews", "statistics")


class Draft(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    category: Domain
    topic: str = Field(min_length=1, max_length=300)
    subtopics: str = Field(default="", max_length=1000)
    title: str = Field(min_length=1, max_length=70)
    description: str = Field(min_length=1, max_length=160)
    slug: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    date: str
    content: str = Field(min_length=1, max_length=50000)
    source: Literal["groq", "fixture"] = "groq"

    @field_validator("date")
    @classmethod
    def valid_date(cls, value):
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError("date must be YYYY-MM-DD")
        return value

    @field_validator("content", "title", "description", "topic")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("text must not be blank")
        return value

    def digest(self):
        return hashlib.sha256(json.dumps(self.model_dump(), sort_keys=True,
                                        ensure_ascii=False).encode("utf-8")).hexdigest()


def safe_key(key):
    parts = PurePosixPath(key).parts
    if (not key or "\\" in key or ":" in key or key.startswith("/")
            or any(part in ("..", ".") for part in key.split("/")) or not parts):
        raise ValueError("invalid storage path")
    return key


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     delete=False, newline="\n") as handle:
        temporary = Path(handle.name)
        try:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class StorageHistory:
    def get_articles_json(self, domain):
        if domain not in DOMAINS:
            raise ValueError("unknown category")
        raw = self.get_object(f"blogs/{domain}/articles.json")
        if raw is None:
            return []
        articles = json.loads(raw)
        if not isinstance(articles, list):
            raise ValueError("article index must be an array")
        for article in articles:
            if (not isinstance(article, dict) or article.get("category") != domain
                    or not isinstance(article.get("file"), str)):
                raise ValueError("invalid article metadata")
            safe_key(article["file"])
            if not article["file"].startswith(f"blogs/{domain}/") or not article["file"].endswith(".md"):
                raise ValueError("article path does not match category")
            for field in ("title", "description", "date", "readTime"):
                if not isinstance(article.get(field), str):
                    raise ValueError("invalid article field")
            date.fromisoformat(article["date"])
        return articles

    def get_recent_history(self, domain, limit=3):
        articles = sorted(self.get_articles_json(domain), key=lambda item: item["date"], reverse=True)
        return [{"title": item["title"], "topic": item.get("topic", item["title"]),
                 "subtopics": item.get("subtopics", "")} for item in articles[:limit]]

    def get_all_domains_last_updated(self):
        return {domain: max((item["date"] for item in self.get_articles_json(domain)), default="")
                for domain in DOMAINS}


class LocalStorageService(StorageHistory):
    def __init__(self, root=None):
        self.root = Path(root or app_settings.SITE_ROOT).resolve()

    def path(self, key):
        path = self.root / safe_key(key)
        if not path.resolve().is_relative_to(self.root):
            raise ValueError("storage path escapes root")
        return path

    def get_object(self, key):
        path = self.path(key)
        return path.read_text(encoding="utf-8") if path.exists() else None

    def put_object(self, key, data, content_type="text/plain"):
        atomic_write(self.path(key), data)
        return True

    @contextmanager
    def publishing_lock(self):
        self.root.mkdir(parents=True, exist_ok=True)
        lock = self.root / ".publish.lock"
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            os.close(descriptor)
            yield
        finally:
            lock.unlink()

    def publish(self, draft, approved_digest):
        if not isinstance(draft, Draft) or approved_digest != draft.digest():
            raise ValueError("approval digest does not match the reviewed draft")
        relative = f"blogs/{draft.category}/{draft.slug}-{draft.digest()[:12]}.md"
        with self.publishing_lock():
            articles = self.get_articles_json(draft.category)
            existing = self.get_object(relative)
            if existing is not None and existing != draft.content:
                raise ValueError("immutable article collision")
            self.put_object(relative, draft.content, "text/markdown")
            entry = {"id": relative, "file": relative, "category": draft.category,
                     "title": draft.title, "description": draft.description, "date": draft.date,
                     "topic": draft.topic, "subtopics": draft.subtopics,
                     "tags": [draft.category, draft.source],
                     "readTime": f"{max(1, (len(draft.content.split()) + 199) // 200)} min",
                     "source": draft.source, "approvalDigest": draft.digest()}
            articles = [item for item in articles if item.get("id") != relative] + [entry]
            for article in articles:
                if self.get_object(article["file"]) is None:
                    raise ValueError("index references a missing article")
            self.put_object(f"blogs/{draft.category}/articles.json",
                            json.dumps(sorted(articles, key=lambda item: item["date"], reverse=True), indent=2),
                            "application/json")
        return relative

    def verify(self):
        count = 0
        for domain in DOMAINS:
            for article in self.get_articles_json(domain):
                if not (self.get_object(article["file"]) or "").strip():
                    raise ValueError("missing or blank article")
                count += 1
        return count


class R2StorageService(StorageHistory):
    def __init__(self):
        import boto3
        from botocore.config import Config

        settings = app_settings.r2
        if not all((settings.ACCOUNT_ID, settings.ACCESS_KEY_ID, settings.SECRET_ACCESS_KEY, settings.BUCKET_NAME)):
            raise ValueError("R2 history requires configured R2 credentials")
        self.bucket_name = settings.BUCKET_NAME
        self.client = boto3.client("s3", endpoint_url=f"https://{settings.ACCOUNT_ID}.r2.cloudflarestorage.com",
                                   aws_access_key_id=settings.ACCESS_KEY_ID,
                                   aws_secret_access_key=settings.SECRET_ACCESS_KEY, region_name="auto",
                                   config=Config(connect_timeout=10, read_timeout=30,
                                                 retries={"max_attempts": 2}))

    def get_object(self, key):
        from botocore.exceptions import ClientError

        try:
            return self.client.get_object(Bucket=self.bucket_name, Key=safe_key(key))["Body"].read().decode("utf-8")
        except ClientError as error:
            if error.response["Error"]["Code"] == "NoSuchKey":
                return None
            raise OSError("R2 read failed; existing index preserved") from None

    def put_object(self, key, data, content_type="text/plain"):
        try:
            self.client.put_object(Bucket=self.bucket_name, Key=safe_key(key),
                                   Body=data.encode("utf-8"), ContentType=content_type)
        except Exception:
            raise OSError("R2 upload failed") from None
        return True


def get_storage_service():
    return R2StorageService() if app_settings.STORAGE_BACKEND == "r2" else LocalStorageService()


def save_draft(draft):
    path = app_settings.DRAFT_ROOT / f"{draft.digest()}.json"
    atomic_write(path, json.dumps(draft.model_dump(), indent=2, ensure_ascii=False))
    return str(path)

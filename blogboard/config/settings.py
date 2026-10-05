from pathlib import Path
from typing import Dict, Literal
from pydantic import BaseModel, Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict

class LLMSettings(BaseModel):
    API_KEY: str = Field(default="", validation_alias=AliasChoices('API_KEY', 'api_key', 'GROQ_API_KEY', 'groq_api_key'))
    MODEL_NAME: str = "llama-3.3-70b-versatile"
    TEMPERATURE: float = 1.0
    TIMEOUT: float = Field(default=30, gt=0, le=120)
    MAX_TOKENS: int = Field(default=3500, ge=100, le=8000)
    MAX_RETRIES: int = Field(default=2, ge=0, le=3)

class TagSettings(BaseModel):
    ml: Dict[str, str] = {"label": "Machine Learning", "shortLabel": "ML"}
    dl: Dict[str, str] = {"label": "Deep Learning", "shortLabel": "DL"}
    statistics: Dict[str, str] = {"label": "Statistics for AI", "shortLabel": "Stats"}
    nlp: Dict[str, str] = {"label": "Natural Language Processing", "shortLabel": "NLP"}
    cv: Dict[str, str] = {"label": "Computer Vision", "shortLabel": "CV"}
    genai: Dict[str, str] = {"label": "Generative AI", "shortLabel": "Gen AI"}
    ainews: Dict[str, str] = {"label": "AI News", "shortLabel": "AI News"}

class R2Settings(BaseModel):
    ACCOUNT_ID: str = ""
    ACCESS_KEY_ID: str = ""
    SECRET_ACCESS_KEY: str = ""
    BUCKET_NAME: str = ""

class ContentAPISettings(BaseModel):
    TAVILY_API_KEY: str = ""
    GUARDIAN_API_KEY: str = ""
    UNSPLASH_API_KEY: str = ""

class Settings(BaseSettings):
    llm: LLMSettings = Field(default_factory=LLMSettings)
    tags: TagSettings = Field(default_factory=TagSettings)
    r2: R2Settings = Field(default_factory=R2Settings)
    content: ContentAPISettings = Field(default_factory=ContentAPISettings)
    STORAGE_BACKEND: Literal["local", "r2"] = "local"
    SITE_ROOT: Path = Path(__file__).resolve().parents[1] / "web"
    DRAFT_ROOT: Path = Path(__file__).resolve().parents[2] / "drafts"
    MAX_REVISIONS: int = Field(default=3, ge=0, le=3)

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore"
    )

app_settings = Settings()
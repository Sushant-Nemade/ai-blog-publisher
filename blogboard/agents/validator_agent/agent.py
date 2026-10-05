from pydantic import BaseModel, ConfigDict, Field

from blogboard.config.settings import app_settings
from blogboard.graph.state import BlogState
from blogboard.services.llm import LLMAgentService
from blogboard.services.prompt_manager import prompt_manager
from blogboard.services.storage import Draft, save_draft
from .prompts import VALIDATOR_PROMPT


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    approved: bool
    feedback: str = Field(max_length=2000)
    title: str = Field(max_length=70)
    description: str = Field(max_length=160)
    slug: str = Field(max_length=80)


def validator_node(state: BlogState) -> BlogState:
    if state.get("dry_run"):
        return {**state, "revision_needed": False}
    prompt = prompt_manager.get_prompt("Validator_Prompt", VALIDATOR_PROMPT,
                                      topic=state["topic"], content=state["content"])
    raw = LLMAgentService(temperature=0.1).llm.invoke(prompt).content
    review = Review.model_validate_json(raw)
    if not review.approved:
        revision = state.get("revision_count", 0)
        if revision >= app_settings.MAX_REVISIONS:
            raise ValueError("editorial review rejected after maximum revisions; nothing published")
        return {**state, "revision_needed": True, "validator_feedback": review.feedback,
                "revision_count": revision + 1}
    draft = Draft(category=state["domain"], topic=state["topic"], subtopics=state.get("subtopics", ""),
                  date=state["date"], title=review.title, description=review.description,
                  slug=review.slug, content=state["content"])
    path = save_draft(draft)
    return {**state, "revision_needed": False, "draft_path": path,
            "title": draft.title, "description": draft.description, "slug": draft.slug}

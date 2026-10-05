import json
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from pydantic import ValidationError

from blogboard.agents.validator_agent.agent import Review, validator_node
from blogboard.config.settings import app_settings
from blogboard.graph.graph import build_graph
from blogboard.services.llm import LLMAgentService
from blogboard.services.storage import Draft, LocalStorageService
from blogboard.tools import GuardianSearchTool, TavilySearchTool


def example():
    return Draft(category="ml", topic="Review workflow", title="A reviewed draft",
                 description="Synthetic test article", slug="reviewed-draft", date="2026-10-06",
                 content="## A safe publishing workflow\n\nSynthetic test content.", source="fixture")


class PublishingTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = LocalStorageService(self.folder.name)
        self.draft = example()

    def test_requires_current_digest(self):
        with self.assertRaises(ValueError):
            self.store.publish(self.draft, "wrong")
        changed = self.draft.model_copy(update={"content": "modified"})
        with self.assertRaises(ValueError):
            self.store.publish(changed, self.draft.digest())

    def test_idempotent_publication_and_integrity(self):
        first = self.store.publish(self.draft, self.draft.digest())
        self.assertEqual(first, self.store.publish(self.draft, self.draft.digest()))
        self.assertEqual(self.store.verify(), 1)

    def test_corrupt_index_preserved(self):
        self.store.put_object("blogs/ml/articles.json", "not JSON")
        with self.assertRaises(ValueError):
            self.store.publish(self.draft, self.draft.digest())
        self.assertEqual(self.store.get_object("blogs/ml/articles.json"), "not JSON")

    def test_failed_article_write_does_not_create_index(self):
        with patch.object(self.store, "put_object", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.store.publish(self.draft, self.draft.digest())
        self.assertIsNone(self.store.get_object("blogs/ml/articles.json"))

    def test_single_writer_lock(self):
        with self.store.publishing_lock():
            with self.assertRaises(FileExistsError):
                self.store.publish(self.draft, self.draft.digest())

    def test_invalid_path_and_category(self):
        for key in ("../secrets", "/absolute", "blogs\\file", "C:/file"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.store.get_object(key)
        with self.assertRaises(ValidationError):
            Draft(**{**self.draft.model_dump(), "category": "../bad"})

    def test_review_fails_closed(self):
        valid = {"approved": True, "feedback": "", "title": "Title", "description": "Description", "slug": "title"}
        for document in ("not JSON", "{}", json.dumps({**valid, "approved": "false"})):
            with self.subTest(document=document), self.assertRaises(ValidationError):
                Review.model_validate_json(document)

    def test_accepted_review_only_saves_private_draft(self):
        state = {"topic": "test", "content": "article", "domain": "ml", "date": "2026-10-06"}
        with patch("blogboard.agents.validator_agent.agent.LLMAgentService") as provider:
            provider.return_value.llm.invoke.return_value.content = json.dumps(
                {"approved": True, "feedback": "", "title": "Title", "description": "Description", "slug": "title"})
            with patch("blogboard.agents.validator_agent.agent.save_draft", return_value="private.json") as save:
                result = validator_node(state)
                self.assertEqual(result["draft_path"], "private.json")
                save.assert_called_once()
                self.assertIsNone(self.store.get_object("blogs/ml/articles.json"))

    def test_revision_exhaustion_never_saves(self):
        state = {"topic": "test", "content": "test", "revision_count": 3}
        with patch("blogboard.agents.validator_agent.agent.LLMAgentService") as provider:
            provider.return_value.llm.invoke.return_value.content = json.dumps(
                {"approved": False, "feedback": "reject", "title": "", "description": "", "slug": ""})
            with patch("blogboard.agents.validator_agent.agent.save_draft") as save:
                with self.assertRaises(ValueError):
                    validator_node(state)
                save.assert_not_called()

    def test_index_failure_can_be_retried(self):
        original = self.store.put_object
        def failing(key, data, content_type="text/plain"):
            if key.endswith("articles.json"):
                raise OSError("index write failed")
            return original(key, data, content_type)
        with patch.object(self.store, "put_object", side_effect=failing):
            with self.assertRaises(OSError):
                self.store.publish(self.draft, self.draft.digest())
        self.assertIsNone(self.store.get_object("blogs/ml/articles.json"))
        self.store.publish(self.draft, self.draft.digest())
        self.assertEqual(self.store.verify(), 1)

    def test_actual_graph_tracks_save_only_a_draft(self):
        for domain, generator in (("ml", "tutorial_agent"), ("ainews", "news_agent")):
            with self.subTest(domain=domain), patch.object(app_settings, "DRAFT_ROOT", self.store.root / "drafts"), \
                    patch.object(app_settings, "SITE_ROOT", self.store.root), \
                    patch(f"blogboard.agents.{generator}.agent.LLMAgentService") as generation, \
                    patch("blogboard.agents.validator_agent.agent.LLMAgentService") as validation:
                generation.return_value.llm.invoke.return_value.content = "## Mocked article\n\nProvider contract fixture."
                generation.return_value.get_news_agent.return_value.invoke.return_value = {
                    "messages": [SimpleNamespace(content="Source: https://example.org/reference")]}
                validation.return_value.llm.invoke.return_value.content = json.dumps({
                    "approved": True, "feedback": "", "title": "Graph test", "description": "Mocked workflow",
                    "slug": "graph-test"})
                result = build_graph().invoke({"domain": domain, "topic": "Test", "date": "2026-10-06"},
                                              config={"configurable": {"thread_id": domain}, "recursion_limit": 20})
                self.assertTrue(result["draft_path"].endswith(".json"))
                self.assertEqual(self.store.verify(), 0)

    def test_provider_is_bounded(self):
        with patch.object(app_settings.llm, "API_KEY", "synthetic-placeholder"), \
                patch("blogboard.services.llm.ChatGroq") as client:
            LLMAgentService()
            options = client.call_args.kwargs
            self.assertEqual(options["timeout"], 30)
            self.assertEqual(options["max_retries"], 2)
            self.assertEqual(options["max_tokens"], 3500)

    def test_missing_provider_key_rejected(self):
        with patch.object(app_settings.llm, "API_KEY", ""):
            with self.assertRaises(ValueError):
                LLMAgentService()

    def test_search_failure_is_redacted_and_stops(self):
        for tool, setting, request in ((TavilySearchTool(), "TAVILY_API_KEY", "post"),
                                       (GuardianSearchTool(), "GUARDIAN_API_KEY", "get")):
            with self.subTest(setting=setting), patch.object(app_settings.content, setting, "synthetic-placeholder"), \
                    patch(f"requests.{request}", side_effect=RuntimeError("private-provider-detail")):
                with self.assertRaises(RuntimeError) as caught:
                    tool.invoke({"query": "research", "days": 7})
                self.assertNotIn("private-provider-detail", str(caught.exception))

    def test_search_bounds_are_enforced(self):
        for tool in (TavilySearchTool(), GuardianSearchTool()):
            with self.subTest(tool=tool.name), self.assertRaises(ValidationError):
                tool.invoke({"query": "research", "days": 100})


if __name__ == "__main__":
    unittest.main()
from typing import Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from blogboard.config.settings import app_settings
import requests
from typing import Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool


class TavilySearchInput(BaseModel):
    """Input schema for the TavilySearchTool."""
    query: str = Field(min_length=1, max_length=300, description="The search query to look up on the web.")
    days: int = Field(default=7, ge=1, le=14, description="Number of days to look back for recent news.")


class TavilySearchTool(BaseTool):
    """
    Tavily Search Tool.
    
    This tool utilizes the Tavily API to fetch the most recent news articles
    based on a specific query. It is designed to be used by Langchain agents.
    """
    name: str = "tavily_search"
    description: str = "Search the web for news articles using the Tavily API. Useful for getting up-to-date technical or general news."
    args_schema: Type[BaseModel] = TavilySearchInput

    # Properly configuring the Pydantic behaviour for LangChain's BaseTool
    model_config = {
        "extra": "ignore" 
    }

    def _run(self, query: str, days: int = 7) -> str:
        """
        Executes the search query against the Tavily API.
        
        Args:
            query (str): The search phrase.
            days (int): Number of days to look back.
            
        Returns:
            str: A formatted string containing the top search results.
        """
        api_key = app_settings.content.TAVILY_API_KEY
        if not api_key:
             raise ValueError("Tavily is not configured")
        if not query.strip() or len(query) > 300 or not 1 <= days <= 14:
            raise ValueError("Invalid search bounds")

        try:
            response = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": query,
                    "topic": "news",
                    "days": days,
                    "max_results": 3,
                    "include_raw_content": False,
                    "include_images": False
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for result in data.get("results", [])[:3]:
                results.append(
                    f"Title: {result.get('title')}\n"
                    f"URL: {result.get('url')}\n"
                    f"Content: {str(result.get('content', ''))[:2000]}"
                )
                
            if not results:
                raise RuntimeError("No research sources returned")
                
            return "\n\n".join(results)
            
        except Exception:
            raise RuntimeError("Tavily research unavailable; no article generated") from None

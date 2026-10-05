from typing import Optional, List
from langchain_groq import ChatGroq
from langchain_core.tools import BaseTool
from langgraph.prebuilt import create_react_agent

from blogboard.config.settings import app_settings
from blogboard.tools import TavilySearchTool, GuardianSearchTool


class LLMAgentService:
    """
    A core service class responsible for managing LLM connections and 
    orchestrating tool-binding for multi-agent workflows.
    
    This class adheres to OOP principles, allowing easy instantiation 
    of different base LLMs and assembling specialized agents as needed.
    """
    
    def __init__(self, model_name: Optional[str] = None, temperature: Optional[float] = None):
        """
        Initializes the LLM Service with specific model configurations.
        
        Args:
            model_name (Optional[str]): The Groq model variant to use. Defaults to settings.
            temperature (Optional[float]): The inference temperature. Defaults to settings.
        """
        self.model_name = model_name or app_settings.llm.MODEL_NAME
        self.temperature = temperature if temperature is not None else app_settings.llm.TEMPERATURE
        self.api_key = app_settings.llm.API_KEY
        if not self.api_key:
            raise ValueError("Set llm__api_key locally before live generation")
        
        # Statically instantiate the main LLM client for reuse across agents created by this service
        self.llm = self._initialize_llm()

    def _initialize_llm(self) -> ChatGroq:
        """
        Core logic to instantiate the connection with Groq.
        
        Returns:
             ChatGroq: An active, authenticated Groq LLM instance.
        """
        return ChatGroq(
            model=self.model_name,
            temperature=self.temperature,
            api_key=self.api_key,
            timeout=app_settings.llm.TIMEOUT,
            max_tokens=app_settings.llm.MAX_TOKENS,
            max_retries=app_settings.llm.MAX_RETRIES,
        )
        
    def get_news_agent(self, system_prompt: Optional[str] = None):
        """
        Constructs a specialized News Research Agent equipped with our web-search tools.
        
        Args:
            system_prompt (Optional[str]): Context or behavioral instructions injected into the StateGraph.
            
        Returns:
            CompiledGraph: A runnable LangGraph ReAct agent pre-equipped with Tavily and Guardian search tools.
        """
        # Step 1: Initialize the tools designed for the News Agent
        news_tools: List[BaseTool] = []
        if app_settings.content.TAVILY_API_KEY:
            news_tools.append(TavilySearchTool())
        if app_settings.content.GUARDIAN_API_KEY:
            news_tools.append(GuardianSearchTool())
        if not news_tools:
            raise ValueError("News research requires at least one configured search provider")
        
        # Step 2: Bind the tools and LLM using LangGraph's prebuilt ReAct orchestrator
        agent = create_react_agent(
            model=self.llm,
            tools=news_tools,
            prompt=system_prompt
        )
        return agent
        
    def get_custom_agent(self, tools: List[BaseTool], system_prompt: Optional[str] = None):
        """
        A flexible builder method to create a custom agent given an arbitrary set of OOP-based tools.
        
        Args:
            tools (List[BaseTool]): A list of initialized classes inheriting from BaseTool.
            system_prompt (Optional[str]): Context or behavioral instructions injected into the agent.
            
        Returns:
            CompiledGraph: A customizable runnable LangGraph ReAct agent.
        """
        agent = create_react_agent(
            model=self.llm,
            tools=tools,
            prompt=system_prompt
        )
        return agent

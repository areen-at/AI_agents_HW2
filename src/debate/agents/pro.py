"""ProAgent — argues FOR the motion using its distinct persuasion skill (Phase 5).

Differs from :class:`~debate.agents.con.ConAgent` *only* by position (``PRO``)
and the skill drawn from config; every behaviour lives in :class:`DebaterAgent`.
"""

from __future__ import annotations

from ..config.schema import Config
from ..llm.base import LLMProvider
from ..protocol.message import Party
from ..tools.web_search import WebSearchTool
from .debater import DebaterAgent


class ProAgent(DebaterAgent):
    """The affirmative debater."""

    def __init__(
        self,
        *,
        llm: LLMProvider,
        config: Config,
        web: WebSearchTool | None = None,
        logger: object | None = None,
    ) -> None:
        super().__init__(
            llm=llm,
            config=config,
            agent_id="pro",
            position=Party.PRO,
            skill=config.debate.pro_skill,
            prompt_name="pro",
            web=web,
            logger=logger,
        )

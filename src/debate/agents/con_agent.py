"""ConAgent — argues AGAINST the motion using its distinct persuasion skill.

Differs from :class:`~debate.agents.pro.ProAgent` *only* by position (``CON``)
and the skill drawn from config; every behaviour lives in :class:`DebaterAgent`.

Note: this module is named ``con_agent`` rather than ``con`` because ``con`` is
a reserved device name on Windows — a file named ``con.py`` cannot be created,
committed, or checked out there. The same reason names its prompt ``con_side.md``.
"""

from __future__ import annotations

from ..config.schema import Config
from ..llm.base import LLMProvider
from ..protocol.message import Party
from ..tools.web_search import WebSearchTool
from .debater import DebaterAgent


class ConAgent(DebaterAgent):
    """The opposing debater."""

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
            agent_id="con",
            position=Party.CON,
            skill=config.debate.con_skill,
            prompt_name="con_side",
            web=web,
            logger=logger,
        )

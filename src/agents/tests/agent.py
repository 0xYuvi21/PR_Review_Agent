from typing import List, Dict, Any
from src.models.finding import Finding
from .prompts import TESTS_AGENT_SYSTEM_PROMPT

class TestsSpecialist:
    def __init__(self):
        self.agent_type = "tests"

    async def analyze(self, diff: str) -> List[Finding]:
        """
        Analyzes the diff to ensure code changes are adequately tested.
        
        Steps:
        1. Inspect the diff
        2. Determine missing evidence
        3. Use role-scoped tools for retrieval
        4. Ground findings in observed evidence
        """
        # TODO: Implement retrieval (changed files, tests, callers/callees)
        # TODO: LLM Invocation with structured output parsing
        return []

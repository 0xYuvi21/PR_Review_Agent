from pydantic import BaseModel, Field
from typing import Optional, List

class Finding(BaseModel):
    agent_type: str = Field(..., description="The specialist agent that generated this finding (e.g., 'tests', 'security')")
    severity: str = Field(..., description="Post-amplification severity level (e.g., LOW, MEDIUM, HIGH, CRITICAL)")
    category: str = Field(..., description="Category of the finding")
    summary: str = Field(..., description="Short summary of the issue")
    file_path: str = Field(..., description="Path to the file where the issue was found")
    line_start: int = Field(..., description="Starting line number")
    line_end: int = Field(..., description="Ending line number")
    suggestion: str = Field(..., description="Suggested fix or improvement")
    confidence: float = Field(..., description="Confidence score between 0.0 and 1.0")
    rationale: str = Field(..., description="Rationale referencing evidence visible to the agent")
    blast_radius: Optional[float] = Field(None, description="Blast radius score [0,1], or null if graph unavailable")

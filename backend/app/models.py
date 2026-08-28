from pydantic import BaseModel


class Finding(BaseModel):
    source: str
    severity: str
    category: str
    component: str
    issue: str
    explanation: str
    recommendation: str
    risk_score: int = 0
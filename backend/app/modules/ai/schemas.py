from pydantic import BaseModel

class SummarizeRequest(BaseModel):
    text: str
    
class SummaryResult(BaseModel):
    # The one shape every ai provide must return

    summary: str

    # The ui can show a DEMO label so nobody mistakes a mock for real AI.
    is_mock: bool # True when the text came for a fake provider

from typing import List, Dict, Literal
from pydantic import BaseModel, Field

class ProofPoint(BaseModel):
    name: str
    summary: str

class EmailTemplate(BaseModel):
    subject: str
    body: str

class ThreeWhys(BaseModel):
    why_anything: str
    why_mongodb: str
    why_now: str

class SpokeContent(BaseModel):
    company: str
    spoke_name: str
    hypothesis: Dict[str, str]
    why_mongodb: Dict[str, str]
    proof_points: List[ProofPoint]
    talk_track: str
    email_template: EmailTemplate
    three_whys: ThreeWhys

class SpokeCreateRequest(BaseModel):
    company: str
    notes: str = ""
    transcript: str = ""

    provider: Literal["openai", "anthropic"] = "anthropic"
    # default to opus 4.6
    model: str = "claude-opus-4-6"
    extra_instructions: str = ""

class SpokeInDB(SpokeContent):
    id: str = Field(alias="_id")
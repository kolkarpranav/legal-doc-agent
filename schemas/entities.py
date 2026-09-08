from pydantic import BaseModel
from typing import List, Optional

class Respondent(BaseModel):
    number: int
    name: str

class Deponent(BaseModel):
    name: str
    designation: str
    organisation: str
    address: str

class ReplyPoint(BaseModel):
    paragraph_number: int
    heading: str
    content: str

class EvidenceMap(BaseModel):
    field_name: str
    value: str
    source_document: str
    source_context: str

class CaseEntities(BaseModel):
    court: str
    jurisdiction: str
    case_type: str
    case_number: str
    year: str
    petitioner: str
    respondents: List[Respondent]
    filing_respondent_number: int
    deponent: Deponent
    verification_verb: str
    jurat_verb: str
    place: str
    date: str
    exhibit: str
    advocate_firm: str
    paragraph_count: int
    reply_points: List[ReplyPoint] = []
    evidence_map: Optional[List[EvidenceMap]] = None

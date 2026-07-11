from pydantic import BaseModel
from typing import Optional


class EvolutionWebhookPayload(BaseModel):
    event: str
    data: dict

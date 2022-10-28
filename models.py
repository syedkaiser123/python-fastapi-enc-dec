from datetime import datetime
from typing import Union

from fastapi import FastAPI
from pydantic import BaseModel


class AddMeeting(BaseModel):
    meeting_date_time: datetime
    host_name: Union[str, None] = None
    meeting_name: str
    meeting_source: Union[str, None] = None
    
    
class AddConversation(BaseModel):
    date_time: datetime
    meeting_id: str
    meeting_transcribed_text: str
    meeting_translation_text: Union[str, None] = None
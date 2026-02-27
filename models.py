from __future__ import annotations

from datetime import datetime
from enum import IntEnum
from typing import List, Optional
import uuid

from pydantic import BaseModel, Field, validator


class MoodLevel(IntEnum):
    veryBad = 1
    bad = 2
    neutral = 3
    good = 4
    veryGood = 5

    @property
    def emoji(self) -> str:
        return {
            MoodLevel.veryBad: "😢",
            MoodLevel.bad: "😟",
            MoodLevel.neutral: "😐",
            MoodLevel.good: "🙂",
            MoodLevel.veryGood: "😊",
        }[self]

    @classmethod
    def _missing_(cls, value):
        # Fallback to neutral for unknown values (mirrors Dart implementation)
        return cls.neutral


class DiaryEntryModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime
    moodLevel: MoodLevel
    emotions: List[str] = Field(default_factory=list)
    healthComplaints: Optional[str] = None
    foodIntake: Optional[str] = None
    notes: Optional[str] = None

    @validator("emotions", pre=True, always=True)
    def ensure_emotions_list(cls, v):
        if v is None:
            return []
        if not isinstance(v, list):
            raise ValueError("emotions must be a list of strings")
        # allow pydantic to coerce list contents; ensure they're strings
        return [str(x) for x in v]

    class Config:
        # Serialize enums to their values (ints) when exporting
        use_enum_values = True
        json_encoders = {datetime: lambda v: v.isoformat()}

    def to_json_dict(self) -> dict:
        """Return a JSON-serializable dict matching the frontend shape."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "moodLevel": int(self.moodLevel),
            "emotions": self.emotions,
            "healthComplaints": self.healthComplaints,
            "foodIntake": self.foodIntake,
            "notes": self.notes,
        }

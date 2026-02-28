from __future__ import annotations

from datetime import datetime
from enum import IntEnum, Enum
from typing import List, Optional

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
    id: Optional[int] = None
    patientProfileId: int
    timestamp: datetime
    moodLevel: MoodLevel
    emotions: List[str] = Field(default_factory=list)
    healthComplaints: Optional[str] = None
    foodIntake: Optional[str] = None
    notes: Optional[str] = None
    suggestion: Optional[str] = None


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
            "suggestion": self.suggestion,
        }

class AlertSeverity(int, Enum):
    info = 0
    warning = 1
    urgent = 2

    @classmethod
    def _missing_(cls, value):
        # fallback to info when unknown
        return cls.info


class HealthAlertModel(BaseModel):
    id: Optional[int] = None
    patientProfileId: int
    title: str
    message: str
    timestamp: datetime
    isRead: bool = False
    severity: AlertSeverity = AlertSeverity.info

    class Config:
        use_enum_values = True
        json_encoders = {datetime: lambda v: v.isoformat()}

    def to_json_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "isRead": self.isRead,
            "severity": str(self.severity),
        }



class PatientProfileModel(BaseModel):
    """Pydantic model matching the Flutter `PatientProfile` structure.

    Note: an `id` field is added to act as a unique key for CRUD operations.
    JSON keys are kept compatible with the Dart `toJson()` (e.g. `languageCode`).
    """

    id: Optional[int] = None
    name: str = ""
    tajNumber: Optional[int] = None
    languageCode: str = Field(default="en")
    chronicIllnesses: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    drugSensitivities: List[str] = Field(default_factory=list)
    dateOfBirth: Optional[datetime] = None


    @validator("chronicIllnesses", "allergies", "drugSensitivities", pre=True, always=True)
    def ensure_list_of_strings(cls, v):
        if v is None:
            return []
        if not isinstance(v, list):
            raise ValueError("must be a list of strings")
        return [str(x) for x in v]

    @validator("dateOfBirth", pre=True)
    def parse_date_of_birth(cls, v):
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        # accept ISO-8601 string
        try:
            return datetime.fromisoformat(v)
        except Exception:
            raise ValueError("dateOfBirth must be an ISO-8601 datetime string or null")

    class Config:
        use_enum_values = True
        json_encoders = {datetime: lambda v: v.isoformat()}

    def to_json_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "tajNumber": self.tajNumber,
            "languageCode": self.languageCode,
            "chronicIllnesses": self.chronicIllnesses,
            "allergies": self.allergies,
            "drugSensitivities": self.drugSensitivities,
            "dateOfBirth": self.dateOfBirth.isoformat() if self.dateOfBirth else None,
        }

class ClinicalNote(BaseModel):
    id: Optional[int] = None
    patientProfileId: int
    timestamp: datetime
    content: str

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

    def to_json_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "content": self.content,
        }

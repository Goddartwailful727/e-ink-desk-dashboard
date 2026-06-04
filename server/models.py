from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DDLItem(BaseModel):
    name: str
    due_str: str = ""
    days_left: int | None = None
    priority: int = 0


class PlanItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    time: str = ""
    task: str = ""
    subject: str = ""
    done: bool = False
    break_item: bool = Field(default=False, alias="break")


class Exam(BaseModel):
    name: str
    date: str = ""
    days_left: int = 0


class PlanData(BaseModel):
    date: str = ""
    items: list[PlanItem] = Field(default_factory=list)
    exams: list[Exam] = Field(default_factory=list)


class ReciteData(BaseModel):
    text: str = ""


class TickBody(BaseModel):
    index: int = -1


class ReciteBody(BaseModel):
    text: str = ""


class PlanPushBody(BaseModel):
    items: list[PlanItem] = Field(default_factory=list)
    exams: list[Exam] = Field(default_factory=list)


class DDLListBody(BaseModel):
    items: list[DDLItem] = Field(default_factory=list)

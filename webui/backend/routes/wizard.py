from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..auth import CurrentUser
from ..db import get_db

router = APIRouter(prefix="/api/wizard", tags=["wizard"])


class WizardState(BaseModel):
    current_step: int = 1
    answers: dict = Field(default_factory=dict)


GOPAY_PHONE_PLACEHOLDER = "YOUR_PHONE_NUMBER"
GOPAY_PIN_PLACEHOLDER = "YOUR_6_DIGIT_GOPAY_PIN"


def _without_gopay_credentials(answers: dict) -> dict:
    clean = dict(answers)
    gopay = clean.get("gopay")
    if isinstance(gopay, dict):
        clean["gopay"] = {
            **gopay,
            "phone_number": GOPAY_PHONE_PLACEHOLDER,
            "pin": GOPAY_PIN_PLACEHOLDER,
        }
    return clean


def _read() -> WizardState:
    data = get_db().get_runtime_json("wizard_state", {})
    if not isinstance(data, dict):
        return WizardState()
    try:
        state = WizardState(**data)
        clean_answers = _without_gopay_credentials(state.answers)
        if clean_answers != state.answers:
            state.answers = clean_answers
            get_db().set_runtime_json("wizard_state", state.model_dump())
        else:
            state.answers = clean_answers
        return state
    except Exception:
        return WizardState()


def _write(state: WizardState) -> None:
    state.answers = _without_gopay_credentials(state.answers)
    get_db().set_runtime_json("wizard_state", state.model_dump())


@router.get("/state")
def get_state(user: str = CurrentUser):
    return _read()


@router.post("/state")
def set_state(state: WizardState, user: str = CurrentUser):
    _write(state)
    return {"ok": True}

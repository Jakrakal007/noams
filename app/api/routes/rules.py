from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.rules import RuleConfigurationResponse, RuleListResponse, RuleUpdateRequest
from app.services.rules import rule_service

router = APIRouter(prefix="/api/rules", tags=["rules"])


@router.get("", response_model=RuleListResponse)
def list_rules(db: Session = Depends(get_db)) -> RuleListResponse:
    return RuleListResponse(items=rule_service.list_rules(db))


@router.get("/{rule_code}", response_model=RuleConfigurationResponse)
def get_rule(rule_code: str, db: Session = Depends(get_db)) -> RuleConfigurationResponse:
    return rule_service.get_rule(db, rule_code)


@router.patch("/{rule_code}", response_model=RuleConfigurationResponse)
def update_rule(rule_code: str, payload: RuleUpdateRequest, db: Session = Depends(get_db)) -> RuleConfigurationResponse:
    return rule_service.update_rule(db, rule_code, enabled=payload.enabled, configuration=payload.configuration)


@router.post("/{rule_code}/reset", response_model=RuleConfigurationResponse)
def reset_rule(rule_code: str, db: Session = Depends(get_db)) -> RuleConfigurationResponse:
    return rule_service.reset_rule(db, rule_code)

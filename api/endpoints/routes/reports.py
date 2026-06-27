from fastapi import APIRouter, Depends
from typing import Annotated

from api.endpoints.deps import RoleChecker
from api.models.user import User, UserRole
from api.services.reports import adr_service
from api.models.report import CreateADR, ReadADR
from api.services.base import BaseService
from api.schemas.response import APIResponse
from api.core.database import ReadSessionDep
from fastapi import APIRouter

router = APIRouter(prefix='/reports',tags=["reports"])


@router.get("/adr",response_model=APIResponse[list[ReadADR]])
async def get_adr_reports(session: ReadSessionDep):
    # Fetch records using the generic base service
    reports = adr_service.get_multi(session)
    
    return APIResponse(data=reports)


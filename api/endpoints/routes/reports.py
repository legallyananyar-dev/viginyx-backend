from api.models.report import CreateADR, ReadADR
from api.services.base import BaseService
from api.schemas.response import APIResponse
from api.core.database import ReadSessionDep
from fastapi import APIRouter

router = APIRouter(tags=["reports"])

adr_service = BaseService(CreateADR)

@router.get("/adr-reports", response_model=APIResponse[list[ReadADR]])
def get_adr_reports(session: ReadSessionDep):
    # Fetch records using the generic base service
    reports = adr_service.get_multi(session)
    
    return {
        "data": reports
    }

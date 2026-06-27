from typing import Any
from sqlmodel import Session, select
from api.models.report import CreateADR
from api.services.base import BaseService

class ADRService(BaseService[CreateADR, CreateADR, CreateADR]):
    """
    ADR specific repository/service logic.
    Inherits standard CRUD from BaseService and adds custom domain logic.
    """

    
    
# Instantiate a global instance of the service to be used across the app
adr_service = ADRService(CreateADR)

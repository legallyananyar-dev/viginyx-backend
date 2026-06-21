import logging
import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlmodel import Session
from api.core.database import write_engine
from api.core.config import settings
from api.services.user import user_service
from api.models.user import UserCreate, UserRole, UserType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init() -> None:
    with Session(write_engine) as session:
        if settings.first_superuser and settings.first_superuser_password:
            user = user_service.get_by_email(session, email=settings.first_superuser)
            if not user:
                user_in = UserCreate(
                    email=settings.first_superuser,
                    password=settings.first_superuser_password,
                    confirm_password=settings.first_superuser_password,
                    role=UserRole.SUPER_ADMIN,
                    user_type=UserType.DOCTOR,
                    first_name="Super",
                    last_name="Admin",
                    is_active=True,
                )
                user = user_service.create(session, obj_in=user_in)
                logger.info(f"Super user {user.email} created successfully.")
            else:
                logger.info(f"Super user {user.email} already exists.")
        else:
            logger.warning("FIRST_SUPERUSER or FIRST_SUPERUSER_PASSWORD not set in env.")

if __name__ == "__main__":
    logger.info("Creating initial data")
    init()
    logger.info("Initial data created")

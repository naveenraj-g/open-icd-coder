from dependency_injector.wiring import Provide, inject
from fastapi import Depends

from app.di.container import Container
from app.services.coding_service import CodingService


@inject
def get_coding_service(
    service: CodingService = Depends(Provide[Container.coding.coding_service]),
) -> CodingService:
    return service

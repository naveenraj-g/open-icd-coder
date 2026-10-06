from dependency_injector import containers, providers

from app.di.core import CoreContainer
from app.di.modules import CodingContainer, TerminologyContainer


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(packages=["app.di.dependencies"])

    core = providers.Container(CoreContainer)

    terminology = providers.Container(
        TerminologyContainer,
        core=core,
    )

    coding = providers.Container(
        CodingContainer,
        core=core,
        terminology=terminology,
    )

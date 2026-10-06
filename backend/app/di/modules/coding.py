from dependency_injector import containers, providers

from app.coding.engines.jev import JevEngine
from app.coding.engines.search_rank import SearchRankEngine
from app.core.config import settings
from app.repository.coding_repository import CodingRepository
from app.services.coding_service import CodingService


class CodingContainer(containers.DeclarativeContainer):
    core = providers.DependenciesContainer()
    terminology = providers.DependenciesContainer()

    coding_repository = providers.Factory(
        CodingRepository,
        session_factory=core.database.provided.session,
    )

    # Decision engines by name — selected per request (?engine=) or by
    # coding.default_engine.
    # "jev" is the configured route (jev.route); each route is also
    # selectable by its own name.
    jev_opencode = providers.Singleton(
        JevEngine, config=settings.jev, route="opencode", api_key=settings.OPENCODE_API_KEY
    )
    jev_vercel = providers.Singleton(
        JevEngine, config=settings.jev, route="vercel", api_key=settings.AI_GATEWAY_API_KEY
    )
    engines = providers.Dict(
        {
            SearchRankEngine.name: providers.Singleton(SearchRankEngine),
            "jev": jev_opencode if settings.jev.route == "opencode" else jev_vercel,
            "jev-opencode": jev_opencode,
            "jev-vercel": jev_vercel,
        }
    )

    coding_service = providers.Factory(
        CodingService,
        repository=coding_repository,
        terminology=terminology.terminology_service,
        engines=engines,
        config=settings.coding,
    )

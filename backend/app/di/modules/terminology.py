from dependency_injector import containers, providers

from app.core.config import settings
from app.repository.terminology_repository import TerminologyRepository
from app.services.terminology_service import TerminologyService


class TerminologyContainer(containers.DeclarativeContainer):
    core = providers.DependenciesContainer()

    terminology_repository = providers.Factory(
        TerminologyRepository,
        session_factory=core.database.provided.session,
    )

    terminology_service = providers.Factory(
        TerminologyService,
        repository=terminology_repository,
        embedding_client=core.embedding_client,
        use_index_terms=settings.search.use_index_terms,
        collapse_variants=settings.search.collapse_variants,
        candidate_pool=settings.search.candidate_pool,
        text_match=settings.search.text_match,
        index_length_penalty=settings.search.index_length_penalty,
        hybrid_text_weight=settings.search.hybrid_text_weight,
    )

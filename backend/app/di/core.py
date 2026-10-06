from dependency_injector import containers, providers

from app.core.config import settings
from app.core.database import Database
from app.core.embeddings import EmbeddingClient


class CoreContainer(containers.DeclarativeContainer):
    # Singleton database
    database = providers.Singleton(
        Database,
        db_url=settings.DATABASE_URL,
    )

    # Singleton so every request shares one HTTP connection pool
    embedding_client = providers.Singleton(
        EmbeddingClient,
        config=settings.embedding,
        api_key=settings.EMBEDDING_API_KEY,
    )

from typing import Literal

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


class LogConfig(BaseModel):
    """Consumed by app.core.logging.setup_logging() and app.core.database's
    query listeners."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # "json" (one JSON object per line) or "console" (human-readable).
    format: Literal["json", "console"] = "json"

    # Hand-edited values like `level: debug` or `format: JSON` are accepted.
    @field_validator("level", "format", mode="before")
    @classmethod
    def _normalise_case(cls, v):
        if isinstance(v, str):
            return v.upper() if v.upper() in _LOG_LEVELS else v.lower()
        return v

    # Any SQL statement slower than this logs a `db.slow_query` WARNING.
    slow_query_ms: int = 500

    # Log every SQL statement at DEBUG (very noisy — debugging only).
    sql_echo: bool = False


class CorsConfig(BaseModel):
    allow_origins: list[str] = Field(default_factory=list)


class SearchConfig(BaseModel):
    default_limit: int = 20
    max_limit: int = 100
    # Mode used when the caller doesn't pass ?mode=. semantic/hybrid need the
    # embedding server; set "text" to run without it.
    default_mode: Literal["text", "semantic", "hybrid"] = "hybrid"
    # Also match Alphabetic Index terms (synonyms, eponyms, cross-references).
    use_index_terms: bool = True
    # Merge codes that differ only in the 7th character into one hit.
    collapse_variants: bool = True
    # Candidates fetched per source (concept text / index terms) per method
    # before merging, expansion and collapsing.
    candidate_pool: int = Field(200, ge=10, le=1000)
    # How text search treats query words: "all" must match; "any" may match
    # (all-words bonus); "fallback" = all, then any only if all finds ~nothing.
    text_match: Literal["all", "any", "fallback"] = "all"
    # Score index terms so a term that merely CONTAINS the query ranks below
    # one that IS the query.
    index_length_penalty: bool = True
    # Weighted reciprocal rank fusion in hybrid mode (semantic weight is 1.0).
    hybrid_text_weight: float = Field(1.0, ge=0.0, le=2.0)


class TerminologyConfig(BaseModel):
    # Percent of Alphabetic Index terms held OUT of search so evaluation can
    # query them without testing on loaded text. Prototype: 20. For
    # production, set 0 and reload the index so every term is searchable.
    index_holdout_percent: int = Field(20, ge=0, le=100)


class CodingConfig(BaseModel):
    """Stage 2-4 pipeline: candidates -> decision engine -> review."""

    # Item types that get searched + scored. Others are stored as not_coded.
    coded_item_types: list[Literal["condition", "observation", "service_request", "medication_request"]] = (
        Field(default_factory=lambda: ["condition"])
    )
    # Search candidates stored per item and handed to the decision engine.
    candidates_per_item: int = Field(100, ge=1, le=500)
    # Ranked alternatives shown per item under the assigned code.
    alternatives_shown: int = Field(15, ge=0, le=100)
    # Assigned-code probability below this -> LOW_CONFIDENCE -> close review.
    low_confidence_threshold: float = Field(0.75, ge=0.0, le=1.0)
    # "None of the above" probability at or above this -> NONE_OF_THE_ABOVE.
    nota_flag_threshold: float = Field(0.2, ge=0.0, le=1.0)
    # Engine used when a request doesn't name one.
    default_engine: str = "search-rank"


class JevRouteConfig(BaseModel):
    """One way to reach Jev — both speak TypeSafe's state + typed-questions
    format and return a probability per choice option."""

    base_url: str
    path: str  # "/evaluate" (Vercel) or "/systemone" (TypeSafe-native)
    model: str
    # Settings field holding the key (a secret, so it lives in .env).
    api_key_setting: str
    # Used to compute cost when the response doesn't report it.
    input_price_per_million: float | None = None
    # Whether the route accepts providerOptions.gateway.zeroDataRetention.
    supports_zdr_option: bool = False


class JevConfig(BaseModel):
    """Jev (TypeSafe AI). The candidate codes become the options of a
    `choice` question; the answer carries a probability for every option."""

    # Route the "jev" engine uses. Each route is also available by name as
    # engine "jev-<route>".
    route: Literal["opencode", "vercel"] = "opencode"
    routes: dict[str, JevRouteConfig] = Field(
        default_factory=lambda: {
            # OpenCode Zen — model jev-1.13 (paid; zero-retention per OpenCode's
            # docs) or jev-1.13-free (prompts may be used for training: synthetic
            # data only). Reports usage, not cost.
            "opencode": JevRouteConfig(
                base_url="https://opencode.ai/zen/v1",
                path="/systemone",
                model="jev-1.13",
                api_key_setting="OPENCODE_API_KEY",
                input_price_per_million=0.042,
            ),
            # Vercel AI Gateway evaluation API — reports cost. Gateway listing
            # says zdr "none".
            "vercel": JevRouteConfig(
                base_url="https://ai-gateway.vercel.sh/v1",
                path="/evaluate",
                model="typesafe-ai/jev",
                api_key_setting="AI_GATEWAY_API_KEY",
                input_price_per_million=0.042,
                supports_zdr_option=True,
            ),
        }
    )
    timeout_seconds: float = 60.0
    # Retries on 429 / 5xx / network errors only — 4xx means a bad request or
    # account problem and won't succeed on retry.
    max_retries: int = Field(2, ge=0, le=5)
    retry_backoff_seconds: float = 1.0
    # Vercel route only: route only to zero-data-retention providers.
    zero_data_retention: bool = False
    # Offer "none of the above" as an extra option (docs/goal.md §4.3).
    include_none_of_the_above: bool = True
    instructions: str = (
        "Select the ICD-10-CM code that most accurately and specifically codes the "
        "condition in `condition_to_code`, as documented in the SOAP note in `soap_note`. "
        "Prefer the most specific code the documentation supports. Choose "
        "NONE_OF_THE_ABOVE if no listed code fits the condition."
    )


class EmbeddingConfig(BaseModel):
    """OpenAI-compatible embeddings endpoint (LM Studio locally)."""

    base_url: str = "http://localhost:1234/v1"
    model: str = "text-embedding-qwen3-embedding-0.6b"
    # Must match the vector(N) column in terminology_concept_embedding.
    dimensions: int = 1024
    # Prepended to search queries only — documents are embedded as-is.
    # Qwen3-Embedding is instruction-aware; omitting this costs 1-5% recall.
    query_instruction: str = (
        "Instruct: Given a clinical phrase, retrieve the matching ICD-10-CM diagnosis\nQuery: "
    )
    # Bulk embedding job: texts per request, and requests in flight.
    batch_size: int = 64
    concurrency: int = 4
    timeout_seconds: float = 300.0
    # Retries per request on HTTP/connection errors, with linear backoff.
    max_retries: int = 3
    retry_backoff_seconds: float = 2.0


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DATABASE_URL: str
    # Optional — LM Studio ignores it; set for hosted OpenAI-compatible APIs.
    EMBEDDING_API_KEY: str | None = None
    # Vercel AI Gateway key — used by the Jev decision engine.
    AI_GATEWAY_API_KEY: str | None = None
    # OpenCode Zen key — alternative route to decision models.
    OPENCODE_API_KEY: str | None = None

    logging: LogConfig = Field(default_factory=LogConfig)
    cors: CorsConfig = Field(default_factory=CorsConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    terminology: TerminologyConfig = Field(default_factory=TerminologyConfig)
    coding: CodingConfig = Field(default_factory=CodingConfig)
    jev: JevConfig = Field(default_factory=JevConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        # .env holds secrets — never echo a value back in a validation error.
        hide_input_in_errors=True,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Precedence, highest first: real env var > `.env` >
        `configs/config.yaml` > field defaults. `.env` stays reserved for
        per-environment secrets (DB URL); checked-in application behavior
        lives in `configs/config.yaml`."""
        # Explicit encoding — the platform default on Windows is cp1252.
        yaml_settings = YamlConfigSettingsSource(
            settings_cls,
            yaml_file="configs/config.yaml",
            yaml_file_encoding="utf-8",
        )
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            yaml_settings,
            file_secret_settings,
        )


settings = Settings()

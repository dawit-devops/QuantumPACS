from pydantic import BaseModel, Field


class FileUpdateRequest(BaseModel):
    tag: dict | None = Field(default=None, max_length=100_000, description="Custom metadata tag (JSON dict)")
    tools_state: dict | None = Field(default=None, max_length=100_000, description="Viewer tools state snapshot (JSON dict)")


class ShareRequest(BaseModel):
    # Bounds keep share keys from being minted with nonsensical lifetimes:
    # at least 1 minute, at most 30 days. Values outside the range are
    # rejected with a 422, never silently clamped.
    duration: int = Field(
        ge=60, le=2_592_000,
        description="Share link lifetime in seconds (1 minute – 30 days)",
    )


class SearchRequest(BaseModel):
    """Validated body for POST /files (full-text search).

    `results`/`page` are bounded so one request cannot ask ES for an
    unbounded page; `query` is the free-text search string. Extra keys are
    preserved as passthrough filters for the indexed columns (see
    es.es.search), which is why the schema is not strict.
    """
    query: str | None = Field(default=None, max_length=2000, description="Full-text search query")
    results: int = Field(default=10, ge=1, le=100, description="Page size")
    page: int = Field(default=1, ge=1, le=10_000, description="Page number")

    model_config = {'extra': 'allow'}

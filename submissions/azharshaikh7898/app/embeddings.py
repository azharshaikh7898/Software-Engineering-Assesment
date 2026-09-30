from functools import lru_cache

from .config import settings


@lru_cache(maxsize=1)
def _model():
    from fastembed import TextEmbedding  # imported lazily: heavy, only the worker needs it

    return TextEmbedding(model_name=settings.embedding_model)


def warmup() -> None:
    _model()


def embed_documents(texts: list[str]) -> list[list[float]]:
    return [vec.tolist() for vec in _model().embed(texts, batch_size=32)]


def embed_query(text: str) -> list[float]:
    return next(iter(_model().query_embed(text))).tolist()

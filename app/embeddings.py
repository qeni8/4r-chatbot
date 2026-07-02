from functools import lru_cache

from fastembed import TextEmbedding

from app.config import settings


@lru_cache(maxsize=1)
def _model() -> TextEmbedding:
    return TextEmbedding(settings.embedding_model)


def _is_e5() -> bool:
    return "e5" in settings.embedding_model.lower()


def embed_passages(texts: list[str]) -> list[list[float]]:
    if _is_e5():
        texts = [f"passage: {t}" for t in texts]
    return [v.tolist() for v in _model().embed(texts)]


def embed_query(text: str) -> list[float]:
    if _is_e5():
        text = f"query: {text}"
    return next(iter(_model().embed([text]))).tolist()

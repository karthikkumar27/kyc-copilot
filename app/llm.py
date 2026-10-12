"""Thin client for the LiteLLM gateway. Provider choice, keys, retries across providers and
fallbacks live in the gateway config, not here."""

from functools import lru_cache

from openai import AsyncOpenAI

from app.config import get_settings


@lru_cache
def get_llm_client() -> AsyncOpenAI:
    s = get_settings()
    return AsyncOpenAI(
        base_url=s.llm_base_url, api_key=s.llm_api_key, timeout=s.llm_timeout_s, max_retries=2
    )


async def embed_texts(texts: list[str]) -> list[list[float]]:
    s = get_settings()
    vectors: list[list[float]] = []
    for start in range(0, len(texts), s.embed_batch_size):
        batch = texts[start : start + s.embed_batch_size]
        response = await get_llm_client().embeddings.create(
            model=s.embed_model, input=batch, dimensions=s.embedding_dim
        )
        for item in sorted(response.data, key=lambda d: d.index):
            if len(item.embedding) != s.embedding_dim:
                raise RuntimeError(
                    f"Embedding dimension mismatch: got {len(item.embedding)}, expected "
                    f"{s.embedding_dim}. Check EMBED_MODEL and EMBEDDING_DIM together."
                )
            vectors.append(item.embedding)
    return vectors


def to_pgvector(vector: list[float]) -> str:
    return "[" + ",".join(f"{x:.7f}" for x in vector) + "]"


async def chat_json(messages: list[dict]) -> tuple[str, dict, str]:
    """Returns (content, usage, model actually used)."""
    s = get_settings()
    response = await get_llm_client().chat.completions.create(
        model=s.chat_model,
        messages=messages,
        temperature=0,
        response_format={"type": "json_object"},
    )
    usage = response.usage.model_dump() if response.usage else {}
    return response.choices[0].message.content or "", usage, response.model

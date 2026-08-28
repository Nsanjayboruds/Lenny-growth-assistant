"""
ingestion/embed.py — Generate embeddings using Ollama's nomic-embed-text model.
"""
from __future__ import annotations

import asyncio
import sys
import time
from typing import Optional

import httpx

OLLAMA_BASE_URL = "http://localhost:11434"
EMBEDDING_MODEL = "nomic-embed-text"
_TIMEOUT = 60
_RETRY_ATTEMPTS = 3
_RETRY_DELAY = 2.0


async def embed_text(
    text: str,
    base_url: str = OLLAMA_BASE_URL,
    model: str = EMBEDDING_MODEL,
) -> Optional[list[float]]:
    """
    Generate a vector embedding for a text string using Ollama.

    Returns None on failure after retries.
    """
    for attempt in range(_RETRY_ATTEMPTS):
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(
                    f"{base_url}/api/embed",
                    json={"model": model, "input": text},
                )
                resp.raise_for_status()
                data = resp.json()
                embeddings = data.get("embeddings", [])
                if embeddings:
                    return embeddings[0]
                return None
        except httpx.ConnectError:
            if attempt == 0:
                print(f"[embed] Cannot connect to Ollama at {base_url}. Is it running?", file=sys.stderr)
            return None
        except httpx.TimeoutException:
            if attempt < _RETRY_ATTEMPTS - 1:
                await asyncio.sleep(_RETRY_DELAY)
                continue
            return None
        except Exception as e:
            if attempt < _RETRY_ATTEMPTS - 1:
                await asyncio.sleep(_RETRY_DELAY)
                continue
            print(f"[embed] Error: {e}", file=sys.stderr)
            return None

    return None


async def embed_batch(
    texts: list[str],
    base_url: str = OLLAMA_BASE_URL,
    model: str = EMBEDDING_MODEL,
    batch_size: int = 10,
    show_progress: bool = True,
) -> list[Optional[list[float]]]:
    """
    Generate embeddings for a batch of texts.

    Processes in small batches with a small delay to avoid overwhelming Ollama.
    Returns list of embeddings (None for failed items).
    """
    results: list[Optional[list[float]]] = []
    total = len(texts)
    start = time.perf_counter()

    for i in range(0, total, batch_size):
        batch = texts[i : i + batch_size]
        batch_embeddings = await asyncio.gather(*[
            embed_text(t, base_url=base_url, model=model) for t in batch
        ])
        results.extend(batch_embeddings)

        if show_progress:
            done = min(i + batch_size, total)
            elapsed = time.perf_counter() - start
            rate = done / elapsed if elapsed > 0 else 0
            remaining = (total - done) / rate if rate > 0 else 0
            print(
                f"[embed] {done}/{total} chunks embedded "
                f"({rate:.1f}/s, ~{remaining:.0f}s remaining)",
                end="\r",
            )
        # Small delay to avoid overwhelming Ollama
        await asyncio.sleep(0.05)

    if show_progress:
        print()  # newline after progress

    failed = sum(1 for r in results if r is None)
    if failed > 0:
        print(f"[embed] Warning: {failed}/{total} embeddings failed")

    return results


if __name__ == "__main__":
    async def test():
        vec = await embed_text("What is product-market fit?")
        if vec:
            print(f"Embedding dim: {len(vec)}, first 5 values: {vec[:5]}")
        else:
            print("Embedding failed — check Ollama is running with nomic-embed-text")
    asyncio.run(test())

from __future__ import annotations

from pathlib import Path

from apex.core.logging import get_logger

LOGGER = get_logger(__name__)

class ChromaMarketStore:
    def __init__(self, chromadb_path: Path):
        try:
            import chromadb
            from chromadb.utils import embedding_functions
        except ImportError:
            LOGGER.warning("ChromaDB not installed. Semantic matching will be disabled.")
            self._collection = None
            return

        try:
            self._client = chromadb.PersistentClient(path=str(chromadb_path))
            try:
                self._ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="all-MiniLM-L6-v2"
                )
            except (ValueError, ImportError, OSError) as embed_exc:
                LOGGER.warning(
                    "sentence_transformers unavailable (%s); using DefaultEmbeddingFunction",
                    embed_exc,
                )
                self._ef = embedding_functions.DefaultEmbeddingFunction()
            self._collection = self._client.get_or_create_collection(
                name="market_titles",
                embedding_function=self._ef,
            )
        except chromadb.errors.ChromaError as e:
            LOGGER.warning("Failed to initialize ChromaMarketStore: %s", e)
            self._collection = None
        except (ValueError, OSError) as e:
            LOGGER.warning("Value error initializing ChromaMarketStore: %s", e)
            self._collection = None

    def upsert_market(self, market_id: str, title: str, platform: str) -> None:
        if self._collection is None:
            return
        
        import chromadb.errors
        try:
            self._collection.upsert(
                documents=[title],
                metadatas=[{"platform": platform, "title": title}],
                ids=[f"{platform}_{market_id}"]
            )
        except chromadb.errors.ChromaError as e:
            LOGGER.warning("ChromaDB upsert failed for %s: %s", market_id, e)
        except ValueError as e:
            LOGGER.warning("Value error upserting market %s: %s", market_id, e)

    def find_semantic_match(self, title: str, platform: str, top_k: int = 5) -> list[tuple[str, float]]:
        if self._collection is None:
            return []
        
        import chromadb.errors
        target_platform = "polymarket" if platform.lower() == "kalshi" else "kalshi"
        try:
            results = self._collection.query(
                query_texts=[title],
                n_results=top_k,
                where={"platform": target_platform}
            )
            
            matches = []
            if results and results.get("ids") and results.get("distances"):
                for m_id, dist in zip(results["ids"][0], results["distances"][0]):
                    score = max(0.0, 1.0 - (dist / 2.0))
                    clean_id = m_id.split("_", 1)[1] if "_" in m_id else m_id
                    matches.append((clean_id, score))
            return matches
        except chromadb.errors.ChromaError as e:
            LOGGER.warning("ChromaDB search failed for '%s': %s", title, e)
            return []
        except ValueError as e:
            LOGGER.warning("Value error searching market %s: %s", title, e)
            return []

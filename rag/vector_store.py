"""Vector Store and Local RAG Manager.
Manages ChromaDB persistent vector collection and semantic query with SentenceTransformers.
"""
import os
import glob
import logging
from typing import List, Dict, Any, Optional

try:
    import chromadb
    from chromadb.utils import embedding_functions
except ImportError:
    chromadb = None
    embedding_functions = None

from config.settings import settings

logger = logging.getLogger("rag.vector_store")


class VectorStoreManager:
    """Manages local ChromaDB storage and similarity search for trading rules."""

    def __init__(self, db_path: Optional[str] = None, collection_name: str = "master_knowledge") -> None:
        self.db_path: str = db_path or settings.CHROMA_PATH
        self.collection_name: str = collection_name
        self.client: Optional[Any] = None
        self.collection: Optional[Any] = None
        self.embedding_fn: Optional[Any] = None

    def initialize(self) -> bool:
        """Initialize ChromaDB client and local embedding model."""
        if chromadb is None:
            logger.error("Error in initialize: chromadb is not installed.")
            return False

        try:
            os.makedirs(self.db_path, exist_ok=True)
            self.client = chromadb.PersistentClient(path=self.db_path)

            try:
                # Use local all-MiniLM-L6-v2 model for embedding
                self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="all-MiniLM-L6-v2"
                )
            except Exception as emb_err:
                logger.warning(f"SentenceTransformer not ready yet, using default Chroma embedding: {emb_err}")
                self.embedding_fn = None

            # Get or create collection
            if self.embedding_fn is not None:
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    embedding_function=self.embedding_fn,
                    metadata={"hnsw:space": "cosine"}
                )
            else:
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}
                )

            logger.info(f"Vector Store initialized at '{self.db_path}', collection='{self.collection_name}'")
            return True

        except Exception as e:
            logger.error(f"Error in initialize: {str(e)}")
            return False

    def init_vector_store(self, kb_dir: str = "rag/knowledge_base") -> bool:
        """Read all markdown files in kb_dir, chunk them and persist to ChromaDB."""
        try:
            if self.collection is None and not self.initialize():
                logger.error("Error in init_vector_store: Vector store initialization failed.")
                return False

            if not os.path.exists(kb_dir):
                logger.warning(f"Knowledge base directory '{kb_dir}' does not exist.")
                return False

            md_files = glob.glob(os.path.join(kb_dir, "*.md"))
            if not md_files:
                logger.warning(f"No markdown files found in '{kb_dir}'.")
                return False

            all_docs: List[str] = []
            all_ids: List[str] = []
            all_metadatas: List[Dict[str, Any]] = []

            for file_path in md_files:
                filename = os.path.basename(file_path)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Chunk content by headers or double newlines
                chunks = self._chunk_markdown(content, chunk_size=400)
                for idx, chunk in enumerate(chunks):
                    if not chunk.strip():
                        continue
                    doc_id = f"{filename}_{idx}"
                    all_docs.append(chunk.strip())
                    all_ids.append(doc_id)
                    all_metadatas.append({
                        "source": filename,
                        "chunk_index": idx,
                    })

            if all_docs and self.collection is not None:
                # Upsert into ChromaDB
                self.collection.upsert(
                    ids=all_ids,
                    documents=all_docs,
                    metadatas=all_metadatas,
                )
                logger.info(f"Successfully indexed {len(all_docs)} knowledge chunks into '{self.collection_name}'.")
                return True

            return False

        except Exception as e:
            logger.error(f"Error in init_vector_store: {str(e)}")
            return False

    def query_relevant_rules(self, market_context_text: str, top_k: int = 3) -> List[str]:
        """Retrieve most relevant master rules and case studies based on current market context.
        
        Args:
            market_context_text: Text description of current setup (trends, FVG, RSI, Price).
            top_k: Number of relevant chunks to retrieve.
            
        Returns:
            List of matching rule text chunks.
        """
        try:
            if self.collection is None and not self.initialize():
                logger.warning("Vector store unavailable. Returning default master guidelines.")
                return [
                    "Quy tắc cốt lõi: Không giao dịch ngược xu hướng H4/H1.",
                    "Không vào lệnh khi RR < 1:2.5 hoặc sát giờ tin tức mạnh.",
                    "Luôn đặt SL theo ATR + đáy/đỉnh FVG/OB để tránh liquidity sweep."
                ]

            results = self.collection.query(
                query_texts=[market_context_text],
                n_results=top_k,
            )

            documents = results.get("documents", [[]])
            if documents and len(documents[0]) > 0:
                retrieved_chunks = documents[0]
                logger.info(f"Retrieved {len(retrieved_chunks)} relevant RAG rules for AI Brain.")
                return retrieved_chunks

            return []

        except Exception as e:
            logger.error(f"Error in query_relevant_rules: {str(e)}")
            return [
                "Cấm giao dịch ngược trend H4.",
                "R:R tối thiểu 1:2.5.",
                "Tránh phiên Á và tin tức đỏ."
            ]

    @staticmethod
    def _chunk_markdown(text: str, chunk_size: int = 400) -> List[str]:
        """Split markdown by sections or paragraph blocks."""
        sections = text.split("\n## ")
        chunks = []
        for i, sec in enumerate(sections):
            prefix = "## " if i > 0 else ""
            full_sec = prefix + sec
            if len(full_sec) <= chunk_size * 2:
                chunks.append(full_sec)
            else:
                paragraphs = full_sec.split("\n\n")
                current_chunk = ""
                for p in paragraphs:
                    if len(current_chunk) + len(p) < chunk_size * 1.5:
                        current_chunk += "\n\n" + p
                    else:
                        if current_chunk.strip():
                            chunks.append(current_chunk.strip())
                        current_chunk = p
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
        return chunks


vector_store = VectorStoreManager()

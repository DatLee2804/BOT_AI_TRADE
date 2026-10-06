"""Unit test for RAG Vector Store and Knowledge Chunking."""
import os
import shutil
import unittest
from rag.vector_store import VectorStoreManager


class TestRAGVectorStore(unittest.TestCase):
    """Test ChromaDB indexing and querying of trading rules."""

    def setUp(self) -> None:
        self.test_chroma_path = "./test_chroma_db"
        if os.path.exists(self.test_chroma_path):
            shutil.rmtree(self.test_chroma_path, ignore_errors=True)

        self.vs = VectorStoreManager(db_path=self.test_chroma_path, collection_name="test_rules")

    def tearDown(self) -> None:
        if os.path.exists(self.test_chroma_path):
            shutil.rmtree(self.test_chroma_path, ignore_errors=True)

    def test_chunking_and_indexing(self) -> None:
        """Verify markdown chunking and indexing from knowledge base."""
        # Index knowledge base
        indexed = self.vs.init_vector_store(kb_dir="rag/knowledge_base")
        self.assertTrue(indexed)

        # Query relevant rule
        query = "Khung H4 tăng mạnh, M15 có Bullish FVG test lại Demand"
        results = self.vs.query_relevant_rules(query, top_k=2)
        self.assertGreater(len(results), 0)
        # Check that retrieved content contains relevant rule or setup text
        combined = " ".join(results)
        self.assertTrue("FVG" in combined or "A+" in combined or "Quy tắc" in combined)


if __name__ == "__main__":
    unittest.main()

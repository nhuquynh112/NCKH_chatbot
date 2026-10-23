"""Catalog migration and provenance; no model calls or answer-quality scores."""
import json
from pathlib import Path
import tempfile
import unittest

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.catalog_data import read_catalog, synchronize_catalog
from app.config import BACKEND_ROOT, Settings
from app.database import Base
from app.models import Product
from app.schemas.product import ProductResponse


class CatalogUpdateTests(unittest.TestCase):
    def setUp(self):
        self.rows = read_catalog(BACKEND_ROOT / "rag_data_150/techcare_products.json")
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_new_defaults_keep_old_model_and_use_separate_corpus(self):
        config = Settings(_env_file=None)
        self.assertEqual(config.products_path.parent.name, "rag_data_150")
        self.assertEqual(config.legacy_vector_index_path.parent.name, "rag_data_150")
        self.assertEqual(config.chat_model, "qwen2.5:7b-instruct-fp16")
        self.assertEqual(config.embedding_model, "nomic-embed-text")
        self.assertEqual(len(self.rows), 150)
        self.assertTrue((BACKEND_ROOT / "rag_data/techcare_products.json").exists())

    def test_replace_hides_older_rows_and_preserves_unrelated_data(self):
        older = Product(id=900, slug="older-user-product", name="Older product", category="Laptop",
                        description="Keep this row", price=1, specifications={}, is_active=True)
        self.db.add(older)
        self.db.execute(text("CREATE TABLE retained_probe (content TEXT)"))
        self.db.execute(text("INSERT INTO retained_probe VALUES ('history remains')"))
        self.db.commit()
        result = synchronize_catalog(self.db, self.rows, replace_active=True)
        self.db.commit()
        self.assertEqual(result["active"], 150)
        self.assertEqual(result["retired"], 1)
        self.assertEqual(self.db.get(Product, 900).description, "Keep this row")
        self.assertFalse(self.db.get(Product, 900).is_active)
        self.assertEqual(self.db.execute(text("SELECT content FROM retained_probe")).scalar(), "history remains")
        again = synchronize_catalog(self.db, self.rows, replace_active=True)
        self.assertEqual((again["added"], again["updated"], again["retired"]), (0, 0, 0))

    def test_fresh_clone_preserves_exported_ids_and_source_policies(self):
        synchronize_catalog(self.db, self.rows)
        self.db.commit()
        for row in self.rows:
            product = self.db.get(Product, row["id"])
            self.assertEqual(product.slug, row["slug"])
            payload = ProductResponse.model_validate(product)
            self.assertEqual(payload.verification_status, "retailer_reported")
            self.assertTrue(payload.source_urls[0]["url"].startswith("https://cellphones.com.vn/"))
            self.assertTrue(payload.warranty_source_text)
            if row["warranty_months"] is None:
                self.assertIsNone(payload.warranty_months)

    def test_invalid_catalog_rejected_before_any_database_write(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "catalog.json"
            for rows in ([], [self.rows[0], self.rows[0]], [{**self.rows[0], "price": 0}]):
                path.write_text(json.dumps(rows), encoding="utf-8")
                with self.assertRaises(ValueError):
                    read_catalog(path)
        self.assertEqual(self.db.query(Product).count(), 0)

    def test_excluded_tablet_is_absent_from_every_active_rag_source(self):
        corpus = BACKEND_ROOT / "rag_data_150"
        slug = "may-tinh-bang-alldocube-iplay-80-mini-turbo"
        for name in ("techcare_products.json", "product_verified_specs.json", "techcare_rag_documents.json",
                     "product_catalog_extended.md", "vector_index.json"):
            with self.subTest(source=name):
                self.assertNotIn(slug, (corpus / name).read_text(encoding="utf-8"))
        manifest = json.loads((corpus / "catalog_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["product_count"], len(self.rows))
        self.assertEqual(len(manifest["images"]), len(self.rows))
        self.assertIn(slug, [row["slug"] for row in manifest["excluded_products"]])
        from app.rag.vector_store import load_markdown_documents
        from app.rag.embedding import OllamaClient
        from app.rag.json_store import JsonVectorStore
        paths = [corpus / "knowledge_base.md", corpus / "product_catalog_extended.md", corpus / "faq_curated.json"]
        documents = load_markdown_documents(paths)
        store = JsonVectorStore(corpus / "vector_index.json", OllamaClient("http://127.0.0.1:11434", "unused", "nomic-embed-text"))
        self.assertEqual(store.count(), manifest["document_count"])
        self.assertTrue(store.is_current(documents))


if __name__ == "__main__":
    unittest.main()

import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from dotenv import load_dotenv # <-- Pastikan dotenv diimpor
import logging

logger = logging.getLogger(__name__)

# Import-import Haystack 2.x yang benar
from haystack import Pipeline
from haystack.utils import Secret
from haystack.components.converters import PyPDFToDocument
from haystack.components.preprocessors import DocumentSplitter
from haystack.components.writers import DocumentWriter
from haystack.components.embedders import SentenceTransformersDocumentEmbedder
from haystack_integrations.document_stores.pgvector import PgvectorDocumentStore

# Ukuran batch untuk diproses agar tidak memakan banyak memori
BATCH_SIZE = 16

class Command(BaseCommand):
    help = 'Mengambil data dari PDF, mengubahnya menjadi vektor, dan menyimpannya ke PostgreSQL.'

    def handle(self, *args, **kwargs):
        # Memuat variabel dari file .env
        load_dotenv() 
        self.stdout.write(self.style.SUCCESS("Memulai proses ingesti dokumen PDF..."))

        # 1. Inisialisasi DocumentStore dengan Secret
        try:
            # Bungkus connection string dengan Secret dari environment variable
            document_store = PgvectorDocumentStore(
                connection_string=Secret.from_env_var("PG_CONN_STR"), # <--- PERUBAHAN UTAMA DI SINI
                embedding_dimension=384
            )
            initial_doc_count = document_store.count_documents()
            self.stdout.write(f"Berhasil terhubung ke database. Jumlah dokumen saat ini: {initial_doc_count}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Gagal menginisialisasi DocumentStore: {e}"))
            # Jika error karena PG_CONN_STR tidak ditemukan, beri pesan yang lebih jelas
            if "PG_CONN_STR" in str(e):
                 self.stdout.write(self.style.WARNING("Pastikan Anda sudah membuat file .env dan mengisi variabel PG_CONN_STR di dalamnya."))
            return
        
        # ... sisa kode Anda tetap sama persis ...
        # (Definisi Pipeline, koneksi, dan loop batch)

        # 2. Definisikan Komponen-komponen Pipeline
        pdf_converter = PyPDFToDocument()
        splitter = DocumentSplitter(split_by="sentence", split_length=10, split_overlap=2)
        embedder = SentenceTransformersDocumentEmbedder(model="sentence-transformers/all-MiniLM-L6-v2", progress_bar=True)
        writer = DocumentWriter(document_store=document_store)

        # 3. Bangun Pipeline Ingesti
        indexing_pipeline = Pipeline()
        indexing_pipeline.add_component("converter", pdf_converter)
        indexing_pipeline.add_component("splitter", splitter)
        indexing_pipeline.add_component("embedder", embedder)
        indexing_pipeline.add_component("writer", writer)
        indexing_pipeline.connect("converter.documents", "splitter.documents")
        indexing_pipeline.connect("splitter.documents", "embedder.documents")
        indexing_pipeline.connect("embedder.documents", "writer.documents")
        self.stdout.write("Pipeline ingesti berhasil dibangun.")

        # 4. Temukan file PDF dan proses secara batch
        data_dir = Path(settings.BASE_DIR) / 'data'
        pdf_paths = [str(p) for p in data_dir.glob("*.pdf")]

        if not pdf_paths:
            self.stdout.write(self.style.WARNING('Tidak ada file PDF yang ditemukan di folder data.'))
            return

        self.stdout.write(f"Menemukan {len(pdf_paths)} file PDF untuk diproses dalam batch...")

        for i in range(0, len(pdf_paths), BATCH_SIZE):
            batch_paths = pdf_paths[i:i + BATCH_SIZE]
            self.stdout.write(f"--- Memproses batch {i//BATCH_SIZE + 1}/{len(pdf_paths)//BATCH_SIZE + 1} ({len(batch_paths)} file) ---")
            
            try:
                indexing_pipeline.run({"converter": {"sources": batch_paths}})
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Terjadi kesalahan saat memproses batch: {e}"))
                logger.error(f"Failed to process batch {batch_paths}: {e}", exc_info=True)
                continue

        final_doc_count = document_store.count_documents()
        self.stdout.write(self.style.SUCCESS(f"Proses ingesti selesai!"))
        self.stdout.write(f"Total dokumen di database sekarang: {final_doc_count} (bertambah {final_doc_count - initial_doc_count} dokumen).")

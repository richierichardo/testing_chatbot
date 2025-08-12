# Lokasi: core/management/commands/start_crawl.py

import asyncio
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings

# Import-import yang benar untuk Crawl4AI versi modern
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig  # PERHATIKAN INI

class Command(BaseCommand):
    help = "Memulai proses crawling dari website untuk mengunduh file PDF peraturan."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Memulai Crawling !"))
        try:
            asyncio.run(self.run_crawler())
            self.stdout.write(self.style.SUCCESS('Proses crawling selesai dengan sukses.'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Proses Gagal karena :{e}'))

    async def run_crawler(self):
        # 1. Tentukan folder output
        output_dir = Path(settings.BASE_DIR) / 'data'
        output_dir.mkdir(parents=True, exist_ok=True)
        self.stdout.write(f"File akan disimpan di: {output_dir}")

        # 2. Konfigurasi yang Benar
        # Konfigurasi browser (bisa dibiarkan kosong untuk default)
        browser_config = BrowserConfig(headless=True)

        # Konfigurasi untuk TUGAS CRAWLING SPESIFIK
        run_config = CrawlerRunConfig(
            # Semua konfigurasi output dan unduhan diletakkan di sini
            output_folder=str(output_dir),
            download_media=True,
            media_extensions=[".pdf"],
            # Kita tidak butuh konten Markdown, jadi biarkan False
            extract_content=False
        )

        # 3. Inisialisasi dan jalankan crawler
        target_urls = [
            "https://peraturan.bpk.go.id/",
            "https://jdih.kemenkeu.go.id/in/page/peraturan"
        ]
        
        # Gunakan 'async with' untuk memastikan browser ditutup dengan benar
        async with AsyncWebCrawler(config=browser_config) as crawler:
            # Jalankan crawler untuk setiap URL
            for url in target_urls:
                self.stdout.write(f"--> Mencari file di: {url}")
                await crawler.arun(
                    url=url,
                    config=run_config  # Konfigurasi spesifik tugas dilewatkan di sini
                )
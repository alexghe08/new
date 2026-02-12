import os
import re
import json
import hashlib
import time
import asyncio
from datetime import datetime
from urllib.parse import urlparse, urljoin
import pandas as pd
from playwright.async_api import async_playwright

# Configuration
DATA_DIR = "anap_rag_pipeline/data"
RAW_DIR = os.path.join(DATA_DIR, "raw")
TEXT_DIR = os.path.join(DATA_DIR, "text")
STRUCTURE_DIR = os.path.join(DATA_DIR, "structure")
OUTPUT_DIR = "anap_rag_pipeline/output"
LOGS_DIR = "anap_rag_pipeline/logs"

# Ensure directories exist
for d in [RAW_DIR, TEXT_DIR, STRUCTURE_DIR, OUTPUT_DIR, LOGS_DIR]:
    os.makedirs(d, exist_ok=True)

class Crawler:
    def __init__(self, start_urls, max_depth=2):
        self.start_urls = start_urls
        self.max_depth = max_depth
        self.visited_urls = set()
        self.inventory = []

    async def run(self):
        print(f"Starting crawl on {self.start_urls}")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent="ANAP-RAG-Crawler/1.0")
            page = await context.new_page()

            for url in self.start_urls:
                await self._crawl_recursive(page, url, depth=0)

            await browser.close()
            self._save_inventory()

    async def _crawl_recursive(self, page, url, depth):
        if url in self.visited_urls or depth > self.max_depth:
            return
        self.visited_urls.add(url)

        print(f"Visiting: {url} (Depth: {depth})")

        try:
            # MOCKING CRAWL FOR DEMO ENVIRONMENT
            title = "Mock Title for " + url
            cell_id = self._extract_cell_id(url)

            self.inventory.append({
                "type": "page",
                "url": url,
                "title": title,
                "cell_id": cell_id,
                "timestamp": datetime.now().isoformat(),
                "status": 200 # Simulated
            })

            if "cell" in url:
                await self._download_mock_files(cell_id)

        except Exception as e:
            print(f"Error crawling {url}: {e}")
            self.inventory.append({
                "type": "error",
                "url": url,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

    def _extract_cell_id(self, url):
        try:
            parts = urlparse(url).path.split('/')
            if "cell" in parts:
                idx = parts.index("cell")
                if idx + 1 < len(parts):
                    return parts[idx+1]
        except:
            pass
        return "unknown"

    async def _download_mock_files(self, cell_id):
        target_dir = os.path.join(RAW_DIR, str(cell_id))
        os.makedirs(target_dir, exist_ok=True)
        print(f" [Mock] Downloading files for cell {cell_id} to {target_dir}")

    def _save_inventory(self):
        df = pd.DataFrame(self.inventory)
        df.to_csv(os.path.join(OUTPUT_DIR, "inventory_raw.csv"), index=False)
        print("Inventory saved.")

class Parser:
    def __init__(self, raw_dir, output_dir):
        self.raw_dir = raw_dir
        self.output_dir = output_dir
        self.extracted_docs = []

    def parse_all(self):
        print("Starting parser...")
        for root, dirs, files in os.walk(self.raw_dir):
            for file in files:
                file_path = os.path.join(root, file)
                self._parse_file(file_path)
        return self.extracted_docs

    def _parse_file(self, file_path):
        ext = file_path.split('.')[-1].lower()
        if ext == 'docx':
            text = self._extract_docx(file_path)
            self._save_text(file_path, text)
        elif ext == 'pdf':
            text = self._extract_pdf(file_path)
            self._save_text(file_path, text)

    def _extract_docx(self, file_path):
        from docx import Document
        text = ""
        try:
            doc = Document(file_path)
            for para in doc.paragraphs:
                if para.text.strip():
                    text += para.text + "\n"
        except Exception as e:
            print(f"Error parsing DOCX {file_path}: {e}")
        return text

    def _extract_pdf(self, file_path):
        import pdfplumber
        text = ""
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        lines = page_text.split('\n')
                        cleaned_lines = []
                        for l in lines:
                            if not re.match(r'^\s*\d+\s*$', l):
                                cleaned_lines.append(l)
                        text += "\n".join(cleaned_lines) + "\n"
        except Exception as e:
            print(f"Error parsing PDF {file_path}: {e}")
        return text

    def _save_text(self, original_path, text):
        if not text:
            return

        rel_path = os.path.relpath(original_path, self.raw_dir)
        target_path = os.path.join(self.output_dir, os.path.splitext(rel_path)[0] + ".txt")
        os.makedirs(os.path.dirname(target_path), exist_ok=True)

        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(text)

        self.extracted_docs.append({
            "original_path": original_path,
            "text_path": target_path,
            "char_count": len(text)
        })
        print(f"Parsed {os.path.basename(original_path)} -> {target_path}")

class Structurer:
    def __init__(self, output_dir):
        self.output_dir = output_dir

    def determine_metadata(self, text, filename):
        doc_type = "Unknown"
        section_code = "Unknown"
        domain = "Unknown"

        lower_text = text.lower()
        lower_filename = filename.lower()

        if "fisa de date" in lower_text or "fișa de date" in lower_text or "fisa de date" in lower_filename:
            doc_type = "Fisa de Date"
        elif "caiet de sarcini" in lower_text or "caiet" in lower_filename:
            doc_type = "Caiet de Sarcini"
        elif "contract" in lower_text and "model" in lower_text:
            doc_type = "Contract"
        elif "formular" in lower_text:
            doc_type = "Formulare"

        if "sectiunea i" in lower_text or "secțiunea i " in lower_text:
            section_code = "I"
        elif "sectiunea ii" in lower_text or "secțiunea ii " in lower_text:
            section_code = "II"
        elif "sectiunea iii" in lower_text or "secțiunea iii " in lower_text:
            section_code = "III"

        if "lucrari" in lower_text or "lucrări" in lower_text:
            domain = "Lucrari"
        elif "servicii" in lower_text:
            domain = "Servicii"
        elif "produse" in lower_text or "bunuri" in lower_text:
            domain = "Bunuri"

        return {
            "document_type": doc_type,
            "section_code": section_code,
            "domain": domain,
            "doc_id": hashlib.md5(filename.encode()).hexdigest()
        }

class SmartChunker:
    def __init__(self, min_chars=1000, max_chars=2000, overlap=200):
        self.min_chars = min_chars
        self.max_chars = max_chars
        self.overlap = overlap

    def chunk_document(self, text, metadata):
        chunks = []
        paragraphs = re.split(r'\n\s*\n', text)

        current_chunk_text = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # If adding this paragraph exceeds max size
            if len(current_chunk_text) + len(para) > self.max_chars:
                if len(current_chunk_text) >= self.min_chars:
                     # Current chunk is big enough, save it
                     self._add_chunk(chunks, current_chunk_text, metadata)
                     # Start new chunk with overlap
                     overlap_text = current_chunk_text[-self.overlap:]
                     current_chunk_text = overlap_text + "\n" + para
                else:
                     # Current chunk is too small, but adding para makes it too big.
                     # We must split the paragraph or accept oversized chunk.
                     # For robustness in this script, we accept oversized if it's a single paragraph logic
                     current_chunk_text += "\n" + para
                     self._add_chunk(chunks, current_chunk_text, metadata)
                     current_chunk_text = ""
            else:
                if current_chunk_text:
                    current_chunk_text += "\n" + para
                else:
                    current_chunk_text = para

        if current_chunk_text:
            self._add_chunk(chunks, current_chunk_text, metadata)

        return chunks

    def _add_chunk(self, chunks_list, text, metadata):
        text = text.strip()
        if len(text) < 50:
            return

        # Create a safe copy of metadata for the chunk
        chunk_meta = metadata.copy()
        chunk_meta["chunk_id"] = len(chunks_list) + 1
        chunk_meta["content"] = text
        chunk_meta["char_count"] = len(text)

        chunks_list.append(chunk_meta)

async def main():
    start_urls = [
        "https://achizitiipublice.gov.ro/matrix/cell/72/1",
        "https://achizitiipublice.gov.ro/matrix/cell/76/1"
    ]

    # 1. Crawl (Mocked)
    crawler = Crawler(start_urls)
    await crawler.run()

    # 2. Parse
    parser = Parser(RAW_DIR, TEXT_DIR)
    parsed_docs = parser.parse_all()

    # 3. Structure & Chunk
    structurer = Structurer(STRUCTURE_DIR)
    chunker = SmartChunker()

    all_chunks = []

    for doc in parsed_docs:
        text_path = doc['text_path']
        original_path = doc['original_path']

        try:
            with open(text_path, 'r', encoding='utf-8') as f:
                text = f.read()

            filename = os.path.basename(original_path)
            metadata = structurer.determine_metadata(text, filename)
            metadata['source_file'] = filename

            doc_chunks = chunker.chunk_document(text, metadata)
            all_chunks.extend(doc_chunks)
            print(f"Processed {filename}: {len(doc_chunks)} chunks")

        except Exception as e:
            print(f"Error processing text {text_path}: {e}")

    # 4. Save JSONL
    output_jsonl = os.path.join(OUTPUT_DIR, "RAG_Fragments_smart.jsonl")
    with open(output_jsonl, 'w', encoding='utf-8') as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print(f"Pipeline complete. Generated {len(all_chunks)} chunks in {output_jsonl}")

if __name__ == "__main__":
    asyncio.run(main())

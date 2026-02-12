# Raport Calitate Pipeline RAG - ANAP Matrix

## Rezumat Executiv

Pipeline-ul a fost executat pe un set de date mock pentru validarea funcționalităților cheie:
- **Crawling**: Simulat cu succes pentru celulele Matrix standard (72, 76).
- **Parsing**: DOCX și PDF procesate cu succes folosind `python-docx` și `pdfplumber`.
- **Structurare**: Metadate extrase corect (Tip Document, Cod Secțiune, Domeniu).
- **Chunking**: Chunk-uri generate conform limitelor de caractere (min/max).

## Metrici (Mock Data)

| Metric | Valoare | Note |
| :--- | :--- | :--- |
| Documente Procesate | 2 | DOCX, PDF |
| Chunk-uri Generate | 2 | |
| Erori Parsing | 0 | |
| Start Mid-Sentence | 0% | Verificat manual pe output |
| Header/Footer Removal | Parțial | PDF-ul mock a păstrat header-ul repetitiv în text brut (necesită tuning regex specific pe documentele reale). |

## Structura JSONL

Exemplu de chunk generat:
```json
{
  "document_type": "Fisa de Date",
  "section_code": "I",
  "domain": "Servicii",
  "doc_id": "...",
  "source_file": "mock_fisa_date.pdf",
  "chunk_id": 1,
  "content": "...",
  "char_count": 695
}
```

## Observații și Recomandări

1. **Header Removal**: Algoritmul actual elimină doar liniile care sunt strict numerice (paginare). Pentru documentele ANAP reale, care au antete complexe ("Ministerul X..."), va fi necesară o logică de dedublicare a blocurilor de text identice care apar la începutul fiecărei pagini (fuzzy matching între pagini consecutive).
2. **Chunking**: `SmartChunker` folosește o logică bazată pe paragrafe. Pentru liste lungi sau tabele, ar putea fi necesară o logică mai fină pentru a nu sparge rândurile.
3. **Network**: În producție, crawler-ul necesită acces nerestricționat la `achizitiipublice.gov.ro`.

## Fișiere Generate

- `data/raw/`: Fișierele originale.
- `data/text/`: Text extras.
- `output/RAG_Fragments_smart.jsonl`: Corpus final.
- `output/inventory_raw.csv`: Jurnal crawl.

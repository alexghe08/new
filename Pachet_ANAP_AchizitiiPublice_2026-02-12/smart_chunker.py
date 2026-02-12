import re
import argparse
import sys

def identify_structure_indices(text):
    """
    Identifies document structure (headers, chapters, sections) using regex.
    Returns a sorted list of start indices.
    """
    indices = {0, len(text)}

    # Combined regex pattern for structure:
    # 1. Markdown Headers (#, ##, ###) at start of line
    # 2. Numbered Headers (1. Title, 1.1. Title) at start of line
    # 3. Specific Keywords (CAPITOLUL I, SECTIUNEA A) at start of line
    pattern = re.compile(r'^(#+\s+.*)|(^(\d+(\.\d+)*\.?)\s+[A-Z].*)|(^(CAPITOLUL|SECTIUNEA)\s+[IVX0-9]+.*)', re.MULTILINE)

    for match in pattern.finditer(text):
        indices.add(match.start())

    return sorted(list(indices))

def chunk_text_content(text, max_chunk_size=1000):
    """
    Chunks text respecting structure and sentence boundaries.
    """
    structure_indices = identify_structure_indices(text)
    final_chunks = []

    for i in range(len(structure_indices) - 1):
        start = structure_indices[i]
        end = structure_indices[i+1]
        section_content = text[start:end].strip()

        if not section_content:
            continue

        # If section fits in max_chunk_size, add it
        if len(section_content) <= max_chunk_size:
            final_chunks.append(section_content)
        else:
            # Section is too large, split by sentences.
            parts = re.split(r'([.?!]\s+)', section_content)

            sentences = []
            current_sent_build = ""

            for part in parts:
                current_sent_build += part

                # Check if this part IS a delimiter (matches .?! followed by space)
                if re.fullmatch(r'[.?!]\s+', part):
                    # We have a complete sentence (text + delimiter)
                    if current_sent_build.strip():
                        sentences.append(current_sent_build)
                    current_sent_build = ""

            # Add any remaining text
            if current_sent_build.strip():
                sentences.append(current_sent_build)

            current_chunk = ""
            for sentence in sentences:
                if len(current_chunk) + len(sentence) > max_chunk_size:
                    if current_chunk:
                        final_chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    current_chunk += sentence

            if current_chunk:
                final_chunks.append(current_chunk.strip())

    return final_chunks

def main():
    parser = argparse.ArgumentParser(description="Intelligent Text Chunker for Documents")
    parser.add_argument('input_file', help="Path to input text/markdown file")
    parser.add_argument('--max-size', type=int, default=1000, help="Maximum chunk size in characters")

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

    try:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            content = f.read()

        chunks = chunk_text_content(content, max_chunk_size=args.max_size)

        print(f"--- Processing: {args.input_file} ---")
        print(f"--- Max Chunk Size: {args.max_size} ---")
        print(f"--- Total Chunks: {len(chunks)} ---")
        for i, chunk in enumerate(chunks):
            print(f"\n=== CHUNK {i+1} ({len(chunk)} chars) ===")
            print(chunk)
            print("=" * 30)

    except FileNotFoundError:
        print(f"Error: File '{args.input_file}' not found.")
    except Exception as e:
        print(f"Error processing file: {e}")

if __name__ == "__main__":
    main()

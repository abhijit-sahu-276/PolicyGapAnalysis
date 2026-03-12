def chunk_text(text, max_words=500):
    words = text.split()
    if not words:
        return []
    chunks = []
    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i : i + max_words])
        chunks.append(chunk)
    return chunks

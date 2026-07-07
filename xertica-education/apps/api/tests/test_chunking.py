"""RED-first spec del chunker estructural (ADR-0006 §2)."""
from services.kb.chunking import chunk_markdown, estimate_tokens


def test_empty_returns_no_chunks():
    assert chunk_markdown("") == []
    assert chunk_markdown("   \n\n ") == []


def test_short_text_is_a_single_chunk():
    text = "# Título\n\nUn párrafo corto sobre IA generativa."
    chunks = chunk_markdown(text)
    assert len(chunks) == 1
    assert "IA generativa" in chunks[0]


def test_long_text_splits_into_multiple_chunks_under_budget():
    # ~40 párrafos → excede holgadamente 500 tokens
    body = "\n\n".join(f"Párrafo {i}: " + ("palabra " * 40) for i in range(40))
    text = f"# Sección\n\n{body}"
    chunks = chunk_markdown(text, target_tokens=500, overlap_tokens=64)
    assert len(chunks) > 1
    # cada chunk respeta un tope suave (target + solape)
    for c in chunks:
        assert estimate_tokens(c) <= 500 + 128


def test_overlap_carries_context_between_chunks():
    body = "\n\n".join(f"Concepto {i} " + ("dato " * 30) for i in range(30))
    chunks = chunk_markdown(body, target_tokens=300, overlap_tokens=64)
    assert len(chunks) > 1
    # la cola del chunk previo reaparece al inicio del siguiente
    tail_words = set(chunks[0].split()[-10:])
    assert tail_words & set(chunks[1].split())


def test_structural_split_prefers_heading_boundaries():
    text = "# Uno\n\n" + ("a " * 300) + "\n\n# Dos\n\n" + ("b " * 300)
    chunks = chunk_markdown(text, target_tokens=200, overlap_tokens=0)
    # no debe mezclar el cuerpo de 'Uno' con el heading 'Dos' en un mismo trozo grande
    assert any("Uno" in c for c in chunks)
    assert any("Dos" in c for c in chunks)

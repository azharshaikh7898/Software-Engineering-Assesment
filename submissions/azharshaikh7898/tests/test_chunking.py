from app.chunking import chunk_pages

SIZE, OVERLAP = 800, 120


def test_short_text_is_one_chunk():
    chunks = chunk_pages([(None, "Hello world.\n\nSecond paragraph.")])
    assert len(chunks) == 1 and "Second paragraph." in chunks[0].text


def test_empty_text_gives_no_chunks():
    assert chunk_pages([(None, "  \n\n  ")]) == []


def test_chunks_are_bounded_and_overlap():
    text = "\n\n".join(f"Paragraph {i}. " + "lorem ipsum " * 20 + f"END{i}" for i in range(40))
    chunks = chunk_pages([(None, text)], SIZE, OVERLAP)
    assert len(chunks) > 3
    assert all(len(c.text) <= SIZE + OVERLAP + 2 for c in chunks)
    last_token = chunks[0].text.split()[-1]
    assert last_token in chunks[1].text  # overlap carried into the next chunk


def test_no_text_is_lost():
    text = "\n\n".join(f"unique{i} " + "word " * 60 for i in range(30))
    joined = " ".join(c.text for c in chunk_pages([(None, text)], SIZE, OVERLAP))
    assert all(f"unique{i}" in joined for i in range(30))


def test_page_numbers_are_kept():
    chunks = chunk_pages([(1, "Page one text."), (2, "Page two text.")])
    assert [c.page for c in chunks] == [1, 2]


def test_long_paragraph_and_unbroken_string_are_split():
    sentences = " ".join(f"This is sentence number {i}." for i in range(200))
    for text in (sentences, "x" * 3000):
        chunks = chunk_pages([(None, text)], SIZE, OVERLAP)
        assert len(chunks) > 1
        assert all(len(c.text) <= SIZE + OVERLAP + 2 for c in chunks)

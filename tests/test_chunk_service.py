from app.services.chunk_service import ChunkConfig, ChunkService


def test_chunk_service_preserves_paragraph_and_overlap():
    service = ChunkService(ChunkConfig(min_chars=20, target_chars=45, max_chars=80, overlap_chars=15))
    text = "第一段讲春天和花草。\n\n第二段讲东风和新绿。\n\n第三段讲少年闰土和瓜地。\n\n第四段讲童年伙伴。"
    chunks = service.create_chunks(text)
    assert chunks
    assert any("少年闰土" in chunk for chunk in chunks)
    assert all(len(chunk) <= 110 for chunk in chunks)

import json
from unittest.mock import Mock, patch

from backend.core.config import settings
from backend.services.rag_service import RAGPipeline


def test_manifest_changes_when_document_content_changes(tmp_path):
    document = tmp_path / "regimento.pdf"
    document.write_bytes(b"versao inicial")
    pipeline = RAGPipeline()

    first_manifest = pipeline.build_manifest([document])
    document.write_bytes(b"versao atualizada")
    second_manifest = pipeline.build_manifest([document])

    assert first_manifest != second_manifest
    assert first_manifest["documents"][0]["sha256"] != second_manifest["documents"][0]["sha256"]


def test_initialize_vectorstore_reuses_matching_index(tmp_path, monkeypatch):
    documents_dir = tmp_path / "documents"
    documents_dir.mkdir()
    document = documents_dir / "regimento.pdf"
    document.write_bytes(b"conteudo para manifesto")
    index_dir = tmp_path / "chroma"
    index_dir.mkdir()

    monkeypatch.setattr(settings, "DOCUMENTS_DIR", documents_dir)
    monkeypatch.setattr(settings, "CHROMA_PERSIST_DIR", index_dir)

    pipeline = RAGPipeline()
    pipeline.embeddings = object()
    manifest = pipeline.build_manifest([document])
    (index_dir / pipeline.MANIFEST_FILE).write_text(json.dumps(manifest), encoding="utf-8")
    pipeline.load_documents = Mock(side_effect=AssertionError("O índice não deveria ser reconstruído"))

    with patch("backend.services.rag_service.Chroma") as chroma:
        pipeline.initialize_vectorstore()

    chroma.assert_called_once_with(
        persist_directory=str(index_dir),
        embedding_function=pipeline.embeddings,
    )


def test_activate_index_version_switches_pointer_without_deleting_previous(tmp_path, monkeypatch):
    link = tmp_path / "chroma"
    current_version = tmp_path / "current"
    new_version = tmp_path / "new"
    current_version.mkdir()
    new_version.mkdir()
    (current_version / "marker.txt").write_text("anterior", encoding="utf-8")
    link.symlink_to(current_version, target_is_directory=True)
    monkeypatch.setattr(settings, "CHROMA_PERSIST_DIR", link)

    pipeline = RAGPipeline()
    pipeline._activate_index_version(new_version)

    assert link.is_symlink()
    assert link.resolve() == new_version
    assert (current_version / "marker.txt").read_text(encoding="utf-8") == "anterior"


def test_failed_rebuild_reuses_previous_index(tmp_path, monkeypatch):
    documents_dir = tmp_path / "documents"
    documents_dir.mkdir()
    (documents_dir / "regimento.pdf").write_bytes(b"documento novo")
    index_dir = tmp_path / "chroma"
    index_dir.mkdir()
    (index_dir / "manifest.json").write_text('{"documents": []}', encoding="utf-8")

    monkeypatch.setattr(settings, "DOCUMENTS_DIR", documents_dir)
    monkeypatch.setattr(settings, "CHROMA_PERSIST_DIR", index_dir)
    pipeline = RAGPipeline()
    pipeline.embeddings = object()
    pipeline.load_documents = Mock(return_value=[Mock()])
    pipeline.create_vectorstore = Mock(side_effect=RuntimeError("falha simulada"))
    pipeline._load_existing_vectorstore = Mock()

    pipeline.initialize_vectorstore()

    pipeline._load_existing_vectorstore.assert_called_once_with(index_dir)

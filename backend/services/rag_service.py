import fcntl
import glob
import hashlib
import json
import logging
import os
import shutil
import tempfile
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, List, Tuple

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate

from backend.core.config import settings

logger = logging.getLogger("backend.rag_service")


class RAGPipeline:
    """Pipeline RAG com índice versionado, reutilizável e protegido por lock."""

    CHUNK_SIZE = 800
    CHUNK_OVERLAP = 150
    MANIFEST_FILE = "manifest.json"

    def __init__(self):
        self.vectorstore = None
        self.llm = None
        self.embeddings = None
        os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY

    def initialize_models(self) -> None:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY não encontrada no ambiente.")

        logger.info(f"🔗 [EMBEDDINGS] Inicializando: {settings.EMBEDDING_MODEL}")
        self.embeddings = OpenAIEmbeddings(model=settings.EMBEDDING_MODEL)
        logger.info(f"🤖 [LLM] Inicializando: {settings.LLM_MODEL_RAG}")
        self.llm = ChatOpenAI(model=settings.LLM_MODEL_RAG, temperature=0)
        logger.info("✅ [IA] Modelos carregados com sucesso.")

    def find_document_paths(self) -> List[Path]:
        docs_dir = settings.DOCUMENTS_DIR
        if not docs_dir.exists():
            logger.warning(f"📁 [DOCS] Pasta '{docs_dir}' não encontrada. Criando...")
            docs_dir.mkdir(parents=True, exist_ok=True)

        paths = sorted(Path(path) for path in glob.glob(str(docs_dir / "*.pdf")))
        if not paths:
            logger.warning(f"⚠️ [DOCS] Nenhum PDF em '{docs_dir}'. O sistema funcionará sem base de conhecimento.")
        return paths

    def load_documents(self, caminhos: List[Path] | None = None) -> List[Document]:
        caminhos = caminhos if caminhos is not None else self.find_document_paths()
        if not caminhos:
            return []

        logger.info(f"📄 [DOCS] Encontrados {len(caminhos)} PDF(s) para ingestão.")
        documentos = []
        for caminho in caminhos:
            start = time.time()
            try:
                docs = PyPDFLoader(str(caminho)).load()
                for doc in docs:
                    doc.metadata["documento"] = caminho.name
                documentos.extend(docs)
                logger.info(f"  ↳ '{caminho.name}' carregado ({len(docs)} pág) em {time.time()-start:.2f}s")
            except Exception as e:
                logger.error(f"  ❌ [DOCS] Falha ao carregar '{caminho.name}': {e}")

        logger.info(f"✅ [DOCS] Total: {len(documentos)} páginas carregadas.")
        return documentos

    @staticmethod
    def _hash_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file:
            while block := file.read(1024 * 1024):
                digest.update(block)
        return digest.hexdigest()

    def build_manifest(self, paths: List[Path]) -> dict:
        """Descreve os insumos que tornam um índice reutilizável."""
        return {
            "schema_version": 1,
            "embedding_model": settings.EMBEDDING_MODEL,
            "chunk_size": self.CHUNK_SIZE,
            "chunk_overlap": self.CHUNK_OVERLAP,
            "documents": [
                {
                    "name": path.name,
                    "size": path.stat().st_size,
                    "mtime_ns": path.stat().st_mtime_ns,
                    "sha256": self._hash_file(path),
                }
                for path in paths
            ],
        }

    @property
    def _persist_link(self) -> Path:
        return Path(settings.CHROMA_PERSIST_DIR)

    @property
    def _versions_dir(self) -> Path:
        return self._persist_link.parent / f"{self._persist_link.name}_versions"

    @property
    def _lock_path(self) -> Path:
        return self._persist_link.parent / f".{self._persist_link.name}.lock"

    @contextmanager
    def _reindex_lock(self) -> Iterator[None]:
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock_path.open("a+") as lock_file:
            logger.info("🔒 [CHROMA] Aguardando lock de índice...")
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _active_index_directory(self) -> Path | None:
        link = self._persist_link
        if not link.exists() and not link.is_symlink():
            return None
        resolved = link.resolve()
        return resolved if resolved.exists() else None

    def _read_manifest(self, index_dir: Path | None) -> dict | None:
        if index_dir is None:
            return None
        try:
            with (index_dir / self.MANIFEST_FILE).open(encoding="utf-8") as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return None

    def _load_existing_vectorstore(self, index_dir: Path) -> None:
        self.vectorstore = Chroma(
            persist_directory=str(index_dir),
            embedding_function=self.embeddings,
        )

    def initialize_vectorstore(self) -> None:
        """Reutiliza o índice atual ou cria uma nova versão quando os PDFs mudam."""
        if self.embeddings is None:
            raise RuntimeError("Modelo de embeddings não inicializado.")

        paths = self.find_document_paths()
        if not paths:
            self.vectorstore = None
            return

        manifest = self.build_manifest(paths)
        with self._reindex_lock():
            active_dir = self._active_index_directory()
            if active_dir and self._read_manifest(active_dir) == manifest:
                self._load_existing_vectorstore(active_dir)
                logger.info(f"♻️ [CHROMA] Índice existente reutilizado: {active_dir}")
                return

            logger.info("🔄 [CHROMA] Documentos ou configuração alterados; criando nova versão do índice.")
            documents = self.load_documents(paths)
            if not documents:
                if active_dir:
                    self._load_existing_vectorstore(active_dir)
                    logger.warning("⚠️ [CHROMA] Falha ao carregar PDFs; índice anterior mantido em uso.")
                    return
                self.vectorstore = None
                return

            try:
                self.create_vectorstore(documents, manifest)
            except Exception:
                if active_dir:
                    self._load_existing_vectorstore(active_dir)
                    logger.exception("⚠️ [CHROMA] Reindexação falhou; índice anterior mantido em uso.")
                    return
                raise

    def _classify_chunks(self, chunks: List[Document]) -> None:
        for chunk in chunks:
            texto = chunk.page_content.lower()
            if any(k in texto for k in ["regimento", "norma"]):
                chunk.metadata["categoria"] = "regimento"
            elif any(k in texto for k in ["diretriz", "resolução"]):
                chunk.metadata["categoria"] = "diretriz"
            elif "estatuto" in texto:
                chunk.metadata["categoria"] = "estatuto"
            else:
                chunk.metadata["categoria"] = "geral"

    def _write_manifest(self, index_dir: Path, manifest: dict) -> None:
        with (index_dir / self.MANIFEST_FILE).open("w", encoding="utf-8") as file:
            json.dump(manifest, file, ensure_ascii=False, indent=2, sort_keys=True)

    def _validate_index(self, index_dir: Path, expected_count: int) -> None:
        validation_store = Chroma(
            persist_directory=str(index_dir),
            embedding_function=self.embeddings,
        )
        if validation_store._collection.count() != expected_count:
            raise RuntimeError("Índice Chroma gerado com quantidade inesperada de fragmentos.")

    def _activate_index_version(self, version_dir: Path) -> None:
        """Troca o apontador do índice por symlink sem apagar a versão anterior."""
        link = self._persist_link
        link.parent.mkdir(parents=True, exist_ok=True)
        temporary_link = link.parent / f".{link.name}.next-{uuid.uuid4().hex}"
        legacy_backup = None

        try:
            if (link.exists() or link.is_symlink()) and not link.is_symlink():
                self._versions_dir.mkdir(parents=True, exist_ok=True)
                legacy_backup = self._versions_dir / f"legacy-{int(time.time())}-{uuid.uuid4().hex[:8]}"
                os.replace(link, legacy_backup)
                logger.info(f"📦 [CHROMA] Índice anterior preservado em: {legacy_backup}")

            os.symlink(version_dir, temporary_link, target_is_directory=True)
            os.replace(temporary_link, link)
            logger.info(f"✅ [CHROMA] Nova versão ativada: {version_dir}")
        except Exception:
            if temporary_link.exists() or temporary_link.is_symlink():
                temporary_link.unlink()
            if legacy_backup and legacy_backup.exists() and not link.exists():
                os.replace(legacy_backup, link)
            raise

    def create_vectorstore(self, documentos: List[Document], manifest: dict) -> None:
        if not documentos:
            self.vectorstore = None
            return

        logger.info("✂️ [CHUNKING] Iniciando fragmentação dos documentos...")
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.CHUNK_SIZE,
            chunk_overlap=self.CHUNK_OVERLAP,
        )
        chunks = splitter.split_documents(documentos)
        logger.info(f"✅ [CHUNKING] {len(chunks)} fragmentos gerados.")
        self._classify_chunks(chunks)

        self._versions_dir.mkdir(parents=True, exist_ok=True)
        version_dir = Path(tempfile.mkdtemp(prefix="build-", dir=self._versions_dir))
        logger.info(f"🚀 [CHROMA] Construindo nova versão em: {version_dir}")

        try:
            candidate_store = Chroma.from_documents(
                documents=chunks,
                embedding=self.embeddings,
                persist_directory=str(version_dir),
            )
            self._write_manifest(version_dir, manifest)
            self._validate_index(version_dir, len(chunks))
            self._activate_index_version(version_dir)
            self.vectorstore = candidate_store
        except Exception:
            shutil.rmtree(version_dir, ignore_errors=True)
            raise

    def rerank_documentos(self, pergunta: str, documentos: List[Document]) -> List[Document]:
        if not documentos or not self.llm:
            return documentos

        logger.info(f"🔄 [RERANK] Reclassificando {len(documentos)} trechos via LLM...")
        prompt_rerank = PromptTemplate(
            input_variables=["pergunta", "texto"],
            template="Pergunta: {pergunta}\nTrecho: {texto}\nAvalie a relevância (0 a 10). Responda apenas o número.",
        )
        docs_com_score = []
        for doc in documentos:
            try:
                response = self.llm.invoke(prompt_rerank.format(pergunta=pergunta, texto=doc.page_content))
                score = float(response.content.strip())
            except Exception:
                score = 0.0
            docs_com_score.append((score, doc))

        docs_com_score.sort(key=lambda item: item[0], reverse=True)
        logger.info(f"✅ [RERANK] Finalizado. Top Score: {docs_com_score[0][0] if docs_com_score else 0}")
        return [doc for _, doc in docs_com_score]

    def query(self, pergunta: str) -> Tuple[str, List[Document]]:
        if self.vectorstore is None:
            raise RuntimeError("Banco vetorial não inicializado.")

        logger.info(f"🔍 [RAG] Iniciando busca para: '{pergunta[:60]}...'")
        start_total = time.time()
        docs_recuperados = self.vectorstore.similarity_search(pergunta, k=8)
        docs_rerankeados = self.rerank_documentos(pergunta, docs_recuperados)
        contexto_final = docs_rerankeados[:4]
        contexto_texto = "\n\n".join(doc.page_content for doc in contexto_final)
        prompt_final = f"""Você é um assistente especializado em regimentos.
Responda APENAS com base no contexto fornecido abaixo.

Contexto:
{contexto_texto}

Pergunta:
{pergunta}"""

        logger.info("🧠 [LLM] Gerando resposta final...")
        resposta = self.llm.invoke(prompt_final)
        logger.info(f"✅ [RAG] Concluído em {time.time()-start_total:.2f}s.")
        return resposta.content, contexto_final


rag_pipeline = RAGPipeline()

import os
import glob
import shutil
import time
import logging
from pathlib import Path
from typing import List, Tuple

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document

from backend.core.config import settings

logger = logging.getLogger("backend.rag_service")

class RAGPipeline:
    def __init__(self):
        self.vectorstore = None
        self.llm = None
        self.embeddings = None
        os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY

    def initialize_models(self):
        if not settings.OPENAI_API_KEY:
            logger.error("❌ [LLM] OPENAI_API_KEY não encontrada no ambiente!")
            return

        logger.info(f"🔗 [EMBEDDINGS] Inicializando: {settings.EMBEDDING_MODEL}")
        self.embeddings = OpenAIEmbeddings(model=settings.EMBEDDING_MODEL)
        
        logger.info(f"🤖 [LLM] Inicializando: {settings.LLM_MODEL_RAG}")
        self.llm = ChatOpenAI(model=settings.LLM_MODEL_RAG, temperature=0)
        logger.info("✅ [IA] Modelos carregados com sucesso.")

    def load_documents(self) -> List[Document]:
        docs_dir = settings.DOCUMENTS_DIR
        if not docs_dir.exists():
            logger.warning(f"📁 [DOCS] Pasta '{docs_dir}' não encontrada. Criando...")
            docs_dir.mkdir(parents=True, exist_ok=True)

        caminhos = glob.glob(str(docs_dir / "*.pdf"))
        if not caminhos:
            logger.warning(f"⚠️ [DOCS] Nenhum PDF em '{docs_dir}'. O sistema funcionará sem base de conhecimento.")
            return []

        logger.info(f"📄 [DOCS] Encontrados {len(caminhos)} PDF(s) para ingestão.")
        documentos = []
        for caminho in caminhos:
            start = time.time()
            try:
                loader = PyPDFLoader(caminho)
                docs = loader.load()
                for doc in docs:
                    doc.metadata["documento"] = Path(caminho).name
                documentos.extend(docs)
                logger.info(f"  ↳ '{Path(caminho).name}' carregado ({len(docs)} pág) em {time.time()-start:.2f}s")
            except Exception as e:
                logger.error(f"  ❌ [DOCS] Falha ao carregar '{Path(caminho).name}': {e}")

        logger.info(f"✅ [DOCS] Total: {len(documentos)} páginas carregadas.")
        return documentos

    def create_vectorstore(self, documentos: List[Document]):
        if not documentos:
            self.vectorstore = None
            return

        logger.info("✂️ [CHUNKING] Iniciando fragmentação dos documentos...")
        splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
        chunks = splitter.split_documents(documentos)
        logger.info(f"✅ [CHUNKING] {len(chunks)} fragmentos gerados.")

        # Classificação básica
        for chunk in chunks:
            texto = chunk.page_content.lower()
            if any(k in texto for k in ["regimento", "norma"]): chunk.metadata["categoria"] = "regimento"
            elif any(k in texto for k in ["diretriz", "resolução"]): chunk.metadata["categoria"] = "diretriz"
            elif "estatuto" in texto: chunk.metadata["categoria"] = "estatuto"
            else: chunk.metadata["categoria"] = "geral"

        persist_dir = str(settings.CHROMA_PERSIST_DIR)
        logger.info(f"🗄️ [CHROMA] Limpando cache anterior em: {persist_dir}")
        if os.path.exists(persist_dir):
            shutil.rmtree(persist_dir)

        logger.info("🚀 [CHROMA] Construindo novo banco vetorial...")
        start = time.time()
        self.vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=persist_dir
        )
        logger.info(f"✅ [CHROMA] Banco vetorial persistido em {time.time()-start:.2f}s.")

    def rerank_documentos(self, pergunta: str, documentos: List[Document]) -> List[Document]:
        if not documentos or not self.llm: return documentos
        
        logger.info(f"🔄 [RERANK] Reclassificando {len(documentos)} trechos via LLM...")
        prompt_rerank = PromptTemplate(
            input_variables=["pergunta", "texto"],
            template="Pergunta: {pergunta}\nTrecho: {texto}\nAvalie a relevância (0 a 10). Responda apenas o número."
        )
        
        docs_com_score = []
        for doc in documentos:
            try:
                response = self.llm.invoke(prompt_rerank.format(pergunta=pergunta, texto=doc.page_content))
                score = float(response.content.strip())
            except Exception:
                score = 0.0
            docs_com_score.append((score, doc))
            
        docs_com_score.sort(key=lambda x: x[0], reverse=True)
        logger.info(f"✅ [RERANK] Finalizado. Top Score: {docs_com_score[0][0] if docs_com_score else 0}")
        return [doc for _, doc in docs_com_score]

    def query(self, pergunta: str) -> Tuple[str, List[Document]]:
        if self.vectorstore is None:
            raise RuntimeError("Banco vetorial não inicializado.")

        logger.info(f"🔍 [RAG] Iniciando busca para: '{pergunta[:60]}...'")
        start_total = time.time()

        logger.info("📡 [SEARCH] Busca vetorial (k=8)...")
        docs_recuperados = self.vectorstore.similarity_search(pergunta, k=8)

        docs_rerankeados = self.rerank_documentos(pergunta, docs_recuperados)
        contexto_final = docs_rerankeados[:4]

        contexto_texto = "\n\n".join([doc.page_content for doc in contexto_final])
        prompt_final = f"""Você é um assistente especializado em regimentos.
Responda APENAS com base no contexto fornecido abaixo.

Contexto:
{contexto_texto}

Pergunta:
{pergunta}"""

        logger.info("🧠 [LLM] Gerando resposta final...")
        resposta = self.llm.invoke(prompt_final)
        
        elapsed = time.time() - start_total
        logger.info(f"✅ [RAG] Concluído em {elapsed:.2f}s.")
        
        return resposta.content, contexto_final

rag_pipeline = RAGPipeline()

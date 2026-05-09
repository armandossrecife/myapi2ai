import httpx
import json
import time
import logging
from typing import AsyncIterable
from backend.core.config import settings
from backend.core.exceptions import LLMServiceUnavailable

logger = logging.getLogger(__name__)

async def generate_response(prompt: str, context: str = None, stream: bool = False) -> str | AsyncIterable[str]:
    """
    Interface unificada para gerar resposta do Ollama com logging detalhado.
    """
    if stream:
        return generate_response_stream(prompt, context)
    
    url = f"{settings.OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_predict": settings.OLLAMA_MAX_TOKENS
        }
    }
    
    if context:
        payload["prompt"] = f"Contexto Anterior: {context}\nNova Pergunta: {prompt}"

    start_time = time.time()
    logger.info(f"Enviando requisição (não-stream) para o Ollama. Modelo: {settings.OLLAMA_MODEL}")
    
    try:
        async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            duration = time.time() - start_time
            logger.info(f"Resposta recebida do Ollama com sucesso em {duration:.2f}s.")
            return data.get("response", "")
            
    except httpx.RequestError as e:
        logger.error(f"Falha de conexão com o Ollama em {settings.OLLAMA_BASE_URL}: {str(e)}")
        raise LLMServiceUnavailable(f"Erro de conexão com o LLM: {str(e)}")
    except httpx.HTTPStatusError as e:
        logger.error(f"O Ollama retornou erro HTTP {e.response.status_code}: {e.response.text}")
        raise LLMServiceUnavailable(f"Erro HTTP do LLM: {str(e)}")

async def generate_response_stream(prompt: str, context: str = None) -> AsyncIterable[str]:
    """
    Gerador assíncrono para streaming do Ollama com logging de início e fim.
    """
    url = f"{settings.OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": settings.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": 0.7,
            "num_predict": settings.OLLAMA_MAX_TOKENS
        }
    }
    
    if context:
        payload["prompt"] = f"Contexto Anterior: {context}\nNova Pergunta: {prompt}"

    start_time = time.time()
    logger.info(f"Iniciando streaming do Ollama. Modelo: {settings.OLLAMA_MODEL}")

    try:
        async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT_SECONDS) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                chunk_count = 0
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        if "response" in chunk:
                            chunk_count += 1
                            yield chunk["response"]
                        if chunk.get("done"):
                            duration = time.time() - start_time
                            logger.info(f"Streaming finalizado com sucesso. Chunks: {chunk_count}, Duração: {duration:.2f}s.")
                            break
                    except json.JSONDecodeError:
                        continue
    except httpx.RequestError as e:
        logger.error(f"Falha de conexão (stream) com o Ollama: {str(e)}")
        raise LLMServiceUnavailable(f"Erro de conexão com o LLM: {str(e)}")
    except httpx.HTTPStatusError as e:
        logger.error(f"Erro HTTP (stream) do Ollama: {str(e)}")
        raise LLMServiceUnavailable(f"Erro HTTP do LLM: {str(e)}")

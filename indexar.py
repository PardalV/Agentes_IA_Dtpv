"""Gera os embeddings dos trechos e guarda no banco vetorial (Chroma).

Uso:  python indexar.py
Pode ser interrompido e rodado de novo: só indexa o que ainda não está no banco.
"""
import json
import time
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()  # lê GOOGLE_API_KEY do .env

CHUNKS = Path("data/chunks.json")
PASTA_BANCO = "data/chroma"
COLECAO = "bestiario"
LOTE = 10        # trechos por requisição
PAUSA = 20       # segundos entre lotes (respeita o limite de tokens por minuto)
TENTATIVAS = 3


def montar_documento(c):
    # O Chroma não aceita valores None nos metadados, então só incluímos o que existe.
    metadados = {"tipo": c["tipo"], "pagina": c["pagina"]}
    if c.get("nome"):
        metadados["nome"] = c["nome"]
    if c.get("nd") is not None:
        metadados["nd"] = float(c["nd"])
    if c.get("nd_obs"):
        metadados["nd_obs"] = c["nd_obs"]
    return Document(page_content=c["texto"], metadata=metadados, id=f"trecho-{c['id']}")


def main():
    chunks = json.loads(CHUNKS.read_text(encoding="utf-8"))
    documentos = [montar_documento(c) for c in chunks]

    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    banco = Chroma(collection_name=COLECAO, embedding_function=embeddings,
                   persist_directory=PASTA_BANCO)

    ja_indexados = set(banco.get()["ids"])
    pendentes = [d for d in documentos if d.id not in ja_indexados]
    print(f"{len(documentos)} trechos no total, {len(ja_indexados)} já indexados, "
          f"{len(pendentes)} a indexar.")

    for inicio in range(0, len(pendentes), LOTE):
        lote = pendentes[inicio:inicio + LOTE]
        for tentativa in range(1, TENTATIVAS + 1):
            try:
                banco.add_documents(lote, ids=[d.id for d in lote])
                break
            except Exception as erro:
                print(f"  erro no lote (tentativa {tentativa}/{TENTATIVAS}): {erro}")
                if tentativa == TENTATIVAS:
                    print("Parei. Rode de novo mais tarde: ele continua de onde parou.")
                    return
                time.sleep(60)
        print(f"  indexados {min(inicio + LOTE, len(pendentes))}/{len(pendentes)}")
        time.sleep(PAUSA)

    print("Pronto. Total no banco:", len(banco.get()["ids"]))


if __name__ == "__main__":
    main()
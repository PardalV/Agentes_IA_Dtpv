"""Testa a busca por significado no banco vetorial.

Uso:  python buscar_teste.py
"""
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()

banco = Chroma(
    collection_name="bestiario",
    embedding_function=GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001"),
    persist_directory="data/chroma",
)

PERGUNTAS = [
    "Qual é a defesa e a vida do Balor?",
    "Quais monstros ficam na água ou no pântano?",
    "O que é a Lien Anima?",
    "Um monstro que captura vítimas com teia",
    "Qual é a vida do Beholder?",  # não está no material
]

for pergunta in PERGUNTAS:
    print("\n" + "=" * 70)
    print("PERGUNTA:", pergunta)
    for doc, distancia in banco.similarity_search_with_score(pergunta, k=3):
        m = doc.metadata
        print(f"  dist={distancia:.3f} | {m.get('tipo'):9} | {m.get('nome')} | p.{m.get('pagina')}")
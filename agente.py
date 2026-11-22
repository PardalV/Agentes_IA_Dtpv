"""Agente do bestiário: grafo LangGraph com RAG agêntico e memória (Fase 2)."""
import os
from typing import Annotated, Optional

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.messages import AnyMessage, SystemMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict

load_dotenv()

# ---------------------------------------------------------------- configuração
MODELO = os.getenv("MODELO_LLM", "gemini-3.1-flash-lite")  # troque aqui (ou no .env)
MODELO_EMBEDDINGS = "models/gemini-embedding-001"          # o mesmo usado no indexar.py
PASTA_BANCO = "data/chroma"

PROMPT_SISTEMA = """Você é o assistente do bestiário "O Fantástico Guia Ilustrado de Ameaças", \
um material de fãs de Tormenta20. Você ajuda mestres e jogadores com dúvidas sobre os monstros \
do livro e ajuda mestres a escolher monstros para os encontros.

Os trechos da base são de três tipos: "ficha" (atributos de combate), "descricao" (texto sobre \
o monstro) e "evento" (desafios do livro que não têm ficha).

Regras:
- Para qualquer pergunta sobre monstros, eventos ou regras do livro, use a ferramenta \
buscar_bestiario ANTES de responder. Não responda de memória.
- Se o resultado não responder à pergunta ou não trouxer o monstro pedido, reformule a consulta \
(outras palavras, sinônimos, outro tipo de trecho) e busque de novo. Você pode buscar várias vezes.
- Faça consultas curtas e focadas, com um conceito por busca. Em perguntas de lista \
("quais monstros...", "me sugira monstros..."), faça pelo menos duas ou três buscas com \
termos diferentes antes de responder, e avise que a lista pode não ser completa.
- Ao descrever um monstro, use apenas o que está escrito nos trechos retornados.
- Use somente o que veio nos trechos retornados. Nunca invente atributos, números ou habilidades.
- Se o monstro ou a informação não estiver na base, diga isso claramente. O livro tem só uma \
parte dos monstros de Tormenta20.
- Responda em português do Brasil, de forma objetiva, citando o nome do monstro e a página."""


# ------------------------------------------------------------------ ferramentas
_banco = Chroma(
    collection_name="bestiario",
    embedding_function=GoogleGenerativeAIEmbeddings(model=MODELO_EMBEDDINGS),
    persist_directory=PASTA_BANCO,
)


@tool
def buscar_bestiario(consulta: str, tipo: Optional[str] = None) -> str:
    """Busca trechos no bestiário (fichas de monstros, descrições e eventos) por significado.

    Args:
        consulta: o que procurar, em português (ex.: "Balor defesa e pontos de vida").
        tipo: opcional. "ficha" para atributos de combate, "descricao" para o texto sobre
            o monstro ou "evento" para desafios sem ficha. Sem valor, busca em todos.
    """
    filtro = {"tipo": tipo} if tipo in ("ficha", "descricao", "evento") else None
    resultados = _banco.similarity_search(consulta, k=5, filter=filtro)
    if not resultados:
        return "Nenhum trecho encontrado."
    partes = []
    for doc in resultados:
        m = doc.metadata
        partes.append(f"[{m.get('tipo')} | {m.get('nome')} | p.{m.get('pagina')}]\n{doc.page_content}")
    return "\n\n---\n\n".join(partes)


FERRAMENTAS = [buscar_bestiario]


# ------------------------------------------------------------------------ grafo
class Estado(TypedDict):
    # add_messages: cada nó devolve mensagens novas e elas são ACRESCENTADAS à lista
    messages: Annotated[list[AnyMessage], add_messages]


llm = ChatGoogleGenerativeAI(model=MODELO, max_retries=5)
llm_com_ferramentas = llm.bind_tools(FERRAMENTAS)


def no_agente(estado: Estado):
    """Chama o modelo com o prompt de sistema + a conversa até agora."""
    mensagens = [SystemMessage(content=PROMPT_SISTEMA)] + estado["messages"]
    resposta = llm_com_ferramentas.invoke(mensagens)
    return {"messages": [resposta]}


def construir_grafo(checkpointer=None):
    grafo = StateGraph(Estado)
    grafo.add_node("agente", no_agente)
    grafo.add_node("ferramentas", ToolNode(FERRAMENTAS))

    grafo.add_edge(START, "agente")
    # Se a resposta do modelo pede ferramenta -> "ferramentas"; senão -> fim.
    grafo.add_conditional_edges("agente", tools_condition, {"tools": "ferramentas", END: END})
    grafo.add_edge("ferramentas", "agente")  # depois da ferramenta, o modelo lê o resultado

    return grafo.compile(checkpointer=checkpointer or MemorySaver())


def extrair_texto(mensagem) -> str:
    """O Gemini pode devolver o conteúdo como lista de blocos; junta só os de texto."""
    conteudo = mensagem.content
    if isinstance(conteudo, str):
        return conteudo
    return "".join(b.get("text", "") for b in conteudo if isinstance(b, dict) and b.get("type") == "text")
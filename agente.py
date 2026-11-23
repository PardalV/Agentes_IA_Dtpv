"""Agente do bestiário: grafo LangGraph com RAG agêntico, MCP, memória e guardrails."""
import logging
import os
import shutil
from pathlib import Path
from typing import Annotated, Optional

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict

from guardrails import detectar_injecao, redigir_saida, valores_sem_fundamento
from skills import catalogo_de_skills, ler_skill

load_dotenv()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------- configuração
MODELO = os.getenv("MODELO_LLM", "gemini-3.5-flash-lite")  # troque aqui (ou no .env)
MODELO_EMBEDDINGS = "models/gemini-embedding-001"          # o mesmo usado no indexar.py
PASTA_BANCO = "data/chroma"

# Pasta onde o assistente salva e lê os encontros do mestre (o servidor de arquivos
# só enxerga esta pasta).
PASTA_ENCONTROS = Path(__file__).parent / "encontros"
PASTA_ENCONTROS.mkdir(exist_ok=True)
PASTA_POSIX = PASTA_ENCONTROS.as_posix()  # com "/", para o modelo não errar as barras

PASTAS_LOCAIS_GUARDRAIL = [
    str(PASTA_ENCONTROS),
    PASTA_POSIX,
    str(Path(__file__).parent),
    Path(__file__).parent.as_posix(),
]

# Servidores MCP a que o agente se conecta.
SERVIDORES_MCP = {
    # servidor próprio (precisa estar rodando: python servidor_bestiario.py)
    "bestiario": {
        "transport": "streamable_http",
        "url": os.getenv("URL_MCP_BESTIARIO", "http://127.0.0.1:8000/mcp"),
    },
    # servidor da comunidade (filesystem oficial, em Node), restrito à pasta de encontros
    "arquivos": {
        "transport": "stdio",
        "command": shutil.which("npx") or "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", str(PASTA_ENCONTROS)],
    },
}

# Dentre as ferramentas do servidor de arquivos, só liberamos estas (as demais, como
# mover e editar arquivos, ficam de fora de propósito).
ARQUIVOS_PERMITIDOS = {"write_file", "list_directory", "create_directory"}

NOMES_FERRAMENTAS: list[str] = []  # preenchida em construir_agente (usada na interface)

PROMPT_SISTEMA = f"""Você é o assistente do bestiário "O Fantástico Guia Ilustrado de Ameaças", \
um material de fãs de Tormenta20. Você ajuda mestres e jogadores com dúvidas sobre os monstros \
do livro e ajuda mestres a escolher monstros para os encontros.

Ferramentas:
- buscar_bestiario: busca por significado em trechos do livro (tipos: "ficha", "descricao" e \
"evento"). Serve para descobrir monstros por descrição, tema ou habilidade.
- obter_ficha_monstro: devolve a ficha exata de um monstro pelo nome e confirma se ele existe.
- listar_monstros_por_nd: lista os monstros de uma faixa de nível de desafio (ND).
- planejar_encontro: calcula o ND alvo e a faixa de ND para um encontro (heurística do projeto).
- rolar_dados: rola dados (ex.: "1d20+13", "3d8+13+4d6").
- carregar_skill: carrega as instruções completas de uma skill do catálogo (abaixo).
- write_file, read_text_file, list_directory, create_directory: arquivos do mestre, SOMENTE \
dentro da pasta {PASTA_POSIX}.

Regras:
- Para qualquer pergunta sobre monstros, eventos ou regras do livro, use as ferramentas ANTES de \
responder. Não responda de memória.
- Para números exatos (defesa, vida, ataques, ND), use obter_ficha_monstro depois de identificar \
o monstro. Se você só tem uma descrição, primeiro descubra o nome com buscar_bestiario.
- Antes de dizer que um monstro não existe, confirme com obter_ficha_monstro.
- Para sugerir monstros por nível de desafio, use listar_monstros_por_nd.
- Para rolagens, use rolar_dados, buscando na ficha os bônus e danos corretos. Não invente resultados.
- Em ataques, role o ataque e, se o usuário informar a Defesa do alvo, compare para dizer se acertou. \
Se ele não informou, NÃO diga que o ataque acertou: informe o total rolado e diga que o resultado \
depende da Defesa do alvo. Se pedir o dano "se acertar", role o dano e apresente-o como condicional.
- Se uma ferramenta avisar que o ND da ficha difere do ND da tabela do livro, informe ao usuário.
- Se o resultado não responder à pergunta, reformule a consulta (outras palavras, outro tipo de \
trecho) e busque de novo. Faça consultas curtas, com um conceito por busca. Em perguntas de lista, \
faça mais de uma busca e avise que a lista pode não ser completa.
- Só salve arquivos quando o usuário pedir. Ao salvar, use o caminho completo dentro de \
{PASTA_POSIX}, com nome em minúsculas, sem acentos, extensão .md e conteúdo em Markdown (título, \
ND, e cada monstro com página e atributos principais tirados das fichas). Se uma ferramenta de \
arquivo falhar, conte o erro ao usuário e não diga que salvou.
- Use somente o que veio das ferramentas. Nunca invente atributos, números ou habilidades.
- Responda em português do Brasil, de forma objetiva, citando o nome do monstro e a página."""

PROMPT_SISTEMA += "\n\n" + catalogo_de_skills()


# --------------------------------------------------- ferramenta local (RAG)
_banco = Chroma(
    collection_name="bestiario",
    embedding_function=GoogleGenerativeAIEmbeddings(model=MODELO_EMBEDDINGS),
    persist_directory=PASTA_BANCO,
)


@tool
def buscar_bestiario(consulta: str, tipo: Optional[str] = None) -> str:
    """Busca trechos no bestiário (fichas de monstros, descrições e eventos) por significado.

    Args:
        consulta: o que procurar, em português (ex.: "monstro que captura com teia").
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


@tool
def carregar_skill(nome: str) -> str:
    """Carrega as instruções completas de uma skill (procedimento de várias etapas).

    Chame ANTES de executar uma tarefa que combine com uma skill do catálogo.

    Args:
        nome: nome exato da skill, como aparece no catálogo (ex.: "montar-encontro").
    """
    return ler_skill(nome)


# ------------------------------------------------------------------------ grafo
class Estado(TypedDict):
    # add_messages: cada nó devolve mensagens novas e elas são ACRESCENTADAS à lista
    messages: Annotated[list[AnyMessage], add_messages]


llm = ChatGoogleGenerativeAI(model=MODELO, max_retries=5)


def extrair_texto(mensagem) -> str:
    """O Gemini pode devolver o conteúdo como lista de blocos; junta só os de texto."""
    conteudo = getattr(mensagem, "content", mensagem)
    if isinstance(conteudo, str):
        return conteudo
    if isinstance(conteudo, list):
        return "".join(
            b.get("text", "") for b in conteudo if isinstance(b, dict) and b.get("type") == "text"
        )
    return str(conteudo)


def _montar_corpus_turno(mensagens: list[AnyMessage]) -> str:
    """Coleta mensagens do turno atual (após o último HumanMessage) e resultados de ferramentas."""
    ultimo_human_idx = 0
    for i, msg in enumerate(mensagens):
        if isinstance(msg, HumanMessage):
            ultimo_human_idx = i

    partes: list[str] = []
    for msg in mensagens[ultimo_human_idx:]:
        if isinstance(msg, (HumanMessage, ToolMessage)):
            texto = extrair_texto(msg)
            if texto:
                prefixo = "usuário: " if isinstance(msg, HumanMessage) else ""
                partes.append(f"{prefixo}{texto}")
    return "\n".join(partes)


async def carregar_ferramentas_mcp():
    """Conecta aos servidores MCP e devolve as ferramentas deles como ferramentas LangChain."""
    cliente = MultiServerMCPClient(SERVIDORES_MCP)
    ferramentas = await cliente.get_tools(server_name="bestiario")
    arquivos = await cliente.get_tools(server_name="arquivos")
    leitura = "read_text_file" if any(t.name == "read_text_file" for t in arquivos) else "read_file"
    permitidas = ARQUIVOS_PERMITIDOS | {leitura}
    ferramentas += [t for t in arquivos if t.name in permitidas]
    return ferramentas


async def construir_agente(checkpointer=None):
    ferramentas_mcp = await carregar_ferramentas_mcp()
    ferramentas = [buscar_bestiario, carregar_skill, *ferramentas_mcp]
    # Os servidores MCP mandam "$schema" no esquema das ferramentas e o Gemini não aceita
    # essa chave (gera um aviso a cada chamada). Tiramos antes de entregar ao modelo.
    for ferramenta in ferramentas:
        esquema = getattr(ferramenta, "args_schema", None)
        if isinstance(esquema, dict):
            esquema.pop("$schema", None)
    NOMES_FERRAMENTAS[:] = [t.name for t in ferramentas]
    llm_com_ferramentas = llm.bind_tools(ferramentas)

    async def guardrail_entrada(estado: Estado):
        """Bloqueia tentativas de injeção ou acesso externo antes de rodar o modelo."""
        mensagens = estado["messages"]
        if not mensagens or not isinstance(mensagens[-1], HumanMessage):
            return {"messages": []}

        texto_usuario = extrair_texto(mensagens[-1])
        motivo = detectar_injecao(texto_usuario)
        if motivo:
            logger.warning("Guardrail de entrada acionado (%s): %r", motivo, texto_usuario)
            return {
                "messages": [
                    AIMessage(
                        content=(
                            "Não posso atender a esse pedido por questões de segurança "
                            f"({motivo}). Posso ajudar com monstros do bestiário, encontros e rolagens."
                        )
                    )
                ]
            }
        return {"messages": []}

    def rota_apos_entrada(estado: Estado) -> str:
        mensagens = estado["messages"]
        if len(mensagens) >= 2 and isinstance(mensagens[-2], HumanMessage) and isinstance(mensagens[-1], AIMessage):
            return "fim"
        return "agente"

    async def no_agente(estado: Estado):
        """Chama o modelo com o prompt de sistema + a conversa até agora."""
        mensagens = [SystemMessage(content=PROMPT_SISTEMA)] + estado["messages"]
        resposta = await llm_com_ferramentas.ainvoke(mensagens)
        return {"messages": [resposta]}

    async def guardrail_saida(estado: Estado):
        """Sanitiza vazamentos e sinaliza valores de PV/Defesa sem respaldo nas ferramentas."""
        mensagens = estado["messages"]
        if not mensagens or not isinstance(mensagens[-1], AIMessage):
            return {"messages": []}

        ultima = mensagens[-1]
        texto_original = extrair_texto(ultima)
        if not texto_original:
            return {"messages": []}

        texto_limpo, avisos = redigir_saida(texto_original, PASTAS_LOCAIS_GUARDRAIL)
        for aviso in avisos:
            logger.warning("Guardrail de saída: %s", aviso)

        corpus = _montar_corpus_turno(mensagens)
        suspeitos = valores_sem_fundamento(texto_limpo, corpus)
        if suspeitos:
            logger.warning("Valores de PV/Defesa sem respaldo no corpus: %s", suspeitos)
            aviso_valores = ", ".join(suspeitos)
            texto_limpo = (
                f"{texto_limpo}\n\n"
                f"*(Aviso: os valores de PV/Defesa [{aviso_valores}] não apareceram "
                "diretamente nos resultados das ferramentas deste turno.)*"
            )

        if texto_limpo != texto_original:
            return {"messages": [AIMessage(content=texto_limpo, id=ultima.id)]}
        return {"messages": []}

    def rota_apos_agente(estado: Estado) -> str:
        # Se o modelo chamou ferramentas, vai para o nó "ferramentas"; senão, valida a saída.
        if tools_condition(estado) == "tools":
            return "ferramentas"
        return "guardrail_saida"

    grafo = StateGraph(Estado)
    grafo.add_node("guardrail_entrada", guardrail_entrada)
    grafo.add_node("agente", no_agente)
    grafo.add_node("ferramentas", ToolNode(ferramentas))
    grafo.add_node("guardrail_saida", guardrail_saida)

    grafo.add_edge(START, "guardrail_entrada")
    grafo.add_conditional_edges(
        "guardrail_entrada",
        rota_apos_entrada,
        {"fim": END, "agente": "agente"},
    )
    grafo.add_conditional_edges(
        "agente",
        rota_apos_agente,
        {"ferramentas": "ferramentas", "guardrail_saida": "guardrail_saida"},
    )
    grafo.add_edge("ferramentas", "agente")
    grafo.add_edge("guardrail_saida", END)

    return grafo.compile(checkpointer=checkpointer or MemorySaver())
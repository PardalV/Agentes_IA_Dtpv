# app.py
"""Interface Streamlit para o Assistente do Bestiário (LangGraph + RAG + MCP + Guardrails)."""
import asyncio
from concurrent.futures import Future
from threading import Thread
import uuid

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage

from agente import NOMES_FERRAMENTAS, PASTA_ENCONTROS, construir_agente, extrair_texto


class _RunnerAsync:
    """Mantém um event loop próprio em uma thread em segundo plano."""

    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self._thread = Thread(target=self._iniciar_loop, daemon=True)
        self._thread.start()

    def _iniciar_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def executar(self, coro):
        futuro: Future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return futuro.result()


def _nova_config() -> dict:
    return {"configurable": {"thread_id": str(uuid.uuid4())}}


def _obter_runner() -> _RunnerAsync:
    if "runner_async" not in st.session_state:
        st.session_state.runner_async = _RunnerAsync()
    return st.session_state.runner_async


async def _inicializar_grafo():
    grafo = await construir_agente()
    config = _nova_config()
    return grafo, config


async def _executar_turno(grafo, config: dict, pergunta: str) -> tuple[str, list[str], list[str]]:
    estado_anterior = await grafo.aget_state(config)
    valores_estado = getattr(estado_anterior, "values", {}) or {}
    indice_antes = len(valores_estado.get("messages", []))

    resultado = await grafo.ainvoke(
        {"messages": [HumanMessage(content=pergunta)]},
        config,
    )

    mensagens_resultado = resultado.get("messages", []) if isinstance(resultado, dict) else []
    novas_mensagens = mensagens_resultado[indice_antes:]
    ferramentas_usadas: list[str] = []
    skills_carregadas: list[str] = []

    for msg in novas_mensagens:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for chamada in msg.tool_calls:
                nome_tool = chamada.get("name", "")
                args = chamada.get("args", {}) or {}
                args_str = ", ".join(f"{k}={v!r}" for k, v in args.items())
                ferramentas_usadas.append(f"{nome_tool}({args_str})")

                if nome_tool == "carregar_skill":
                    nome_skill = args.get("nome") or args_str
                    if str(nome_skill) not in skills_carregadas:
                        skills_carregadas.append(str(nome_skill))

    resposta_texto = extrair_texto(mensagens_resultado[-1]) if mensagens_resultado else ""
    return resposta_texto, ferramentas_usadas, skills_carregadas


def _garantir_sessao():
    runner = _obter_runner()
    if "grafo" not in st.session_state or "config" not in st.session_state:
        with st.spinner("Conectando aos servidores MCP e carregando o bestiário..."):
            try:
                grafo, config = runner.executar(_inicializar_grafo())
            except Exception as erro:
                st.error(
                    "Não foi possível inicializar o agente ou conectar aos servidores MCP. "
                    "Verifique se `python servidor_bestiario.py` está rodando e se o Node.js (`npx`) está instalado."
                )
                st.exception(erro)
                st.stop()

        st.session_state.grafo = grafo
        st.session_state.config = config
        st.session_state.mensagens_ui = []


def _listar_encontros_md():
    """Retorna arquivos .md dentro de PASTA_ENCONTROS, do mais recente ao mais antigo."""
    if not PASTA_ENCONTROS.exists():
        return []
    arquivos = [
        arq for arq in PASTA_ENCONTROS.iterdir()
        if arq.is_file() and arq.suffix.lower() == ".md"
    ]
    return sorted(arquivos, key=lambda p: p.stat().st_mtime, reverse=True)


def _renderizar_leitor_encontros():
    """Exibe na barra lateral os encontros salvos em Markdown na pasta encontros."""
    arquivos = _listar_encontros_md()
    with st.expander(f"📄 Encontros salvos ({len(arquivos)})", expanded=False):
        if not arquivos:
            st.caption("Nenhum encontro `.md` salvo ainda na pasta `encontros`.")
            return

        nomes = [arq.name for arq in arquivos]
        selecionado = st.selectbox(
            "Escolha um encontro:",
            options=nomes,
            key="encontro_selecionado",
        )
        caminho_escolhido = (PASTA_ENCONTROS / selecionado).resolve()
        pasta_base = PASTA_ENCONTROS.resolve()

        if pasta_base not in caminho_escolhido.parents or caminho_escolhido.suffix.lower() != ".md":
            st.warning("Arquivo inválido.")
            return

        conteudo_md = caminho_escolhido.read_text(encoding="utf-8")
        st.download_button(
            label="Baixar .md",
            data=conteudo_md,
            file_name=caminho_escolhido.name,
            mime="text/markdown",
            use_container_width=True,
            key=f"download_{caminho_escolhido.name}",
        )
        st.divider()
        st.markdown(conteudo_md)


def _renderizar_metadados_resposta(ferramentas: list[str], skills: list[str]):
    if skills:
        st.caption("Skills carregadas: " + ", ".join(f"`{s}`" for s in skills))

    if ferramentas:
        with st.expander("Ferramentas chamadas nesta resposta", expanded=False):
            for chamada in ferramentas:
                st.code(chamada, language="text")


def main():
    st.set_page_config(
        page_title="Assistente do Bestiário — Tormenta20",
        page_icon="🐉",
        layout="centered",
    )

    st.title("🐉 Assistente do Bestiário")
    st.caption(
        "O Fantástico Guia Ilustrado de Ameaças (Tormenta20) • RAG, MCP e Guardrails"
    )

    _garantir_sessao()

    with st.sidebar:
        st.header("Controle da conversa")
        st.caption(f"Thread: `{st.session_state.config['configurable']['thread_id'][:8]}`")

        if st.button("🔄 Nova conversa", use_container_width=True):
            st.session_state.config = _nova_config()
            st.session_state.mensagens_ui = []
            st.rerun()

        if NOMES_FERRAMENTAS:
            with st.expander("Ferramentas disponíveis", expanded=False):
                for nome in NOMES_FERRAMENTAS:
                    st.markdown(f"- `{nome}`")

        _renderizar_leitor_encontros()

    # Renderiza histórico da interface
    for item in st.session_state.mensagens_ui:
        with st.chat_message(item["role"]):
            st.markdown(item["content"])
            if item["role"] == "assistant":
                _renderizar_metadados_resposta(
                    item.get("ferramentas", []),
                    item.get("skills", []),
                )

    pergunta = st.chat_input("Pergunte sobre monstros, ND, rolagens ou peça um encontro...")
    if not pergunta:
        return

    st.session_state.mensagens_ui.append({"role": "user", "content": pergunta})
    with st.chat_message("user"):
        st.markdown(pergunta)

    with st.chat_message("assistant"):
        with st.spinner("Consultando o bestiário..."):
            try:
                resposta, ferramentas_usadas, skills_carregadas = _obter_runner().executar(
                    _executar_turno(
                        st.session_state.grafo,
                        st.session_state.config,
                        pergunta,
                    )
                )
            except Exception as erro:
                resposta = (
                    "Ocorreu uma falha ao processar sua solicitação "
                    f"(`{type(erro).__name__}: {erro}`). Tente novamente em instantes."
                )
                ferramentas_usadas = []
                skills_carregadas = []

        st.markdown(resposta)
        _renderizar_metadados_resposta(ferramentas_usadas, skills_carregadas)

    st.session_state.mensagens_ui.append(
        {
            "role": "assistant",
            "content": resposta,
            "ferramentas": ferramentas_usadas,
            "skills": skills_carregadas,
        }
    )


if __name__ == "__main__":
    main()
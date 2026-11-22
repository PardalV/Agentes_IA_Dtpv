"""Conversa com o agente pelo terminal (para testar o grafo antes da interface).

Antes: suba o servidor MCP em outro terminal  ->  python servidor_bestiario.py
Uso:   python conversar.py        ('nova' = nova conversa, 'sair' = encerrar)
"""
import asyncio
import uuid

from langchain_core.messages import AIMessage

from agente import NOMES_FERRAMENTAS, construir_agente, extrair_texto


def nova_config():
    return {"configurable": {"thread_id": str(uuid.uuid4())}}


async def main():
    try:
        grafo = await construir_agente()
    except Exception as erro:
        print("Não consegui conectar aos servidores MCP. O servidor do bestiário está rodando em outro terminal?")
        print("(python servidor_bestiario.py) E o Node.js está instalado (npx)?")
        print("Detalhe:", erro)
        return

    config = nova_config()
    print("Ferramentas carregadas:", ", ".join(NOMES_FERRAMENTAS))
    print("Assistente do bestiário. Digite 'nova' para nova conversa ou 'sair' para encerrar.")

    while True:
        pergunta = input("\nVocê: ").strip()
        if not pergunta:
            continue
        if pergunta.lower() == "sair":
            break
        if pergunta.lower() == "nova":
            config = nova_config()
            print("Nova conversa iniciada.")
            continue

        estado = await grafo.aget_state(config)
        antes = len(estado.values.get("messages", []))
        resultado = await grafo.ainvoke({"messages": [("user", pergunta)]}, config)

        for m in resultado["messages"][antes:]:  # só as mensagens desta rodada
            if isinstance(m, AIMessage) and m.tool_calls:
                for chamada in m.tool_calls:
                    print(f"  [ferramenta] {chamada['name']}({chamada['args']})")

        print("\nAssistente:", extrair_texto(resultado["messages"][-1]))


if __name__ == "__main__":
    asyncio.run(main())
"""Conversa com o agente pelo terminal (para testar o grafo antes da interface).

Uso:  python conversar.py        ('nova' = nova conversa, 'sair' = encerrar)
"""
import uuid

from langchain_core.messages import AIMessage

from agente import construir_grafo, extrair_texto

grafo = construir_grafo()


def nova_config():
    return {"configurable": {"thread_id": str(uuid.uuid4())}}


config = nova_config()
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

    antes = len(grafo.get_state(config).values.get("messages", []))
    resultado = grafo.invoke({"messages": [("user", pergunta)]}, config)

    for m in resultado["messages"][antes:]:  # só as mensagens desta rodada
        if isinstance(m, AIMessage) and m.tool_calls:
            for chamada in m.tool_calls:
                print(f"  [ferramenta] {chamada['name']}({chamada['args']})")

    print("\nAssistente:", extrair_texto(resultado["messages"][-1]))
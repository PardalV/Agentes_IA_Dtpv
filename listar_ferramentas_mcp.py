"""Lista as ferramentas de cada servidor MCP (não gasta cota do modelo).

Uso:  python listar_ferramentas_mcp.py    (com o servidor do bestiário rodando)
"""
import asyncio

from langchain_mcp_adapters.client import MultiServerMCPClient

from agente import SERVIDORES_MCP


async def main():
    cliente = MultiServerMCPClient(SERVIDORES_MCP)
    for servidor in SERVIDORES_MCP:
        print(f"\n== {servidor} ==")
        for ferramenta in await cliente.get_tools(server_name=servidor):
            print(" -", ferramenta.name)


asyncio.run(main())
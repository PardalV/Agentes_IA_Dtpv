"""Teste de segurança: o servidor de arquivos deve RECUSAR escrever fora da pasta de encontros.

Não usa o modelo (não gasta cota) e não precisa do servidor do bestiário.
Uso:  python testar_limite_arquivos.py
"""
import asyncio

from langchain_mcp_adapters.client import MultiServerMCPClient

from agente import PASTA_ENCONTROS, SERVIDORES_MCP


async def main():
    cliente = MultiServerMCPClient(SERVIDORES_MCP)
    ferramentas = await cliente.get_tools(server_name="arquivos")
    escrever = next(t for t in ferramentas if t.name == "write_file")

    fora = (PASTA_ENCONTROS.parent / "teste-fora-da-pasta.txt").as_posix()
    print("Tentando escrever fora da pasta permitida:", fora)
    try:
        print("Resultado:", await escrever.ainvoke({"path": fora, "content": "teste"}))
    except Exception as erro:
        print("Recusado pelo servidor:", erro)


asyncio.run(main())
"""Servidor MCP do bestiário (desenvolvido neste trabalho).

Uso:  python servidor_bestiario.py      (fica escutando em http://127.0.0.1:8000/mcp)
"""
from mcp.server.fastmcp import FastMCP

import ferramentas_bestiario as fb

mcp = FastMCP("bestiario", host="127.0.0.1", port=8000)


@mcp.tool()
def obter_ficha_monstro(nome: str, nd: float = 0) -> str:
    """Confere se um monstro existe no bestiário e devolve a ficha completa dele
    (atributos, ataques, habilidades), copiada do livro sem alterações.

    Use sempre que precisar de números exatos (defesa, vida, ataques) ou para confirmar
    se um monstro está na base. Se o nome não existir, informa isso e sugere nomes parecidos.

    Args:
        nome: nome do monstro, como "Balor" ou "Arranha-Rosto" (sem diferenciar acentos).
        nd: opcional. Use 0 (padrão) para qualquer versão; informe o ND só para escolher
            uma versão específica quando o nome tem várias (ex.: Objeto Animado).
    """
    return fb.obter_ficha(nome, nd if nd else None)


@mcp.tool()
def listar_monstros_por_nd(nd_min: float = 0, nd_max: float = 99, incluir_eventos: bool = False) -> str:
    """Lista os monstros do bestiário com nível de desafio (ND) dentro de uma faixa,
    em ordem de ND. Use para sugerir monstros para um encontro.

    Args:
        nd_min: ND mínimo (aceita frações como 0.5).
        nd_max: ND máximo.
        incluir_eventos: se verdadeiro, inclui também os eventos do livro (que não têm ficha).
    """
    return fb.listar_monstros(nd_min, nd_max, incluir_eventos)


@mcp.tool()
def rolar_dados(expressao: str) -> str:
    """Rola dados e soma os resultados. Aceita expressões como "1d20+13", "2d6+3"
    ou "3d8+13+4d6" (várias parcelas). Use para ataques, danos, iniciativa e testes."""
    return fb.rolar_dados(expressao)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
"""Skills do assistente: procedimentos em arquivos SKILL.md, carregados sob demanda.

Cada skill fica em skills/<nome>/SKILL.md, com um cabeçalho (entre ---) contendo `name` e
`description`. O catálogo (nome + descrição) vai no prompt de sistema; o texto completo só é
lido quando o agente chama a ferramenta carregar_skill.
"""
from pathlib import Path

PASTA_SKILLS = Path(__file__).parent / "skills"


def _separar(texto):
    """Devolve (metadados, corpo) de um SKILL.md. Os valores do cabeçalho ficam em uma linha."""
    meta, corpo = {}, texto
    if texto.startswith("---"):
        _, cabecalho, corpo = texto.split("---", 2)
        for linha in cabecalho.strip().splitlines():
            if ":" in linha:
                chave, valor = linha.split(":", 1)
                meta[chave.strip()] = valor.strip()
    return meta, corpo.strip()


def listar_skills():
    skills = {}
    for caminho in sorted(PASTA_SKILLS.glob("*/SKILL.md")):
        meta, _ = _separar(caminho.read_text(encoding="utf-8"))
        nome = meta.get("name") or caminho.parent.name
        skills[nome] = {"descricao": meta.get("description", ""), "caminho": caminho}
    return skills


def catalogo_de_skills():
    """Texto do catálogo para o prompt de sistema."""
    linhas = [
        "Skills disponíveis (procedimentos de várias etapas). Se a tarefa do usuário combinar com "
        "uma skill, chame carregar_skill com o nome dela ANTES de executar a tarefa e siga o "
        "procedimento carregado:"
    ]
    for nome, info in listar_skills().items():
        linhas.append(f"- {nome}: {info['descricao']}")
    return "\n".join(linhas)


def ler_skill(nome):
    skills = listar_skills()
    if nome not in skills:
        return f"Skill '{nome}' não existe. Skills disponíveis: {', '.join(skills)}."
    _, corpo = _separar(skills[nome]["caminho"].read_text(encoding="utf-8"))
    return corpo


if __name__ == "__main__":
    print(catalogo_de_skills())
    print("\n--- skill carregada ---")
    print(ler_skill("montar-encontro")[:300], "...")
    print("\n", ler_skill("inexistente"))
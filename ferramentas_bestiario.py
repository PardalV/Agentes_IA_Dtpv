"""Lógica das ferramentas do servidor MCP do bestiário.

Fica separada do servidor (que só "embrulha" estas funções) para poder ser testada
sem o MCP:   python ferramentas_bestiario.py
"""
import json
import random
import re
import unicodedata
from difflib import get_close_matches
from pathlib import Path

CHUNKS = Path(__file__).parent / "data" / "chunks.json"

# ND de cada criatura segundo a "Tabela 1: Criaturas por ND" (p.7 do livro).
# Em alguns casos ela difere do ND que aparece no título da ficha; as ferramentas avisam.
# (Objeto Animado, com ND 1/2 a 10, e Cyeta, com ND variável, ficam de fora.)
TABELA_ND = {
    "Condor Gigante": 1, "Ofidímio": 1, "Skum": 1, "Troll Pigmeu": 1,
    "Cão Teleportador": 2, "Terror Gélido": 2,
    "Arranha-Rosto": 3, "Cavaleiro Rubro": 3, "Feiticeiro Furioso": 3, "Huay Chivo": 3,
    "Piranhas do Deserto": 3,
    "Assassino em Série": 4, "Cipó Assassino": 4, "Cria de Vampiro": 4,
    "Guerreiro Imortal": 4, "Lyx - Luxúria": 4, "Tigre Dentes-de-Sabre": 4,
    "Árvore-Matilha": 5, "Assassino Mascarado": 5, "Besouro Gigante": 5, "Dandara": 5,
    "Neri": 5, "Elananx": 5, "Leão Grande Dourado": 5, "Ninfa do Pântano": 5,
    "Aucharai": 6, "Elefante": 6, "Embaixador Vampírico": 6, "Zavist - Inveja": 6,
    "Afogado": 7, "Orquídea Carnívora": 7, "Voluptie": 7, "Wendigo": 7,
    "Gorila Escorpião": 8, "Predador de Allihanna": 8, "Urso Marrom Vegetal": 8,
    "Aboleth": 9, "Assassino da Savana": 9, "Jhumariel": 9, "Faulheit - Preguiça": 9,
    "Gyvenima - Gula": 9,
    "Lien Anima": 10, "Kemakan - Avareza": 11, "Besouro do Óleo": 12, "Dusmas - Ira": 12,
    "Grim, o Infindável": 13, "Marilith": 15, "Nogthren": 15,
    "Balor": 18, "Vampiro Ancião": 18, "Kraken": 20,
}


def _normalizar(texto):
    """Minúsculas, sem acento e sem pontuação: 'Arranha-Rosto' -> 'arranha rosto'."""
    sem_acento = "".join(c for c in unicodedata.normalize("NFD", texto or "")
                         if unicodedata.category(c) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", sem_acento.lower()).split())


_TABELA = {_normalizar(k): v for k, v in TABELA_ND.items()}


def _fmt_nd(nd):
    if nd is None:
        return "variável"
    if nd == 0.5:
        return "1/2"
    if nd == 0.25:
        return "1/4"
    return str(int(nd)) if float(nd).is_integer() else str(nd)


def _carregar():
    return json.loads(CHUNKS.read_text(encoding="utf-8"))


def _fichas():
    return [c for c in _carregar() if c["tipo"] == "ficha"]


def _eventos():
    eventos = {}
    for c in _carregar():
        if c["tipo"] == "evento":
            e = eventos.setdefault(c["nome"], {"nome": c["nome"], "nd": c["nd"], "paginas": []})
            e["paginas"].append(c["pagina"])
    return list(eventos.values())


def _nd_tabela(nome):
    return _TABELA.get(_normalizar(nome))


def _aviso_divergencia(ficha):
    tabela = _nd_tabela(ficha["nome"])
    if tabela is not None and ficha["nd"] is not None and float(tabela) != float(ficha["nd"]):
        return (f"ATENÇÃO: o livro é inconsistente. O título da ficha diz ND {_fmt_nd(ficha['nd'])}, "
                f"mas a Tabela 1 (p.7) lista ND {_fmt_nd(tabela)}.")
    return None


def _procurar(nome, itens):
    """Acha itens pelo nome: exato, depois por palavras contidas, depois por semelhança."""
    alvo = _normalizar(nome)
    if not alvo:
        return [], False
    exatos = [i for i in itens if _normalizar(i["nome"]) == alvo]
    if exatos:
        return exatos, False
    palavras = set(alvo.split())
    contidos = [i for i in itens if palavras <= set(_normalizar(i["nome"]).split())]
    if contidos:
        return contidos, False
    nomes = {_normalizar(i["nome"]): i["nome"] for i in itens}
    parecido = get_close_matches(alvo, list(nomes), n=1, cutoff=0.8)
    if parecido:
        return [i for i in itens if _normalizar(i["nome"]) == parecido[0]], True
    return [], False


def obter_ficha(nome, nd=None):
    fichas = _fichas()
    candidatas, aproximado = _procurar(nome, fichas)

    if not candidatas:
        eventos, _ = _procurar(nome, _eventos())
        if eventos:
            e = eventos[0]
            paginas = f"{min(e['paginas'])}-{max(e['paginas'])}" if len(set(e['paginas'])) > 1 else e['paginas'][0]
            return (f"'{e['nome']}' é um evento do livro (ND {_fmt_nd(e['nd'])}, p.{paginas}) e "
                    f"não tem ficha de monstro. Use a busca no bestiário para ler a descrição.")
        nomes = sorted({f["nome"] for f in fichas})
        sugestoes = get_close_matches(_normalizar(nome), [_normalizar(n) for n in nomes], n=3, cutoff=0.6)
        mapa = {_normalizar(n): n for n in nomes}
        dica = f" Nomes parecidos: {', '.join(mapa[s] for s in sugestoes)}." if sugestoes else ""
        return (f"Nenhum monstro chamado '{nome}' foi encontrado no bestiário "
                f"({len(nomes)} nomes de monstros com ficha).{dica}")

    if nd is not None:
        filtradas = [f for f in candidatas if f["nd"] is not None and float(f["nd"]) == float(nd)]
        if not filtradas:
            disponiveis = ", ".join(_fmt_nd(f["nd"]) for f in candidatas)
            return f"'{candidatas[0]['nome']}' existe, mas não com ND {_fmt_nd(nd)}. NDs disponíveis: {disponiveis}."
        candidatas = filtradas

    blocos = []
    for f in candidatas[:8]:
        bloco = f"{f['texto']}\n(página {f['pagina']})"
        aviso = _aviso_divergencia(f)
        if aviso:
            bloco += "\n" + aviso
        blocos.append(bloco)
    prefixo = "(Nome aproximado; confira se é o monstro certo.)\n" if aproximado else ""
    return prefixo + "\n\n---\n\n".join(blocos)


def listar_monstros(nd_min=0, nd_max=99, incluir_eventos=False):
    itens = []
    for f in _fichas():
        tabela = _nd_tabela(f["nome"])
        valores = [float(v) for v in (f["nd"], tabela) if v is not None]
        if valores and not any(nd_min <= v <= nd_max for v in valores):
            continue
        linha = f"- {f['nome']} (ND {_fmt_nd(f['nd'])}"
        if f["nd"] is None and f.get("nd_obs"):
            linha = f"- {f['nome']} (ND {f['nd_obs']}"
        linha += f") — p.{f['pagina']}"
        if tabela is not None and f["nd"] is not None and float(tabela) != float(f["nd"]):
            linha += f" [Tabela p.7: ND {_fmt_nd(tabela)}]"
        itens.append((min(valores) if valores else 99, f["nome"], linha))
    if incluir_eventos:
        for e in _eventos():
            if e["nd"] is not None and nd_min <= float(e["nd"]) <= nd_max:
                itens.append((float(e["nd"]), e["nome"],
                              f"- {e['nome']} (evento, ND {_fmt_nd(e['nd'])}) — p.{min(e['paginas'])}"))
    itens.sort(key=lambda t: (t[0], t[1]))
    cabecalho = f"{len(itens)} resultado(s) com ND entre {_fmt_nd(nd_min)} e {_fmt_nd(nd_max)}:"
    return cabecalho + "\n" + "\n".join(linha for _, _, linha in itens) if itens else \
        f"Nenhum monstro com ND entre {_fmt_nd(nd_min)} e {_fmt_nd(nd_max)}."


# Heurística do projeto para montar encontros (o livro NÃO traz regra de balanceamento).
AJUSTE_DIFICULDADE = {"facil": -2, "padrao": 0, "dificil": 2, "mortal": 4}
SUBTRAIR_POR_QUANTIDADE = {1: 0, 2: 2, 3: 3, 4: 4, 5: 5, 6: 5, 7: 6, 8: 6}


def planejar_encontro(nivel, dificuldade="padrao", quantidade=3):
    chave = _normalizar(dificuldade)
    if chave not in AJUSTE_DIFICULDADE:
        return "Dificuldade inválida. Use: fácil, padrão, difícil ou mortal."
    quantidade = int(quantidade)
    if quantidade not in SUBTRAIR_POR_QUANTIDADE:
        return "A quantidade de monstros deve ser de 1 a 8."

    ajuste = AJUSTE_DIFICULDADE[chave]
    alvo = nivel + ajuste
    menor_nd = min(float(f["nd"]) for f in _fichas() if f["nd"] is not None)
    por_monstro = alvo - SUBTRAIR_POR_QUANTIDADE[quantidade]
    aviso = ""
    if por_monstro < menor_nd:
        por_monstro = menor_nd
        aviso = (f"\nAviso: o ND por monstro ficaria abaixo do menor ND do livro "
                 f"({_fmt_nd(menor_nd)}); foi usado o menor disponível.")
    faixa_min = max(menor_nd, por_monstro - 1)
    faixa_max = por_monstro + 1

    return (
        "HEURÍSTICA DO PROJETO (o livro não traz regra de balanceamento).\n"
        f"- Grupo de nível {nivel}, dificuldade {chave} (ajuste {ajuste:+d}): ND alvo = {_fmt_nd(alvo)}.\n"
        f"- Com {quantidade} monstro(s): ND de cada monstro = {_fmt_nd(por_monstro)}.\n"
        f"- Faixa de busca (ND por monstro, 1 para mais e para menos): {_fmt_nd(faixa_min)} a {_fmt_nd(faixa_max)}."
        f"{aviso}\n\nCandidatos nessa faixa (sem filtro de tema):\n"
        + listar_monstros(faixa_min, faixa_max)
    )


def rolar_dados(expressao):
    texto = expressao.replace(" ", "").lower()
    if not re.fullmatch(r"([+-]?(\d*d\d+|\d+))+", texto):
        return "Expressão inválida. Exemplos: 1d20+13, 2d6+3, 3d8+13+4d6."
    total, partes = 0, []
    for m in re.finditer(r"([+-]?)(?:(\d*)d(\d+)|(\d+))", texto):
        sinal = -1 if m.group(1) == "-" else 1
        marca = "-" if sinal < 0 else "+"
        if m.group(3):
            qtd, lados = int(m.group(2) or 1), int(m.group(3))
            if not (1 <= qtd <= 100 and 2 <= lados <= 1000):
                return "Limites: de 1 a 100 dados, com 2 a 1000 lados."
            rolagens = [random.randint(1, lados) for _ in range(qtd)]
            subtotal = sum(rolagens)
            partes.append(f"{marca}{qtd}d{lados}{rolagens}")
        else:
            subtotal = int(m.group(4))
            partes.append(f"{marca}{subtotal}")
        total += sinal * subtotal
    return f"{expressao}: {' '.join(partes).lstrip('+')} = {total}"


if __name__ == "__main__":
    print("== obter_ficha('Balor') ==")
    print(obter_ficha("Balor"))
    print("\n== obter_ficha('Beholder') ==")
    print(obter_ficha("Beholder"))
    print("\n== obter_ficha('Lien Anima') ==")
    print(obter_ficha("Lien Anima"))
    print("\n== listar_monstros(3, 5) ==")
    print(listar_monstros(3, 5))
    print("\n== rolar_dados ==")
    for expr in ("1d20+13", "3d8+13+4d6", "d20", "2d6-1", "abc"):
        print(rolar_dados(expr))

    print("\n== conferência com a Tabela 1 (p.7) ==")
    nomes = {_normalizar(f["nome"]) for f in _fichas()} | {_normalizar(e["nome"]) for e in _eventos()}
    print("Nomes da tabela sem correspondência nos trechos:",
          [k for k in TABELA_ND if _normalizar(k) not in nomes] or "nenhum")
    print("ND da ficha diferente do ND da tabela:",
          [f"{f['nome']} (ficha {_fmt_nd(f['nd'])}, tabela {_fmt_nd(_nd_tabela(f['nome']))})"
           for f in _fichas() if _aviso_divergencia(f)] or "nenhum")
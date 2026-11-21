import json
import re
from pathlib import Path

ARQUIVO = Path("data/bestiario_extraido.txt")
SAIDA = Path("data/chunks.json")
PAG_INICIO, PAG_FIM = 8, 64  # páginas das criaturas (sumário: 8 a 64)

# "nd 3", "ND 15", "ND 1/2"
PADRAO_ND = re.compile(r"\bnd\s+(\d+(?:/\d+)?)", re.IGNORECASE)
# linha de título: nome + nd no fim da linha
PADRAO_TITULO = re.compile(r"^(.+?)\s+nd\s+(\d+(?:/\d+)?)\s*$", re.IGNORECASE)


def nd_para_numero(texto):
    if "/" in texto:
        a, b = texto.split("/")
        return int(a) / int(b)
    return int(texto)


def formatar_nome(nome):
    return re.sub(r"\s+", " ", nome).strip().lower().title()


def ler_paginas():
    texto = ARQUIVO.read_text(encoding="utf-8")
    partes = re.split(r"===== PÁGINA (\d+) =====", texto)
    return {int(partes[i]): partes[i + 1] for i in range(1, len(partes), 2)}


def limpar_linhas(conteudo, numero, avisos):
    linhas = [l.strip() for l in conteudo.splitlines()]
    linhas = [l for l in linhas if l and not l.isdigit()]  # tira linhas vazias e o nº da página
    for i, l in enumerate(linhas):
        if l.startswith("Audiodescrição"):
            if any(x.startswith("TESOURO") for x in linhas[i:]):
                avisos.append(f"p.{numero}: há TESOURO depois da audiodescrição (não cortei)")
            else:
                linhas = linhas[:i]
            break
    return linhas


def achar_fichas(linhas):
    """Cada ficha termina numa linha TESOURO e começa na linha antes de INICIATIVA."""
    fichas, fim_anterior = [], -1
    for t, l in enumerate(linhas):
        if not l.startswith("TESOURO"):
            continue
        pv = max((i for i in range(fim_anterior + 1, t) if linhas[i].startswith("PONTOS DE VIDA")), default=None)
        inicio = None
        if pv is not None:
            for i in range(pv, max(pv - 6, fim_anterior), -1):
                if linhas[i].startswith("INICIATIVA"):
                    inicio = max(i - 1, fim_anterior + 1)
                    break
        if inicio is None:
            inicio = max(t - 12, fim_anterior + 1)
        fichas.append({"inicio": inicio, "fim": t})
        fim_anterior = t
    return fichas


def achar_titulos(linhas):
    titulos, cabecalhos = [], []
    for i, l in enumerate(linhas):
        achados = PADRAO_ND.findall(l)
        if not achados or len(l) > 80:
            continue
        m = PADRAO_TITULO.match(l)
        if len(achados) == 1 and m:
            titulos.append({"linha": i, "nome": formatar_nome(m.group(1)), "nd": nd_para_numero(m.group(2))})
        else:
            cabecalhos.append({"linha": i, "texto": l})
    return titulos, cabecalhos


def associar(fichas, titulos):
    usados = set()
    # 1) título logo antes da ficha (entre a ficha anterior e esta)
    for k, f in enumerate(fichas):
        limite = fichas[k - 1]["fim"] if k > 0 else -1
        antes = [t for t in titulos if limite < t["linha"] < f["inicio"] and t["linha"] not in usados]
        if antes:
            f["titulo"] = antes[-1]
            usados.add(antes[-1]["linha"])
    # 2) sobras (título no fim da página) vão para as fichas sem título, em ordem
    sobras = [t for t in titulos if t["linha"] not in usados]
    for f in fichas:
        if "titulo" not in f and sobras:
            f["titulo"] = sobras.pop(0)


def processar():
    paginas = ler_paginas()
    chunks, avisos, sem_titulo, sem_nome_desc = [], [], [], []
    for numero in range(PAG_INICIO, PAG_FIM + 1):
        if numero not in paginas:
            continue
        linhas = limpar_linhas(paginas[numero], numero, avisos)
        fichas = achar_fichas(linhas)
        titulos, cabecalhos = achar_titulos(linhas)
        associar(fichas, titulos)

        usadas = set()
        nomes_pagina = []
        for k, f in enumerate(fichas):
            t = f.get("titulo")
            nome, nd = (t["nome"], t["nd"]) if t else (None, None)
            if t is None:
                sem_titulo.append(f"p.{numero} (ficha {k + 1})")
            else:
                nomes_pagina.append(nome)
            usadas.update(range(f["inicio"], f["fim"] + 1))
            if t:
                usadas.add(t["linha"])
            corpo = "\n".join(linhas[f["inicio"]:f["fim"] + 1])
            cab = f"{nome} (ND {nd})" if t else "(nome não identificado)"
            chunks.append({"tipo": "ficha", "nome": nome, "nd": nd, "pagina": numero,
                           "texto": f"{cab}\n{corpo}"})

        # descrição: o que sobrou na página (sem fichas, títulos e cabeçalhos)
        for c in cabecalhos:
            usadas.add(c["linha"])
        nomes_min = {n.lower() for n in nomes_pagina}
        resto = [l for i, l in enumerate(linhas) if i not in usadas and l.lower() not in nomes_min]
        descricao = "\n".join(resto)
        if len(descricao) >= 80:
            if nomes_pagina:
                nome_desc = " / ".join(nomes_pagina)
            elif cabecalhos:
                nome_desc = cabecalhos[0]["texto"]
            else:
                nome_desc = None
                sem_nome_desc.append(f"p.{numero}")
            chunks.append({"tipo": "descricao", "nome": nome_desc, "nd": None, "pagina": numero,
                           "texto": f"{nome_desc or '(nome não identificado)'} (descrição)\n{descricao}"})

    for i, c in enumerate(chunks):
        c["id"] = i
    SAIDA.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")

    fichas = [c for c in chunks if c["tipo"] == "ficha"]
    print("Fichas:", len(fichas))
    print("Trechos de descrição:", len(chunks) - len(fichas))
    print("Fichas sem título:", sem_titulo or "nenhuma")
    print("Descrições sem nome:", sem_nome_desc or "nenhuma")
    print("Avisos:", avisos or "nenhum")


if __name__ == "__main__":
    processar()
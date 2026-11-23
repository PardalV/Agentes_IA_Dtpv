---
name: montar-encontro
description: Monta um encontro de combate para um grupo (nível, dificuldade e tema), escolhendo monstros do bestiário, conferindo as fichas e, se o mestre pedir, salvando o encontro em arquivo. Use quando o mestre pedir para montar, sugerir ou balancear um encontro.
---

# Montar um encontro

IMPORTANTE: o livro NÃO traz regra de balanceamento. Quem calcula a dificuldade é a ferramenta
planejar_encontro, que aplica uma HEURÍSTICA DO PROJETO, e você deve dizer isso ao mestre.
Nunca some os ND dos monstros, nunca refaça a conta à mão e nunca invente orientações sobre
dificuldade.

## Passo 1: levantar os dados
Descubra: o nível do grupo, a dificuldade desejada (fácil, padrão, difícil ou mortal), a
quantidade de monstros e, se houver, o tema ou ambiente. Se faltar o nível, pergunte. Se faltar a
dificuldade, assuma "padrão"; se faltar a quantidade, assuma 3. Avise sobre o que assumiu. A
heurística considera um grupo de 4 jogadores; se o mestre tiver outro número, avise que é preciso
ajustar à mão.

## Passo 2: planejar
Chame planejar_encontro(nivel, dificuldade, quantidade). Ela devolve:
- o ND alvo do encontro (que NÃO é o ND de cada monstro);
- o ND de cada monstro;
- a faixa de ND para buscar candidatos, já com a lista dos monstros nessa faixa.
Anote esses três valores e use-os exatamente como vierem.

## Passo 3: escolher os monstros
1. Parta da lista de candidatos devolvida pelo planejar_encontro.
2. Se houver tema ou ambiente, use buscar_bestiario com consultas curtas (uma ideia por busca) e
   cruze os nomes com a lista de candidatos. Só vale monstro que esteja na lista.
3. NÃO amplie a faixa de ND por conta própria. Se não houver candidato do tema dentro da faixa,
   diga isso ao mestre e ofereça opções: (a) ignorar o tema e escolher dentro da faixa, (b) mudar
   a quantidade de monstros (chame planejar_encontro de novo) ou (c) aceitar de forma explícita
   monstros acima da faixa, dizendo quais são e que a dificuldade passa do planejado. Espere a
   escolha do mestre antes de salvar.
4. Prefira monstros de ND igual ou com diferença de até 1 entre si.
5. Anote qualquer aviso de divergência de ND entre a ficha e a Tabela 1 do livro.
6. Eventos do livro (como Lien Anima) não são monstros com ficha: só os inclua se o mestre pedir.

## Passo 4: conferir as fichas
Para cada monstro escolhido, chame obter_ficha_monstro. Leia Defesa, PV, ataques e habilidades,
incluindo resistências, imunidades e vulnerabilidades. Use SOMENTE dados da ficha. Observe se as
habilidades combinam entre si e se alguma delas atrapalha o grupo de forma incomum.

## Passo 5: verificar antes de apresentar
Compare o ND de cada monstro escolhido com a faixa do passo 2. Se todos estiverem dentro, o
encontro segue a heurística. Se algum estiver fora, declare o desvio e NUNCA diga que o encontro
segue a heurística.

## Passo 6: apresentar o encontro
Mostre: nível, dificuldade, ND alvo e ND por monstro (separados), e a composição. Para cada
monstro: nome, ND, página, Defesa, PV, o ataque principal e as 1 ou 2 habilidades mais
importantes, resumidas sem mudar o sentido. Sugira táticas apenas a partir das habilidades da
ficha. Termine avisando que a dificuldade vem da heurística do projeto, e não de uma regra do livro.

## Passo 7: salvar (somente se o mestre pedir)
Use write_file com o caminho completo dentro da pasta de encontros, nome em minúsculas, sem
acentos e terminado em .md. Modelo do conteúdo:

```
# Encontro: <título>

- Grupo: nível <N>, dificuldade <D>
- ND alvo: <X> | ND por monstro: <Y> (heurística do projeto)
- Tema: <tema ou "livre">

## Monstros
### <nome> (ND <nd>, p.<página>)
- Defesa / PV: ...
- Ataques: ...
- Habilidades: ...
- Tática: ...
```

Depois de salvar, confirme o nome do arquivo. Se a ferramenta falhar, conte o erro.
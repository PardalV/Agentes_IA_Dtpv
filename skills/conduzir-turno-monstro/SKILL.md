---
name: conduzir-turno-monstro
description: Conduz o turno de um monstro em combate: lê a ficha, resolve os efeitos do início do turno, rola ataques e danos com os valores da ficha, compara com a Defesa dos alvos e acompanha os pontos de vida. Use quando o mestre pedir para jogar, rodar ou resolver o turno ou o ataque de um monstro.
---

# Conduzir o turno de um monstro

Use somente os valores da ficha. Nunca invente tipos de dano, bônus ou regras que a ficha não traga.

## Passo 1: situação atual
Descubra qual monstro (e quantos), quais são os PV atuais e se há condições ativas. Se o mestre
não disser, use os PV cheios da ficha e avise. Chame obter_ficha_monstro (a menos que a ficha
já esteja na conversa).

## Passo 2: início do turno
Releia a ficha procurando habilidades que acontecem no início do turno do monstro (auras,
constrição em quem está agarrado, regeneração e parecidas). Resolva essas primeiro e informe o
que cada uma causa, rolando o dano com rolar_dados quando houver dados.

## Passo 3: escolher as ações
Liste as ações do monstro pela ficha, respeitando os marcadores que ela traz, como (PADRÃO),
(LIVRE) e (REAÇÃO). Escolha o que faz mais sentido pelas habilidades e pelo que o mestre disse;
se houver dúvida sobre o que o monstro quer fazer, pergunte ao mestre.

## Passo 4: resolver o ataque
1. Role o ataque com rolar_dados no formato 1d20+bônus, usando o bônus da ficha.
2. Compare com a Defesa do alvo e diga qual Defesa usou. Se o mestre não informou a Defesa, NÃO diga que acertou:
   informe o total rolado e pergunte a Defesa.
3. Se o resultado do d20 estiver na margem de ameaça indicada na ficha (como 17-20), avise o
   mestre que há ameaça de crítico. Não invente a confirmação: deixe o mestre decidir.

## Passo 5: dano e efeitos
1. Para CADA ataque que acertou, role o dano separadamente (uma chamada de rolar_dados por
   ataque), com a expressão da ficha e somando todas as parcelas indicadas (por exemplo, o dano
   base mais o dano de fogo). Mostre o dano de cada ataque e depois o total.
2. Aplique resistências ou imunidades do alvo só se o mestre as informar.
3. Quando uma habilidade pedir teste do alvo (como Reflexos CD 17), informe o teste e a CD ao
   mestre. Quem rola são os jogadores, a menos que o mestre peça para você rolar.

## Passo 6: registro da mesa
Ao final de cada turno, mostre um registro curto:
```
Monstro: <nome> | PV: <atuais>/<totais> | Condições: <lista ou nenhuma>
```
Atualize os PV a cada dano que o mestre informar e mantenha o registro nos próximos turnos.

## Passo 7: narração (opcional)
Se o mestre quiser, escreva 1 ou 2 frases narrando o que aconteceu, baseadas apenas nos
resultados das rolagens.
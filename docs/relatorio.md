# Compilador Fortran 77 → EWVM

## Relatório Técnico

**Unidade Curricular:** Processamento de Linguagens (PL) — 2025/2026

**Autores:**
- Jorge Rafael Machado Fernandes (A104168)
- Diogo Teixeira Fernandes (A104260)
- André Filipe Pereira Ribeiro (A)

**Data:** maio de 2026

---

## 1. Introdução

O presente relatório descreve o desenvolvimento de um compilador capaz de traduzir programas escritos em Fortran 77 (standard ANSI X3.9-1978) para código executável na EWVM (EPL Web Virtual Machine), uma máquina virtual de stack desenvolvida no Departamento de Informática da Universidade do Minho.

O compilador foi implementado em Python, utilizando a biblioteca PLY (Python Lex-Yacc) para as fases de análise léxica e sintática, e segue a arquitetura clássica de um compilador modular com seis fases: pré-processamento, análise léxica, análise sintática, análise semântica, otimização e geração de código.

Optámos pelo formato free-form (em vez do formato de colunas fixas do Fortran 77 original) por simplificar o pré-processamento sem comprometer a compatibilidade com os programas exemplo do enunciado.

## 2. Arquitetura do Compilador

O compilador está organizado em 7 módulos Python independentes, cada um responsável por uma fase ou componente específico da pipeline de compilação:

```
Código Fortran 77 (.f)
        │
        ▼
  ┌─────────────┐
  │ preprocess() │  Remoção de comentários F77 (linhas com C, c, *)
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │  lexer.py   │  Tokenização via ply.lex (expressões regulares)
  └──────┬──────┘
         ▼
  ┌─────────────┐
  │  parser.py  │  Construção da AST via ply.yacc (gramática LALR)
  └──────┬──────┘
         ▼
  ┌──────────────┐
  │ semantic.py  │  Verificação de tipos, declarações e labels
  └──────┬───────┘
         ▼
  ┌──────────────┐
  │ optimizer.py │  Constant Folding na AST
  └──────┬───────┘
         ▼
  ┌─────────────┐
  │ codegen.py  │  Travessia da AST e emissão de instruções EWVM
  └──────┬──────┘
         ▼
  Código EWVM (.vm)
```

O módulo `main.py` orquestra toda a pipeline e serve como ponto de entrada único. A classe `SymbolTable` em `symbol_table.py` é partilhada pela análise semântica e pela geração de código, gerindo offsets de memória, tipos de variáveis, arrays, funções e labels.

## 3. Análise Léxica

### 3.1 Implementação

O analisador léxico (`lexer.py`) foi construído com `ply.lex` e reconhece os seguintes tipos de tokens:

- **Palavras reservadas** (19): PROGRAM, END, INTEGER, REAL, LOGICAL, IF, THEN, ELSE, ENDIF, DO, CONTINUE, GOTO, PRINT, READ, STOP, RETURN, CALL, FUNCTION, SUBROUTINE
- **Literais**: constantes inteiras (ICONST), reais (RCONST) e strings (SCONST)
- **Identificadores** (ID): sequências alfanuméricas que começam por letra
- **Operadores aritméticos**: +, -, \*, /, \*\*
- **Operadores relacionais**: .EQ., .NE., .LT., .GT., .LE., .GE.
- **Operadores lógicos**: .AND., .OR., .NOT., .TRUE., .FALSE.
- **Delimitadores**: (, ), vírgula, =
- **Newlines**: usados como separadores de statements

### 3.2 Decisões de Implementação

O Fortran 77 é case-insensitive, pelo que a função `t_ID` converte todos os identificadores para maiúsculas antes de verificar se correspondem a uma palavra reservada. Esta abordagem segue o padrão ensinado nas aulas (NB03), onde keywords são capturadas pela expressão regular do identificador e depois reclassificadas via dicionário:

```python
def t_ID(t):
    r'[A-Za-z_][A-Za-z0-9_]*'
    upper = t.value.upper()
    t.type = reserved.get(upper, 'ID')
    t.value = upper
    return t
```

O operador `**` (potência) é definido como função antes de `*` para garantir prioridade na correspondência, conforme as regras de prioridade do PLY (funções têm prioridade sobre strings, e dentro de strings, padrões mais longos primeiro).

Os comentários do Fortran 77 são tratados em duas fases: a função `preprocess()` remove linhas que começam com `C`, `c` ou `*` (comentários de coluna), enquanto comentários inline com `!` são ignorados diretamente pelo lexer.

## 4. Análise Sintática

### 4.1 Gramática

O analisador sintático (`parser.py`) foi construído com `ply.yacc`, que gera um parser LALR(1). A gramática suporta as construções fundamentais do Fortran 77. As produções principais são:

```
program_units → program_unit | program_units program_unit
program_unit  → program | function
program       → PROGRAM ID NEWLINE block END
function      → type_spec FUNCTION ID ( id_list ) NEWLINE block END
block         → statements

statement     → simple_statement | ICONST simple_statement
              | if_statement | ICONST if_statement

simple_statement → type_spec id_list                          (declaração)
                 | type_spec ID ( ICONST )                    (declaração de array)
                 | ID = expr                                  (atribuição)
                 | ID ( expr ) = expr                         (atribuição a array)
                 | PRINT * , print_list                       (output)
                 | READ * , read_list                         (input)
                 | DO ICONST ID = expr , expr [, expr]        (ciclo DO)
                 | GOTO ICONST                                (salto)
                 | CONTINUE | STOP | RETURN

if_statement  → IF ( condition ) THEN NEWLINE block ENDIF
              | IF ( condition ) THEN NEWLINE block ELSE NEWLINE block ENDIF

expr          → expr + term | expr - term | term
term          → term * power | term / power | power
power         → factor ** power | factor
factor        → ID | ID ( arg_list ) | ICONST | RCONST
              | .TRUE. | .FALSE. | ( expr ) | - factor

condition     → expr relop expr | condition .AND. condition
              | condition .OR. condition | .NOT. condition
              | ( condition ) | expr
```

### 4.2 Precedência e Associatividade

A tabela de precedência foi definida explicitamente no PLY para resolver ambiguidades, seguindo as regras padrão do Fortran 77:

```python
precedence = (
    ('left', 'OR'),
    ('left', 'AND'),
    ('right', 'NOT'),
    ('nonassoc', 'LT', 'LE', 'GT', 'GE', 'EQ', 'NE'),
    ('left', 'PLUS', 'MINUS'),
    ('left', 'TIMES', 'DIVIDE'),
    ('right', 'POWER'),
    ('right', 'UMINUS'),
)
```

### 4.3 Representação da AST

A AST é representada como tuplos Python aninhados, seguindo o padrão apresentado nas aulas (NB07). Cada nó é um tuplo cujo primeiro elemento identifica o tipo. Exemplos:

- `('program', 'HELLO', [statements...])` — programa principal
- `('assign', 'X', ('int', 5))` — atribuição
- `('binop', '+', left, right)` — operação binária
- `('cond', '.GT.', left, right)` — comparação
- `('if', condition, then_block, else_block)` — condicional
- `('do', label, var, start, end, step)` — ciclo DO

## 5. Análise Semântica

### 5.1 Tabela de Símbolos

A classe `SymbolTable` (`symbol_table.py`) gere o registo de todos os identificadores do programa. Para cada variável, armazena o tipo (INTEGER, REAL, LOGICAL) e o offset na região global da stack. Para arrays, armazena adicionalmente o tamanho. Para funções, armazena o tipo de retorno e a lista de parâmetros.

A tabela também é responsável pela geração de labels únicos (L0, L1, L2, ...) usados na tradução de estruturas de controlo para código EWVM, e pela gestão de labels numéricos do Fortran (para DO/CONTINUE e GOTO).

### 5.2 Verificações Realizadas

O analisador semântico (`semantic.py`) percorre a AST em duas passagens:

**1ª passagem:** regista todas as funções definidas no programa, permitindo chamadas cruzadas entre funções e o programa principal.

**2ª passagem:** percorre cada unidade de programa e verifica:

- **Declaração de variáveis:** uso de variáveis não declaradas é reportado como erro.
- **Declaração de arrays:** verificação de duplicados e validação de tamanhos.
- **Type checking rigoroso:** incompatibilidades de tipos em atribuições são detetadas. A promoção implícita entre INTEGER e REAL é permitida (conforme o standard F77), mas atribuir um LOGICAL a um INTEGER gera erro.
- **Validação de labels:** cada GOTO referencia um label existente; cada DO aponta para um CONTINUE válido.
- **Validação de chamadas a funções:** o número de argumentos é verificado contra a assinatura registada.
- **Inferência de tipos em expressões:** cada expressão tem um tipo inferido (INTEGER, REAL ou LOGICAL) que é propagado ascendentemente na AST.

## 6. Otimização

### 6.1 Constant Folding

O módulo `optimizer.py` implementa a otimização de Constant Folding: expressões cujos operandos são ambos constantes são avaliadas em tempo de compilação, substituindo a sub-árvore inteira por um único nó constante na AST.

Por exemplo, a expressão `2 + 3 * 4` na AST original contém 5 nós (dois operandos e duas operações aninhadas). Após otimização, é reduzida a um único nó `('int', 14)`, gerando apenas a instrução `PUSHI 14` em vez de 5 instruções (`PUSHI 2`, `PUSHI 3`, `PUSHI 4`, `MUL`, `ADD`).

O optimizer suporta folding para operações aritméticas (+, -, \*, /, \*\*) com constantes inteiras e reais, incluindo negação unária. A otimização é aplicada recursivamente a toda a AST antes da fase de geração de código.

Esta fase encaixa na etapa de "Transformation" da pipeline de compilação descrita no NB01, onde a representação intermédia é transformada antes da geração de output.

## 7. Geração de Código

### 7.1 Modelo de Execução

A EWVM é uma máquina virtual de stack. O código gerado utiliza a região global da stack para armazenar variáveis, e a stack de operandos para avaliar expressões (travessia post-order da AST, conforme ensinado no NB07). Os principais padrões de geração são:

- **Variáveis escalares:** `PUSHG offset` para ler, `STOREG offset` para escrever.
- **Arrays:** `PUSHGP + PUSHI offset + PADD` para calcular o endereço base, ajuste de índice de base-1 (Fortran) para base-0 (memória), e `LOADN`/`STOREN` para acesso indexado.
- **Expressões:** travessia post-order — gerar código para operandos esquerdo e direito, depois emitir a instrução da operação (ADD, SUB, MUL, DIV, etc.).
- **IF/ELSE:** padrão com `JZ` para salto condicional e labels gerados (`L0`, `L1`, ...).
- **DO loops:** inicialização da variável de controlo, label de início do loop, teste de condição com `SUP + JZ`, e incremento no CONTINUE correspondente. A ligação entre DO e CONTINUE é feita via `loop_stack`.
- **GOTO:** traduzido diretamente para `JUMP lbl<N>`.
- **I/O:** `READ + ATOI + STOREG` para input; `PUSHS + WRITES` para strings e `WRITEI` para inteiros no output.

### 7.2 Suporte a Funções (Valorização)

A implementação de `INTEGER FUNCTION` constitui uma das valorizações do projeto. A passagem de argumentos é feita via memória estática global, inspirada nos compiladores originais do Fortran 77 que não usavam stack frames dinâmicos.

O mecanismo funciona da seguinte forma:

1. O **caller** avalia cada argumento e guarda-o na posição global correspondente ao parâmetro da função (`STOREG`).
2. Emite `PUSHA funcNOME` seguido de `CALL` para transferir controlo.
3. A **função** acede aos parâmetros como variáveis globais normais, executa o corpo, e guarda o resultado numa variável global com o seu próprio nome (ex: `CONVRT = VAL`).
4. A função termina com `RETURN`.
5. O caller lê o resultado via `PUSHG offset_da_função`.

Esta abordagem foi escolhida por se adequar às limitações da EWVM (que não tem suporte nativo para frames locais) e por ser historicamente consistente com o Fortran 77, onde a passagem por memória estática era o padrão antes da introdução de stack frames.

## 8. Testes

### 8.1 Programas Exemplo

Os 5 programas obrigatórios do enunciado foram implementados e compilam com sucesso:

| Programa | Construções Testadas |
|----------|---------------------|
| `hello.f` | PRINT com string, estrutura mínima de programa |
| `fatorial.f` | DO loop, READ, expressões aritméticas (MUL), PRINT misto |
| `primo.f` | GOTO com labels, .AND. lógico, MOD built-in, IF/ELSE, LOGICAL |
| `somaarr.f` | Arrays (declaração, READ indexado, acesso indexado), DO loop |
| `conversor.f` | FUNCTION com CALL/RETURN, múltiplos argumentos, MOD, GOTO |

### 8.2 Testes Automatizados

O script `run_tests.py` executa 17 testes automatizados divididos em três categorias:

- **Semântica (ficheiros válidos):** verifica que os 5 programas exemplo passam sem erros semânticos.
- **Semântica (deteção de erros):** verifica que ficheiros inválidos são corretamente rejeitados — variável não declarada (`test_semantic_bad.f`), GOTO para label inexistente (`test_goto_bad.f`), e incompatibilidade de tipos (`test_type_bad.f`).
- **Geração de código:** verifica que cada programa gera código EWVM válido contendo `START`/`STOP`, e que construções específicas produzem as instruções esperadas (PUSHS/WRITES para strings, JUMP/MUL para loops, PUSHGP/PADD/LOADN/STOREN para arrays, PUSHA/CALL/RETURN para funções).

Todos os 17 testes passam com sucesso.

## 9. Dificuldades Encontradas e Decisões Tomadas

### 9.1 Formato Free-form vs. Colunas Fixas

O Fortran 77 original usa um formato de colunas fixas (colunas 1-5 para labels, coluna 6 para continuação, colunas 7-72 para código). Optámos pelo formato free-form por simplificar significativamente o pré-processamento e o lexer, sem perder compatibilidade com os programas do enunciado. Os comentários de coluna (linhas começadas por `C`, `c` ou `*`) são removidos na fase de pré-processamento.

### 9.2 Passagem de Argumentos a Funções

A EWVM não oferece suporte nativo para stack frames locais ou passagem de parâmetros. A solução encontrada — passagem via variáveis globais estáticas — é simples e funcional, embora implique que funções não podem ser recursivas. Esta limitação é aceitável dado que o Fortran 77 original também não garantia suporte a recursão.

### 9.3 Ligação DO-CONTINUE

A ligação entre o statement `DO` e o `CONTINUE` correspondente é feita através de uma stack (`loop_stack`) no gerador de código. Quando um `DO` é processado, a informação do loop (offset da variável, step, labels) é empilhada. Quando o `CONTINUE` com o label correspondente é encontrado, a informação é desempilhada e usada para gerar o incremento e o salto de retorno ao início do loop.

### 9.4 Arrays com Indexação Base-1

O Fortran usa indexação a partir de 1, enquanto a memória da EWVM usa base 0. A conversão é feita em tempo de execução subtraindo 1 ao índice calculado (`PUSHI 1` + `SUB`) antes de cada acesso ao array.

## 10. Instruções de Utilização

### Compilar um programa Fortran 77

```sh
pip install -r requirements.txt
python src/main.py tests/fortran/conversor.f
```

O código EWVM é impresso no terminal. Pode ser copiado e executado no simulador [EWVM Online](https://ewvm.epl.di.uminho.pt/).

### Outros modos

```sh
python src/main.py <ficheiro.f> --semantic   # apenas análise semântica
python src/main.py <ficheiro.f> --ast        # mostrar a AST
python tests/run_tests.py                    # correr os 17 testes
```

## 11. Conclusão

O compilador desenvolvido cumpre todos os requisitos obrigatórios do enunciado: implementa análise léxica, sintática e semântica completas para um subconjunto relevante do Fortran 77, e gera código funcional para a EWVM. Os 5 programas exemplo compilam e produzem código executável correto.

Foram implementadas três valorizações: suporte a funções com `FUNCTION`/`CALL`/`RETURN`, verificação rigorosa de tipos na análise semântica, e otimização por Constant Folding. A arquitetura modular do projeto, com separação clara entre as fases da pipeline de compilação, facilita a manutenção e a extensibilidade do compilador.

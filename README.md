# Compilador Fortran 77 -> EWVM

Este repositorio contem o projeto da Unidade Curricular de **Processamento de Linguagens** (PL) no ano letivo 2025/2026. O objetivo deste projeto e desenvolver um **Compilador** completo capaz de traduzir codigo escrito na linguagem *Fortran 77* para codigo maquina executavel na *EWVM* (EPL Web Virtual Machine).

O projeto foi desenvolvido em **Python** e implementa um motor de compilacao modular composto por analise lexica, sintatica, semantica, otimizacao e geracao de codigo.

## Estrutura do Projeto
```text
pl2526/
├── src/
│   ├── main.py            # Ponto de entrada do compilador (pipeline completa)
│   ├── lexer.py           # Analisador Lexico (tokenizacao e remocao de comentarios)
│   ├── parser.py          # Analisador Sintatico (construcao da AST)
│   ├── symbol_table.py    # Tabela de Simbolos (gestao de variaveis, arrays e funcoes)
│   ├── semantic.py        # Analisador Semantico (verificacao rigorosa de tipos)
│   ├── optimizer.py       # Otimizador (Constant Folding)
│   └── codegen.py         # Gerador de Codigo EWVM
├── tests/
│   ├── fortran/           # Programas Fortran 77 de exemplo (.f)
│   ├── vm/                # Codigo EWVM gerado para cada exemplo (.vm)
│   └── run_tests.py       # Script de testes automatizados (17 testes)
├── docs/                  # Relatorio tecnico
├── .gitignore
├── requirements.txt       # Dependencias Python (PLY)
└── README.md
```

## Instalacao e Configuracao

O compilador requer **Python 3.8+** e depende apenas da biblioteca PLY (Python Lex-Yacc).

```sh
pip install -r requirements.txt
```

## Como Utilizar o Compilador

### Compilar um ficheiro Fortran (pipeline completa)
```sh
python src/main.py tests/fortran/conversor.f
```
As instrucoes EWVM geradas sao impressas no terminal. Copie-as e execute-as no simulador [EWVM Online](https://ewvm.epl.di.uminho.pt/).

### Apenas analise semantica (sem gerar codigo)
```sh
python src/main.py tests/fortran/test_type_bad.f --semantic
```

### Mostrar a AST (arvore sintatica)
```sh
python src/main.py tests/fortran/hello.f --ast
```

### Correr os testes automatizados
```sh
python tests/run_tests.py
```

## Funcionalidades Extra (Valorizacoes)

1. **Subprogramas (FUNCTION):** Suporte completo para funcoes com passagem de argumentos via memoria estatica global, inspirado nos compiladores originais do Fortran 77.
2. **Type Checking Rigoroso:** O analisador semantico rejeita atribuicoes invalidas (ex: guardar um LOGICAL num INTEGER).
3. **Otimizacao (Constant Folding):** Expressoes constantes sao avaliadas em tempo de compilacao (ex: `2 + 3 * 4` gera apenas `PUSHI 14`).

## Desenvolvido por

- [Jorge Rafael Machado Fernandes](https://github.com/rafafernandes888)
- [Diogo Teixeira Fernandes](https://github.com/diogo7fernandes)
- [Andre Filipe Pereira Ribeiro](https://github.com/andreribeiro5)

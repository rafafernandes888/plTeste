"""
Compilador Fortran 77 -> EWVM
Ponto de entrada principal.

Pipeline de compilação:
  1. Pré-processamento (remoção de comentários Fortran)
  2. Análise Léxica (tokenização via PLY)
  3. Análise Sintática (construção da AST via PLY/YACC)
  4. Análise Semântica (verificação de tipos e declarações)
  5. Otimização (Constant Folding)
  6. Geração de Código (tradução para instruções EWVM)

Uso:
  python src/main.py <ficheiro.f>
  python src/main.py <ficheiro.f> --semantic    (apenas análise semântica)
  python src/main.py <ficheiro.f> --ast         (mostrar a AST)
"""

import sys
import lexer as lexer_module
import parser as parser_module
from lexer import preprocess
from semantic import SemanticAnalyzer
from codegen import CodeGenerator


def compile_file(path, mode='codegen'):
    """Compila um ficheiro Fortran 77.

    Args:
        path: Caminho para o ficheiro .f
        mode: 'codegen' (gerar código), 'semantic' (apenas semântica), 'ast' (mostrar AST)
    """
    # Ler o ficheiro fonte
    with open(path, 'r', encoding='utf-8') as f:
        source = f.read()

    # 1. Pré-processamento: remover comentários Fortran 77
    source = preprocess(source)

    # 2-3. Análise Léxica e Sintática: gerar a AST
    lex = lexer_module.lex.lex(module=lexer_module)
    tree = parser_module.parser.parse(source, lexer=lex)

    if tree is None:
        print("Erro: Falha no parsing do ficheiro.")
        sys.exit(1)

    # Modo AST: mostrar a árvore e sair
    if mode == 'ast':
        import json
        print(json.dumps(tree, indent=2, default=str))
        return

    # 4. Análise Semântica: verificar tipos e declarações
    analyzer = SemanticAnalyzer()
    analyzer.analyze(tree)

    if analyzer.errors:
        sys.exit(1)

    # Modo semântico: parar aqui
    if mode == 'semantic':
        return

    # 5-6. Otimização + Geração de Código EWVM
    gen = CodeGenerator()
    gen.generate(tree)
    print(gen.get_code())


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Compilador Fortran 77 -> EWVM")
        print()
        print("Uso:")
        print("  python src/main.py <ficheiro.f>              Compilar e gerar código EWVM")
        print("  python src/main.py <ficheiro.f> --semantic   Apenas análise semântica")
        print("  python src/main.py <ficheiro.f> --ast        Mostrar a AST")
        sys.exit(1)

    path = sys.argv[1]
    mode = 'codegen'

    if len(sys.argv) > 2:
        flag = sys.argv[2]
        if flag == '--semantic':
            mode = 'semantic'
        elif flag == '--ast':
            mode = 'ast'

    compile_file(path, mode)

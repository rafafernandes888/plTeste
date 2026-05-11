"""
Script de testes automatizados para o compilador Fortran 77 -> EWVM.
Testa o lexer, parser, análise semântica e geração de código.
"""
import sys
import os

# Adicionar o diretório src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import lexer as lexer_module
import parser as parser_module
from lexer import preprocess
from semantic import SemanticAnalyzer
from codegen import CodeGenerator


TESTS_DIR = os.path.join(os.path.dirname(__file__), 'fortran')

# ─────────────────────────────────────────────
# Utilitários
# ─────────────────────────────────────────────
def parse_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        source = f.read()
    source = preprocess(source)
    lex = lexer_module.lex.lex(module=lexer_module)
    tree = parser_module.parser.parse(source, lexer=lex)
    return tree


def run_semantic(path):
    """Retorna (tem_erros: bool, lista_erros: list)."""
    tree = parse_file(path)
    if not isinstance(tree, list):
        return True, ["AST inválida"]

    analyzer = SemanticAnalyzer()

    # Replicar a lógica do analyze() mas sem imprimir
    # 1ª passagem: registar funções
    for unit in tree:
        if unit[0] == 'function':
            _, var_type, name, args, _ = unit
            analyzer.symbols.declare_function(name, var_type, args)

    # 2ª passagem: analisar
    for unit in tree:
        if unit[0] == 'program':
            _, program_name, statements = unit
            analyzer.symbols.clear_labels()
            analyzer._collect_labels(statements)
            analyzer._check_statements(statements)
        elif unit[0] == 'function':
            _, var_type, name, args, statements = unit
            analyzer.symbols.clear_labels()
            analyzer._collect_labels(statements)
            analyzer._check_statements(statements)

    return len(analyzer.errors) > 0, analyzer.errors


def run_codegen(path):
    """Retorna (sucesso: bool, codigo: str)."""
    tree = parse_file(path)
    gen = CodeGenerator()
    gen.generate(tree)
    code = gen.get_code()
    return len(code) > 0, code


# ─────────────────────────────────────────────
# Definição dos testes
# ─────────────────────────────────────────────
passed = 0
failed = 0


def test(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  PASS  {name}")
        passed += 1
    else:
        msg = f"  FAIL  {name}"
        if detail:
            msg += f" -- {detail}"
        print(msg)
        failed += 1


# ─────────────────────────────────────────────
# Testes de Análise Semântica (ficheiros válidos)
# ─────────────────────────────────────────────
print("\n=== Analise Semantica: Ficheiros Validos ===")

valid_files = ['hello.f', 'fatorial.f', 'primo.f', 'somaarr.f', 'conversor.f']
for fname in valid_files:
    path = os.path.join(TESTS_DIR, fname)
    has_errors, errors = run_semantic(path)
    test(f"{fname} -- sem erros semanticos", not has_errors, str(errors) if has_errors else "")

# ─────────────────────────────────────────────
# Testes de Análise Semântica (ficheiros com erros)
# ─────────────────────────────────────────────
print("\n=== Analise Semantica: Detecao de Erros ===")

path = os.path.join(TESTS_DIR, 'test_semantic_bad.f')
has_errors, errors = run_semantic(path)
test("test_semantic_bad.f -- deteta variavel nao declarada",
     has_errors and any("declarada" in e for e in errors))

path = os.path.join(TESTS_DIR, 'test_goto_bad.f')
has_errors, errors = run_semantic(path)
test("test_goto_bad.f -- deteta GOTO para label inexistente",
     has_errors and any("inexistente" in e for e in errors))

path = os.path.join(TESTS_DIR, 'test_type_bad.f')
if os.path.exists(path):
    has_errors, errors = run_semantic(path)
    test("test_type_bad.f -- deteta incompatibilidade de tipos",
         has_errors and any("Incompatibilidade" in e for e in errors))

# ─────────────────────────────────────────────
# Testes de Geração de Código
# ─────────────────────────────────────────────
print("\n=== Geracao de Codigo EWVM ===")

for fname in valid_files:
    path = os.path.join(TESTS_DIR, fname)
    success, code = run_codegen(path)
    test(f"{fname} -- gera codigo",
         success and "START" in code and "STOP" in code,
         "Codigo vazio ou sem START/STOP" if not success else "")

# Verificações específicas do código gerado
path = os.path.join(TESTS_DIR, 'hello.f')
_, code = run_codegen(path)
test("hello.f -- contem PUSHS e WRITES",
     'PUSHS' in code and 'WRITES' in code)

path = os.path.join(TESTS_DIR, 'fatorial.f')
_, code = run_codegen(path)
test("fatorial.f -- contem ciclo DO (JUMP e labels)",
     'JUMP' in code and 'MUL' in code)

path = os.path.join(TESTS_DIR, 'somaarr.f')
_, code = run_codegen(path)
test("somaarr.f -- usa instrucoes de array (PUSHGP, PADD, LOADN, STOREN)",
     all(instr in code for instr in ['PUSHGP', 'PADD', 'LOADN', 'STOREN']))

path = os.path.join(TESTS_DIR, 'conversor.f')
_, code = run_codegen(path)
test("conversor.f -- gera chamada a funcao (PUSHA, CALL)",
     'PUSHA' in code and 'CALL' in code and 'RETURN' in code)

# ─────────────────────────────────────────────
# Resumo
# ─────────────────────────────────────────────
total = passed + failed
print(f"\n{'='*40}")
print(f"Resultados: {passed}/{total} testes passaram")
if failed == 0:
    print("Todos os testes passaram!")
else:
    print(f"{failed} teste(s) falharam")
print(f"{'='*40}\n")

sys.exit(0 if failed == 0 else 1)

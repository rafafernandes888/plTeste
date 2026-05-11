"""
Analisador Semântico do Compilador Fortran 77.

Responsável por validar a corretude lógica do programa após o parsing:
- Verificação de declaração de variáveis e arrays
- Verificação rigorosa de tipos (Type Checking)
- Validação de chamadas a funções (número de argumentos)
- Validação de labels e referências GOTO/DO
- Compatibilidade de tipos em atribuições e expressões

Utiliza a SymbolTable para gerir o registo de identificadores.
"""

import sys
import lexer as lexer_module
import parser as parser_module
from lexer import preprocess
from symbol_table import SymbolTable


class SemanticAnalyzer:
    def __init__(self):
        self.symbols = SymbolTable()
        self.errors = []
        self.reported = set()

    def error(self, msg):
        """Regista um erro semântico (sem duplicados)."""
        if msg not in self.reported:
            self.errors.append(msg)
            self.reported.add(msg)

    # ─────────────────────────────────────────────
    # Ponto de entrada principal
    # ─────────────────────────────────────────────
    def analyze(self, tree):
        """Analisa a AST completa (lista de unidades de programa)."""
        if not isinstance(tree, list):
            self.error("AST inválida")
            self._print_results()
            return

        # 1ª passagem: registar todas as funções (para chamadas cruzadas)
        for unit in tree:
            if unit[0] == 'function':
                _, var_type, name, args, _ = unit
                self.symbols.declare_function(name, var_type, args)

        # 2ª passagem: analisar cada unidade
        for unit in tree:
            if unit[0] == 'program':
                _, program_name, statements = unit
                self.symbols.clear_labels()
                self._collect_labels(statements)
                self._check_statements(statements)

            elif unit[0] == 'function':
                _, var_type, name, args, statements = unit
                self.symbols.clear_labels()
                self._collect_labels(statements)
                self._check_statements(statements)

        self._print_results()

    def _print_results(self):
        """Imprime os resultados da análise semântica."""
        if self.errors:
            print("Erros semânticos:")
            for err in self.errors:
                print(f"  - {err}")
        else:
            print("Análise semântica sem erros.")

    # ─────────────────────────────────────────────
    # Recolha de labels (1ª passagem por bloco)
    # ─────────────────────────────────────────────
    def _collect_labels(self, statements):
        for stmt in statements:
            self._collect_labels_stmt(stmt)

    def _collect_labels_stmt(self, stmt):
        kind = stmt[0]

        if kind == 'label':
            label_num = stmt[1]
            inner_stmt = stmt[2]

            if self.symbols.label_exists(label_num):
                self.error(f"Label repetido: {label_num}")
            else:
                self.symbols.register_label(label_num, inner_stmt)

            self._collect_labels_stmt(inner_stmt)

        elif kind == 'if':
            _, _, then_block, else_block = stmt
            self._collect_labels(then_block)
            if else_block:
                self._collect_labels(else_block)

    # ─────────────────────────────────────────────
    # Verificação de statements
    # ─────────────────────────────────────────────
    def _check_statements(self, statements):
        for stmt in statements:
            self._check_stmt(stmt)

    def _check_stmt(self, stmt):
        kind = stmt[0]

        if kind == 'decl':
            _, var_type, ids = stmt
            for name in ids:
                self.symbols.declare_var(name, var_type)

        elif kind == 'decl_array':
            _, var_type, name, size = stmt
            try:
                self.symbols.declare_array(name, var_type, size)
            except Exception as e:
                self.error(str(e))

        elif kind == 'assign':
            _, name, expr = stmt
            if not self.symbols.var_exists(name):
                self.error(f"Variável não declarada: {name}")
            else:
                var_type = self.symbols.var_type(name)
                expr_t = self._check_expr(expr)
                if expr_t and var_type and expr_t != var_type:
                    # Permitir INTEGER <-> REAL (promoção implícita do Fortran)
                    if not ({var_type, expr_t} <= {'INTEGER', 'REAL'}):
                        self.error(
                            f"Incompatibilidade de tipos em '{name}': "
                            f"esperado {var_type}, obteve {expr_t}"
                        )

        elif kind == 'assign_array':
            _, name, index_expr, value_expr = stmt
            if not self.symbols.array_exists(name):
                self.error(f"Array não declarado: {name}")
            else:
                arr_info = self.symbols.lookup_array(name)
                idx_t = self._check_expr(index_expr)
                if idx_t and idx_t != 'INTEGER':
                    self.error(f"Índice do array '{name}' deve ser INTEGER, obteve {idx_t}")
                val_t = self._check_expr(value_expr)
                if val_t and arr_info['type'] and val_t != arr_info['type']:
                    if not ({val_t, arr_info['type']} <= {'INTEGER', 'REAL'}):
                        self.error(
                            f"Incompatibilidade de tipos em '{name}(...)': "
                            f"esperado {arr_info['type']}, obteve {val_t}"
                        )

        elif kind == 'read':
            _, vars_list = stmt
            for var in vars_list:
                if var[0] == 'var':
                    name = var[1]
                    if not self.symbols.var_exists(name):
                        self.error(f"Variável não declarada em READ: {name}")
                elif var[0] == 'array_var':
                    name = var[1]
                    if not self.symbols.array_exists(name):
                        self.error(f"Array não declarado em READ: {name}")
                    self._check_expr(var[2])

        elif kind == 'print':
            _, items = stmt
            for item in items:
                if isinstance(item, tuple) and item[0] != 'string':
                    self._check_expr(item)

        elif kind == 'goto':
            _, label_num = stmt
            if not self.symbols.label_exists(label_num):
                self.error(f"GOTO para label inexistente: {label_num}")

        elif kind == 'do':
            _, label_num, var_name, start_expr, end_expr, step_expr = stmt

            if not self.symbols.var_exists(var_name):
                self.error(f"Variável de controlo do DO não declarada: {var_name}")

            self._check_expr(start_expr)
            self._check_expr(end_expr)
            if step_expr is not None:
                self._check_expr(step_expr)

            if not self.symbols.label_exists(label_num):
                self.error(f"DO com label inexistente: {label_num}")
            else:
                target_stmt = self.symbols.lookup_label(label_num)
                if target_stmt[0] != 'continue':
                    self.error(f"Label {label_num} do DO não aponta para CONTINUE")

        elif kind == 'if':
            _, condition, then_block, else_block = stmt
            self._check_expr(condition)
            self._check_statements(then_block)
            if else_block:
                self._check_statements(else_block)

        elif kind == 'label':
            _, _, inner_stmt = stmt
            self._check_stmt(inner_stmt)

        elif kind in ('continue', 'stop', 'return'):
            pass

        else:
            self.error(f"Tipo de statement desconhecido: {kind}")

    # ─────────────────────────────────────────────
    # Verificação de expressões (com inferência de tipo)
    # ─────────────────────────────────────────────
    def _check_expr(self, expr):
        """Verifica a expressão e retorna o tipo inferido (ou None)."""
        if not isinstance(expr, tuple):
            return None

        kind = expr[0]

        if kind == 'int':
            return 'INTEGER'

        elif kind == 'real':
            return 'REAL'

        elif kind == 'bool':
            return 'LOGICAL'

        elif kind == 'string':
            return 'STRING'

        elif kind == 'id':
            name = expr[1]
            if not self.symbols.var_exists(name):
                self.error(f"Variável não declarada: {name}")
                return None
            return self.symbols.var_type(name)

        elif kind == 'var':
            name = expr[1]
            if not self.symbols.var_exists(name):
                self.error(f"Variável não declarada: {name}")
                return None
            return self.symbols.var_type(name)

        elif kind == 'uminus':
            t = self._check_expr(expr[1])
            if t and t not in ('INTEGER', 'REAL'):
                self.error(f"Operador unário '-' aplicado a tipo não numérico: {t}")
            return t

        elif kind == 'not':
            t = self._check_expr(expr[1])
            if t and t != 'LOGICAL':
                self.error(f"Operador .NOT. aplicado a tipo não lógico: {t}")
            return 'LOGICAL'

        elif kind == 'binop':
            _, op, left, right = expr
            lt = self._check_expr(left)
            rt = self._check_expr(right)
            if lt and lt not in ('INTEGER', 'REAL'):
                self.error(f"Operando esquerdo de '{op}' não é numérico: {lt}")
            if rt and rt not in ('INTEGER', 'REAL'):
                self.error(f"Operando direito de '{op}' não é numérico: {rt}")
            if lt == 'REAL' or rt == 'REAL':
                return 'REAL'
            return 'INTEGER'

        elif kind == 'cond':
            _, op, left, right = expr
            lt = self._check_expr(left)
            rt = self._check_expr(right)
            if lt and lt not in ('INTEGER', 'REAL'):
                self.error(f"Operando esquerdo de '{op}' não é numérico: {lt}")
            if rt and rt not in ('INTEGER', 'REAL'):
                self.error(f"Operando direito de '{op}' não é numérico: {rt}")
            return 'LOGICAL'

        elif kind in ('and', 'or'):
            _, left, right = expr
            lt = self._check_expr(left)
            rt = self._check_expr(right)
            if lt and lt != 'LOGICAL':
                self.error(f"Operando de .{kind.upper()}. não é lógico: {lt}")
            if rt and rt != 'LOGICAL':
                self.error(f"Operando de .{kind.upper()}. não é lógico: {rt}")
            return 'LOGICAL'

        elif kind == 'call':
            name = expr[1]
            args = expr[2]
            for arg in args:
                self._check_expr(arg)
            # Funções built-in
            if name == 'MOD':
                if len(args) != 2:
                    self.error(f"MOD espera 2 argumentos, recebeu {len(args)}")
                return 'INTEGER'
            # Acesso a array
            elif self.symbols.array_exists(name):
                arr_info = self.symbols.lookup_array(name)
                if len(args) != 1:
                    self.error(f"Array '{name}' espera 1 índice, recebeu {len(args)}")
                return arr_info['type']
            # Função do utilizador
            elif self.symbols.function_exists(name):
                func_info = self.symbols.lookup_function(name)
                if len(args) != len(func_info['params']):
                    self.error(
                        f"Função '{name}' espera {len(func_info['params'])} argumentos, "
                        f"recebeu {len(args)}"
                    )
                return func_info['type']
            else:
                self.error(f"Função ou array não declarado: {name}")
                return None

        else:
            self.error(f"Expressão desconhecida: {kind}")
            return None


# ─────────────────────────────────────────────
# Utilitários
# ─────────────────────────────────────────────
def parse_file(path):
    """Faz o parsing de um ficheiro Fortran e retorna a AST."""
    with open(path, 'r', encoding='utf-8') as f:
        source = f.read()

    source = preprocess(source)
    lex = lexer_module.lex.lex(module=lexer_module)
    tree = parser_module.parser.parse(source, lexer=lex)
    return tree


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python src/semantic.py <ficheiro.f>")
        sys.exit(1)

    tree = parse_file(sys.argv[1])
    analyzer = SemanticAnalyzer()
    analyzer.analyze(tree)
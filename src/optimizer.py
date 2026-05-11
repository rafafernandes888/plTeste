"""
Otimizador de código do Compilador Fortran 77.

Implementa otimizações na AST (Abstract Syntax Tree) antes da
geração de código, reduzindo o número de instruções EWVM geradas.

Otimizações implementadas:
- Constant Folding: avaliação de expressões constantes em tempo de compilação
  Exemplo: 2 + 3 * 4 -> 14 (gera PUSHI 14 em vez de 5 instruções)
"""


class Optimizer:
    """Aplica otimizações à AST antes da geração de código."""

    def optimize(self, tree):
        """Ponto de entrada: aplica todas as otimizações à AST completa."""
        if not isinstance(tree, list):
            return tree
        return [self._optimize_unit(unit) for unit in tree]

    # ─────────────────────────────────────────────
    # Otimização por unidade de programa
    # ─────────────────────────────────────────────
    def _optimize_unit(self, unit):
        if unit[0] == 'program':
            _, name, stmts = unit
            return ('program', name, [self._optimize_stmt(s) for s in stmts])
        elif unit[0] == 'function':
            _, vtype, name, args, stmts = unit
            return ('function', vtype, name, args, [self._optimize_stmt(s) for s in stmts])
        return unit

    # ─────────────────────────────────────────────
    # Otimização de statements
    # ─────────────────────────────────────────────
    def _optimize_stmt(self, stmt):
        kind = stmt[0]
        if kind == 'assign':
            return ('assign', stmt[1], self._optimize_expr(stmt[2]))
        elif kind == 'assign_array':
            return ('assign_array', stmt[1],
                    self._optimize_expr(stmt[2]),
                    self._optimize_expr(stmt[3]))
        elif kind == 'print':
            return ('print', [
                self._optimize_expr(item) if isinstance(item, tuple) else item
                for item in stmt[1]
            ])
        elif kind == 'do':
            _, lbl, var, start, end, step = stmt
            return ('do', lbl, var,
                    self._optimize_expr(start),
                    self._optimize_expr(end),
                    self._optimize_expr(step) if step else None)
        elif kind == 'if':
            _, cond, then_b, else_b = stmt
            return ('if', self._optimize_expr(cond),
                    [self._optimize_stmt(s) for s in then_b],
                    [self._optimize_stmt(s) for s in else_b] if else_b else None)
        elif kind == 'label':
            return ('label', stmt[1], self._optimize_stmt(stmt[2]))
        return stmt

    # ─────────────────────────────────────────────
    # Constant Folding — otimização de expressões
    # ─────────────────────────────────────────────
    def _optimize_expr(self, expr):
        """Avalia expressões constantes em tempo de compilação."""
        if not isinstance(expr, tuple):
            return expr

        kind = expr[0]

        if kind == 'binop':
            _, op, left, right = expr
            left = self._optimize_expr(left)
            right = self._optimize_expr(right)

            # Constantes inteiras: calcular resultado em tempo de compilação
            if left[0] == 'int' and right[0] == 'int':
                a, b = left[1], right[1]
                if op == '+': return ('int', a + b)
                if op == '-': return ('int', a - b)
                if op == '*': return ('int', a * b)
                if op == '/' and b != 0: return ('int', a // b)
                if op == '**': return ('int', a ** b)

            # Constantes reais ou mistas: calcular se pelo menos um é real
            if left[0] in ('int', 'real') and right[0] in ('int', 'real'):
                a = float(left[1]) if left[0] == 'real' else left[1]
                b = float(right[1]) if right[0] == 'real' else right[1]
                if left[0] == 'real' or right[0] == 'real':
                    if op == '+': return ('real', a + b)
                    if op == '-': return ('real', a - b)
                    if op == '*': return ('real', a * b)
                    if op == '/' and b != 0: return ('real', a / b)

            return ('binop', op, left, right)

        elif kind == 'uminus':
            inner = self._optimize_expr(expr[1])
            if inner[0] == 'int':
                return ('int', -inner[1])
            if inner[0] == 'real':
                return ('real', -inner[1])
            return ('uminus', inner)

        elif kind == 'cond':
            return ('cond', expr[1],
                    self._optimize_expr(expr[2]),
                    self._optimize_expr(expr[3]))

        elif kind in ('and', 'or'):
            return (kind,
                    self._optimize_expr(expr[1]),
                    self._optimize_expr(expr[2]))

        elif kind == 'not':
            return ('not', self._optimize_expr(expr[1]))

        elif kind == 'call':
            return ('call', expr[1],
                    [self._optimize_expr(a) for a in expr[2]])

        return expr

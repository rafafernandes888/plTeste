"""
Gerador de Código EWVM do Compilador Fortran 77.
"""

import sys
import lexer as lexer_module
import parser as parser_module
from lexer import preprocess
from symbol_table import SymbolTable
from optimizer import Optimizer


class CodeGenerator:
    def __init__(self):
        self.code = []
        self.symbols = SymbolTable()
        self.optimizer = Optimizer()
        self.current_function = None
        self.loop_stack = []

    def emit(self, instruction):
        self.code.append(instruction)

    def get_code(self):
        return '\n'.join(self.code)

    def generate(self, tree):
        if not isinstance(tree, list):
            print("Erro: AST inválida")
            return

        tree = self.optimizer.optimize(tree)

        for unit in tree:
            if unit[0] == 'program':
                self._collect_declarations(unit[2])
            elif unit[0] == 'function':
                _, var_type, name, args, statements = unit
                self.symbols.declare_function(name, var_type, args)
                self._collect_declarations(statements)

        self.emit("START")

        # Reservar 2 posições temporárias para computação de potências
        self.symbols.declare_var('__POW_BASE__', 'INTEGER')
        self.symbols.declare_var('__POW_EXP__', 'INTEGER')
        self._pow_base_offset = self.symbols.var_offset('__POW_BASE__')
        self._pow_exp_offset = self.symbols.var_offset('__POW_EXP__')

        total = self.symbols.total_allocated
        if total > 0:
            self.emit(f"PUSHN {total}")

        for unit in tree:
            if unit[0] == 'program':
                _, name, statements = unit
                self.current_function = None
                for stmt in statements:
                    self._gen_statement(stmt)
                self.emit("STOP")

            elif unit[0] == 'function':
                _, var_type, name, args, statements = unit
                self.current_function = name
                self.emit(f"func{name}:")
                for stmt in statements:
                    self._gen_statement(stmt)

    def _collect_declarations(self, statements):
        for stmt in statements:
            if stmt[0] == 'decl':
                _, var_type, names = stmt
                for name in names:
                    self.symbols.declare_var(name, var_type)
            elif stmt[0] == 'decl_array':
                _, var_type, name, size = stmt
                self.symbols.declare_array(name, var_type, size)

    def _gen_statement(self, stmt):
        kind = stmt[0]

        if kind == 'decl' or kind == 'decl_array':
            pass

        elif kind == 'assign':
            _, name, expr = stmt
            self._gen_expr(expr)
            offset = self.symbols.var_offset(name)
            self.emit(f"STOREG {offset}")

        elif kind == 'assign_array':
            _, name, index_expr, value_expr = stmt
            arr_info = self.symbols.lookup_array(name)
            offset = arr_info['offset']
            # 1. Endereço base do array
            self.emit("PUSHGP")
            self.emit(f"PUSHI {offset}")
            self.emit("PADD")
            # 2. Índice (Fortran base-1 -> memória base-0)
            self._gen_expr(index_expr)
            self.emit("PUSHI 1")
            self.emit("SUB")
            # 3. Valor a guardar
            self._gen_expr(value_expr)
            # Pilha: [endereço, índice, valor] -> STOREN
            self.emit("STOREN")

        elif kind == 'print':
            _, items = stmt
            for item in items:
                if isinstance(item, tuple) and item[0] == 'string':
                    self.emit(f'PUSHS "{item[1]}"')
                    self.emit("WRITES")
                else:
                    self._gen_expr(item)
                    self.emit("WRITEI")
            self.emit("WRITELN")

        elif kind == 'read':
            _, vars_list = stmt
            for var in vars_list:
                if var[0] == 'var':
                    self.emit("READ")
                    self.emit("ATOI")
                    offset = self.symbols.var_offset(var[1])
                    self.emit(f"STOREG {offset}")
                elif var[0] == 'array_var':
                    name = var[1]
                    index_expr = var[2]
                    arr_info = self.symbols.lookup_array(name)
                    offset = arr_info['offset']
                    self.emit("PUSHGP")
                    self.emit(f"PUSHI {offset}")
                    self.emit("PADD")
                    self._gen_expr(index_expr)
                    self.emit("PUSHI 1")
                    self.emit("SUB")
                    self.emit("READ")
                    self.emit("ATOI")
                    self.emit("STOREN")

        elif kind == 'label':
            _, label_num, inner_stmt = stmt
            if inner_stmt[0] == 'continue' and self.loop_stack:
                info = self.loop_stack.pop()
                step = info['step']
                offset = info['var_offset']
                self.emit(f"PUSHG {offset}")
                if step:
                    self._gen_expr(step)
                else:
                    self.emit("PUSHI 1")
                self.emit("ADD")
                self.emit(f"STOREG {offset}")
                self.emit(f"JUMP {info['loop_label']}")
                self.emit(f"lbl{label_num}end:")
            else:
                self.emit(f"lbl{label_num}:")
                self._gen_statement(inner_stmt)

        elif kind == 'continue':
            pass

        elif kind == 'goto':
            _, label_num = stmt
            self.emit(f"JUMP lbl{label_num}")

        elif kind == 'stop':
            self.emit("STOP")

        elif kind == 'return':
            self.emit("RETURN")

        elif kind == 'if':
            self._gen_if(stmt)

        elif kind == 'do':
            self._gen_do(stmt)

    def _gen_expr(self, expr):
        if not isinstance(expr, tuple):
            return

        kind = expr[0]

        if kind == 'int':
            self.emit(f"PUSHI {expr[1]}")

        elif kind == 'real':
            self.emit(f"PUSHF {expr[1]}")

        elif kind == 'bool':
            self.emit(f"PUSHI {1 if expr[1] else 0}")

        elif kind == 'string':
            self.emit(f'PUSHS "{expr[1]}"')

        elif kind == 'id':
            name = expr[1]
            if self.symbols.var_exists(name):
                self.emit(f"PUSHG {self.symbols.var_offset(name)}")
            elif self.symbols.array_exists(name):
                arr_info = self.symbols.lookup_array(name)
                self.emit(f"PUSHG {arr_info['offset']}")

        elif kind == 'binop':
            _, op, left, right = expr
            if op == '**':
                # Potência: base ** exp via loop com slots temporários
                # 1. Guardar base e expoente nos slots temporários
                self._gen_expr(left)
                self.emit(f"STOREG {self._pow_base_offset}")
                self._gen_expr(right)
                self.emit(f"STOREG {self._pow_exp_offset}")
                # 2. resultado = 1
                self.emit("PUSHI 1")
                # 3. Loop: enquanto exp > 0, resultado *= base, exp--
                loop_lbl = self.symbols.new_label()
                end_lbl = self.symbols.new_label()
                self.emit(f"{loop_lbl}:")
                self.emit(f"PUSHG {self._pow_exp_offset}")
                self.emit("PUSHI 0")
                self.emit("SUP")
                self.emit(f"JZ {end_lbl}")
                # resultado (no topo da stack) *= base
                self.emit(f"PUSHG {self._pow_base_offset}")
                self.emit("MUL")
                # exp--
                self.emit(f"PUSHG {self._pow_exp_offset}")
                self.emit("PUSHI 1")
                self.emit("SUB")
                self.emit(f"STOREG {self._pow_exp_offset}")
                self.emit(f"JUMP {loop_lbl}")
                self.emit(f"{end_lbl}:")
                # O resultado fica no topo da stack
            else:
                self._gen_expr(left)
                self._gen_expr(right)
                ops = {
                    '+': 'ADD', '-': 'SUB',
                    '*': 'MUL', '/': 'DIV',
                }
                self.emit(ops[op])

        elif kind == 'uminus':
            self.emit("PUSHI 0")
            self._gen_expr(expr[1])
            self.emit("SUB")

        elif kind == 'call':
            self._gen_call(expr)

        elif kind == 'cond':
            _, op, left, right = expr
            self._gen_expr(left)
            self._gen_expr(right)
            cond_ops = {
                '.EQ.': 'EQUAL',
                '.NE.': 'EQUAL\nNOT',
                '.LT.': 'INF',
                '.GT.': 'SUP',
                '.LE.': 'INFEQ',
                '.GE.': 'SUPEQ',
            }
            for instr in cond_ops[op].split('\n'):
                self.emit(instr)

        elif kind == 'and':
            self._gen_expr(expr[1])
            self._gen_expr(expr[2])
            self.emit("AND")

        elif kind == 'or':
            self._gen_expr(expr[1])
            self._gen_expr(expr[2])
            self.emit("OR")

        elif kind == 'not':
            self._gen_expr(expr[1])
            self.emit("NOT")

    def _gen_call(self, expr):
        name = expr[1]
        args = expr[2]

        if name == 'MOD':
            self._gen_expr(args[0])
            self._gen_expr(args[1])
            self.emit("MOD")

        elif self.symbols.array_exists(name):
            arr_info = self.symbols.lookup_array(name)
            offset = arr_info['offset']
            self.emit("PUSHGP")
            self.emit(f"PUSHI {offset}")
            self.emit("PADD")
            self._gen_expr(args[0])
            self.emit("PUSHI 1")
            self.emit("SUB")
            self.emit("LOADN")

        else:
            func_info = self.symbols.lookup_function(name)
            for param_name, arg_expr in zip(func_info['params'], args):
                self._gen_expr(arg_expr)
                offset = self.symbols.var_offset(param_name)
                self.emit(f"STOREG {offset}")

            self.emit(f"PUSHA func{name}")
            self.emit("CALL")
            offset = self.symbols.var_offset(name)
            self.emit(f"PUSHG {offset}")

    def _gen_if(self, stmt):
        _, condition, then_block, else_block = stmt
        if else_block:
            else_label = self.symbols.new_label()
            end_label = self.symbols.new_label()
            self._gen_expr(condition)
            self.emit(f"JZ {else_label}")
            for s in then_block:
                self._gen_statement(s)
            self.emit(f"JUMP {end_label}")
            self.emit(f"{else_label}:")
            for s in else_block:
                self._gen_statement(s)
            self.emit(f"{end_label}:")
        else:
            end_label = self.symbols.new_label()
            self._gen_expr(condition)
            self.emit(f"JZ {end_label}")
            for s in then_block:
                self._gen_statement(s)
            self.emit(f"{end_label}:")

    def _gen_do(self, stmt):
        _, label_num, var_name, start, end, step = stmt
        offset = self.symbols.var_offset(var_name)
        loop_label = self.symbols.new_label()

        self._gen_expr(start)
        self.emit(f"STOREG {offset}")

        self.emit(f"{loop_label}:")

        self.emit(f"PUSHG {offset}")
        self._gen_expr(end)
        self.emit("SUP")
        self.emit(f"JZ {loop_label}b")
        self.emit(f"JUMP lbl{label_num}end")
        self.emit(f"{loop_label}b:")

        self.loop_stack.append({
            'var_offset': offset,
            'step': step,
            'loop_label': loop_label,
            'label_num': label_num,
        })
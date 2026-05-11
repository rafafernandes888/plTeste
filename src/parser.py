import sys
import ply.yacc as yacc
from lexer import tokens, preprocess
import lexer as lexer_module


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


start = 'program_units'

def p_program_units_single(p):
    'program_units : program_unit opt_newlines'
    p[0] = [p[1]]

def p_program_units_many(p):
    'program_units : program_units program_unit opt_newlines'
    p[0] = p[1] + [p[2]]

def p_program_unit(p):
    '''program_unit : program
                    | function'''
    p[0] = p[1]

def p_program(p):
    'program : PROGRAM ID NEWLINE block END'
    p[0] = ('program', p[2], p[4])

def p_function(p):
    'function : type_spec FUNCTION ID LPAREN id_list RPAREN NEWLINE block END'
    p[0] = ('function', p[1], p[3], p[5], p[8])

def p_block(p):
    'block : statements opt_newlines'
    p[0] = p[1]


def p_opt_newlines_empty(p):
    'opt_newlines : empty'
    p[0] = None


def p_opt_newlines_some(p):
    'opt_newlines : NEWLINE opt_newlines'
    p[0] = None


def p_statements_empty(p):
    'statements : empty'
    p[0] = []


def p_statements_single(p):
    'statements : statement'
    p[0] = [p[1]]


def p_statements_many(p):
    'statements : statements NEWLINE statement'
    p[0] = p[1] + [p[3]]


def p_statement_simple(p):
    'statement : simple_statement'
    p[0] = p[1]


def p_statement_labelled_simple(p):
    'statement : ICONST simple_statement'
    p[0] = ('label', p[1], p[2])


def p_statement_if(p):
    'statement : if_statement'
    p[0] = p[1]


def p_statement_labelled_if(p):
    'statement : ICONST if_statement'
    p[0] = ('label', p[1], p[2])


def p_simple_statement_print(p):
    'simple_statement : PRINT TIMES COMMA print_list'
    p[0] = ('print', p[4])


def p_simple_statement_read(p):
    'simple_statement : READ TIMES COMMA read_list'
    p[0] = ('read', p[4])


def p_simple_statement_decl(p):
    'simple_statement : type_spec id_list'
    p[0] = ('decl', p[1], p[2])

def p_simple_statement_decl_array(p):
    'simple_statement : type_spec ID LPAREN ICONST RPAREN'

    p[0] = ('decl_array', p[1], p[2], p[4])


def p_simple_statement_assign(p):
    'simple_statement : ID ASSIGN expr'
    p[0] = ('assign', p[1], p[3])

def p_simple_statement_assign_array(p):
    'simple_statement : ID LPAREN expr RPAREN ASSIGN expr'
    p[0] = ('assign_array', p[1], p[3], p[6])


def p_simple_statement_goto(p):
    'simple_statement : GOTO ICONST'
    p[0] = ('goto', p[2])


def p_simple_statement_continue(p):
    'simple_statement : CONTINUE'
    p[0] = ('continue',)


def p_simple_statement_do(p):
    'simple_statement : DO ICONST ID ASSIGN expr COMMA expr'
    p[0] = ('do', p[2], p[3], p[5], p[7], None)


def p_simple_statement_do_step(p):
    'simple_statement : DO ICONST ID ASSIGN expr COMMA expr COMMA expr'
    p[0] = ('do', p[2], p[3], p[5], p[7], p[9])


def p_simple_statement_stop(p):
    'simple_statement : STOP'
    p[0] = ('stop',)


def p_simple_statement_return(p):
    'simple_statement : RETURN'
    p[0] = ('return',)


def p_if_statement(p):
    'if_statement : IF LPAREN condition RPAREN THEN NEWLINE block ENDIF'
    p[0] = ('if', p[3], p[7], None)


def p_if_statement_else(p):
    'if_statement : IF LPAREN condition RPAREN THEN NEWLINE block ELSE NEWLINE block ENDIF'
    p[0] = ('if', p[3], p[7], p[10])


def p_type_spec_integer(p):
    'type_spec : INTEGER'
    p[0] = 'INTEGER'


def p_type_spec_real(p):
    'type_spec : REAL'
    p[0] = 'REAL'


def p_type_spec_logical(p):
    'type_spec : LOGICAL'
    p[0] = 'LOGICAL'


def p_id_list_single(p):
    'id_list : ID'
    p[0] = [p[1]]


def p_id_list_many(p):
    'id_list : id_list COMMA ID'
    p[0] = p[1] + [p[3]]


def p_read_list_single(p):
    'read_list : variable'
    p[0] = [p[1]]


def p_read_list_many(p):
    'read_list : read_list COMMA variable'
    p[0] = p[1] + [p[3]]


def p_variable_id(p):
    'variable : ID'
    p[0] = ('var', p[1])
    

def p_variable_array(p):
    'variable : ID LPAREN expr RPAREN'
    p[0] = ('array_var', p[1], p[3])



def p_print_list_single(p):
    'print_list : print_item'
    p[0] = [p[1]]


def p_print_list_many(p):
    'print_list : print_list COMMA print_item'
    p[0] = p[1] + [p[3]]

def p_arg_list_single(p):
    'arg_list : expr'
    p[0] = [p[1]]

def p_arg_list_many(p):
    'arg_list : arg_list COMMA expr'
    p[0] = p[1] + [p[3]]

def p_print_item_string(p):
    'print_item : SCONST'
    p[0] = ('string', p[1])


def p_print_item_expr(p):
    'print_item : expr'
    p[0] = p[1]


def p_condition_relop(p):
    'condition : expr relop expr'
    p[0] = ('cond', p[2], p[1], p[3])


def p_condition_and(p):
    'condition : condition AND condition'
    p[0] = ('and', p[1], p[3])


def p_condition_or(p):
    'condition : condition OR condition'
    p[0] = ('or', p[1], p[3])


def p_condition_not(p):
    'condition : NOT condition'
    p[0] = ('not', p[2])


def p_condition_group(p):
    'condition : LPAREN condition RPAREN'
    p[0] = p[2]


def p_condition_expr(p):
    'condition : expr'
    p[0] = p[1]


def p_relop_gt(p):
    'relop : GT'
    p[0] = p[1]


def p_relop_lt(p):
    'relop : LT'
    p[0] = p[1]


def p_relop_ge(p):
    'relop : GE'
    p[0] = p[1]


def p_relop_le(p):
    'relop : LE'
    p[0] = p[1]


def p_relop_eq(p):
    'relop : EQ'
    p[0] = p[1]


def p_relop_ne(p):
    'relop : NE'
    p[0] = p[1]


def p_expr_plus(p):
    'expr : expr PLUS term'
    p[0] = ('binop', '+', p[1], p[3])


def p_expr_minus(p):
    'expr : expr MINUS term'
    p[0] = ('binop', '-', p[1], p[3])


def p_expr_term(p):
    'expr : term'
    p[0] = p[1]


def p_term_times(p):
    'term : term TIMES power'
    p[0] = ('binop', '*', p[1], p[3])


def p_term_divide(p):
    'term : term DIVIDE power'
    p[0] = ('binop', '/', p[1], p[3])


def p_term_power(p):
    'term : power'
    p[0] = p[1]


def p_power_exp(p):
    'power : factor POWER power'
    p[0] = ('binop', '**', p[1], p[3])


def p_power_factor(p):
    'power : factor'
    p[0] = p[1]


def p_factor_id(p):
    'factor : ID'
    p[0] = ('id', p[1])

def p_factor_call(p):
    'factor : ID LPAREN arg_list RPAREN'
    p[0] = ('call', p[1], p[3])


def p_factor_int(p):
    'factor : ICONST'
    p[0] = ('int', p[1])


def p_factor_real(p):
    'factor : RCONST'
    p[0] = ('real', p[1])


def p_factor_true(p):
    'factor : LTRUE'
    p[0] = ('bool', True)


def p_factor_false(p):
    'factor : LFALSE'
    p[0] = ('bool', False)


def p_factor_group(p):
    'factor : LPAREN expr RPAREN'
    p[0] = p[2]


def p_factor_uminus(p):
    'factor : MINUS factor %prec UMINUS'
    p[0] = ('uminus', p[2])


def p_empty(p):
    'empty :'
    pass


def p_error(p):
    if p:
        print(f"Erro sintático no token {p.type} ({p.value}) na linha {p.lineno}")
    else:
        print("Erro sintático: fim inesperado do ficheiro")


parser = yacc.yacc()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python src/parser.py <ficheiro.f>")
        sys.exit(1)

    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        source = f.read()

    source = preprocess(source)

    lex = lexer_module.lex.lex(module=lexer_module)
    result = parser.parse(source, lexer=lex)

    print(result)
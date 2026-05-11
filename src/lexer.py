import ply.lex as lex
import sys

# Palavras reservadas do Fortran 77
# Dicionários: 'PALAVRA' -> 'NOME_DO_TOKEN'

reserved = {
    'PROGRAM':    'PROGRAM',
    'END':        'END',
    'INTEGER':    'INTEGER',
    'REAL':       'REAL',
    'LOGICAL':    'LOGICAL',
    'IF':         'IF',
    'THEN':       'THEN',
    'ELSE':       'ELSE',
    'ENDIF':      'ENDIF',
    'DO':         'DO',
    'CONTINUE':   'CONTINUE',
    'GOTO':       'GOTO',
    'PRINT':      'PRINT',
    'READ':       'READ',
    'STOP':       'STOP',
    'RETURN':     'RETURN',
    'CALL':       'CALL',
    'FUNCTION':   'FUNCTION',
    'SUBROUTINE': 'SUBROUTINE',
}

tokens = [
    #Literais
    'ICONST',     # inteiro: 42
    'RCONST',     # real: 3.14
    'SCONST',     # string: 'hello'

    #Identificador
    'ID',

    #Operadores aritméticos
    'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'POWER',

    #Operadores relacionais
    'EQ', 'NE', 'LT', 'GT', 'LE', 'GE',

    #Operadores lógicos
    'AND', 'OR', 'NOT', 'LTRUE', 'LFALSE',

    #Delimitadores
    'LPAREN', 'RPAREN', 'COMMA', 'ASSIGN',

    #Separador de statements
    'NEWLINE',
] + list(reserved.values())

t_PLUS = r'\+'
t_MINUS = r'-'
t_DIVIDE = r'/'
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_COMMA = r','
t_ASSIGN = r'='

def t_POWER(t):
    r'\*\*'
    return t

def t_TIMES(t):
    r'\*'
    return t

# Relacionais: .EQ. .NE. .LT. .GT. .LE. .GE.
def t_EQ(t):
    r'\.[Ee][Qq]\.'
    return t

def t_NE(t):
    r'\.[Nn][Ee]\.'
    return t

def t_LE(t):
    r'\.[Ll][Ee]\.'
    return t

def t_GE(t):
    r'\.[Gg][Ee]\.'
    return t

def t_LT(t):
    r'\.[Ll][Tt]\.'
    return t

def t_GT(t):
    r'\.[Gg][Tt]\.'
    return t

# Lógicos: .AND. .OR. .NOT. .TRUE. .FALSE.
def t_AND(t):
    r'\.[Aa][Nn][Dd]\.'
    return t

def t_OR(t):
    r'\.[Oo][Rr]\.'
    return t

def t_NOT(t):
    r'\.[Nn][Oo][Tt]\.'
    return t

def t_LTRUE(t):
    r'\.[Tt][Rr][Uu][Ee]\.'
    return t

def t_LFALSE(t):
    r'\.[Ff][Aa][Ll][Ss][Ee]\.'
    return t


def t_RCONST(t):
    r'\d+\.\d*|\d*\.\d+'
    t.value = float(t.value)
    return t

def t_ICONST(t):
    r'\d+'
    t.value = int(t.value)
    return t

def t_SCONST(t):
    r"'[^']*'"
    t.value = t.value[1:-1]  # remove as aspas
    return t

def t_ID(t):
    r'[A-Za-z_][A-Za-z0-9_]*'
    upper = t.value.upper()       # Fortran é case-insensitive
    t.type = reserved.get(upper, 'ID')  # keyword ou ID?
    t.value = upper
    return t

def t_COMMENT(t):
    r'!.*'
    pass  # Ignorar comentários inline

def t_NEWLINE(t):
    r'\n+'
    t.lexer.lineno += len(t.value)
    return t

# Ignorar espaços e tabs
t_ignore = ' \t\r'

def t_error(t):
    print(f"Erro léxico: caractere ilegal '{t.value[0]}' na linha {t.lexer.lineno}")
    t.lexer.skip(1)

def preprocess(source):
    """Remove comentários Fortran 77 (linhas que começam com C, c ou *)"""
    lines = source.split('\n')
    result = []
    for line in lines:
        if line.startswith('*') or line.startswith('C ') or line.startswith('c '):
            result.append('')  # substituir por linha vazia
        else:
            result.append(line)
    return '\n'.join(result)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python lexer.py <ficheiro.f>")
        sys.exit(1)

    with open(sys.argv[1], 'r') as f:
        source = f.read()

    source = preprocess(source)
    lexer = lex.lex()
    lexer.input(source)

    for tok in lexer:
        print(tok)


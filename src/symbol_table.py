"""
Tabela de Símbolos do Compilador Fortran 77.

Gere o registo de variáveis, arrays e funções, incluindo:
- Tipos (INTEGER, REAL, LOGICAL)
- Offsets de memória para geração de código
- Labels únicos para controlo de fluxo
- Verificação de declarações duplicadas

Inspirada no padrão ensinado nas aulas de Processamento de Linguagens.
"""


class SemanticError(Exception):
    """Exceção levantada para erros semânticos."""
    pass


class SymbolTable:
    """Tabela de símbolos com suporte a variáveis, arrays e funções."""

    def __init__(self):
        self._variables = {}    # nome -> {'type': str, 'offset': int}
        self._arrays = {}       # nome -> {'type': str, 'offset': int, 'size': int}
        self._functions = {}    # nome -> {'type': str, 'params': [str]}
        self._labels = {}       # label_num -> statement associado
        self._next_offset = 0
        self._label_counter = 0

    def __repr__(self):
        return (
            f"SymbolTable(\n"
            f"  variables={self._variables},\n"
            f"  arrays={self._arrays},\n"
            f"  functions={self._functions}\n"
            f")"
        )

    # ─────────────────────────────────────────────
    # Propriedades
    # ─────────────────────────────────────────────
    @property
    def total_allocated(self):
        """Número total de posições de memória alocadas."""
        return self._next_offset

    # ─────────────────────────────────────────────
    # Variáveis
    # ─────────────────────────────────────────────
    def declare_var(self, name, var_type='INTEGER'):
        """Declara uma variável com tipo e atribui um offset de memória."""
        if name not in self._variables:
            self._variables[name] = {
                'type': var_type,
                'offset': self._next_offset,
            }
            self._next_offset += 1
        else:
            # Atualizar tipo (ex: parâmetro que depois é declarado com tipo)
            self._variables[name]['type'] = var_type

    def lookup_var(self, name):
        """Consulta uma variável. Retorna dict com 'type' e 'offset', ou None."""
        return self._variables.get(name)

    def var_exists(self, name):
        """Verifica se a variável existe."""
        return name in self._variables

    def var_type(self, name):
        """Retorna o tipo da variável, ou None se não existir."""
        info = self._variables.get(name)
        return info['type'] if info else None

    def var_offset(self, name):
        """Retorna o offset de memória da variável."""
        info = self._variables.get(name)
        return info['offset'] if info else None

    # ─────────────────────────────────────────────
    # Arrays
    # ─────────────────────────────────────────────
    def declare_array(self, name, arr_type, size):
        """Declara um array com tipo e tamanho, alocando posições contíguas."""
        if name in self._arrays:
            raise SemanticError(f"Array já declarado: {name}")
        self._arrays[name] = {
            'type': arr_type,
            'offset': self._next_offset,
            'size': size,
        }
        # Registar também como variável (para type checking)
        self._variables[name] = {
            'type': arr_type,
            'offset': self._next_offset,
        }
        self._next_offset += size

    def lookup_array(self, name):
        """Consulta um array. Retorna dict com 'type', 'offset', 'size'."""
        return self._arrays.get(name)

    def array_exists(self, name):
        """Verifica se o array existe."""
        return name in self._arrays

    # ─────────────────────────────────────────────
    # Funções
    # ─────────────────────────────────────────────
    def declare_function(self, name, ret_type, params):
        """Declara uma função com tipo de retorno e lista de parâmetros."""
        self._functions[name] = {
            'type': ret_type,
            'params': params,
        }
        # A função tem uma variável com o seu nome (para o RETURN)
        self.declare_var(name, ret_type)
        # Declarar os parâmetros como variáveis
        for param in params:
            self.declare_var(param, 'INTEGER')  # Tipo será atualizado na declaração

    def lookup_function(self, name):
        """Consulta uma função. Retorna dict com 'type' e 'params'."""
        return self._functions.get(name)

    def function_exists(self, name):
        """Verifica se a função existe."""
        return name in self._functions

    # ─────────────────────────────────────────────
    # Labels
    # ─────────────────────────────────────────────
    def new_label(self):
        """Gera um identificador de label único (L0, L1, L2, ...)."""
        label = f"L{self._label_counter}"
        self._label_counter += 1
        return label

    def register_label(self, label_num, stmt):
        """Associa um número de label a um statement."""
        self._labels[label_num] = stmt

    def lookup_label(self, label_num):
        """Consulta o statement associado a um label."""
        return self._labels.get(label_num)

    def label_exists(self, label_num):
        """Verifica se o label existe."""
        return label_num in self._labels

    def clear_labels(self):
        """Limpa os labels (usado entre unidades de programa)."""
        self._labels = {}

    # ─────────────────────────────────────────────
    # Utilitários
    # ─────────────────────────────────────────────
    def all_variables(self):
        """Retorna todos os nomes de variáveis declaradas."""
        return list(self._variables.keys())

    def all_arrays(self):
        """Retorna todos os nomes de arrays declarados."""
        return list(self._arrays.keys())

    def all_functions(self):
        """Retorna todos os nomes de funções declaradas."""
        return list(self._functions.keys())

#!/usr/bin/env python3
import sys
import os
import argparse
import subprocess
from dataclasses import dataclass
from typing import List, Dict, Optional

# --- Token and AST Definitions ---
@dataclass
class Token:
    type: str
    value: str
    
    def __repr__(self):
        return f"Token({self.type}, '{self.value}')"

@dataclass
class Node:
    pass

@dataclass
class Module(Node):
    name: str
    imports: List[str]
    functions: List['Function']

@dataclass
class Function(Node):
    name: str
    params: List[tuple]
    returns: str
    body: List[Node]

@dataclass
class Call(Node):
    func: str
    args: List[Node]

@dataclass
class StringLiteral(Node):
    value: str

@dataclass
class Return(Node):
    value: Node

# --- Lexer ---
class Lexer:
    KEYWORDS = {'module', 'import', 'func', 'return'}
    
    def __init__(self, source):
        self.source = source
        self.pos = 0
        self.current_char = self.source[self.pos] if self.source else None
    
    def advance(self):
        self.pos += 1
        if self.pos < len(self.source):
            self.current_char = self.source[self.pos]
        else:
            self.current_char = None
    
    def skip_whitespace(self):
        while self.current_char is not None and self.current_char.isspace():
            self.advance()
    
    def get_identifier(self):
        result = ''
        while self.current_char is not None and (self.current_char.isalnum() or self.current_char == '_'):
            result += self.current_char
            self.advance()
        return result
    
    def get_string(self):
        result = ''
        self.advance()  # Skip opening quote
        while self.current_char is not None and self.current_char != '"':
            result += self.current_char
            self.advance()
        self.advance()  # Skip closing quote
        return f'"{result}"'
    
    def get_next_token(self):
        while self.current_char is not None:
            if self.current_char.isspace():
                self.skip_whitespace()
                continue
            
            if self.current_char == '/' and self.pos + 1 < len(self.source) and self.source[self.pos+1] == '/':
                while self.current_char is not None and self.current_char != '\n':
                    self.advance()
                continue
            
            if self.current_char.isalpha() or self.current_char == '_':
                ident = self.get_identifier()
                if ident in self.KEYWORDS:
                    return Token(ident.upper(), ident)
                return Token('IDENT', ident)
            
            if self.current_char == '"':
                return Token('STRING', self.get_string())
            
            if self.current_char in {';', '{', '}', '(', ')', ',', '.', ':'}:
                char = self.current_char
                self.advance()
                return Token(char, char)
            
            self.advance()
        
        return Token('EOF', '')

# --- Parser ---
class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.current_token = self.tokens[self.pos] if self.tokens else Token('EOF', '')
    
    def advance(self):
        self.pos += 1
        if self.pos < len(self.tokens):
            self.current_token = self.tokens[self.pos]
        else:
            self.current_token = Token('EOF', '')
    
    def expect(self, expected_type):
        if (self.current_token.type == expected_type or 
            self.current_token.value == expected_type):
            token = self.current_token
            self.advance()
            return token
        raise SyntaxError(f"Expected {expected_type}, got {self.current_token}")
    
    def parse(self):
        return self.parse_module()
    
    def parse_module(self):
        self.expect('module')
        name = self.expect('IDENT').value
        self.expect(';')
        
        imports = []
        while self.current_token.value == 'import':
            imports.append(self.parse_import())
        
        functions = []
        while self.current_token.value == 'func':
            functions.append(self.parse_function())
        
        return Module(name, imports, functions)
    
    def parse_import(self):
        self.expect('import')
        path = []
        path.append(self.expect('IDENT').value)
        
        while self.current_token.value == '.':
            self.expect('.')
            path.append(self.expect('IDENT').value)
        
        self.expect(';')
        return '.'.join(path)
    
    def parse_function(self):
        self.expect('func')
        name = self.expect('IDENT').value
        self.expect('(')
        
        params = []
        while self.current_token.value != ')':
            param_name = self.expect('IDENT').value
            self.expect(':')
            param_type = self.expect('IDENT').value
            params.append((param_name, param_type))
            if self.current_token.value == ',':
                self.expect(',')
        
        self.expect(')')
        
        returns = 'void'
        if self.current_token.value == '->':
            self.expect('->')
            returns = self.expect('IDENT').value
        
        self.expect('{')
        body = []
        while self.current_token.value != '}':
            body.append(self.parse_statement())
        self.expect('}')
        
        return Function(name, params, returns, body)
    
    def parse_statement(self):
        if self.current_token.value == 'return':
            return self.parse_return()
        elif self.current_token.type == 'IDENT' and self.peek().value == '(':
            return self.parse_call()
        else:
            raise SyntaxError(f"Unexpected token: {self.current_token}")
    
    def peek(self):
        if self.pos + 1 < len(self.tokens):
            return self.tokens[self.pos + 1]
        return Token('EOF', '')
    
    def parse_call(self):
        func = self.expect('IDENT').value
        self.expect('(')
        args = []
        while self.current_token.value != ')':
            args.append(self.parse_expression())
            if self.current_token.value == ',':
                self.expect(',')
        self.expect(')')
        self.expect(';')
        return Call(func, args)
    
    def parse_expression(self):
        if self.current_token.type == 'STRING':
            return StringLiteral(self.expect('STRING').value)
        else:
            raise NotImplementedError("Complex expressions not implemented yet")
    
    def parse_return(self):
        self.expect('return')
        expr = self.parse_expression()
        self.expect(';')
        return Return(expr)

# --- Code Generator ---
class CodeGenerator:
    def __init__(self):
        self.output = []
        self.indent = 0
    
    def generate(self, module):
        self.emit('#include <stdio.h>')
        self.emit('#include <stdlib.h>')
        self.emit('')
        
        # Generate forward declarations for imports
        for imp in module.imports:
            if imp == 'std.io':
                self.emit('void std_io_print(const char* msg);')
        
        self.emit('')
        
        for func in module.functions:
            self.generate_function(func)
    
    def generate_function(self, func):
        type_map = {
            'int': 'int',
            'void': 'void',
            'word': 'size_t',
            'ptr': 'void*'
        }
        
        return_type = type_map.get(func.returns, 'int')
        params = []
        for name, typ in func.params:
            c_type = type_map.get(typ, 'int')
            params.append(f"{c_type} {name}")
        
        self.emit(f"{return_type} {func.name}({', '.join(params)}) {{")
        self.indent += 1
        
        for stmt in func.body:
            self.generate_statement(stmt)
        
        self.indent -= 1
        self.emit('}')
        self.emit('')
    
    def generate_statement(self, stmt):
        if isinstance(stmt, Call):
            self.generate_call(stmt)
        elif isinstance(stmt, Return):
            self.generate_return(stmt)
    
    def generate_call(self, call):
        if call.func == 'print':
            self.emit(f'printf({call.args[0].value});')
        else:
            args = ', '.join(arg.value for arg in call.args)
            self.emit(f'{call.func}({args});')
    
    def generate_return(self, ret):
        if isinstance(ret.value, StringLiteral):
            self.emit(f'return {ret.value.value};')
        else:
            self.emit(f'return {ret.value};')
    
    def emit(self, line):
        self.output.append('    ' * self.indent + line)
    
    def get_code(self):
        return '\n'.join(self.output)

# --- Compiler Driver ---
class RereCompiler:
    def __init__(self):
        self.verbose = False
    
    def compile_to_executable(self, source_file, output_file=None):
        if not output_file:
            output_file = 'a.out'
        
        # Step 1: Compile to C
        c_file = source_file.replace('.rere', '.c')
        self.compile_to_c(source_file, c_file)
        
        # Step 2: Compile C to executable
        runtime_obj = 'build/rere_runtime.o'
        cmd = [
            'gcc', 
            '-Wall', 
            '-Wextra', 
            '-std=c11',
            c_file,
            runtime_obj,
            '-o', 
            output_file
        ]
        
        if self.verbose:
            print('Executing:', ' '.join(cmd))
        
        result = subprocess.run(cmd)
        if result.returncode != 0:
            raise RuntimeError("Compilation to executable failed")
        
        print(f"Successfully compiled to {output_file}")
    
    def compile_to_c(self, source_file, output_file):
        with open(source_file, 'r') as f:
            source = f.read()
        
        lexer = Lexer(source)
        tokens = []
        while True:
            token = lexer.get_next_token()
            if token.type == 'EOF':
                break
            tokens.append(token)
        
        if self.verbose:
            print("Tokens:", tokens)
        
        parser = Parser(tokens)
        ast = parser.parse()
        
        if self.verbose:
            print("AST:", ast)
        
        gen = CodeGenerator()
        gen.generate(ast)
        c_code = gen.get_code()
        
        with open(output_file, 'w') as f:
            f.write(c_code)
        
        if self.verbose:
            print(f"Generated C code saved to {output_file}")

# --- Main ---
def main():
    parser = argparse.ArgumentParser(description='Rerechan02 Compiler')
    parser.add_argument('input', help='Input .rere file')
    parser.add_argument('-o', '--output', help='Output executable (default: a.out)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    args = parser.parse_args()
    
    compiler = RereCompiler()
    compiler.verbose = args.verbose
    
    try:
        compiler.compile_to_executable(args.input, args.output)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()

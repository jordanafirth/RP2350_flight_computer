"""Small S-expression reader/writer for inspecting generated KiCad artifacts."""
import json
import re

class Quoted(str):
    pass

def loads(text):
    token = re.compile(r'\s*(\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+)')
    stack = []
    root = None
    for match in token.finditer(text):
        value = match.group(1)
        if value == '(':
            node = []
            if stack:
                stack[-1].append(node)
            else:
                if root is not None:
                    raise ValueError('Multiple root expressions')
                root = node
            stack.append(node)
        elif value == ')':
            if not stack:
                raise ValueError('Unbalanced close parenthesis')
            stack.pop()
        else:
            if not stack:
                raise ValueError('Atom outside root')
            stack[-1].append(Quoted(json.loads(value)) if value.startswith('"') else value)
    if stack:
        raise ValueError('Unclosed expression')
    return root

def dumps(node, level=0):
    if isinstance(node, Quoted):
        return json.dumps(str(node), ensure_ascii=False)
    if not isinstance(node, list):
        return str(node)
    if not any(isinstance(child, list) for child in node):
        return '('+' '.join(dumps(child, level+1) for child in node)+')'
    result = '('+dumps(node[0], level+1)
    for child in node[1:]:
        result += ('\n'+'  '*(level+1) if isinstance(child, list) else ' ')+dumps(child, level+1)
    return result+')'

def children(node, name):
    return [child for child in node if isinstance(child, list) and child and child[0] == name]

def first(node, name):
    return next(iter(children(node, name)), None)

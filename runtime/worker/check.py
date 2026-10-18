"""Fixed clamp-v1 checker: interpret a small pure expression, never import edits."""
import ast
import json
import math
import os
from pathlib import Path


def check_source(source):
    if len(source)>8192:raise ValueError('invalid_fixture')
    tree=ast.parse(source)
    if len(list(ast.walk(tree)))>128 or len(tree.body)!=1:raise ValueError('invalid_fixture')
    fn=tree.body[0]
    if not isinstance(fn,ast.FunctionDef):raise ValueError('invalid_fixture')
    args=fn.args
    if (fn.name!='clamp' or fn.decorator_list or fn.returns or len(fn.body)!=1
        or not isinstance(fn.body[0],ast.Return) or args.posonlyargs or args.kwonlyargs
        or args.vararg or args.kwarg or args.defaults or args.kw_defaults
        or [a.arg for a in args.args]!=['value','low','high']
        or any(a.annotation for a in args.args)):
        raise ValueError('invalid_fixture')
    expression=fn.body[0].value
    # Validate every branch before evaluating any test case.
    allowed=(ast.Name,ast.Load,ast.Constant,ast.Call,ast.IfExp,ast.Compare,
             ast.Lt,ast.LtE,ast.Gt,ast.GtE,ast.Eq,ast.NotEq,ast.UnaryOp,ast.USub,ast.UAdd)
    for node in ast.walk(expression):
        if not isinstance(node,allowed):raise ValueError('invalid_fixture')
        if isinstance(node,ast.Name) and node.id not in ('value','low','high','min','max'):
            raise ValueError('invalid_fixture')
        if isinstance(node,ast.Constant) and (type(node.value) not in (int,float)
                or not -1e6<=node.value<=1e6 or not math.isfinite(node.value)):
            raise ValueError('invalid_fixture')
        if isinstance(node,ast.Call) and (not isinstance(node.func,ast.Name)
                or node.func.id not in ('min','max') or len(node.args)!=2 or node.keywords):
            raise ValueError('invalid_fixture')
    def evaluate(node,values):
        if isinstance(node,ast.Constant):return node.value
        if isinstance(node,ast.Name):return values[node.id]
        if isinstance(node,ast.Call):
            return (min if node.func.id=='min' else max)(*(evaluate(a,values) for a in node.args))
        if isinstance(node,ast.IfExp):
            return evaluate(node.body if evaluate(node.test,values) else node.orelse,values)
        if isinstance(node,ast.UnaryOp):
            return (-1 if isinstance(node.op,ast.USub) else 1)*evaluate(node.operand,values)
        if isinstance(node,ast.Compare):
            left=evaluate(node.left,values)
            for op,right in zip(node.ops,node.comparators):
                right=evaluate(right,values)
                matches={ast.Lt:left<right,ast.LtE:left<=right,ast.Gt:left>right,
                         ast.GtE:left>=right,ast.Eq:left==right,ast.NotEq:left!=right}
                if not matches[type(op)]:return False
                left=right
            return True
        raise ValueError('invalid_fixture')
    for value,expected in ((-1,0),(4,4),(20,10)):
        if evaluate(expression,dict(value=value,low=0,high=10))!=expected:
            raise ValueError('fixture_test_failed')
    return dict(cases=3,exit_code=0)


if __name__=='__main__':
    if os.getuid()!=2000:raise ValueError('invalid_checker_uid')
    with Path('/snapshot/clamp.py').open('rb') as stream:
        result=check_source(stream.read(8193))
    print(json.dumps(result))

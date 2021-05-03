import os
import jsbeautifier

# region Templates

_template = """window.{namespace} = Object.assign({{}}, window.{namespace}, {{
    {content}
}});"""
_ns_template = """{namespace}: {{  
        {content}
    }}"""
_func_template = """{name}: {function}"""


# endregion

class Namespace:
    def __init__(self, *args):
        self.args = list(args)
        self.f_map = {}

    def __call__(self, var):
        all_args = self.args + [var]
        return variable(*all_args)

    def add(self, src, name=None):
        name = f"function{len(self.f_map)}" if name is None else name
        self.f_map[name] = src
        return name

    def dump(self, assets_folder="assets"):
        os.makedirs(assets_folder, exist_ok=True)
        content = "\n".join([_func_template.format(name=name, function=self.f_map[name]) for name in self.f_map])
        for ns in reversed(self.args[1:]):
            content = _ns_template.format(namespace=ns, content=content)
        content = _template.format(namespace=self.args[0], content=content)
        with open(os.path.join(assets_folder, "{}.js".format("_".join(self.args))), 'w') as f:
            f.write(jsbeautifier.beautify(content))


def assign(src, name=None):
    name = _default_name_space.add(src, name)
    _default_name_space.dump()
    return _default_name_space(name)


def arrow_function(value):
    return dict(arrow=value)


def variable(*args):
    return dict(variable=".".join(list(args)))


_default_name_space = Namespace("dashExtensions", "default")

class Namespace:
    def __init__(self, *args):
        self.args = list(args)

    def __call__(self, var):
        all_args = self.args + [var]
        return variable(*all_args)


def arrow_function(value):
    return dict(arrow=value)


def variable(*args):
    return dict(variable=".".join(list(args)))
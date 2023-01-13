"""
bento_meta.util.cypher.functions

Representations of Cypher functions
"""
from string import Template

# cypher functions


class Func(object):
    template = Template("func(${slot1})")
    joiner = ','
    As = ""

    @staticmethod
    def context(arg):
        return _return(arg)

    def __init__(self, arg):
        self.arg = arg

    def __str__(self):
        slot = ""
        if type(self.arg) == list:
            slot = self.joiner.join([self.context(a) for a in self.arg])
        else:
            slot = self.context(self.arg)
        if self.As:
            return self.template.substitute(slot1=slot)+" as "+self.As
        else:
            return self.template.substitute(slot1=slot)


class count(Func):
    template = Template("count($slot1)")


class exists(Func):
    template = Template("exists($slot1)")

class labels(Func):
    template = Template("labels($slot1)")


class Not(Func):
    template = Template("NOT $slot1")

    @staticmethod
    def context(arg):
        return _condition(arg)


class And(Func):
    template = Template("$slot1")
    joiner = " AND "

    @staticmethod
    def context(arg):
        return _condition(arg)

    def __init__(self, *args):
        self.arg = list(args)
        super().__init__(self.arg)


class Or(Func):
    template = Template("$slot1")
    joiner = " OR "

    @staticmethod
    def context(arg):
        return _condition(arg)

    def __init__(self, *args):
        self.arg = list(args)
        super().__init__(self.arg)


class group(Func):
    template = Template("($slot1)")
    joiner = " "


class is_null(Func):
    template = Template("$slot1 IS NULL")


class is_not_null(Func):
    template = Template("$slot1 IS NOT NULL")

# rendering contexts


def _pattern(ent):
    if isinstance(ent, (str, Func)):
        return str(ent)
    return ent.pattern()


def _condition(ent):
    if isinstance(ent, (str, Func)):
        return str(ent)
    return ent.condition()


def _return(ent):
    if isinstance(ent, (str, Func)):
        return str(ent)
    return ent.Return()

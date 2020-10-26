import re
import sys
sys.path.extend(['.','..'])
import pytest
#from pdb import set_trace
from bento_meta.mdf import MDF
from bento_meta.diff import Diff
#from bento_meta.entity import ArgError
from bento_meta.model import Model
from bento_meta.objects import Node, Property, Edge, Term, ValueSet, Concept, Origin


# compare sets of terms
# a_att.terms
#   {'FFPE': <bento_meta.objects.Term object at 0x10..>, 'Snap Frozen': <bento_meta.objects.Term object at 0x10..>}    # set(a_att.terms)
#   {'Snap Frozen', 'FFPE'}

diff = Diff()
term_a = Term({"value":"Merida"})
term_b = Term({"value":"Cumana"})
term_c = Term({"value":"Maracaibo"})
term_d = Term({"value":"Ciudad Bolivar"})
term_e = Term({"value":"Barcelona"})
term_f = Term({"value":"Barquisimeto"})


def test_valuesets_are_different__a():
    '''test using sets as input'''

    vs_1 = ValueSet({"_id":"1"})
    vs_2 = ValueSet({"_id":"2"})

    vs_1.terms['Merida'] = term_a
    vs_1.terms['Cumana'] = term_b
    vs_1.terms['Maracaibo'] = term_c
    vs_1.terms['Ciudad Bolivar'] = term_d

    vs_2.terms['Merida'] = term_a
    vs_2.terms['Cumana'] = term_b
    vs_2.terms['Maracaibo'] = term_c
    vs_2.terms['Ciudad Bolivar'] = term_d

    actual = diff.valuesets_are_different(vs_1, vs_2)
    expected = False
    assert actual == expected


def test_valuesets_are_different__b():
    '''test using sets as input'''

    vs_1 = ValueSet({"_id":"1"})
    vs_2 = ValueSet({"_id":"2"})

    vs_1.terms['Merida'] = term_a
    vs_1.terms['Cumana'] = term_b
    vs_1.terms['Maracaibo'] = term_c
    vs_1.terms['Ciudad Bolivar'] = term_d

    vs_2.terms['Merida'] = term_a
    vs_2.terms['Cumana'] = term_b
    vs_2.terms['Maracaibo'] = term_c

    actual = diff.valuesets_are_different(vs_1, vs_2)
    expected = True
    assert actual == expected


def test_valuesets_are_different__c():
    '''test using sets as input'''

    vs_1 = ValueSet({"_id":"1"})
    vs_2 = ValueSet({"_id":"2"})

    vs_1.terms['Merida'] = term_a
    vs_1.terms['Cumana'] = term_b
    vs_1.terms['Maracaibo'] = term_c
    vs_1.terms['Ciudad Bolivar'] = term_d

    vs_2.terms['Merida'] = term_a
    vs_2.terms['Cumana'] = term_b
    vs_2.terms['Maracaibo'] = term_c
    vs_2.terms['Ciudad Bolivar'] = term_d
    vs_2.terms['Barcelona'] = term_e

    actual = diff.valuesets_are_different(vs_1, vs_2)
    expected = True
    assert actual == expected

def test_valuesets_are_different__d():
    '''test using sets as input'''

    vs_1 = ValueSet({"_id":"1"})
    vs_2 = ValueSet({"_id":"2"})

    actual = diff.valuesets_are_different(vs_1, vs_2)
    expected = False
    assert actual == expected


def test_valuesets_are_different__e():
    '''test using sets as input'''

    vs_1 = ValueSet({"_id":"1"})

    vs_1.terms['Merida'] = term_a
    vs_1.terms['Cumana'] = term_b
    vs_1.terms['Maracaibo'] = term_c
    vs_1.terms['Ciudad Bolivar'] = term_d

    actual = diff.valuesets_are_different(vs_1, vs_1)
    expected = False
    assert actual == expected


def test_valuesets_are_different__f():
    '''test using sets as input'''
    p_1 = Property({"handle":"States"})
    p_2 = Property({"handle":"Estados"})
    vs_1 = ValueSet({"_id":"1"})
    vs_2 = ValueSet({"_id":"2"})

    term_a = Term({"value":"Merida"})
    term_b = Term({"value":"Cumana"})
    term_c = Term({"value":"Maracaibo"})
    term_d = Term({"value":"Ciudad Bolivar"})
    term_e = Term({"value":"Barcelona"})
    term_f = Term({"value":"Barquisimeto"})

    vs_1.terms['Merida'] = term_a
    vs_1.terms['Cumana'] = term_b
    vs_1.terms['Maracaibo'] = term_c
    vs_1.terms['Ciudad Bolivar'] = term_d

    vs_2.terms['Merida'] = term_a
    vs_2.terms['Cumana'] = term_b
    vs_2.terms['Maracaibo'] = term_c
    vs_2.terms['Ciudad Bolivar'] = term_d

    p_1.value_set = vs_1
    p_2.value_set = vs_2

    actual = diff.valuesets_are_different(p_1.value_set, p_2.value_set)
    expected = False
    assert actual == expected



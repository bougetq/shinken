#!/usr/bin/python
# -*- coding: utf-8 -*-

# author:
#   Quentin Bouget, quentin.bouget.ocre@cea.fr
#
# This file is part of Shinken

"""
Module to parse shinken configuration files according to
ClusterShell.NodeSet syntax

In this documentation a macro-function designate a macro that takes
arguments. Its syntax is:
    \\$[^($]*\\(ARGS\\)\\$
"""

from ClusterShell.NodeSet import NodeSet

import re

EXPAND_MACRO_NAME = 'EXPAND'

def process(obj):
    """
    Main function of the module, returns a list of processed objects

    Expands every property according to ClusterShell.NodeSet syntax
    """

    for prop in obj:
        for i in range(0, len(obj[prop])):
            obj[prop][i] = expand(obj[prop][i])

            # Shinken is not a great fan of empty values
            if is_empty(obj[prop][i]):
                del obj[prop][i]

    # Main debug
    #print obj
    return obj

def is_empty(value):
    """Check wether or not value is only whitespaces (empty)"""
    return re.match(r'^\s*$', value)

def find_macro_func(macro_name, value):
    """Parser that finds the first occurence of the macro-function
    named macro_name and returns some informations about it
    """
    val = value
    start = 0
    while val.find(macro_name) > 0:
        mobj = re.search(macro_name, val)
        if val[mobj.start(0) - 1] == '$' and val[mobj.end(0)] == '(':
            opened_parens = 1
            args = ''
            for i in range(mobj.end(0)+1, len(val)):
                char = val[i]
                if char == '(':
                    opened_parens += 1
                elif char == ')':
                    opened_parens -= 1
                    if opened_parens == 0:
                        break
                args += char
            end = i + 1
            if opened_parens == 0 and val[end] == '$':
                return {'start': start + mobj.start(0) - 1,
                        'end': start + end,
                        'args': args}

        start += mobj.end(0)+1
        val = value[start:]
    return None

def expand(value):
    """
    Expands every macro-function named EXPAND_MACRO_NAME by the
    expanded version of its arguments
    """

    start = 0
    val = ''
    macro = find_macro_func(EXPAND_MACRO_NAME, value)
    while macro:
        # Found a macro like the one we are looking for

        # Append what is before it in value
        val += value[start:start + macro['start']]

        # Append the processed args
        val += expand_nodeset(macro['args'])

        # Move forward in value
        start += macro['end']+1
        macro = find_macro_func(EXPAND_MACRO_NAME, value[start:])

    # Append what is left of value
    val += value[start:]

    return val

def split_preserve(value, sep=","):
    """
    Split value on sep if sep is not inside brackets or parentheses

    Sep must be a single char
    """
    val_lst = ['']
    opened_bracket = 0
    opened_parens = 0
    for char in value:
        if char == '[':
            opened_bracket += 1
        elif char == ']':
            opened_bracket -= 1
        if char == '(':
            opened_parens += 1
        if char == ')':
            opened_parens -= 1
        elif char == sep:
            if not opened_bracket and not opened_parens:
                val_lst += ['']
                continue
        val_lst[-1] += char

    return val_lst

def expand_nodeset(value, sep=','):
    """Expands a value to a string according to ClusterShell.NodeSet
    syntax and joins the result with the separator sep"""

    if isinstance(value, list):
        return [expand(elt) for elt in value]

    # NodeSet only processes unicode
    value = value.encode('UTF8')

    # NodeSet's union operator is the comma, but we want to preserve
    # the order of declaration of elements separated by ','
    # Shinken does not mind if you give it the same value several times.
    # That way we can have our own union operator, that does not remove
    # duplicated values but preserve the order
    value_tmp = split_preserve(value)
    val_tmp = []
    for val in value_tmp:
        val_tmp.extend([node for node in NodeSet(val)])

    value = sep.join(val_tmp)

    # Shinken encodes in unicode itself, we cannot do it now
    return value.decode('UTF8')

#!/usr/bin/python
# -*- coding : utf-8 -*-

# author:
#   Quentin Bouget, quentin.bouget.ocre@cea.fr
#
# This file is part of Shinken

"""
Module to parse shinken configuration files according to ClusterShell.NodeSet
syntax
"""

from ClusterShell.NodeSet import NodeSet, NodeSetParseError

import re

EXPAND_MACRO_NAME='EXPAND'

def process(tmp):
    """
    Main function of the module, returns a list of processed objects

    Expands every property according to ClusterShell.NodeSet syntax
    """

    for prop in tmp:
        for i in range(0, len(tmp[prop])):
            # Shinken is not a great fan of empty values
            tmp[prop][i] = repl_macro_function(tmp[prop][i],
                                               EXPAND_MACRO_NAME,
                                               expand,
                                               ',')
            if is_empty(tmp[prop][i]):
                del tmp[prop][i]

    return tmp


def is_empty(value):
    """Check wether or not value is only whitespaces (empty)"""
    return re.match(r'^\s*$', value)

def find_macro(value):
    """
    Parser that finds the first macro-like expression in value and
    returns useful information about it.
    
    Matches:
        \$.*?\$
        \$[^(]*\(ARGS\)\$ 
            where ARGS is a string that contains an arbitrary number of
            nested parentheses
        \$.*?\s
    """

    opened_parens = 0
    args = None
    start_macro = value.find('$')
    end_macro = len(value)-1
    # We found a macro
    if start_macro >= 0:
        end_dollar = False
        for i in range(start_macro+1, len(value)):
            if value[i] == '(':
                opened_parens += 1
                if not args:
                    # The first parenthese
                    args = {'parens_open': i, 'parens_close': None}
                elif args['parens_close']:
                    # There can only be one set of parenthese at the first
                    # level
                    raise SyntaxError("Invalid syntax, only one block of " +\
                            "parentheses is allowed inside a given macro " +\
                            "at: %s" % value)
            elif value[i] == ')':
                if opened_parens > 0:
                    opened_parens -= 1
                    if opened_parens == 0 and not args['parens_close']:
                        # The first level set of parentheses is closed
                        args['parens_close'] = i
                        # What was inside it
                        args['value'] = value[args['parens_open']+1:i]
                else:
                    # This is a closing parenthese before an opening one
                    raise SyntaxError("Too early closing parenthese at: %s" %\
                            value)
            elif re.match(r'\s', value[i]) and opened_parens == 0:
                # We count '\s' as a terminating character because
                # we consider expressions like '\$.*?\s?$' also need to be
                # protected before we use NodeSet to expand values
                end_macro = i
                break
            elif value[i] == '$' and opened_parens == 0:
                end_dollar = True
                end_macro = i
                break
        # We read everything in value but could not close
        # all the set of parentheses
        if args and not args['parens_close']:
            raise SyntaxError("Unclosed parentheses in macro at: %s" % value)

        # Everything went well
        macro_value = value[start_macro:end_macro+1]
        return {'start_macro': start_macro,
                'end_macro': end_macro,
                'name': re.search(r'\$([^($\s]*)', macro_value).group(1),
                'args': args,
                'value': macro_value,
                'end_dollar': end_dollar}
    return None

def repl_macro_function(value, macro_name, rep_func, *args, **kwargs):
    """
    Utility function to replace a macro-function with the result of
    the rep_func when given the arguments of the macro-function

    By macro-function we designate the second kind of macro matched
    find_macro function above.
    The macro-function must take exactly one argument which must be
    a string.
    """

    start = 0
    val = ''
    while start < len(value):
        macro = find_macro(value[start:])
        if not macro:
            # No (more) macro in value
            val += value[start:]
            break
        elif not macro['args'] or not re.match(macro_name, macro['name']):
            # Not interested in this macro
            val += value[start:start + macro['end_macro']+1]
            start += macro['end_macro']+1
        else:
            # Found a macro like we were looking for
            val += value[start:macro['start_macro']]

            # Apply the rep_func on the args of the macro-function
            if len(args) and len(kwargs):
                val += rep_func(macro['args']['value'], args, kwargs)
            elif len(args):
                val += rep_func(macro['args']['value'], args)
            elif len(kwargs):
                val += rep_func(macro['args']['value'], kwargs)
            else:
                val += rep_func(macro['args']['value'])

            start += macro['end_macro']+1

    return val

def expand(value, args):
    """Expands a value to a string according to ClusterShell.NodeSet
    syntax and joins the result with the separator sep"""

    if len(args):
        sep = args[0]
    else:
        sep = ','

    if isinstance(value, list):
        return [expand(elt) for elt in value]

    # NodeSet only processes unicode
    value = value.encode('UTF8')

    # NodeSet's union operator is the comma, but we want to preserve
    # the order of declaration of elements separated by ','
    # Shinken does not mind if you give it the same value several times.
    # That way we can have our own union operator, that does not remove
    # duplicated values but preserve the order
    value_tmp = value.split(',')
    val_tmp = []
    for val in value_tmp:
        try:
            val = [node for node in NodeSet(val)]
        except NodeSetParseError, exc:
            if re.match(r'missing bracket', str(exc)):
                raise SyntaxError(exc.message)
            val = [val]

        val_tmp.extend(val)

    value = sep.join(val_tmp)


    # Shinken encodes in unicode itself, we cannot do it now
    return value.decode('UTF8')

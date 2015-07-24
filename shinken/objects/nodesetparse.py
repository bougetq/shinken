#!/usr/bin/python
# -*- coding : utf-8 -*-

# author:
#   Quentin Bouget, quentin.bouget.ocre@cea.fr
#
# This file is part of Shinken

"""
Module to parse shinken configuration files according to
ClusterShell.NodeSet syntax
"""

from ClusterShell.NodeSet import NodeSet

import re

EXPAND_MACRO_NAME = 'EXPAND'
DUPLICATE_MACRO_NAME = 'DUPLICATE'

def process(obj):
    """
    Main function of the module, returns a list of processed objects

    Expands every property according to ClusterShell.NodeSet syntax
    """

    obj_list = duplicate(obj)
    for obj in obj_list:
        for prop in obj:
            for i in range(0, len(obj[prop])):
                obj[prop][i] = expand(obj[prop][i])

                # Shinken is not a great fan of empty values
                if is_empty(obj[prop][i]):
                    del obj[prop][i]

    return obj_list

def expand(value):
    """Wrapper function for repl_macro_function with expand_repl_func"""
    return repl_macro_function(value,
                               EXPAND_MACRO_NAME,
                               True,
                               expand_repl_func,
                               ',')

def is_empty(value):
    """Check wether or not value is only whitespaces (empty)"""
    return re.match(r'^\s*$', value)

def check_ends_with_dollar(macro):
    """
    Raise an error if the macro matched by
    find_macro ends with a dollar
    """
    if not macro['end_dollar']:
        raise SyntaxError("Macro %s does not end with a dollar" \
                          % macro['value'])

def find_macro(value):
    """
    Parser that finds the first macro-like expression in value and
    returns useful information about it.

    Matches:
        \\$.*?\\$
        \\$[^(]*\\(ARGS\\)\\$
            where ARGS is a string that contains an arbitrary number of
            nested parentheses
        \\$.*?\\s
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

def repl_macro_function(value, macro_name, ends_with_dollar, rep_func,
                        *args, **kwargs):
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
            if ends_with_dollar:
                check_ends_with_dollar(macro)

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

def split_preserve_range(value, sep=","):
    """
    Split value on sep if sep is not inside brackets.

    Sep must be a single char
    """
    val_lst = ['']
    opened_bracket = 0
    for char in value:
        if char == '[':
            opened_bracket += 1
        elif char == ']':
            opened_bracket -= 1
        elif char == sep:
            if not opened_bracket:
                val_lst += ['']
                continue
        val_lst[-1] += char

    return val_lst

def expand_repl_func(value, args):
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
    value_tmp = split_preserve_range(value)
    val_tmp = []
    for val in value_tmp:
        val_tmp.extend([node for node in NodeSet(val)])

    value = sep.join(val_tmp)

    # Shinken encodes in unicode itself, we cannot do it now
    return value.decode('UTF8')

def copy_obj(obj):
    """
    Returns a semi-deep copy of an object like the ones shinken
    provides to the function process.

    Object must be like:
    obj = {'prop1': [], 'prop2': [], ..., 'propN': []}
    """
    new_obj = {}
    for prop in obj:
        new_obj[prop] = obj[prop][:]
    return new_obj

def _append_all(clone_lst, prop, idx, value, reinit=False):
    """
    Utility function to append a string to all the element of a
    clone list as it is defined in duplicate

    Created to reduce the number of branches in duplicate
    """
    if reinit:
        for clone in clone_lst:
            clone[prop][idx] = ''
    else:
        for clone in clone_lst:
            clone[prop][idx] += value

def duplicate(obj):
    """
    Duplicate a shinken object on the macro matching the
    DUPLICATE_MACRO_NAME.
    """
    clone_lst = []
    obj_template = copy_obj(obj)
    for prop in obj:
        for i in range(0, len(obj[prop])):
            start = 0
            value = obj[prop][i]
            macro = find_macro(value)
            reinit_once = False

            while macro and value.find(DUPLICATE_MACRO_NAME) > 0:
                if not reinit_once:
                    # re-init the prop
                    obj_template[prop][i] = ''
                    _append_all(clone_lst, prop, i, None, reinit=True)

                    reinit_once = True

                if macro['args'] \
                    and re.match(DUPLICATE_MACRO_NAME, macro['name']):

                    check_ends_with_dollar(macro)

                    # pfx = what is before the macro
                    pfx = value[start:start+macro['start_macro']]

                    # Expands what needs to be expanded
                    macro['args']['value'] = expand(macro['args']['value'])

                    # Find the different duplicate values
                    values = macro['args']['value'].split(',')
                    # Remove useless whitespaces
                    values = [val.strip() for val in values]

                    for j in range(0, len(values)):
                        # Add a clone if needed
                        if j == len(clone_lst):
                            clone_lst.append(copy_obj(obj_template))

                        # Append the new_value
                        clone_lst[j][prop][i] += pfx + values[j]

                    last_value = pfx + values[-1]

                    # More clone than values
                    for j in range(len(values), len(clone_lst)):
                        clone_lst[j][prop][i] += last_value

                    # To deal with multiple duplicate macro
                    # on the same line of the same property
                    obj_template[prop][i] += last_value
                else:
                    # Not the macro we are looking for => append it as it is
                    _append_all(clone_lst, prop, i,
                                value[start:start + macro['end_macro'] + 1])

                # Move forward in value
                start += macro['end_macro'] + 1
                macro = find_macro(value[start:])

            # No more macros
            if reinit_once:
                # We re-inited the prop => append what is left of the value
                _append_all(clone_lst, prop, i, value[start:])

    if clone_lst == []:
        # There was no duplicate macro => return [obj]
        clone_lst.append(obj)

    return clone_lst

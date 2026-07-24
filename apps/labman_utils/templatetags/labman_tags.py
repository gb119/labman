# -*- coding: utf-8 -*-
"""Provide shared Django template filters and tags for Labman templates."""
# Django imports
from django import template

register = template.Library()


@register.filter(name="zip")
def zip_lists(a, b):
    """Perform the zip lists operation.

    Args:
        a (object):
            Value supplied for ``a``.
        b (object):
            Value supplied for ``b``.

    Returns:
        (object):
            The result of the operation.

    Examples:
        Inspect the public interface in an interactive session::

            >>> callable(zip_lists)
            True

    """
    return zip(a, b)


@register.filter
def item(mapping, key):
    """Perform the item operation.

    Args:
        mapping (object):
            Value supplied for ``mapping``.
        key (object):
            Value supplied for ``key``.

    Returns:
        (object):
            The result of the operation.

    Examples:
        Inspect the public interface in an interactive session::

            >>> callable(item)
            True

    """
    if key.isnumeric():
        key = int(key)
    try:
        return mapping[key]
    except KeyError:
        return ""


@register.filter
def can_edit(thing, target):
    """Proxy through to the edit.

    Args:
        thing (object):
            Value supplied for ``thing``.
        target (object):
            Value supplied for ``target``.

    Returns:
        (object):
            The result of the operation.

    Examples:
        Inspect the public interface in an interactive session::

            >>> callable(can_edit)
            True

    """
    try:
        return thing.can_edit(target)
    except AttributeError:
        pass
    try:
        return target.is_superuser
    except AttributeError:
        raise


@register.filter
def modulus(number1, number2):
    """Return number1 % number2.

    Args:
        number1 (object):
            Value supplied for ``number1``.
        number2 (object):
            Value supplied for ``number2``.

    Returns:
        (object):
            The result of the operation.

    Examples:
        Inspect the public interface in an interactive session::

            >>> callable(modulus)
            True

    """
    return int(number1) % int(number2)

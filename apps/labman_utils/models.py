# -*- coding: utf-8 -*-
# Django imports
from django.db import models

# external imports
from tinymce.models import HTMLField


# Create your models here.
def patch_model(model, name=None, prep=None):
    """Decorator to monkey-patch a function into a model.

    Args:
        model (model):
            Django model to monkey -patch method into.

    Keyword Arguments:
        name (str,None):
            Name of method on the model (default None is to use the function's name)
        prep (callable):
            Callable to use to prepare the function with before adding it to the model (default None is to do nothing).

    Returns:
        Actual decorator
    """

    def patch_model_decorator(func):
        if name is None:
            attr_name = func.__name__
        else:
            attr_name = name
        if prep is not None:
            doc = func.__doc__
            func = prep(func)
            func.__doc__ = doc
        setattr(model, attr_name, func)

    return patch_model_decorator


class NamedObject(models.Model):
    """A base class for objects which have a name and an HTML description."""

    class Meta:
        abstract = True

    name = models.CharField(max_length=80, null=True, blank=True)
    description = HTMLField()

    def __str__(self):
        return f"{self.__class__.__name__}:{self.name}"

"""Shortcut classes for creating model-based autocomplete components.

This module provides ModelAutocomplete, a convenience class that simplifies creating
autocomplete components backed by Django ORM models. It handles QuerySet filtering,
search operations, and result mapping automatically.
"""

# Python imports
import operator
from functools import reduce

# Django imports
from django.db.models import Q

# app imports
from .core import Autocomplete


class ModelAutocomplete(Autocomplete):
    """Autocomplete implementation for Django ORM models.

    This class provides a convenient way to create autocomplete components that
    search and retrieve model instances. It automatically handles QuerySet filtering
    using case-insensitive contains searches across specified model fields.

    Attributes:
        model (Model):
            The Django model class to search. Must be set in subclasses.
        search_attrs (list):
            List of model field names to search across. Supports related field
            lookups using Django's double-underscore notation.

    Examples:
        >>> class UserAutocomplete(ModelAutocomplete):
        ...     model = User
        ...     search_attrs = ['username', 'email', 'profile__name']
        ...
        ...     @classmethod
        ...     def get_label_for_record(cls, record):
        ...         return f"{record.username} ({record.email})"
    """
    model = None
    search_attrs = []

    @classmethod
    def get_search_attrs(cls):
        """Get the list of model fields to search.

        Returns:
            (list): List of field names to search across.

        Raises:
            ValueError:
                If search_attrs is not defined.
        """
        if not cls.search_attrs:
            raise ValueError("ModelAutocomplete must have search_attrs")
        return cls.search_attrs

    @classmethod
    def get_model(cls):
        """Get the Django model class for this autocomplete.

        Returns:
            (Model): The Django model class.

        Raises:
            ValueError:
                If model is not defined.
        """
        if not cls.model:
            raise ValueError("ModelAutocomplete must have a model")

        return cls.model

    @classmethod
    def get_queryset(cls):
        """Get the base QuerySet for searching.

        Override this method to customise the base QuerySet, for example to add
        filters, select_related, or prefetch_related calls.

        Returns:
            (QuerySet): The base QuerySet for this autocomplete.
        """
        return cls.get_model().objects.all()

    @classmethod
    def get_label_for_record(cls, record):
        """Generate a display label for a model instance.

        Override this method to customise how model instances are displayed in
        the autocomplete dropdown and selected items list.

        Args:
            record (Model):
                The model instance to generate a label for.

        Returns:
            (str): The display label for the model instance.
        """
        return str(record)

    @classmethod
    def get_query_filtered_queryset(cls, search, context):
        """Filter the base QuerySet by the search query.

        Applies case-insensitive contains searches across all fields specified in
        search_attrs, combining them with OR logic.

        Args:
            search (str):
                The search query string.
            context (ContextArg):
                Context information including the request and client parameters.

        Returns:
            (QuerySet): Filtered QuerySet matching the search query.
        """
        base_qs = cls.get_queryset()
        conditions = [Q(**{f"{attr}__icontains": search}) for attr in cls.get_search_attrs()]
        condition_filter = reduce(operator.or_, conditions)
        queryset = base_qs.filter(condition_filter)
        return queryset

    @classmethod
    def search_items(cls, search, context):
        """Search for model instances matching the query.

        Args:
            search (str):
                The search query string.
            context (ContextArg):
                Context information including the request and client parameters.

        Returns:
            (QuerysetMappedIterable): An iterable wrapper around the filtered
                QuerySet that provides efficient slicing and length operations.
        """
        filtered_queryset = cls.get_query_filtered_queryset(search, context)

        items = QuerysetMappedIterable(queryset=filtered_queryset, label_for_record=cls.get_label_for_record)
        return items

    @classmethod
    def get_items_from_keys(cls, keys, context):
        """Retrieve model instances by their primary keys.

        Args:
            keys (Iterable):
                Collection of primary key values to retrieve.
            context (ContextArg):
                Context information including the request and client parameters.

        Returns:
            (list): List of dictionaries with 'key' and 'label' fields for each
                found model instance.
        """
        queryset = cls.get_queryset()
        results = queryset.filter(id__in=keys)

        return [{"key": record.id, "label": cls.get_label_for_record(record)} for record in results]


class QuerysetMappedIterable:
    """Efficient iterable wrapper for Django QuerySets with lazy mapping.

    This class provides an iterable interface over a QuerySet that lazily maps
    model instances to dictionary format. It supports efficient slicing, length
    operations, and iteration without loading all results into memory.

    Attributes:
        queryset (QuerySet):
            The Django QuerySet to wrap.
        label_for_record (callable):
            Function that generates a display label for each model instance.

    Notes:
        Using this class avoids loading all QuerySet results into memory at once
        whilst still supporting operations like len() and slicing that are needed
        for pagination.
    """

    def __init__(self, queryset, label_for_record):
        """Initialise the QuerySet wrapper.

        Args:
            queryset (QuerySet):
                The Django QuerySet to wrap.
            label_for_record (callable):
                Function that takes a model instance and returns a display label.
        """
        self.queryset = queryset
        self.label_for_record = label_for_record

    def __iter__(self, *args, **kwargs):
        """Iterate over mapped model instances.

        Returns:
            (generator): Generator yielding dictionaries with 'key' and 'label'
                fields for each model instance.
        """
        return (self.map_record(r) for r in self.queryset)

    def map_record(self, record):
        """Map a model instance to dictionary format.

        Args:
            record (Model):
                The model instance to map.

        Returns:
            (dict): Dictionary with 'key' (primary key) and 'label' (display label).
        """
        return {"key": record.id, "label": self.label_for_record(record)}

    def __getitem__(self, key):
        """Support indexing and slicing operations.

        Args:
            key (int or slice):
                The index or slice to retrieve.

        Returns:
            (dict or list): For integer indices, returns a single mapped record.
                For slices, returns a list of mapped records.

        Raises:
            TypeError:
                If key is neither an integer nor a slice.
        """
        # Handle both single index and slice objects
        if isinstance(key, int):
            records = [self.queryset[key]]
        elif isinstance(key, slice):
            records = self.queryset[key.start : key.stop : key.step]
        else:
            raise TypeError("Invalid argument type")

        mapped = [self.map_record(r) for r in records]

        if isinstance(key, int):
            return mapped[0]

        return mapped

    def __len__(self):
        """Return the number of items in the QuerySet.

        Returns:
            (int): The count of items in the QuerySet.
        """
        # Return the length of the sequence
        return self.queryset.count()

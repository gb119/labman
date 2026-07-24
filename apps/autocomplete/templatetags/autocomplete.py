"""Provide Django template tags for rendering autocomplete components."""

# Python imports
import hashlib
import json

# Django imports
from django import template, urls
from django.template import loader
from django.template.defaultfilters import stringfilter
from django.utils.html import escape, format_html
from django.utils.http import urlencode
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
@stringfilter
def make_id(value):
    """Generate an ID given a string, to use as element IDs in HTML.

    Args:
        value (object):
            Value supplied for ``value``.

    Returns:
        (object):
            The result of the operation.

    Examples:
        Inspect the public interface in an interactive session::

            >>> callable(make_id)
            True

    """
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@register.filter()
@stringfilter
def search_highlight(value, search):
    """Surround the section of text matching the search with a classed span.

    Args:
        value (object):
            Value supplied for ``value``.
        search (object):
            Value supplied for ``search``.

    Returns:
        (object):
            The result of the operation.

    Examples:
        Inspect the public interface in an interactive session::

            >>> callable(search_highlight)
            True

    """
    if search == "":
        return value
    try:
        pos = value.lower().index(search.lower())
        start = value[:pos]
        match = value[pos : pos + len(search)]
        end = value[pos + len(search) :]
        return format_html('{}<span class="highlight">{}</span>{}', start, match, end)
    except ValueError:
        pass
    return value


@register.simple_tag(takes_context=True)
def use_string(context, name, strings):
    """Load a string from a template or the supplied string mapping.

            Loads the string from a template or via the variable dict `strings` if the `name`
            key is defined within.  This allows strings to be overriden in 2 ways, either by
            user defined templates which will override *all* instances, or via the
            `custom_strings` property of the Autocomplete instance which allows individual
            customization.

            When `name` is not found in `strings`, the template name becomes:

            autocomplete/strings/{name}.html



    Args:
        context (object):
            Value supplied for ``context``.
        name (object):
            Value supplied for ``name``.
        strings (object):
            Value supplied for ``strings``.

    Returns:
        (object):
            The result of the operation.

    Examples:
        Inspect the public interface in an interactive session::

            >>> callable(use_string)
            True

    """
    if name in strings:
        return strings[name]

    return loader.get_template(f"autocomplete/strings/{name}.html", using="django").render(context.flatten())


@register.simple_tag
def substitute_string(template_str, **kwargs):
    """Substitute keyword values into a template string.

    Args:
        template_str (object):
            Value supplied for ``template_str``.
    Keyword Parameters:
        **kwargs (object):
            Value supplied for ``kwargs``.

    Returns:
        (object):
            The result of the operation.

    Examples:
        Inspect the public interface in an interactive session::

            >>> callable(substitute_string)
            True

    """
    as_strings = {k: str(v) for k, v in kwargs.items()}
    return template_str % as_strings


@register.simple_tag
def autocomplete(name, selected=None):
    """Render an autocomplete component in a Django template.

    Args:
        name (str):
            The unique component and route name.

    Keyword Parameters:
        selected (iterable | None):
            The values to select initially.

    Returns:
        (SafeString):
            The HTML which loads the autocomplete component.

    Examples:
        Inspect the public interface in an interactive session::

            >>> callable(autocomplete)
            True

    """
    options_selected = ",".join([str(x) for x in selected]) if selected is not None else ""

    url = urls.reverse(name, kwargs={"method": "component"})
    parameter = urlencode({name: options_selected})
    get_url = f"{url}?{parameter}"

    return format_html(("<div " f'hx-get="{get_url}"' 'hx-trigger="load"' 'hx-swap="outerHTML">' "</div>"))


@register.filter
def js_boolean(value):
    """Convert a value to a JavaScript boolean string.

    Args:
        value (object):
            Value supplied for ``value``.

    Returns:
        (object):
            The result of the operation.

    Examples:
        Inspect the public interface in an interactive session::

            >>> callable(js_boolean)
            True

    """
    return "true" if value else "false"


@register.simple_tag
def autocomplete_head(bootstrap=False):
    """Render the styles required by autocomplete components.

    Keyword Parameters:
        bootstrap (bool):
            Whether to load Bootstrap CSS from a content delivery network.

    Returns:
        (str):
            The rendered stylesheet tags.

    Examples:
        Inspect the public interface in an interactive session::

            >>> callable(autocomplete_head)
            True

    """
    return loader.get_template("autocomplete/head.html", using="django").render({"bootstrap": bootstrap})


@register.simple_tag(takes_context=True)
def autocomplete_scripts(context, bootstrap=False, htmx=False, htmx_csrf=False):
    """Render the scripts required by autocomplete components.

    Args:
        context (django.template.Context):
            The current template context.

    Keyword Parameters:
        bootstrap (bool):
            Whether to load Bootstrap from a content delivery network.
        htmx (bool):
            Whether to load HTMX from a content delivery network.
        htmx_csrf (bool):
            Whether to configure HTMX with the CSRF token.

    Returns:
        (str):
            The rendered script tags.

    Examples:
        Inspect the public interface in an interactive session::

            >>> callable(autocomplete_scripts)
            True

    """
    return loader.get_template("autocomplete/scripts.html", using="django").render(
        {
            "csrf_token": context.get("csrf_token", ""),
            "bootstrap": bootstrap,
            "htmx": htmx,
            "htmx_csrf": htmx_csrf,
        }
    )


@register.simple_tag
def value_if_truthy(test, value, default=""):
    """Return a value when a test is truthy, or a default otherwise.

    Args:
        test (object):
            The value whose truthiness is tested.
        value (object):
            The result to return when ``test`` is truthy.

    Keyword Parameters:
        default (object):
            The result to return when ``test`` is falsy.

    Returns:
        (object):
            ``value`` when ``test`` is truthy; otherwise ``default``.

    Examples:
        Inspect the public interface in an interactive session::

            >>> callable(value_if_truthy)
            True

    """
    return value if test else default


@register.simple_tag(takes_context=True)
def base_configurable_values_hx_params(context):
    """Perform the base configurable values hx params operation.

    Args:
        context (object):
            Value supplied for ``context``.

    Returns:
        (object):
            The result of the operation.

    Examples:
        Inspect the public interface in an interactive session::

            >>> callable(base_configurable_values_hx_params)
            True

    """
    field_name = context.get("field_name")
    required = context.get("required")
    disabled = context.get("disabled")
    placeholder = context.get("placeholder")
    multiselect = context.get("multiselect")

    hx_params = f"{field_name},field_name,item,component_prefix"

    if required:
        hx_params += ",required"

    if disabled:
        hx_params += ",disabled"

    if placeholder:
        hx_params += ",placeholder"

    if multiselect:
        hx_params += ",multiselect"

    # Values are code-defined field names, not user-provided HTML.
    return mark_safe(hx_params)  # nosec B308, B703


@register.simple_tag(takes_context=True)
def base_configurable_hx_vals(context):
    """Build the configurable values used in the HTMX ``hx-vals`` attribute.

            json-like format
            must be wrapped in curly braces


    Args:
        context (object):
            Value supplied for ``context``.

    Returns:
        (object):
            The result of the operation.

    Examples:
        Inspect the public interface in an interactive session::

            >>> callable(base_configurable_hx_vals)
            True

    """
    field_name = context.get("field_name")
    required = context.get("required")
    disabled = context.get("disabled")
    placeholder = context.get("placeholder")
    multiselect = context.get("multiselect")
    component_prefix = context.get("component_prefix")

    props = {
        "field_name": escape(field_name),
        "component_prefix": escape(str(component_prefix or "")),
    }

    if required:
        props["required"] = bool(required)

    if disabled:
        props["disabled"] = bool(disabled)

    if multiselect:
        props["multiselect"] = bool(multiselect)

    if placeholder:
        props["placeholder"] = escape(str(placeholder))

    hx_vals = json.dumps(props).replace("{", "").replace("}", "")

    # json.dumps() encodes values and escape() handles the single-quoted HTML attribute boundary.
    return mark_safe(hx_vals)  # nosec B308, B703


def stringify_extra_hx_vals(extra_hx_vals_dict):
    """Perform the stringify extra hx vals operation.

    Args:
        extra_hx_vals_dict (object):
            Value supplied for ``extra_hx_vals_dict``.

    Returns:
        (object):
            The result of the operation.

    Raises:
        ValueError:
            If any value contains a single quote.

    Examples:
        Inspect the public interface in an interactive session::

            >>> callable(stringify_extra_hx_vals)
            True

    """
    if any("'" in val for val in extra_hx_vals_dict.values()):
        raise ValueError(
            "Extra hx vals cannot contain single quotes, consider backticks for JS expressions or escaping double-quotes"
        )

    return ",".join([f' "{key}": {val}' for key, val in extra_hx_vals_dict.items()])


@register.simple_tag(takes_context=True)
def text_input_hx_vals(context):
    """Build the HTMX values used by an autocomplete text input.

            items has augments hx-vals,
            - it adds JS value of the search input
            - users can add more values in their class


    Args:
        context (object):
            Value supplied for ``context``.

    Returns:
        (object):
            The result of the operation.

    Examples:
        Inspect the public interface in an interactive session::

            >>> callable(text_input_hx_vals)
            True

    """
    base_hx_vals_str = base_configurable_hx_vals(context)

    component_id_escape = escape(context.get("component_id"))

    val = "js:{" f"{base_hx_vals_str}," f'search: document.getElementById("{component_id_escape}__textinput").value'

    extra_hx_vals = context.get("ac_class").get_extra_text_input_hx_vals()
    if extra_hx_vals:
        extra_hx_val_str = stringify_extra_hx_vals(extra_hx_vals)
        val = f"{val}, {extra_hx_val_str}"

    val = val + "}"

    # Component IDs are escaped and extension expressions are application code validated above.
    return mark_safe(val)  # nosec B308, B703

.. _api-reference:

API reference
=============

This reference is generated from the Python docstrings.  It concentrates on the domain models and the shared
frameworks used to extend LabMan.

Accounts
--------

.. automodapi:: accounts.models
    :no-inheritance-diagram:
    :no-inherited-members:
    :skip: Role

Role model
^^^^^^^^^^

``Role`` exposes database-backed class properties for the configured access levels.  These properties are excluded
from automatic introspection so that building the documentation never queries the database.

.. autoclass:: accounts.models.Role
    :members: __str__
    :no-inherited-members:

Equipment
---------

.. automodapi:: equipment.models
    :no-inheritance-diagram:
    :no-inherited-members:

Bookings
--------

.. automodapi:: bookings.models
    :no-inheritance-diagram:
    :no-inherited-members:

Costings
--------

.. automodapi:: costings.models
    :no-inheritance-diagram:
    :no-inherited-members:

Shared models
-------------

.. automodapi:: labman_utils.models
    :no-inheritance-diagram:
    :no-inherited-members:

Autocomplete framework
----------------------

.. automodapi:: autocomplete.core
    :no-inheritance-diagram:
    :no-inherited-members:

.. automodapi:: autocomplete.shortcuts
    :no-inheritance-diagram:
    :no-inherited-members:

HTMX view framework
-------------------

.. automodapi:: htmx_views.views
    :no-inheritance-diagram:
    :no-inherited-members:

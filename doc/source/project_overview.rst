.. _project-overview:

LabMan project overview
=======================

Purpose
-------

LabMan is a Django application for operating shared research-facility resources.  It brings together the people,
equipment, permissions, safety records, bookings, and charges involved in laboratory work.  Its principal workflows
allow staff to:

* maintain user accounts, research groups, and laboratory roles;
* organise equipment within a hierarchy of physical locations;
* control which users may access and book each item of equipment;
* require users to acknowledge relevant documents before using equipment;
* apply booking policies, holds, shifts, and time-slot rules;
* associate equipment use with charging rates and cost centres; and
* administer, import, export, and query operational data.

The project is a server-rendered Django site.  HTMX supplies partial-page interactions, while Django REST Framework
provides read-only programmatic access to selected account and equipment data.

Domain structure
----------------

The source docstrings describe four main domain areas:

Accounts
    Accounts extend Django's user model with laboratory-specific information.  Research groups organise users, and
    roles represent levels of responsibility or equipment access.

Equipment
    Locations form a hierarchy containing equipment and related resources.  User-list entries associate accounts
    with equipment and roles.  Equipment also links to shifts, charging rates, documents, and document sign-offs.

Bookings
    Booking entries reserve equipment for time ranges.  Booking policies determine whether a request is permitted
    and how its times are quantised.  Holds and policy-specific exceptions explain why a booking cannot proceed.

Costings
    Cost centres form a hierarchy for financial allocation.  Cost rates describe charging schemes, while chargeable
    items provide the shared basis for calculating and assigning charges.

These areas are related rather than isolated.  A typical booking decision starts with an account and an item of
equipment, resolves the user's equipment role and document status, selects the applicable booking policy, and may
then determine a cost centre and charge.

Django applications
-------------------

The ``apps`` directory contains the project's Django applications:

``accounts``
    Owns account, research-group, and role behaviour.  It also provides account administration, forms, lookup and
    autocomplete integrations, import/export resources, read-only API serializers and view sets, and account views.

``equipment``
    Owns locations, equipment, shifts, user-list entries, document sign-offs, and charging-rate associations.  Its
    forms and views implement equipment details, access management, sign-off, and editing workflows.  Calendar-table
    helpers convert dates and times into display coordinates.

``bookings``
    Owns booking entries, policies, booking-specific exceptions, calendar views, booking dialogs, record filtering,
    administration, and import/export resources.

``costings``
    Owns cost rates, hierarchical cost centres, and the base behaviour for chargeable records.  It supplies
    administration, forms, views, autocomplete support, and import/export resources for those records.

``labman_utils``
    Contains shared model, form, widget, and view infrastructure.  Important abstractions include named and resourced
    models, document and photo handling, access-control mixins, multi-form processing, tree administration, and
    reusable dialog views.

``autocomplete``
    Implements a registry-based autocomplete framework.  It supplies the base autocomplete contract, model-backed
    shortcuts, widgets, HTMX endpoints, and template tags.  Application-specific autocomplete classes register with
    this framework.

``htmx_views``
    Provides reusable processing and form mixins for requests enhanced by HTMX.  Domain applications compose these
    mixins with Django's class-based views rather than duplicating partial-response behaviour.

Application layering
--------------------

The applications generally follow Django's conventional layering:

``models.py``
    Defines persisted domain state and the rules closely associated with it.

``forms.py``
    Validates user input and adapts domain models to editing workflows.

``views.py``
    Coordinates permissions, forms, models, templates, and HTMX response handling.

``urls.py``
    Exposes each application's views beneath the project URL configuration.

``admin.py``
    Configures staff administration, including hierarchical and import/export interfaces where appropriate.

``api.py``
    Defines Django REST Framework serializers, view sets, and routers for the applications that expose an API.

``resource.py``
    Defines import/export mappings for operational and migration tasks.

``autocomplete.py`` and ``lookups.py``
    Provide search endpoints used by forms, widgets, and administrative interfaces.

``templatetags``
    Supplies presentation helpers which are intentionally kept outside the domain models.

Request and integration flow
----------------------------

The top-level ``labman.urls`` module combines application URL configurations, administrative routes, REST API routes,
media handling, and project error views.  A normal interactive request therefore follows this path:

#. Django resolves the request through ``labman.urls`` and an application's ``urls.py``.
#. An application view applies shared authentication or staff mixins from ``labman_utils``.
#. The view reads or updates domain models, usually through a form for write operations.
#. Standard requests render a full template; HTMX requests may render a fragment or return an HTMX response.
#. Autocomplete widgets make separate requests to the registered autocomplete endpoints.

The ``labman.api`` module discovers application API modules and combines their routers.  The documented account and
equipment view sets are read-only, so they provide query access without becoming a second write path around the form
and model rules.

Repository layout
-----------------

The principal repository directories and entry points are:

``apps/``
    Project-owned Django applications.

``labman/``
    Project-level URL, API, WSGI, error-view, and settings configuration.

``labman/settings/``
    Split settings.  ``common.py`` contains shared configuration, while ``development.py``, ``production.py``, and
    ``testing.py`` specialise it for their respective environments.  Deployment-specific secrets are kept separate
    from general settings.

``templates/`` and ``static/``
    Project-wide templates and browser assets.  Applications may also provide their own templates and static files.

``fixtures/``
    Initial or reference data loaded into the Django models.

``configs/``
    Service configuration, including Gunicorn configuration.

``doc/source/``
    The reStructuredText source for this Sphinx documentation.

``tools/``
    One-off data-conversion utilities.  These scripts are maintenance tools rather than runtime application modules.

``manage.py``
    The development and administrative command-line entry point.

``labman/wsgi.py``
    The production WSGI entry point.

Extension points
----------------

New domain behaviour should normally be added to the application that owns the relevant model.  Cross-application
presentation or request-processing behaviour belongs in ``labman_utils`` or ``htmx_views``.  New autocomplete
implementations should subclass the autocomplete framework and register under a unique route name.  API additions
should use an application's ``api.py`` and remain consistent with the permissions and invariants enforced by the
HTML workflow.

The project uses abstract models and view mixins deliberately.  Before adding a new helper, check the shared
``labman_utils`` models and views, the HTMX mixins, and the autocomplete shortcuts for an existing extension point.

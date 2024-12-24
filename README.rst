django-project-skeleton
=======================

**django-project-skeleton** is my skeleton for Django projects. It provides a
directory structure for Django projects during development and deployment.


Meta
----

Author:
    Mischback
    Gavin Burnell (this fork)

Contributors:
    `agirardeaudale <https://github.com/agirardeuadale>`_,
    `jmrbcu <https://github.com/jmrbcu>`_

Status:
    maintained, in development

Version:
    1.5

Django Version:
    4.x


Usage
-----

To use this repository just use the ``template`` option of `django-admin
<https://docs.djangoproject.com/en/2.2/ref/django-admin/#startproject>`_::

    $ django-admin startproject --template=https://github.com/gb119/django-project-skeleton/archive/development.zip --name apache2_vhost.sample [projectname]

If you wish to automagically fill the ``apache2_vhost.sample`` the command is::

    $ django-admin startproject --template=https://github.com/Mischback/django-project-skeleton/archive/development.zip --name apache2_vhost.sample [projectname]


Note
----

Disregard the failing build-status of commits in the branch ``development``.
These commits are tested on Travis with all possible combinations of Django
and Python. This is done to determine the compatibility and update the
documentation accordingly. Failing is expected.


Documentation
-------------

You can see the documentation for the original version over at **Read the Docs**: `django-project-skeleton
<http://django-project-skeleton.readthedocs.org/en/latest/>`_

This fork updates some things for Django 1.9 and Apache 2.4 and changes a few defaults to thinks I like better.
.. django-project-skeleton documentation master file, created by
   sphinx-quickstart on Sat Feb 21 16:55:55 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

django-project-skeleton
=======================

**django-project-skeleton** is my skeleton for Django projects. It provides a
directory structure for Django projects during development and deployment. This
structure is based on research and own experience of developing Django apps.

**Please note:** This is *my* skeleton and is developed to fit my very own
needs for new Django projects. Please feel free to modify it to your own
requirements but be aware that no changes will be made, that **I** do not
consider useful.

**Additional note:** Compatibility checks are made using ``Travis`` and ``tox``.
Please see :ref:`label-versions` to find a suitable version of this repository for
your development needs.

Notable Features
----------------

* prepared directory structure
* modular settings with sane default values
* prepared sample configuration for *Apache2*-deployment with *mod_wsgi*
* including ``.gitignore``-files to help getting started with *Git*

Contents
--------

.. toctree::
    :maxdepth: 2

    quickstart
    structure
    settings
    apache2_vhost
    versions

Hall of Fame
------------

It's been a while, I even missed some Django-releases completely. Some guys at
Github picked up the project and made some changes to keep it in line with
Django-releases. I grabbed some code from the, so they are considered
*Contributors* to this project and should be mentioned here:


* `agirardeaudale <https://github.com/agirardeuadale>`_
* `jmrbcu <https://github.com/jmrbcu>`_

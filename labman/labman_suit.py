# Python imports
from os.path import basename, dirname

# Django imports
from django.apps import AppConfig

# external imports
from suit.apps import DjangoSuitConfig
from suit.menu import ChildItem, ParentItem


class AdminConfigConfig(AppConfig):
    name = basename(dirname(__file__))


class SuitConfig(DjangoSuitConfig):
    layout = "vertical"
    list_per_page = 150
    menu = [
        ParentItem(
            "Users and Groups",
            children=[
                ChildItem(model="accounts.Account"),
                ChildItem(model="auth.Group"),
            ],
            icon="fa fa-users",
        ),
        ParentItem(
            "Advamnced Settings",
            children=[
                ChildItem(model="constance.Config"),
                ChildItem(model="flatpages.FlatPage"),
                ChildItem(model="sites.Site"),
            ],
            icon="fa fa-cog",
        ),
    ]

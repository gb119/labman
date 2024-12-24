# -*- coding: utf-8 -*-
"""
Bookings Settings
"""
# Python imports
from datetime import time

CONSTANCE_ADDITIONAL_FIELDS = {
    "weekday_select": [
        "django.forms.fields.ChoiceField",
        {
            "widget": "django.forms.Select",
            "choices": (
                (0, "Monday"),
                (1, "Tuesday"),
                (2, "Wednesday"),
                (3, "Thursday"),
                (4, "Froday"),
                (5, "Saturday"),
                (6, "Subday"),
            ),
        },
    ],
}

CONSTANCE_CONFIG = {
    "CALENDAR_START_DAY": (5, "Calendar Start Day", "weekday_select"),
    "CALENDAR_START_TIME": (time(hour=8), "Calendar Start Time"),
    "CALENDAR_END_TIME": (time(hour=20), "Calendar End Time"),
}

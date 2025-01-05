# -*- coding: utf-8 -*-
"""
Created on Sun Jan  5 10:35:05 2025

@author: phygbu
"""

# Python imports
from pathlib import Path

# external imports
import pandas as pd
from dateutil.parser import ParserError, parser

people = pd.read_csv(Path("S:/labman/people.csv"))
parse = parser().parse


def sort_nbame(row):
    """Intelligently work out title, first_name, last_name fields."""
    try:
        name = row.Name.strip()
    except AttributeError:
        name = "unknown unknown"
    try:
        status = row.Status.strip().lower()
    except AttributeError:
        status = "unknown"
    parts = [x.strip().title() for x in name.split(" ") if x.strip() != "" and not x.startswith("[")]
    match status:
        case "academic":
            is_staff = True
            title = parts[0]
            last_name = parts[-1]
            first_name = " ".join(parts[1:-1])
            grp = status.title()
        case "staff" | "visitor":
            is_staff = status == "staff"
            if parts[0] in ["Dr", "Mr", "Mrs", "Miss", "Ms", "Prof"]:
                title = parts[0]
                parts = parts[1:]
            else:
                title = ""
            last_name = parts[-1]
            first_name = " ".join(parts[:-1])
            grp = status.title()
        case "pdra":
            is_staff = False
            if parts[0] in ["Dr", "Mr", "Mrs", "Miss", "Ms", "Prof"]:
                title = parts[0]
                parts = parts[1:]
            else:
                title = "Dr"
            last_name = parts[-1]
            first_name = " ".join(parts[:-1])
            grp = status.upper()
        case "project" | "postgrad" | "rpg" | "student" | "students":
            is_staff = False
            title = ""
            last_name = parts[-1]
            first_name = " ".join(parts[:-1])
            if status == "rpg":
                status = "postgrad"
            if status in ["student", "students"]:
                status = "project"
            grp = status.title()
        case _:
            is_staff = False
            title = ""
            last_name = parts[-1]
            first_name = " ".join(parts[:-1])
            grp = ""
    match row["Group"]:
        case "CM" | "MNP" | "EEE" | "School" | "Extern" | "UGrad":
            group = row["Group"]
        case "SMP" | "PCF":
            group = "SMP"
        case "SPEME":
            group = "SCAPE"
        case "CHM":
            group = "CHEM"
        case _:
            group = "Other"
    nrow = {}
    nrow["username"] = row["Username"]
    nrow["title"] = title
    nrow["first_name"] = first_name
    nrow["last_name"] = last_name
    nrow["project"] = None
    try:
        nrow["date_joined"] = parse(row["Date_Joined"])
    except ParserError:
        nrow["date_joined"] = None
    nrow["end_date"] = pd.NaT
    nrow["is_staff"] = is_staff
    nrow["is_superuser"] = status == "academic"
    nrow["group"] = grp
    nrow["number"] = row["Number"]
    nrow["research_group"] = group
    try:
        nrow["manaager"] = people.loc[row["Boss"]].Username
    except KeyError:
        nrow["manaager"] = ""
    return pd.Series(nrow)


people.set_index("ID", inplace=True)
people2 = people.apply(sort_nbame, axis=1)
people2.to_excel("S:/labman/people.xlsx")

# -*- coding: utf-8 -*-
"""
Created on Sun Jan  5 16:38:46 2025

@author: phygbu
"""

# Python imports
import os
from datetime import datetime

# external imports
import numpy as np
import pandas as pd

os.chdir("..")

people_old = pd.read_csv("people.csv")
people_old.Username = people_old.Username.apply(lambda x: x if not isinstance(x, str) else x.strip().lower())
people_old.set_index("Username", inplace=True)
people_new = pd.read_excel("people2.xlsx")
people_new.username = people_new.username.apply(lambda x: x.strip().lower())
people_new.set_index("username", inplace=True)

people_new = people_new.join(people_old.ID, how="left")
people_new["username"] = people_new.index
people_new.set_index("ID", inplace=True)

equipment_old = pd.read_csv("equipment.csv").set_index("name")
equipment_new = pd.read_excel("equipment.xlsx").set_index("name")
equipment_new.drop(columns="id", inplace=True)
equipment_new = equipment_new.join(equipment_old.id, how="left")
equipment_new.id = equipment_new.id.apply(lambda x: -1 if np.isnan(x) else int(x))
equipment_new["name"] = equipment_new.index
equipment_new.set_index("id", inplace=True)

userlist = pd.read_csv("userlists.csv").set_index("ID")

userlist.level = userlist.level.apply(lambda x: 1000 if x >= 40 else x * 10)


def match_entry(row):
    nrow = {}
    if row.user in people_new.index:
        nrow["user"] = people_new.loc[row.user, "username"]
    else:
        return None
    if row.equipment in equipment_new.index:
        nrow["equipment"] = equipment_new.loc[row.equipment, "name"]
    else:
        return None
    nrow["hold"] = True
    nrow["admin_hold"] = False
    nrow["updated"] = datetime.now()
    nrow["role"] = int(100 * np.ceil(row["level"] // 100))
    return pd.Series(nrow)


output = pd.DataFrame([x for x in userlist.apply(match_entry, axis=1) if x is not None])
output = output.loc[~output.duplicated(subset=["user", "equipment"])]
output.to_excel("Userlists.xlsx")

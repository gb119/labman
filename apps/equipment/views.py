# -*- coding: utf-8 -*-
"""View classes for the equipment app - including showing booking tables."""
# Python imports
import json
from datetime import datetime as dt, timedelta as td
from itertools import chain

# Django imports
from django import views
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count
from django.http import (
    HttpResponse,
    HttpResponseForbidden,
    HttpResponseNotFound,
)
from django.urls import reverse
from django.utils.text import slugify
from django.views.generic import UpdateView

# external imports
import pytz
from accounts.models import Account, Project
from bookings.forms import BookinngDialogForm
from extra_views import FormSetView
from htmx_views.views import HTMXFormMixin, HTMXProcessMixin
from labman_utils.models import Document
from labman_utils.views import IsAuthenticaedViewMixin

# app imports
from .forms import SignOffForm, UserListEnryForm
from .models import DocumentSignOff, Equipment, Location, UserListEntry
from .tables import CalTable

DEFAULT_TZ = pytz.timezone(settings.TIME_ZONE)

# Create your views here.


class SignOffFormSetView(IsAuthenticaedViewMixin, FormSetView):
    """Provides the view for signing off risk assessments and SOPs to be allowed to book equipment."""

    template_name = "equipment/sign-off.html"
    form_class = SignOffForm
    success_url = "/accounts/me/"
    factory_kwargs = {"extra": 0, "max_num": None, "can_order": False, "can_delete": False}

    def get_initial(self):
        """Get initial data for the document sign-off formset."""
        equipment_id = int(self.kwargs["equipment"])
        equipment = Equipment.objects.get(pk=equipment_id)
        docs = equipment.all_files.filter(category__in=["ra", "sop"])
        dataset = []
        for doc in docs:
            row = {"document": doc, "user": self.request.user, "version": doc.version}
            try:
                dso = DocumentSignOff.objects.get(user=self.request.user, document=doc, version=doc.version)
                row["id"] = dso.id
                row["signed"] = True
            except ObjectDoesNotExist:
                dso = DocumentSignOff(user=self.request.user, document=doc, version=doc.version)
                row["signed"] = False
            dataset.append(row)
        return dataset

    def formset_valid(self, formset):
        """Process the formset to add sign=offs of documents."""
        equipment_id = int(self.kwargs["equipment"])
        equipment = Equipment.objects.get(pk=equipment_id)
        data = None
        for form in formset.forms:
            data = form.cleaned_data
            if data["signed"]:
                dso, _ = DocumentSignOff.objects.get_or_create(
                    user=self.request.user, document=data["document"], version=data["document"].version
                )
                dso.save()
        if data is None:  # Force userlist save if no docs to sign!
            equipment.users.get(user=self.request.user).save()

        return super().formset_valid(formset)

    def get_context_data(self, **kwargs):
        """Ensure context data includes the documents for the equipment item."""
        context = super().get_context_data(**kwargs)
        docs = [x.initial["document"] for x in context["formset"].forms]
        context["docs"] = docs
        return context


class EquipmentDetailView(HTMXProcessMixin, IsAuthenticaedViewMixin, views.generic.DetailView):
    """Templated view for Equipment detail."""

    template_name = "equipment/equipment_detail.html"
    template_name_resourcestab = "equipment/parts/equipment_detail_resources.html"
    template_name_imagestab = "equipment/parts/equipment_detail_images.html"
    template_name_pagestab = "equipment/parts/equipment_detail_pages.html"
    template_name_userlisttab = "equipment/parts/equipment_detail_userlist.html"
    template_name_scheduletab = "equipment/parts/equipment_detail_schedule.html"
    template_name_schedule_container = "equipment/parts/equipment_detail_schedule.html"
    template_name_cal_back = "equipment/parts/equipment_detail_schedule.html"
    template_name_cal_forward = "equipment/parts/equipment_detail_schedule.html"
    model = Equipment

    def get_context_data_scheduletab(self, **kwargs):
        """Build the context for the calendar display."""
        context = super().get_context_data(_context=True, **kwargs)
        # Build the calendar rows from the shifts.
        date = int(self.request.GET.get("date", dt.today().strftime("%Y%m%d")))
        mode = self.kwargs.get("mode", self.request.GET.get("mode", "single")).strip().lower()
        context["start_date"] = date
        date_obj = dt.strptime(str(date), "%Y%m%d")
        back_date = date_obj - td(days=7)
        forward_date = date_obj + td(days=7)
        context["back_date"] = back_date.strftime("%Y%m%d")
        context["forward_date"] = forward_date.strftime("%Y%m%d")
        context["mode"] = mode

        match mode:
            case "single":
                equipment = context["equipment"]
                equip_vec = None
                table = CalTable(
                    date=self.kwargs.get("date", date),
                    request=self.request,
                    equipment=equipment,
                    equip_vec=equip_vec,
                    table_contents="&nbsp;",
                )
                table.classes += " table-bordered"
                entries = table.fill_entries(equipment)
                context["start"] = table.date_vec[0]
                context["end"] = table.date_vec[-1]
                context["start_date"] = table.date_vec[0].strftime("%Y%m%d")
            case "all":
                equipment = None
                table = {}
                entries = {}
                for cat in Equipment.CATEGORIES:
                    equip_vec = (
                        Equipment.objects.filter(category=cat)
                        .annotate(policy_count=Count("policies"))
                        .filter(policy_count__gt=0)
                        .order_by("name")
                    )
                    if equip_vec.count() == 0:
                        continue
                    table[cat] = CalTable(
                        date=self.kwargs.get("date", date),
                        request=self.request,
                        equipment=equipment,
                        equip_vec=equip_vec,
                        table_contents="&nbsp;",
                    )
                    table[cat].classes += " table-bordered"
                    entries[cat] = chain(*(table[cat].fill_entries(equipment) for equipment in equip_vec))
                context["start"] = table["cryostat"].date_vec[0]
                context["end"] = table["cryostat"].date_vec[-1]
                context["start_date"] = table["cryostat"].date_vec[0].strftime("%Y%m%d")
                context["categories"] = {x: Equipment.CATEGORIES[x] for x in table}
            case _:
                raise ValueError(f"Unknow mode {mode} in scedule detail.")

        context["cal"] = table
        context["entries"] = entries
        context["form"] = BookinngDialogForm()

        opentab = self.request.GET.get("opentab", list(Equipment.CATEGORIES.keys())[0])
        context["opentab"] = opentab

        return context

    get_context_data_schedule_container = get_context_data_scheduletab
    get_context_data_cal_back = get_context_data_scheduletab
    get_context_data_cal_forward = get_context_data_scheduletab

    def get_context_data_userlisttab(self, **kwargs):
        """Build the context for the userlist display."""
        context = super().get_context_data(_context=True, **kwargs)
        context["opentab"] = slugify(self.request.GET.get("opentab", "Manager"))
        return context


class LocationDetailView(HTMXProcessMixin, IsAuthenticaedViewMixin, views.generic.DetailView):
    """Templated view for Equipment detail."""

    template_name = "equipment/location_detail.html"
    template_name_resourcestab = "equipment/parts/location_detail_resources.html"
    template_name_imagestab = "equipment/parts/location_detail_images.html"
    template_name_pagestab = "equipment/parts/location_detail_pages.html"
    template_name_equipmenttab = "equipment/parts/location_detail_equipment.html"

    model = Location

    def get_context_data_locationtab(self, **kwargs):
        """Build the context for the calendar display."""
        context = super().get_context_data(_context=True, **kwargs)


class ModelListView(HTMXProcessMixin, IsAuthenticaedViewMixin, views.generic.ListView):
    """Setup a tabbed view of lists of various things."""

    template_name = "equipment/lists.html"
    template_name_equipmenttab = "equipment/parts/equipment_list.html"
    template_name_locationstab = "equipment/parts/locations_list.html"
    template_name_projectstab = "equipment/parts/projects_list.html"
    template_name_documentstab = "equipment/parts/documents_list.html"
    template_name_accountstab = "equipment/parts/accounts_list.html"

    context_object_equipmenttab = "equipment"
    context_object_locationstab = "locations"
    context_object_projectstab = "projects"
    context_object_documentstab = "documents"
    context_object_accountstab = "accounts"

    def get_queryset(self):
        """Get different querysets for each htmx query."""
        if not getattr(self.request, "htmx", False):
            ret = {}
            for grp in ["Academic", "Staff", "PDRA", "PostGrad", "Visitor", "Project"]:
                ret[grp] = Account.objects.filter(groups__name__icontains=grp).order_by("last_name", "first_name")
            return ret
        match getattr(self.request.htmx, "trigger", ""):
            case "equipment-tab":
                qs = Equipment.objects.all().order_by("category", "name")
            case "locations-tab":
                qs = Location.objects.all().order_by("code", "name")
            case "projects-tab":
                qs = Project.objects.all().order_by("name")
            case "documents-tab":
                qs = {}
                for category in dict(Document.CATEGORIES):
                    qs[category] = Document.objects.filter(category=category)
            case _:
                qs = {}
                for grp in ["Academic", "Staff", "PDRA", "PostGrad", "Visitor", "Project"]:
                    qs[grp] = Account.objects.filter(groups__name__icontains=grp).order_by("last_name", "first_name")
        return qs

    def get_context_data_equipmenttab(self, **kwargs):
        """Extra context for equipment list."""
        context = super().get_context_data(_context=True, **kwargs)
        data = {}
        for category in Equipment.CATEGORIES:
            data[category] = context["equipment"].filter(category=category)
        context["equipment"] = data
        context["categories"] = Equipment.CATEGORIES
        return context

    def get_context_data_documentstab(self, **kwargs):
        """Extra context for equipment list."""
        context = super().get_context_data(_context=True, **kwargs)
        context["categories"] = dict(Document.CATEGORIES)
        return context


class UserlisttDialog(IsAuthenticaedViewMixin, HTMXFormMixin, UpdateView):
    """Prdoce the html for a booking form in the dialog."""

    model = UserListEntry
    template_name = "equipment/userlist_form.html"
    context_object_name = "this"
    form_class = UserListEnryForm

    def get_context_data_dialog(self, **kwargs):
        """Create the context for HTMX calls to open the booking dialog."""
        context = super().get_context_data(_context=True, **kwargs)
        context["current_url"] = self.request.htmx.current_url
        context["this"] = self.get_object()
        verb = "edit" if context["this"] else "new"
        if "equipment" in self.kwargs:
            context["equipment"] = Equipment.objects.get(pk=self.kwargs.get("equipment", None))
        if "user" in self.kwargs:
            context["user"] = Account.objects.get(pk=self.kwargs.get("user", None))
        args = (context["equipment"].pk, context["user"].pk) if verb == "edit" else (context["equipment"].pk,)
        context["post_url"] = reverse(f"equipment:userlist_{verb}", args=args)

        context["edit"] = self.get_object() is not None
        return context

    def get_object(self, queryset=None):
        """Either get the UserList entry or None."""
        try:
            return UserListEntry.objects.get(equipment=self.kwargs["equipment"], user=self.kwargs["user"])
        except (UserListEntry.DoesNotExist, AttributeError, KeyError):
            return None

    def get_initial(self):
        """Make initial entry."""
        equipment = Equipment.objects.get(pk=self.kwargs.get("equipment", None))
        if "user" in self.kwargs:
            dd = self.kwargs
            user = Account.objects.get(pk=self.kwargs["user"])
            return {"equipment": equipment, "user": user}
        return {"equipment": equipment}

    def htmx_form_valid_userlistentry(self, form):
        """Handle the HTMX submitted booking form if it's all ok."""
        entry = form.instance
        if not entry.equipment.can_edit(self.request.user):
            return HttpResponseForbidden("You must be a manager, owner or superuser to rfiy the user entry.")
        entry.save()
        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": json.dumps({"refreshUserList": slugify(entry.role.name)}),
            },
        )

    def htmx_delete_userlistentry(self, request, *args, **kwargs):
        """Handle the HTMX call that deletes a booking."""
        if not (entry := self.get_object()):
            return HttpResponseNotFound("Unable to locate userlist entry.")
        self.object = entry
        # Now check I actually have permission to do this...
        if not entry.equipment.can_edit(self.request.user):
            return HttpResponseForbidden("You must be a manager, owner or superuser to delete the user entry.")

        self.object.delete()

        return HttpResponse(
            status=204,
            headers={
                "HX-Trigger": json.dumps({"refreshUserList": slugify(entry.role.name)}),
            },
        )

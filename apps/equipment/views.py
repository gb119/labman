# -*- coding: utf-8 -*-
"""View classes for the equipment app.

This module provides Django class-based views for managing equipment, locations,
document sign-offs, and user lists. It includes calendar displays for equipment
booking and comprehensive equipment detail views with tabbed interfaces.
"""
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
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.text import slugify
from django.views.generic import UpdateView

# external imports
import pytz
from accounts.models import Account
from bookings.forms import BookinngDialogForm
from costings.models import CostCentre
from extra_views import FormSetView
from htmx_views.views import HTMXFormMixin, HTMXProcessMixin
from labman_utils.models import Document
from labman_utils.views import IsAuthenticaedViewMixin, IsSuperuserViewMixin

# app imports
from .forms import (
    EquipmentForm,
    SelectDatefForm,
    SignOffForm,
    UserListEnryForm,
)
from .models import DocumentSignOff, Equipment, Location, UserListEntry
from .tables import CalTable

DEFAULT_TZ = pytz.timezone(settings.TIME_ZONE)

# Create your views here.


class SignOffFormSetView(IsAuthenticaedViewMixin, FormSetView):
    """View for signing off risk assessments and SOPs required for equipment booking.

    This view presents a formset allowing users to sign off on required documents
    (risk assessments and SOPs) before they are permitted to book equipment.
    Each document must be signed at the current version before the user can proceed.

    Attributes:
        template_name (str): Template path for the sign-off form.
        form_class: Form class used for each document sign-off.
        success_url (str): Redirect URL after successful sign-off.
        factory_kwargs (dict): Configuration for the formset factory.
    """

    template_name = "equipment/sign-off.html"
    form_class = SignOffForm
    success_url = "/accounts/me/"
    factory_kwargs = {"extra": 0, "max_num": None, "can_order": False, "can_delete": False}

    def get_initial(self):
        """Get initial data for the document sign-off formset.

        Retrieves all risk assessment and SOP documents for the specified equipment
        and checks if the current user has already signed them at the current version.

        Returns:
            (list of dict): List of dictionaries containing initial form data with keys:
                'document', 'user', 'version', 'id' (if exists), and 'signed' status.
        """
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
        """Process the formset to add sign-offs of documents.

        Creates or retrieves DocumentSignOff records for each signed document.
        If no documents require signing, forces a save of the user list entry
        to update timestamps.

        Args:
            formset: The validated formset containing document sign-off data.

        Returns:
            (HttpResponse): Redirect response from parent class.
        """
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
            equipment.userlist.get(user=self.request.user).save()

        return super().formset_valid(formset)

    def get_context_data(self, **kwargs):
        """Ensure context data includes the documents for the equipment item.

        Keyword Parameters:
            **kwargs: Additional context data from parent classes.

        Returns:
            (dict): Context dictionary with 'docs' key containing list of documents.
        """
        context = super().get_context_data(**kwargs)
        docs = [x.initial["document"] for x in context["formset"].forms]
        context["docs"] = docs
        return context


class EquipmentDetailView(HTMXProcessMixin, IsAuthenticaedViewMixin, views.generic.DetailView):
    """Detailed view for a single equipment item with tabbed interface.

    Provides a comprehensive detail view for equipment with multiple tabs including
    resources, images, pages, user list, and schedule. Supports both single equipment
    and all-equipment calendar views with HTMX for dynamic tab loading.

    Attributes:
        template_name (str): Main template for equipment detail.
        template_name_resourcestab (str): Template for resources tab.
        template_name_imagestab (str): Template for images tab.
        template_name_pagestab (str): Template for pages tab.
        template_name_userlisttab (str): Template for user list tab.
        template_name_scheduletab (str): Template for schedule tab.
        template_name_schedule_container (str): Template for schedule container.
        template_name_cal_back (str): Template for calendar back navigation.
        template_name_cal_forward (str): Template for calendar forward navigation.
        model: Equipment model class.
    """

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
        """Build the context for the calendar display.

        Creates a calendar table for equipment booking, supporting both single equipment
        and all-equipment views. Handles date navigation and mode switching.

        Keyword Parameters:
            **kwargs: Additional context data from parent classes.

        Returns:
            (dict): Context dictionary containing calendar data, dates, forms, and entries.

        Raises:
            ValueError: If an unknown mode is specified.
        """
        context = super().get_context_data(**kwargs)
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
                        .filter(policy_count__gt=0, offline=False)
                        .prefetch_related("shifts")
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
        context["select_date"] = SelectDatefForm(data={"date": context["start"]})

        opentab = self.request.GET.get("opentab", list(Equipment.CATEGORIES.keys())[0])
        context["opentab"] = opentab

        return context

    get_context_data_schedule_container = get_context_data_scheduletab
    get_context_data_cal_back = get_context_data_scheduletab
    get_context_data_cal_forward = get_context_data_scheduletab

    def get_context_data_userlisttab(self, **kwargs):
        """Build the context for the userlist display.

        Keyword Parameters:
            **kwargs: Additional context data from parent classes.

        Returns:
            (dict): Context dictionary with opentab key for controlling tab state.
        """
        context = super().get_context_data(**kwargs)
        context["opentab"] = slugify(self.request.GET.get("opentab", "Manager"))
        return context


class LocationDetailView(HTMXProcessMixin, IsAuthenticaedViewMixin, views.generic.DetailView):
    """Detailed view for a location with tabbed interface.

    Provides a comprehensive detail view for locations with multiple tabs including
    resources, images, pages, and equipment list. Uses HTMX for dynamic tab loading.

    Attributes:
        template_name (str): Main template for location detail.
        template_name_resourcestab (str): Template for resources tab.
        template_name_imagestab (str): Template for images tab.
        template_name_pagestab (str): Template for pages tab.
        template_name_equipmenttab (str): Template for equipment tab.
        model: Location model class.
    """

    template_name = "equipment/location_detail.html"
    template_name_resourcestab = "equipment/parts/location_detail_resources.html"
    template_name_imagestab = "equipment/parts/location_detail_images.html"
    template_name_pagestab = "equipment/parts/location_detail_pages.html"
    template_name_equipmenttab = "equipment/parts/location_detail_equipment.html"

    model = Location

    def get_context_data_locationtab(self, **kwargs):
        """Build the context for the location tab display.

        Keyword Parameters:
            **kwargs: Additional context data from parent classes.

        Returns:
            (dict): Context dictionary for location tab.
        """
        context = super().get_context_data(**kwargs)


class ModelListView(HTMXProcessMixin, IsAuthenticaedViewMixin, views.generic.ListView):
    """Tabbed list view for equipment, locations, projects, documents, and accounts.

    Provides a unified interface for listing various model types across different tabs.
    Uses HTMX to dynamically load tab content and supports multiple context objects
    for different model types.

    Attributes:
        template_name (str): Main template for the list view.
        template_name_equipmenttab (str): Template for equipment list tab.
        template_name_locationstab (str): Template for locations list tab.
        template_name_projectstab (str): Template for projects list tab.
        template_name_documentstab (str): Template for documents list tab.
        template_name_accountstab (str): Template for accounts list tab.
        context_object_equipmenttab (str): Context object name for equipment.
        context_object_locationstab (str): Context object name for locations.
        context_object_projectstab (str): Context object name for projects.
        context_object_documentstab (str): Context object name for documents.
        context_object_accountstab (str): Context object name for accounts.
    """

    template_name = "equipment/lists.html"
    template_name_equipmenttab = "equipment/parts/equipment_list.html"
    template_name_locationstab = "equipment/parts/locations_list.html"
    template_name_projectstab = "equipment/parts/projects_list.html"
    template_name_documentstab = "equipment/parts/documents_list.html"
    template_name_accountstab = "equipment/parts/accounts_list.html"

    context_object_equipmenttab = "equipment"
    context_object_locationstab = "locations"
    context_object_projectstab = "cost_centres"
    context_object_documentstab = "documents"
    context_object_accountstab = "accounts"

    def get_queryset(self):
        """Get different querysets for each HTMX query.

        Returns different querysets based on the HTMX trigger, supporting equipment,
        locations, projects, documents, and accounts with appropriate filtering.

        Returns:
            (QuerySet or dict): QuerySet for the requested model type, or dictionary
                of querysets grouped by category or user group.
        """
        if not getattr(self.request, "htmx", False):
            ret = {}
            for grp in ["Academic", "Staff", "PDRA", "PostGrad", "Visitor", "Project"]:
                ret[grp] = Account.objects.filter(groups__name__icontains=grp).order_by("last_name", "first_name")
            return ret
        match getattr(self.request.htmx, "trigger", ""):
            case "equipment-tab":
                qs = Equipment.objects.all().order_by("category", "name")
            case "locations-tab":
                qs = Location.objects.all().order_by("tree_id", "lft", "name")
            case "projects-tab":
                qs = CostCentre.objects.all().order_by("tree_id", "lft")
            case "documents-tab":
                qs = {}
                for category in dict(Document.CATEGORIES):
                    qs[category] = Document.objects.filter(category=category)
            case _:
                qs = {}
                for grp in ["Academic", "Staff", "PDRA", "PostGrad", "Visitor", "Project"]:
                    if grp == "Academic":
                        qs[grp] = Account.objects.filter(groups__name__icontains=grp).order_by(
                            "last_name", "first_name"
                        )
                    else:
                        qs[grp] = Account.objects.filter(groups__name__icontains=grp).count()
        return qs

    def get_context_data_equipmenttab(self, **kwargs):
        """Extra context for equipment list.

        Groups equipment by category for organized display.

        Keyword Parameters:
            **kwargs: Additional context data from parent classes.

        Returns:
            (dict): Context dictionary with equipment grouped by category.
        """
        context = super().get_context_data(**kwargs)
        data = {}
        for category in Equipment.CATEGORIES:
            data[category] = context["equipment"].filter(category=category)
        context["equipment"] = data
        context["categories"] = Equipment.CATEGORIES
        return context

    def get_context_data_documentstab(self, **kwargs):
        """Extra context for documents list.

        Adds document categories to the context for display.

        Keyword Parameters:
            **kwargs: Additional context data from parent classes.

        Returns:
            (dict): Context dictionary with document categories.
        """
        context = super().get_context_data(**kwargs)
        context["categories"] = dict(Document.CATEGORIES)
        return context


class UserlisttDialog(IsAuthenticaedViewMixin, HTMXFormMixin, UpdateView):
    """HTMX dialog for creating and editing user list entries.

    Provides an HTMX-powered dialog interface for managing user list entries,
    which define user roles and permissions for specific equipment. Supports
    both creating new entries and editing existing ones.

    Attributes:
        model: UserListEntry model class.
        template_name (str): Template for the user list form dialog.
        context_object_name (str): Name for the object in template context.
        form_class: Form class for user list entries.
    """

    model = UserListEntry
    template_name = "equipment/userlist_form.html"
    context_object_name = "this"
    form_class = UserListEnryForm

    def get_context_data_dialog(self, **kwargs):
        """Create the context for HTMX calls to open the booking dialog."""
        context = super().get_context_data(**kwargs)
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
        """Make initial entry.

        Returns:
            (dict): Initial form data containing equipment and optionally user.
        """
        equipment = Equipment.objects.get(pk=self.kwargs.get("equipment", None))
        if "user" in self.kwargs:
            dd = self.kwargs
            user = Account.objects.get(pk=self.kwargs["user"])
            return {"equipment": equipment, "user": user}
        return {"equipment": equipment}

    def htmx_form_valid_userlistentry(self, form):
        """Handle the HTMX submitted user list form if valid.

        Saves the user list entry after checking permissions. Only managers,
        owners, and superusers can modify user list entries.

        Args:
            form: The validated form containing user list entry data.

        Returns:
            (HttpResponse): Empty response with HTMX trigger to refresh user list.

        Raises:
            HttpResponseForbidden: If user lacks permission to modify the entry.
        """
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
        """Handle the HTMX call that deletes a user list entry.

        Args:
            request: The HTTP request object.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            (HttpResponse): Empty response with HTMX trigger to refresh user list.

        Raises:
            HttpResponseNotFound: If the user list entry cannot be found.
            HttpResponseForbidden: If user lacks permission to delete the entry.
        """
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


class EquipmentDialog(IsAuthenticaedViewMixin, HTMXFormMixin, UpdateView):
    """HTMX dialog for editing equipment details.

    Provides an HTMX-powered dialog interface for editing equipment information
    such as name, description, category, and other equipment-specific settings.

    Attributes:
        model: Equipment model class.
        template_name (str): Template for the equipment form dialog.
        context_object_name (str): Name for the object in template context.
        form_class: Form class for equipment editing.
    """

    model = Equipment
    template_name = "equipment/equipment_form.html"
    context_object_name = "this"
    form_class = EquipmentForm

    def get_context_data_dialog(self, **kwargs):
        """Create the context for HTMX calls to open the booking dialog."""
        context = super().get_context_data(**kwargs)
        context["current_url"] = self.request.htmx.current_url
        context["this"] = self.get_object()
        args = (context["this"].pk,)
        context["post_url"] = reverse(f"equipment:edit_equipment", args=args)

        return context

    def get_object(self, queryset=None):
        """Either get the UserList entry or None."""
        try:
            return Equipment.objects.get(pk=self.kwargs.get("pk"))
        except (Equipment.DoesNotExist, AttributeError, KeyError):
            return None

    def htmx_form_valid_equipment(self, form):
        """Handle the HTMX submitted equipment form if valid.

        Args:
            form: The validated form containing equipment data.

        Returns:
            (HttpResponse): Empty response with HTMX trigger to refresh equipment display.
        """
        form.save()
        return HttpResponse(
            status=204,
            headers={"HX-Trigger": "refreshEquipment"},
        )


class ToggleAccountActiveView(IsSuperuserViewMixin, views.View):
    """HTMX view for toggling the is_active flag on an Account.

    Allows superusers to activate or deactivate accounts via an HTMX POST request.
    Returns a rendered Bootstrap 5 toggle switch reflecting the new state.

    Examples:
        POST /equipment/account/toggle-active/42/ toggles the is_active flag on Account pk=42
        and returns the updated toggle switch HTML fragment.
    """

    def post(self, request, pk, *args, **kwargs):
        """Toggle the is_active flag and return an updated toggle switch fragment.

        Args:
            request: The HTTP request object.
            pk (int): Primary key of the Account to toggle.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            (HttpResponse): Rendered HTML fragment containing the updated toggle switch.
        """
        if (accounts := Account.objects.filter(pk=pk)).count():
            account = accounts.last()
            account.is_active = not account.is_active
            account.save(update_fields=["is_active"])
        return render(request, "equipment/parts/account_active_toggle.html", {"account": account})

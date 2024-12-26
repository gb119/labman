# -*- coding: utf-8 -*-
"""
Created on Sun Jun 25 18:16:19 2023

@author: phygbu
"""
# Django imports
from django import views
from django.core.exceptions import ObjectDoesNotExist

# external imports
from extra_views import FormSetView
from htmx_views.views import HTMXProcessMixin
from labman_utils.views import IsAuthenticaedViewMixin

# app imports
from .forms import SignOffForm
from .models import DocumentSignOff, Equipment

# Create your views here.


class SignOffFormSetView(IsAuthenticaedViewMixin, FormSetView):
    """Provides the view for signing off risk assessments and SOPs to be allowed to book equipment."""

    template_name = "equipment/sign-off.html"
    form_class = SignOffForm
    success_url = "/accounts/me/"
    factory_kwargs = {"extra": 0, "max_num": None, "can_order": False, "can_delete": False}

    def get_initial(self):
        equipment_id = int(self.kwargs["equipment"])
        equipment = Equipment.objects.get(pk=equipment_id)
        docs = equipment.files.filter(category__in=["ra", "sop"])
        dataset = []
        for doc in docs:
            try:
                dso = DocumentSignOff.objects.get(user=self.request.user, document=doc, version=doc.version)
            except ObjectDoesNotExist:
                dso = DocumentSignOff(user=self.request.user, document=doc, version=doc.version)
            row = {"document": doc, "user": self.request.user, "version": doc.version, "signed": dso.pk is not None}
            if dso.pk:
                row["id"] = dso.id
            dataset.append(row)
        return dataset

    def formset_valid(self, formset):
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
        context = super().get_context_data(**kwargs)
        docs = [x.initial["document"] for x in context["formset"].forms]
        context["docs"] = docs
        return context


class EquipmentDetailView(HTMXProcessMixin, views.generic.DetailView):
    """Templated view for Equipment detail."""

    template_name = "equipment/equipment_detail.html"
    template_name_resourcestab = "equipment/parts/equipment_detail_resources.html"
    template_name_pagestab = "equipment/parts/equipment_detail_pages.html"
    template_name_userlisttab = "equipment/parts/equipment_detail_userlist.html"
    model = Equipment

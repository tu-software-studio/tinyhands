from django import forms
from django.db.models import Q
from django.db.models.functions import Lower
from .models import DataentryCountry, DataentryPerson

class ParamsForm(forms.Form):
    # TODO: Set all initial fields to "all" option
    countries = DataentryCountry.objects.values_list('name', flat=True).order_by('name').distinct()
    choices = [(country, country) for country in countries]
    choices.insert(0, ('All countries', "All countries"))
    country = forms.MultipleChoiceField(choices=choices, initial=["Argentina"], widget=forms.SelectMultiple(attrs={'class': 'form-control'}))

    # TODO: Refine query, by frequency?
    roles = DataentryPerson.objects.exclude(Q(role__contains=";") | Q(role__contains=",") | Q(role__contains=" ")).values_list("role", flat=True).annotate(handle_lower=Lower("role")).distinct("handle_lower")
    choices = [(role, role) for role in roles]
    choices.insert(0, ('All roles', "All roles"))
    role = forms.MultipleChoiceField(choices=choices, initial=["PVOT"], widget=forms.SelectMultiple(attrs={'class': 'form-control'}))

    genders = DataentryPerson.objects.values_list("gender", flat=True).distinct()
    choices = [(gender, gender) for gender in genders]
    choices.insert(0, ('All genders', "All genders"))
    gender = forms.MultipleChoiceField(choices=choices, initial=["F"], widget=forms.SelectMultiple(attrs={'class': 'form-control'}));


class IRFForm(forms.Form):
    # TODO: Consider adding a 3rd-party autocomplete library
    irf = forms.ChoiceField(label="IRF number")


class PersonForm(forms.Form):
    person = forms.ChoiceField(label="Person")


class FacematcherForm(forms.Form):
    number = forms.IntegerField(max_value=20, min_value=1, initial=5, label="Select number of face matches to retrieve")


class UploadPhotoForm(ParamsForm):
    photo = forms.FileField()

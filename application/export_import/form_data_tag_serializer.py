import json
import sys

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.serializers.base import DeserializationError
from django.core.serializers import base
from django.core.serializers.python import _get_model
from django.db import DEFAULT_DB_ALIAS, models
import six
from django.utils.encoding import force_str, is_protected_type

from export_import import form_data_serializer
from dataentry.models.form import *

def init_adjustments(adjustments):
    adjustments[Storage] = {'dropId':True, 'fk':{'parent_storage_id':Storage}}
    adjustments[Form] = {'dropId': True, 'clear-m2m': 'stations', 'fk':{'storage_id':Storage}}
    adjustments[Category] = {'dropId': True}
    adjustments[FormCategory] = {'dropId': True, 'fk':{'form_id':Form, 'category_id':Category, 'storage_id': Storage}}
    adjustments[Question] = {'dropId': True}
    adjustments[QuestionLayout] = {'dropId': True, 'fk':{'category_id':Category, 'question_id':Question}}
    adjustments[QuestionStorage] = {'dropId': True, 'fk':{'question_id':Question}}
    adjustments[Answer] = {'dropId': True, 'fk':{'question_id':Question}}
    adjustments[FormValidation] = {'dropId': True, 'fk':{'trigger_id':Question}, 'm2m':{'forms':Form}}
    adjustments[FormValidationQuestion] = {'dropId': True, 'fk':{'question_id':Question, 'validation_id':FormValidation}}
    adjustments[ExportImport] = {'dropId': True, 'fk':{'form_id':Form}}
    adjustments[ExportImportCard] = {'dropId': True, 'fk':{'export_import_id':ExportImport, 'category_id':Category}}
    adjustments[ExportImportField] = {'dropId': True, 'fk':{'export_import_id':ExportImport, 'card_id':ExportImportCard}}
    adjustments[GoogleSheetConfig] = {'dropId': True, 'fk':{'export_import_id':ExportImport}}

class Serializer(form_data_serializer.Serializer):
    def start_serialization(self):
        init_adjustments(self.adjustments)
        return super(Serializer, self).start_serialization()

"""
    Copy of python deserializer with changes for foreign key and m2m
"""
def PythonDeserializer(object_list, **options):
    """
        Change from standard python derserializer to get adjustments for tags
    """
    adjustments = {}
    init_adjustments(adjustments)
    
    """
    Deserialize simple Python objects back into Django ORM instances.

    It's expected that you pass the Python objects themselves (instead of a
    stream or a string) to the constructor
    """
    
    
    db = options.pop('using', DEFAULT_DB_ALIAS)
    ignore = options.pop('ignorenonexistent', False)
    field_names_cache = {}  # Model: <list of field_names>

    for d in object_list:
        # Look up the model and starting build a dict of data for it.
        try:
            Model = _get_model(d["model"])
        except base.DeserializationError:
            if ignore:
                continue
            else:
                raise
        data = {}
        if 'pk' in d:
            try:
                data[Model._meta.pk.attname] = Model._meta.pk.to_python(d.get('pk'))
            except Exception as e:
                raise base.DeserializationError.WithData(e, d['model'], d.get('pk'), None)
        m2m_data = {}

        if Model not in field_names_cache:
            field_names_cache[Model] = {f.name for f in Model._meta.get_fields()}
        field_names = field_names_cache[Model]

        # Handle each field
        for (field_name, field_value) in six.iteritems(d["fields"]):

            if ignore and field_name not in field_names:
                # skip fields no longer on model
                continue

            if isinstance(field_value, str):
                field_value = force_str(
                    field_value, options.get("encoding", settings.DEFAULT_CHARSET), strings_only=True
                )

            field = Model._meta.get_field(field_name)

            # Handle M2M relations
            if field.remote_field and isinstance(field.remote_field, models.ManyToManyRel):
                """
                    Get class object for m2m reference
                """
                if Model in adjustments and 'm2m' in adjustments[Model] and field.name in adjustments[Model]['m2m']:
                    cls = adjustments[Model]['m2m'][field.name]
                else:
                    cls = None
                    
                model = field.remote_field.model
                if hasattr(model._default_manager, 'get_by_natural_key'):
                    def m2m_convert(value):
                        if hasattr(value, '__iter__') and not isinstance(value, six.text_type):
                            return model._default_manager.db_manager(db).get_by_natural_key(*value).pk
                        else:
                            return force_str(model._meta.pk.to_python(value), strings_only=True)
                else:
                    def m2m_convert(v):
                        return force_str(model._meta.pk.to_python(v), strings_only=True)

                try:
                    m2m_data[field.name] = []
                    for pk in field_value:
                        if cls is None:
                            # No adjustment class - normal python deserializer
                            m2m_data[field.name].append(m2m_convert(pk))
                        else:
                            # convert tag to id
                            if hasattr( cls, 'get_by_form_tag' ):
                                foreign_object = cls.get_by_form_tag(pk)
                            else:
                                foreign_object = cls.objects.get(form_tag=pk)
                            m2m_data[field.name].append(m2m_convert(foreign_object.id))
                except Exception as e:
                    raise base.DeserializationError.WithData(e, d['model'], d.get('pk'), pk)

            # Handle FK fields
            elif field.remote_field and isinstance(field.remote_field, models.ManyToOneRel):
                model = field.remote_field.model
                if field_value is not None:
                    """
                        change from standard python deserializer for tags.
                        Retrieve foreign object by tag value and then update field_value to the id
                    """
                    if Model in adjustments and 'fk' in adjustments[Model] and field.attname in adjustments[Model]['fk']:
                        cls = adjustments[Model]['fk'][field.attname]
                        try:
                            foreign_object = cls.get_by_form_tag(field_value)
                        except Exception:
                            try:
                                foreign_object = cls.objects.get(form_tag=field_value)
                            except ObjectDoesNotExist:
                                raise Exception(f"Could set model field '{field.attname}' with form tag '{field_value}', is your form_data_XXX.json correct?")
                        
                        field_value = foreign_object.id
    
                    try:
                        default_manager = model._default_manager
                        field_name = field.remote_field.field_name
                        if hasattr(default_manager, 'get_by_natural_key'):
                            if hasattr(field_value, '__iter__') and not isinstance(field_value, six.text_type):
                                obj = default_manager.db_manager(db).get_by_natural_key(*field_value)
                                value = getattr(obj, field.remote_field.field_name)
                                # If this is a natural foreign key to an object that
                                # has a FK/O2O as the foreign key, use the FK value
                                if model._meta.pk.remote_field:
                                    value = value.pk
                            else:
                                value = model._meta.get_field(field_name).to_python(field_value)
                            data[field.attname] = value
                        else:
                            data[field.attname] = model._meta.get_field(field_name).to_python(field_value)
                    except Exception as e:
                        raise base.DeserializationError.WithData(e, d['model'], d.get('pk'), field_value)
                else:
                    data[field.attname] = None

            # Handle all other fields
            else:
                try:
                    data[field.name] = field.to_python(field_value)
                except Exception as e:
                    raise base.DeserializationError.WithData(e, d['model'], d.get('pk'), field_value)

        obj = base.build_instance(Model, data, db)
        yield base.DeserializedObject(obj, m2m_data)

"""
    Copy of JSON deserializer without modification
    Deserializer method needs to be defined in this file to work
"""
def Deserializer(stream_or_string, **options):
    """
    Deserialize a stream or string of JSON data.
    """
    if not isinstance(stream_or_string, (bytes, six.string_types)):
        stream_or_string = stream_or_string.read()
    if isinstance(stream_or_string, bytes):
        stream_or_string = stream_or_string.decode('utf-8')
    try:
        objects = json.loads(stream_or_string)
        for obj in PythonDeserializer(objects, **options):
            yield obj
    except GeneratorExit:
        raise
    except Exception as e:
        # Map to deserializer error
        six.reraise(DeserializationError, DeserializationError(e), sys.exc_info()[2])


        
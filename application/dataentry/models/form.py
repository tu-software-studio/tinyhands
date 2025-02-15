import pytz
import datetime
from django.db import models
from django.db.models import Q
from django.db.models import JSONField
from django.utils.timezone import make_aware

from accounts.models import Account

#
# Storage is used to describe the relationship between questions on a form
# and the storage of that data in models.  For example, the VIF model contains
# two instance of the Person model - the victim and the guardian.  To reflect
# this we could have data like
#   id   module_name                   form model_name            response_model_name parent_storage foreign_key_field_parent    foreign_key_field_child
#   10   dataentry.models.vif          Vif                        VifResponse         null           null                        null
#   11   dataentry.models.person_box   VictimInterviewPersonBox   null                10             null                        victim_interview                    
#   14   dataentry.models.location_box VictimInterviewLocationBox null                10             null                        victim_interview
class Storage(models.Model):
    form_tag = models.CharField(max_length=126, unique=True)
    module_name = models.CharField(max_length=126)
    form_model_name = models.CharField(max_length=126)
    response_model_name = models.CharField(max_length=126, null=True)
    parent_storage = models.ForeignKey('self', null=True, on_delete=models.CASCADE)
    foreign_key_field_parent = models.CharField(max_length=126, null=True)
    foreign_key_field_child = models.CharField(max_length=126, null=True)
    
    def get_form_storage_class(self):
        mod = __import__(self.module_name, fromlist=[self.form_model_name])
        form_class = getattr(mod, self.form_model_name, None)
        return form_class
    
    @staticmethod
    def get_objects_by_form_type(form_type_list):
        cls = globals()['Form']
        forms = cls.get_objects_by_form_type(form_type_list)
        model_names = set(forms.values_list('storage__form_tag', flat=True))
        qs = Storage.objects.filter(Q(form_tag__in=model_names) | Q(parent_storage__form_tag__in=model_names)).distinct().order_by('id')
        return qs        

# Keep track of checksum of currently loaded form_data.json file so that changes
# to that file can be automatically detected on startup and the new file can be loaded
class FormVersion(models.Model):
    file = models.CharField(max_length=126, unique=True, default='form_data.json')
    checksum = models.IntegerField()
    blocks = models.IntegerField()

class FormType(models.Model):
    name = models.CharField(max_length=126) # IRF, VIF, CEF, etc.
    tag_enabled = models.BooleanField(default=False)

class Form(models.Model):
    form_type = models.ForeignKey(FormType, on_delete=models.CASCADE)
    storage = models.ForeignKey(Storage, on_delete=models.CASCADE)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True)
    form_name = models.CharField(max_length=126, unique=True)
    version = models.CharField(max_length=126, null=True)

    # String to avoid circular import of BaseCard in border_station.py
    # Needs app prefix because otherwise subclass for legal cases thinks its in the legal Django app
    stations = models.ManyToManyField('dataentry.BorderStation')
    
    @property
    def form_tag(self):
        return self.form_name
    
    def find_form_class(self):
        mod = __import__(self.storage.module_name, fromlist=[self.storage.form_model_name])
        form_class = getattr(mod, self.storage.form_model_name)
        return form_class
        
    @staticmethod
    def current_form(form_type_name, station_id):
        today = make_aware(datetime.datetime.now())
        if station_id is None:
            form_list = Form.objects.filter(form_type__name=form_type_name, start_date__lte=today, end_date__gte=today)
        else:
            form_list = Form.objects.filter(form_type__name=form_type_name, start_date__lte=today, end_date__gte=today, stations__id=station_id)
        if len(form_list) > 0:
            return form_list[0]
        else:
            return None
    
    @staticmethod
    def get_by_form_tag(tag):
        return Form.objects.get(form_name = tag)
    
    @staticmethod
    def get_objects_by_form_type(form_type_list):
        qs = Form.objects.filter(form_type__name__in=form_type_list).distinct().order_by('id')
        return qs

class CategoryType(models.Model):
    name = models.CharField(max_length=126) # Grid, Card, etc.

class Category(models.Model):
    form_tag = models.CharField(max_length=126, unique=True)
    category_type = models.ForeignKey(CategoryType, on_delete=models.CASCADE)
    description = models.CharField(max_length=126)
    
    @staticmethod
    def get_objects_by_form_type(form_type_list):
        cls = globals()['FormCategory']
        form_categories = cls.get_objects_by_form_type(form_type_list)
        category_tags = set(form_categories.values_list('category__form_tag', flat=True))
        qs = Category.objects.filter(form_tag__in=category_tags).distinct().order_by('id')
        return qs
        
class FormCategory(models.Model):
    form = models.ForeignKey(Form, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    name = models.CharField(max_length=126)
    order = models.PositiveIntegerField(null=True, blank=True)
    # Json list for helping format the question, all properties will be added to the model on serialization
    # An example with a radio button and a checkbox:
    # {
    #     "questions": [
    #         {
    #             "type": "radio",
    #             "prompt": "# of subcommittee mettings",
    #             "options": [
    #                 {
    #                     "label": "0",
    #                     "format": "col-md-1",
    #                     "points": 0
    #                 },
    #                 {
    #                     "label": "1",
    #                     "format": "col-md-1",
    #                     "points": 20
    #                 },
    #                 {
    #                     "label": "2",
    #                     "format": "col-md-1",
    #                     "points": 30
    #                 },
    #                 {
    #                     "label": ">2",
    #                     "format": "col-md-1",
    #                     "points": 40
    #                 }
    #             ],
    #             "question_id": 716,
    #             "prompt_format": "col-md-2 control-label"
    #         }
    #     ],
    #     "checkboxes": [
    #         {
    #             "type": "checkbox",
    #             "label": "Records",
    #             "format": "col-md-2",
    #             "points": 5,
    #             "question_id": 718
    #         }
    #     ]
    # }
    form_category_question_config = JSONField(null=True)
    
    # Only needed for card type category
    storage = models.ForeignKey(Storage, null=True, on_delete=models.CASCADE)
    
    @staticmethod
    def get_objects_by_form_type(form_type_list):
        forms = Form.get_objects_by_form_type(form_type_list)
        qs = FormCategory.objects.filter(form__in=forms).distinct().order_by('id')
        return qs

class AnswerType(models.Model):
    name = models.CharField(max_length=126) # Multiple Choice, Int, Address, Phone Num, etc.

class Question(models.Model):
    form_tag = models.CharField(max_length=126, unique=True)
    prompt = models.CharField(max_length=126, blank=True)
    description = models.CharField(max_length=126, null=True)
    answer_type = models.ForeignKey(AnswerType, on_delete=models.CASCADE)
    params=JSONField(null=True)   # custom parameters for this question type
    export_name = models.CharField(max_length=126, null=True)
    export_params = JSONField(null=True)
    
    def export_header_Address(self, prefix):
        if self.export_name is not None and  self.export_name != '':
            prefix = prefix + self.export_name + ' '
 
        export_header_list = [
            prefix + 'address1', 
            prefix + 'address2']
        
        return export_header_list
        
    
    def export_header_Person(self, prefix):
        if self.export_name is not None and  self.export_name != '':
            prefix = prefix + self.export_name + ' '
            
        if self.export_params is None or self.export_params['export_parts'] is None:
            return []
        
        export_header_list = []
        for part in self.export_params['export_parts']:
            export_header_list.append(prefix + part['label'])

        return export_header_list
    
    def export_header_ArcGisAddress(self, prefix):
        if self.export_name is not None and  self.export_name != '':
            prefix = prefix + self.export_name + ' '
 
        export_header_list = [prefix]
        
        return export_header_list
    
    def export_headers(self, prefix):
        header_method_name = 'export_header_' + self.answer_type.name
        header_method = getattr(self, header_method_name, None)
        if header_method is not None:
            headers = header_method(prefix)
        else:
            if self.export_name is None:
                headers = [prefix + '']
            else:
                headers = [prefix + self.export_name]
        
        return headers
    
    def format_DateTime(self, answer, station):
        if answer is None:
            formatted_answer_list = ['']
        else:
            tz = pytz.timezone(station.time_zone)
            date_time = answer.astimezone(tz)
            if (date_time.second == 1):
                formatted_answer_list = [str(date_time.replace(tzinfo=None))[:10]]
            else:
                formatted_answer_list = [str(date_time.replace(tzinfo=None))]
        return formatted_answer_list
    
    def format_Address(self, answer, station):
        if answer is None:
            formatted_answer_list = [
                    '',
                    ''
                ]
        else:
            formatted_answer_list = [
                    answer.address1.name,
                    answer.name
                ]
        
        return formatted_answer_list
    
    def format_Person(self, answer, station):
        if self.export_params is None or self.export_params['export_parts'] is None:
            return []
        formatted_answer_list = [];
        if answer is None:
            for part in self.export_params['export_parts']:
                formatted_answer_list.append('')
        else:
            for part in self.export_params['export_parts']:
                value = getattr(answer, part['field'], '')
                if part['field'] == 'gender':
                    if value == 'F':
                        value = 'Female'
                    elif value == 'M':
                        value = 'Male'
                    else:
                        value = 'Unknown'
                elif part['field'] == 'address' and value is not None and value != '':
                    value = value['address']
                elif part['field'] == 'ID':
                    value = ''
                    ids = answer.personidentification_set.all()
                    for id in ids:
                        value += id.type + ':' + id.number + ','
               
                formatted_answer_list.append(value)
        
        return formatted_answer_list
    
    def format_answer_map(self, answer):
        if self.export_params is not None and 'answer_map' in self.export_params and self.export_params['answer_map'] == True:
            answers = Answer.objects.filter(question=self.question, code=answer)
            if len(answers) > 0:
                formatted_answer = answers[0].value
            else:
                formatted_answer = answer
        else:
            formatted_answer = answer
        
        return [formatted_answer]
    
    def format_RadioButton(self, answer, station):
        if answer is None:
            formatted_answer = ['']
        else:
            formatted_answer = self.format_answer_map(answer)
        return formatted_answer
    
    def format_DropDown(self, answer, station):
        if answer is None:
            formatted_answer = ['']
        else:
            formatted_answer = self.format_answer_map(answer)
        return formatted_answer
    
    def format_ArcGisAddress(self, answer, station):
        if answer is None:
            formatted_answer = ''
        else:
            if 'address' in answer:
                formatted_answer = answer['address']
            else:
                formatted_answer = ''
        
        return [ formatted_answer ]
    
    def format_default(self, answer, station):
        if answer is None:
            formatted_answer_list = ['']
        else:
            formatted_answer_list = [answer]
        return formatted_answer_list
    
    def export_value(self, form_data, main_data):
        if form_data is None:
            answer = None
        else:
            answer = form_data.get_answer(self)
        format_method_name = 'format_' + self.answer_type.name
        format_method = getattr(self, format_method_name, None)
        if format_method is not None:
            answer_list = format_method(answer, main_data.form_object.station)
        else:
            answer_list = self.format_default(answer, main_data.form_object.station)
        
        if self.export_params is not None and 'map' in self.export_params and len(answer_list) == 1:
            the_map = self.export_params['map']
            if answer_list[0] in the_map:
                answer_list = [the_map[answer_list[0]]]
            elif 'default' in the_map:
                answer_list = [the_map['default']]
                
        return answer_list
    
    @staticmethod
    def get_objects_by_form_type(form_type_list):
        cls = globals()['QuestionLayout']
        layouts = cls.get_objects_by_form_type(form_type_list)
        question_tags = set(layouts.values_list('question__form_tag', flat=True))
        qs = Question.objects.filter(form_tag__in=question_tags).distinct().order_by('id')
        return qs

class QuestionLayout(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    weight = models.IntegerField(default=0)
    form_config = JSONField(null=True)
    
    @staticmethod
    def get_objects_by_form_type(form_type_list):
        categories = Category.get_objects_by_form_type(form_type_list)
        qs = QuestionLayout.objects.filter(category__in=categories).distinct().order_by('id')
        return qs

class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    value = models.CharField(max_length=100000, null=True)
    code = models.CharField(max_length=125, null=True)
    params=JSONField(null=True)   # custom parameters for this answer type
    
    @staticmethod
    def get_objects_by_form_type(form_type_list):
        questions = Question.get_objects_by_form_type(form_type_list)
        qs = Answer.objects.filter(question__in=questions).distinct().order_by('id')
        return qs


# Identifies validation for IRF or VIF form
#  GENERIC
#    - not_blank_or_null verifies that the answers to the questions are not blank or null
#    - at_least_one_true verifies that at least one of the answers to the questions is true
#  CUSTOM
#    - at_least_one_interceptee verifies that there is at least one interceptee on the IRF
#    - name_came_up_before verifies the answer for the name came up before question on the IRF
#    - trafficker_custody verifies answer for the trafficker taken into custody question on the IRF
class FormValidationType(models.Model):
    name = models.CharField(max_length=126)

# basic_error  - prevents form from being saved (cannot save form with pending status)
# submit_error - prevents form from being submitted (cannot save form with active status)
# warning      - can be overridden to allow the form to be submitted
class FormValidationLevel(models.Model):
    name = models.CharField(max_length=126)

# form - the form on which the question(s) should be validated
# trigger - question whose answer determines if the validation should be performed
#    If trigger question is not null and the answer to the trigger question is true, the validation should be performed
#    If trigger question is null, the validation should always be performed
# validation_type - Is the type of validation to be performed on the questions
# error_warning_message - message returned to client when validation fails
class FormValidation(models.Model):
    form_tag = models.CharField(max_length=126, unique=True)
    level = models.ForeignKey(FormValidationLevel, on_delete=models.CASCADE)
    trigger = models.ForeignKey(Question, null=True, on_delete=models.CASCADE)
    trigger_value = models.CharField(max_length=126, null=True)
    validation_type = models.ForeignKey(FormValidationType, on_delete=models.CASCADE)
    error_warning_message = models.CharField(max_length=126)
    params=JSONField(null=True)
    forms = models.ManyToManyField(Form)
    retrieve = models.BooleanField()
    update = models.BooleanField()
    
    @staticmethod
    def get_objects_by_form_type(form_type_list):
        forms = Form.get_objects_by_form_type(form_type_list)
        qs = FormValidation.objects.filter(forms__in=forms).distinct().order_by('id')
        return qs

# Set of questions to be validated for the FormValidation
class FormValidationQuestion(models.Model):
    validation = models.ForeignKey(FormValidation, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    
    @staticmethod
    def get_objects_by_form_type(form_type_list):
        validations = FormValidation.get_objects_by_form_type(form_type_list)
        qs = FormValidationQuestion.objects.filter(validation__in=validations).distinct().order_by('id')
        return qs

class Condition(models.Model):
    condition = JSONField() 
    # {"type":"red", {12: "true", 14: "false"}, points: 10}
    # Type determines red flag,warning,home situation, etc.
    # Second dictionary associates question with answer (dereferenced to use value in this example)
    # Points would make sense for conditions that may cummulate in their severity

#
# QuestionStorage is used to specify that the question response will be
# stored in a field of the forms model as opposed to being stored as a
# generic response.
# For example, an entry could specify that the response to the 'IRF Number'
# question would be stored in the field name 'irf_number'
class QuestionStorage(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    field_name = models.CharField(max_length=100)
    
    @staticmethod
    def get_objects_by_form_type(form_type_list):
        questions = Question.get_objects_by_form_type(form_type_list)
        qs = QuestionStorage.objects.filter(question__in=questions).distinct().order_by('id')
        return qs

 #
 #  Work still needed on the export/import classes
 #
class ExportImport(models.Model):
    form_tag = models.CharField(max_length=126, unique=True)
    description = models.CharField(max_length=126, null = True)
    implement_module = models.CharField(max_length=126, null=True)
    implement_class_name = models.CharField(max_length=126, null=True)
    form = models.ForeignKey(Form, on_delete=models.CASCADE)
    
    @staticmethod
    def get_objects_by_form_type(form_type_list):
        forms = Form.get_objects_by_form_type(form_type_list)
        qs = ExportImport.objects.filter(form__in=forms).distinct().order_by('id')
        return qs

class GoogleSheetConfig(models.Model):
    export_import = models.ForeignKey(ExportImport, on_delete=models.CASCADE)
    export_or_import = models.CharField(max_length=10)
    spreadsheet_name = models.CharField(max_length=126)
    sheet_name = models.CharField(max_length=126)
    key_field_name = models.CharField(max_length=126)
    import_status_column = models.CharField(max_length=126, null = True)
    import_issue_column = models.CharField(max_length=126, null=True)
    suppress_column_warnings = models.BooleanField(default=True)
    
    @staticmethod
    def get_objects_by_form_type(form_type_list):
        export_imports = ExportImport.get_objects_by_form_type(form_type_list)
        qs = GoogleSheetConfig.objects.filter(export_import__in=export_imports).distinct().order_by('id')
        return qs
    
class ExportImportCard(models.Model):
    export_import = models.ForeignKey(ExportImport, related_name='export_import_base', on_delete=models.CASCADE)
    category = models.ForeignKey(Category, related_name='export_import_card', on_delete=models.CASCADE)
    prefix = models.CharField(max_length=126)
    max_instances = models.PositiveIntegerField()
    index_field_name = models.CharField(max_length=126, null=True)
    
    @staticmethod
    def get_objects_by_form_type(form_type_list):
        export_imports = ExportImport.get_objects_by_form_type(form_type_list)
        qs = ExportImportCard.objects.filter(export_import__in=export_imports).distinct().order_by('id')
        return qs

# data fields to be exported for which there is no question
class ExportImportField(models.Model):
    export_import = models.ForeignKey(ExportImport, on_delete=models.CASCADE)
    card = models.ForeignKey(ExportImportCard, null=True, on_delete=models.CASCADE)
    field_name = models.CharField(max_length=126)
    answer_type = models.ForeignKey(AnswerType, related_name='field_answer_type', on_delete=models.CASCADE)
    export_name = models.CharField(max_length=126)
    arguments_json = JSONField(null=True)
    
    def format_DateTime(self, answer, station):
        tz = pytz.timezone(station.time_zone)
        date_time = answer.astimezone(tz)
        return str(date_time.replace(tzinfo=None))
    
    def format_parts(self, answer):
        if self.arguments_json is not None and 'part' in self.arguments_json:
            part_list = self.arguments_json['part'].split('.')
            formatted_answer = answer
            for part in part_list:
                if formatted_answer is None:
                    break
                formatted_answer = getattr(formatted_answer, part, None)
        else:
            # log error
            formatted_answer = None
        
        return formatted_answer
    
    def format_Address(self, answer, station):
        return self.format_parts(answer)
    
    def format_Person(self, answer, station):
        return self.format_parts(answer)
    
    def export_value(self, form_obj, main_data):
        answer = getattr(form_obj, self.field_name)
        if answer is not None:
            format_method_name = 'format_' + self.answer_type.name
            format_method = getattr(self, format_method_name, None)
            if format_method is not None:
                answer = format_method(answer, main_data.form_object.station)
        
        if self.arguments_json is not None and 'map' in self.arguments_json:
            the_map = self.arguments_json['map']
            if answer in the_map:
                answer = the_map[answer]
            elif 'default' in the_map:
                answer = the_map['default']
                
        return answer
    
    @staticmethod
    def get_objects_by_form_type(form_type_list):
        export_imports = ExportImport.get_objects_by_form_type(form_type_list)
        qs = ExportImportField.objects.filter(export_import__in=export_imports).distinct().order_by('id')
        return qs

class BaseForm(models.Model):
    status = models.CharField('Status', max_length=20, default='pending')
    # String to avoid circular import of BaseCard in border_station.py
    # Needs app prefix because otherwise subclass for legal cases thinks its in the legal Django app
    station = models.ForeignKey('dataentry.BorderStation', on_delete=models.CASCADE)
    date_time_entered_into_system = models.DateTimeField(auto_now_add=True)
    date_time_last_updated = models.DateTimeField(auto_now=True)
    form_entered_by = models.ForeignKey(Account, related_name='%(class)s_entered_by', null=True, on_delete=models.SET_NULL)
    form_version = models.CharField(max_length=126, null=True)
    
    class Meta:
        abstract = True
    
    # Override in subclass when common master person is enabled
    def get_common_master_person(self):
        return None
    
    # Overridden in subclass
    def get_key(self):
        return None
    
    # Overridden in subclass as needed
    def pre_save(self, form_data):
        pass
    
    def post_save(self, form_data):
        pass
        
class BaseResponse(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    value = models.CharField(max_length=100000, null=True)
    
    class Meta:
        abstract = True
        
class BaseCard(models.Model):
    class Meta:
        abstract = True
    
    def setParent(self, the_parent):
        raise NotImplementedError("set parent not defined in card model")
    
    def is_private(self):
        return False
    
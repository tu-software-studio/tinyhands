import logging
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from .models.form import Form, FormCategory, QuestionLayout, QuestionStorage, Storage

logger = logging.getLogger(__name__);

class PersonContainer:
    def __init__(self, person, current_person_identifications, remove_person_identifications, question):
        self.person = person
        self.current_identifications = current_person_identifications
        self.remove_identifications = remove_person_identifications
        self.question = question

class CategoryForm:
    def __init__(self, category, card_class, card_response_class, foreign_key_field_parent):
        self.category = category
        self.form_model = card_class
        self.response_model = card_response_class
        self.foreign_key_field_parent = foreign_key_field_parent
        
class CardData:
    def load_responses(self):
        if self.category_form.response_model is not None:
            responses = self.category_form.response_model.objects.filter(parent = self.form_object)
            self.response_dict = {}
            for response in responses:
                self.response_dict[response.question.id] = response
        else:
            self.response_dict = {}
            
    def __init__(self, card, category_form, response_dict = None, form_data=None):
        self.form_data = form_data
        self.form_object = card
        self.category_form = category_form
        self.is_valid = True
        self.person_containers = []
        self.multi_reference = []
        
        if response_dict is None:
            self.load_responses()
        else:
            self.response_dict = response_dict
    
    def invalidate_card(self):
        self.is_valid = False
    
    def in_form_object(self, question):
        return question.id in self.form_data.question_storage
            
    def get_answer(self, question, value=True):
        try:
            if self.in_form_object(question):
                answer = getattr(self.form_object, self.form_data.question_storage[question.id].field_name, None)
            else:
                if question.id in self.response_dict:
                    if value:
                        answer = self.response_dict[question.id].value
                    else:
                        answer = self.response_dict[question.id]
                else:
                    answer = None
        except ValueError as ve:
            answer = None
        
        return answer
    
    def set_answer (self, question, answer, storage_id):
        if self.in_form_object(question):
            setattr(self.form_object, self.form_data.question_storage[question.id].field_name, answer)
        else:
            if storage_id:
                card_response = self.category_form.response_model.objects.get(id=storage_id)
                card_response.parent = self.form_data.form_object
                card_response.question = question
            else:
                card_response = self.category_form.response_model()
                
            card_response.value = answer
            
            self.response_dict[question.id] = card_response
        
    def set_multi_reference(self, question, object_list):
        tmp = {
            'question':question,
            'object_list': object_list
            }
        self.multi_reference.append(tmp)
    
    def get_answer_storage(self, question):
        if self.in_form_object(question):
            storage = self.form_object.id
        elif question.id in self.response_dict:
            storage = self.response_dict[question.id].id
        else:
            storage = None
        
        return storage
    
    def save(self):
        # first store any person data assoicated with the card
        for person_container in self.person_containers:
            person_container.person.save()
            for remove_identification in person_container.remove_identifications:
                remove_identification.delete()
            for current_identification in person_container.current_identifications:
                current_identification.person = person_container.person
                current_identification.save()
            self.set_answer(person_container.question, person_container.person, None)
        
        self.form_object.set_parent(self.form_data.form_object)
        self.form_object.save()
        for response in self.response_dict.values():
            response.parent = self.form_object
            response.save()
        
        for multi_ref in self.multi_reference:
            answer = getattr(self.form_object, self.question_storage[multi_ref['question'].id].field_name, None)
            answer.clear()
            for obj_ref in multi_ref['object_list']:
                answer.add(obj_ref)
            self.form_object.save()
    
    def delete(self):
        for response in self.response_dict.values():
            response.delete()
            
        self.form_object.delete()
        

class FormData:
    def load_responses(self):
        if self.response_model is not None:
            responses = self.response_model.objects.filter(parent = self.form_object)
            self.response_dict = {}
            for response in responses:
                self.response_dict[response.question.id] = response
        else:
            self.response_dict = {}
            
    def load_cards(self, category, the_object):
        card_list = []
        category_form = self.category_form_dict[category.id]
        if category_form.foreign_key_field_parent is None:
            raise Exception(f"When loading cards for {category_form.category.form_tag} on {category_form.form_model.__name__},"
                            f" could not find 'foreign_key_field_parent', is form.json right?\n"
                            f"Check formcategory for the right storage and storage for the right foreign_key_field_parent\n"
                            f"Then reload form data")
        
        cards = eval('category_form.form_model.objects.filter(' + category_form.foreign_key_field_parent + '__id=the_object.id)').order_by('id')
        for card in cards:
            card_list.append(CardData(card, category_form, form_data=self))
        
        return card_list
    
    def load_question_storage(self, form):
        self.question_storage = {}
        form_categories = FormCategory.objects.filter(form=form)
        category_list = []
        for form_category in form_categories:
            category_list.append(form_category.category)
        question_ids = list(QuestionLayout.objects.filter(category__in = category_list).values_list('question_id', flat=True))
        question_storage_list = QuestionStorage.objects.filter(question__id__in=question_ids)
        for question_storage in question_storage_list:
            self.question_storage[question_storage.question.id] = question_storage
            
    
    def __init__(self, the_object, form):
        self.form = form
        self.form_object = the_object
        self.form_model = the_object.__class__
        self.person_containers = []
        self.multi_reference = []
        storage_list = Storage.objects.filter(form_model_name = the_object.__class__.__name__)
        storage = storage_list[0]
        if storage.response_model_name is not None:
            mod = __import__(storage.module_name, fromlist=[storage.response_model_name])
            self.response_model = getattr(mod, storage.response_model_name, None)
            if self.response_model is None:
                logger.error("Unable to resolve response model")
                self.response_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        else:
            self.response_model = None
        
        self.load_question_storage(form)
        
        self.response_dict = {}
        self.load_responses()
            
        self.card_dict = {}
        self.category_form_dict = {}
        form_categories = FormCategory.objects.filter(form=self.form, category__category_type__name = 'card')
        for form_category in form_categories:
            mod = __import__(form_category.storage.module_name, fromlist=[form_category.storage.form_model_name, form_category.storage.response_model_name])
            card_model = getattr(mod, form_category.storage.form_model_name, None)
            if form_category.storage.response_model_name is not None:
                card_response_model = getattr(mod, form_category.storage.response_model_name, None)
            else:
                card_response_model = None
            category_form = CategoryForm(form_category.category, card_model, card_response_model, form_category.storage.foreign_key_field_parent)
            self.category_form_dict[form_category.category.id] = category_form
            if the_object.id is None:
                self.card_dict[form_category.category.id] = []
            else:
                card_list = self.load_cards(form_category.category, the_object)
                self.card_dict[form_category.category.id] = card_list
                
    def find_card(self, category, card_id):
        ret = None
        card_list = self.card_dict[category.id]
        for card in card_list:
            if card.form_object.id == card_id:
                ret = card
                break
        
        return ret
        
    
    def in_form_object(self, question):
        return question.id in self.question_storage
    
    def get_answer(self, question, value=True):
        try:
            if self.in_form_object(question):
                answer = getattr(self.form_object, self.question_storage[question.id].field_name, None)
            else:
                if question.id in self.response_dict:
                    if value:
                        answer = self.response_dict[question.id].value
                    else:
                        answer = self.response_dict[question.id]
                else:
                    answer = None
        except ValueError as ve:
            answer = None
        
        return answer
    
    def set_answer (self, question, answer, storage_id):
        if self.in_form_object(question):
            setattr(self.form_object, self.question_storage[question.id].field_name, answer)
        else:
            if question.id in self.response_dict:
                self.response_dict[question.id].value = answer
                self.response_dict[question.id].id = storage_id
            else:
                 logger.error("Unable to locate question with id " + str(question.id) + " in response_dict")
    
    def set_multi_reference(self, question, object_list):
        tmp = {
            'question':question,
            'object_list': object_list
            }
        self.multi_reference.append(tmp)
    
    def get_answer_storage(self, question):
        if self.in_form_object(question):
            storage = self.form_object.id
        elif question.id in self.response_dict:
            storage = self.response_dict[question.id].id
        else:
            storage = None
        
        return storage
    
    def invalidate_cards(self):
        for card_list in self.card_dict.values():
                for card in card_list:
                    card.invalidate_card()        
    
    def save(self):
        with transaction.atomic():
            self.form_object.pre_save(self)
            
            for person_container in self.person_containers:
                person_container.person.save()
                for remove_identification in person_container.remove_identifications:
                    remove_identification.delete()
                for current_identification in person_container.current_identifications:
                    current_identification.person = person_container.person
                    current_identification.save()
                self.set_answer(person_container.question, person_container.person, None)
            
            self.form_object.save()
            for response in self.response_dict.values():
                response.parent = self.form_object
                response.save()
            
            for multi_ref in self.multi_reference:
                answer = getattr(self.form_object, self.question_storage[multi_ref['question'].id].field_name, None)
                answer.clear()
                for obj_ref in multi_ref['object_list']:
                    answer.add(obj_ref)
                self.form_object.save()
            
            for card_key, card_list in self.card_dict.items():
                new_card_list = []
                for card in card_list:
                    if card.is_valid:
                        card.save()
                        new_card_list.append(card)
                    else:
                        card.delete()
                self.card_dict[card_key] = new_card_list
            
            self.form_object.post_save(self)
    
    def delete(self):
        with transaction.atomic():
            for card_list in self.card_dict.values():
                for card in card_list:
                    card.delete()
            
            for response in self.response_dict.values():
                response.delete()
            
            self.form_object.delete()
    
    def __str__(self):
        if self.form_object is not None:
            return str(self.form_object)
        else:
            return None
    
    @staticmethod
    def find_form(form_type_name, station_id):
        form = Form.current_form(form_type_name, station_id)
        return form
            
    @staticmethod
    def get_form_class(form):
        mod = __import__(form.storage.module_name, fromlist=[form.storage.form_model_name])
        form_class = getattr(mod, form.storage.form_model_name)
        return form_class
    
    @staticmethod
    def get_form_card_class(form, card_name):
        card_class = None
        try:
            form_category = FormCategory.objects.get(form=form, name=card_name)
            if form_category.storage is not None:
                mod = __import__(form_category.storage.module_name, fromlist=[form_category.storage.form_model_name])
                card_class = getattr(mod, form_category.storage.form_model_name)
        except ObjectDoesNotExist:
            pass
        
        return card_class
    
    @staticmethod
    def find_object_by_number(key_value, form_type_name, station=None):
        form_object = None
        if station is None:
            forms = Form.objects.filter(form_type__name=form_type_name)
        else:
            forms = Form.objects.filter(form_type__name=form_type_name, stations = station)
            
        for form in forms:
            mod = __import__(form.storage.module_name, fromlist=[form.storage.form_model_name])
            form_class = getattr(mod, form.storage.form_model_name)
            key_field = form_class.key_field_name()
            try:
                form_object = eval('form_class.objects.get(' + key_field + '=key_value)')
            except ObjectDoesNotExist:
                pass
        
        return form_object
    
    @staticmethod
    def find_object_by_id(obj_id, form):
        form_class = form.find_form_class()
        try:
            form_object = form_class.objects.get(id=obj_id)
        except ObjectDoesNotExist:
            form_object = None   
        
        return form_object
            
        
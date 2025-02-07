import os
from django.core.management import call_command
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.color import no_style
from django.db import connection, transaction
from .form import Form, FormVersion
from .border_station import BorderStation
from dataentry.models import Category, Form, FormCategory, FormType, QuestionLayout, QuestionStorage
from export_import.load_form_data import LoadFormData

class FormMigration:
    form_model_names = [
        'FormType',
        'Storage',
        'Form',
        'CategoryType',
        'Category',
        'FormCategory',
        'AnswerType',
        'Question',
        'QuestionLayout',
        'QuestionStorage',
        'Answer',
        'FormValidationLevel',
        'FormValidationType',
        'FormValidation',
        'FormValidationQuestion',
        'ExportImport',
        'ExportImportCard',
        'ExportImportField',
        'GoogleSheetConfig',
        ]
    
    # preserve existing connections between form and border stations
    @staticmethod
    def get_form_to_station_references():
        reference_list = []
        forms = Form.objects.all()
        for form in forms:
            stations = form.stations.all()
            for station in stations:
                reference_list.append({'form_name':form.form_name, 'station_code':station.station_code})
            
        return reference_list

    @staticmethod
    def load_fixture(apps, schema_editor, fixture_dir, fixture_filename):
        fixture_file = os.path.join(fixture_dir, fixture_filename)
        call_command('loaddata', fixture_file)
    
    @staticmethod
    def unload_prior(apps):
        class_models = [apps.get_model('dataentry', 'FormVersion')]
        for model_name in reversed(FormMigration.form_model_names):
            my_model = apps.get_model('dataentry', model_name)
            class_models.append(my_model)
            my_model.objects.all().delete()
            
        sequence_sql = connection.ops.sequence_reset_sql(no_style(), class_models)
        with connection.cursor() as cursor:
            for sql in sequence_sql:
                cursor.execute(sql)
    
    # restore connections between form and border stations
    @staticmethod
    def restore_form_to_station_references(reference_list):
        for reference in reference_list:
            try:
                form = Form.objects.get(form_name=reference['form_name'])
                try:
                    station = BorderStation.objects.get(station_code=reference['station_code'])
                    form.stations.add(station)
                except ObjectDoesNotExist:
                    print ('Unable for find station to restore reference from form ' + reference['form_name'] + 
                           ' to station with code ' + reference['station_code'])
            except ObjectDoesNotExist:
                print ('Unable for find form to restore reference from form ' + reference['form_name'] + 
                           ' to station with code ' + reference['station_code'])

    @staticmethod
    def migrate(apps, schema_editor, fixture_filename):
        # No longer used, but old migrations still reference this method
        return
#         fixture_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../fixtures'))
#         file_path = fixture_dir + '/' + fixture_filename
#         if os.access(file_path, os.R_OK):
#             reference_list = FormMigration.get_form_to_station_references()
#             FormMigration.unload_prior(apps)
#             FormMigration.load_fixture(apps, schema_editor, fixture_dir, fixture_filename)
#             FormMigration.restore_form_to_station_references(reference_list)
#         else:
#             print('Fixture ' + file_path + 'not found - skipping form migration')
    
    @staticmethod
    def buildView(form_type_name):
        cxn = transaction.get_connection()
        if cxn.in_atomic_block:
            in_transaction = True
        else:
            in_transaction = False
            
        forms = Form.objects.filter(form_type__name=form_type_name)
        
        # build map from field question information is stored in to list of stations that store that information
        storage_map = {}
        form_categories = FormCategory.objects.filter(form__in=forms)
        for form_category in form_categories:
            layouts = QuestionLayout.objects.filter(category=form_category.category)
            for layout in layouts:
                question_storage = QuestionStorage.objects.get(question=layout.question)
                field = question_storage.field_name
                if field not in storage_map:
                    storage_map[field] = []
                
                if form_category.form.form_name not in storage_map[field]:
                    storage_map[field].append(form_category.form.form_name)
        
        sql = 'CREATE or REPLACE VIEW ' + form_type_name.lower() + 'combined as select '
        storage_class = forms[0].storage.get_form_storage_class()
        dummy = storage_class()
        sep = ''
        for member in dummy.__dict__.keys(): 
            if member == '_state':
                continue
            if member in storage_map and len(storage_map[member]) < len(forms):
                    sql += sep + 'CASE WHEN fn.form_name in ('
                    sep2=''
                    for code in storage_map[member]:
                        sql += sep2 + "'" + code + "'"
                        sep2 = ','
                    sql += ') THEN ' + 'f.' + member + '  ELSE null END as ' + member
            else:
                sql += sep + 'f.' + member
            
            sep = ','  
        
        sql += ', fn.form_name from dataentry_' + form_type_name.lower() + 'common as f inner join '\
            '(select s.id, min(f2.form_name) as form_name '\
            'from dataentry_borderstation as s '\
            'inner join dataentry_form_stations as fs on s.id = fs.borderstation_id '\
            'inner join dataentry_form as f2 on fs.form_id = f2.id '\
            'inner join dataentry_formtype as f3 on f2.form_type_id = f3.id '\
            "where f3.name='" + form_type_name + "' "\
            'group by s.id) as fn '\
            'on f.station_id = fn.id'
            
        
        cursor = connection.cursor()
        cursor.execute('DROP VIEW IF EXISTS ' + form_type_name.lower() + 'combined')
        cursor.execute(sql)
        if not in_transaction:
            transaction.commit()
        
        print ('View ' + form_type_name.lower() + 'combined recreated')
        
    @staticmethod
    def pending_match_view():
        cxn = transaction.get_connection()
        if cxn.in_atomic_block:
            in_transaction = True
        else:
            in_transaction = False
        sql ="create view pendingmatchwithcountry AS select distinct cast(dm.id as CHAR) || '-' || cast(dj.operating_country_id as CHAR) as the_key, dm.id as person_match_id, dj.operating_country_id as country_id "\
            'from dataentry_personmatch dm, ( '\
                'select distinct db.operating_country_id, dp.master_person_id '\
                'from dataentry_cifcommon dc '\
                    'inner join dataentry_person dp on dc.main_pv_id = dp.id '\
                    'inner join dataentry_borderstation db on db.id = dc.station_id '\
                'union '\
                'select distinct db.operating_country_id, dp.master_person_id '\
                'from dataentry_cifcommon dc '\
                    'inner join dataentry_personboxcommon dp1 on dc.id = dp1.cif_id '\
                    'inner join dataentry_person dp on dp1.person_id = dp.id '\
                    'inner join dataentry_borderstation db on db.id = dc.station_id '\
                    'union '\
                'select distinct db.operating_country_id, dp.master_person_id '\
                'from dataentry_cifcommon dc '\
                    'inner join dataentry_potentialvictimcommon dp1 on dc.id = dp1.cif_id '\
                    'inner join dataentry_person dp on dp1.person_id = dp.id '\
                    'inner join dataentry_borderstation db on db.id = dc.station_id '\
                'union '\
                'select distinct db.operating_country_id, dp.master_person_id '\
                'from dataentry_vdfcommon dv '\
                    'inner join dataentry_person dp on dv.victim_id = dp.id '\
                    'inner join dataentry_borderstation db on db.id = dv.station_id '\
                'union '\
                'select distinct db.operating_country_id, dp.master_person_id '\
                'from dataentry_irfcommon di '\
                    'inner join dataentry_intercepteecommon di2 on di2.interception_record_id = di.id '\
                    'inner join dataentry_person dp on di2.person_id = dp.id '\
                    'inner join dataentry_borderstation db on db.id = di.station_id) dj '\
            'where dm.master1_id = dj.master_person_id or dm.master2_id = dj.master_person_id '

        cursor = connection.cursor()
        cursor.execute('DROP VIEW IF EXISTS pendingmatch')
        cursor.execute('DROP VIEW IF EXISTS pendingmatchwithcountry')
        cursor.execute(sql)
        sql ="create view pendingmatch AS select distinct person_match_id as id, person_match_id from pendingmatchwithcountry"
        cursor.execute(sql)
        if not in_transaction:
            transaction.commit()
        
    @staticmethod
    def check_load_form_data(apps, checksums):
        base = 'form_data'
        basic_form_data = base + '.json'
        if base + '.json' not in checksums:
            print ('Base form data file ' + basic_form_data + ' was not found cannot check or load form data')
            return
        
        reload = False
        try:
            form_version = FormVersion.objects.get(file=basic_form_data)
            if form_version.checksum != checksums[basic_form_data]['checksum'] or form_version.blocks != checksums[basic_form_data]['blocks']:
                print (basic_form_data, ' checksum does not match')
                reload = True
        except Exception:
            print (basic_form_data, ' exception')
            reload = True
        
        for tag_file in checksums.keys():
            if tag_file == basic_form_data:
                continue
            try:
                form_version = FormVersion.objects.get(file=tag_file)
                if form_version.checksum != checksums[tag_file]['checksum'] or form_version.blocks != checksums[tag_file]['blocks']:
                    print(tag_file,'checksum does not match')
                    reload = True
            except Exception:
                print(tag_file,'no checksum value in database')
                reload = True
            
        if not reload:
            print ('checksums match - no need to reload form data')
            return
        
        print('Reloading form data') 
        reference_list = FormMigration.get_form_to_station_references()
        FormMigration.unload_prior(apps)
        load_form_data = LoadFormData()
        load_form_data.load() 
        FormMigration.restore_form_to_station_references(reference_list)
        
        try:
            form_version = FormVersion.objects.get(file=basic_form_data)
        except Exception:
            form_version = FormVersion()
            form_version.file = basic_form_data
        
        form_version.checksum = checksums[basic_form_data]['checksum']
        form_version.blocks = checksums[basic_form_data]['blocks']
        form_version.save()
        
        tag_form_types = FormType.objects.filter(tag_enabled=True)
        for form_type in tag_form_types:
            tag_form_name = base + '_' + form_type.name  + '.json'
            try:
                form_version = FormVersion.objects.get(file=tag_form_name)
            except Exception:
                form_version = FormVersion()
                form_version.file = tag_form_name
            
            form_version.checksum = checksums[tag_form_name]['checksum']
            form_version.blocks = checksums[tag_form_name]['blocks']
            form_version.save()
        
        FormMigration.buildView('IRF')
        #FormMigration.buildView('CIF')
        #FormMigration.buildView('VDF')
        FormMigration.pending_match_view()
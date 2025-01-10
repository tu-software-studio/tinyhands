import datetime
import os
import pytz

from django.db import models
from django.db.models import Q
from django.conf import settings
from django.db.models import JSONField

from .border_station import BorderStation
from .country import Country
from .holiday import Holiday

from dataentry.models import BorderStation, Form, FormCategory, IntercepteeCommon, IrfCommon, IrfVerification
from budget.models import MonthlyDistributionForm

from pip._vendor.pyparsing import results

class IndicatorHistory(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    year = models.PositiveIntegerField('Year')
    month = models.PositiveIntegerField('Month')
    indicators = JSONField()
    
    @staticmethod
    def work_days (start_date, end_date, country):
        days_offset = [
                [0,1,2,3,4,4,4],
                [0,1,2,3,3,3,4],
                [0,1,2,2,2,3,4],
                [0,1,1,1,2,3,4],
                [0,0,0,1,2,3,4],
                [0,0,0,1,2,3,4],
                [0,0,1,2,3,4,4]
            ]
        
        if end_date <= start_date:
            return 0
        
        days = (end_date - start_date).days
        weeks = int(days/7)
        partial = days - weeks * 7
        work_days = weeks * 5 + days_offset[start_date.weekday()][partial]
        holidays = Holiday.objects.filter(country=country, holiday__gte=start_date, holiday__lte=end_date)
        for holiday in holidays:
            # Only count Monday through Friday
            if holiday.holiday.weekday() < 5:
                work_days -= 1
        
        return work_days
    
    @staticmethod
    def add_result(result, name, value):
        if name in result:
            if value != '-':
                if result[name] != '-':
                    result[name] = result[name] + value
                else:
                    result[name] = value
        else:
            result[name] = value
    
    @staticmethod
    def compute_pre_blind_verification(results, form_class, station_list, start_date, end_date, start_validation_date):
        query_set = form_class.objects.filter(station__in=station_list,
                                        logbook_first_verification_date__gte=start_date,
                                        logbook_first_verification_date__lte=end_date)
        IndicatorHistory.calculate_irf_first_verification(results, query_set, start_date, end_date)
        
        if start_validation_date is not None:
            query_set = form_class.objects.filter(station__in=station_list,
                                                  logbook_submitted__gte=start_validation_date,
                                                  logbook_submitted__lte=end_date,
                                                  evidence_categorization__isnull=False).exclude(logbook_first_verification_date__lte=end_date)
            IndicatorHistory.calculate_irf_backlog(results, query_set, 'v1')
        
        query_set = form_class.objects.filter(station__in=station_list,
                            verified_date__gte=start_date,
                            verified_date__lte=end_date)
        IndicatorHistory.calculate_irf_second_verification(results, query_set, start_date, end_date)
        
        if start_validation_date is not None:
            query_set = form_class.objects.filter(station__in=station_list,
                                                  logbook_first_verification_date__gte=start_validation_date,
                                                  logbook_first_verification_date__lte=end_date,
                                                  evidence_categorization__isnull=False).exclude(verified_date__lte=end_date)
            IndicatorHistory.calculate_irf_backlog(results, query_set, 'v2')
        

    
    @staticmethod
    def compute_blind_verification(results, form_class, station_list, start_date, end_date, start_validation_date):
        query_set = form_class.objects.filter(station__in=station_list, logbook_submitted__lte=end_date, evidence_categorization__isnull=False).exclude(verified_date__lt=start_date)
        if start_validation_date is not None:
            query_set = query_set.filter(logbook_submitted__gte=start_validation_date)
        initial_lag_count = 0
        initial_lag_time = 0
        initial_victim_count = 0
        initial_backlog = 0
        tie_lag_count = 0
        tie_lag_time = 0
        tie_victim_count = 0
        tie_backlog = 0;
        for irf in query_set:
            initial_date = None
            tie_date = None
            for verification in irf.irfverification_set.all().order_by('verified_date'):
                if verification.verification_type == IrfVerification.INITIAL:
                    initial_date = verification.verified_date
                    
                if verification.verification_type == IrfVerification.TIE_BREAK:
                    if verification.verified_date <= end_date:
                        tie_date = verification.verified_date
            
            if irf.status == 'approved' or initial_date is not None and initial_date > end_date:
                initial_backlog += 1
            elif IndicatorHistory.date_in_range(initial_date, start_date, end_date) and irf.status != 'approved':
                initial_lag_count += 1
                initial_lag_time += IndicatorHistory.work_days(irf.logbook_submitted, initial_date, irf.station.operating_country)
                initial_victim_count += IntercepteeCommon.objects.filter(interception_record=irf, person__role='PVOT').count()
                
            if tie_date is None:
                if irf.status == 'verification-tie':
                    # There has been a verification tie and the tie break has not been completed
                    tie_backlog += 1
                # else no verification tie has occurred
            elif tie_date > end_date:
                # The tie break has been completed, but it was after the end date
                tie_backlog += 1
            elif IndicatorHistory.date_in_range(tie_date, start_date, end_date):
                # tie break has been completed within the time range - compute the lag
                tie_lag_count += 1
                tie_lag_time += IndicatorHistory.work_days(initial_date, tie_date, irf.station.operating_country)
                tie_victim_count += IntercepteeCommon.objects.filter(interception_record=irf, person__role='PVOT').count()
        
        IndicatorHistory.add_result(results, 'v1TotalLag', initial_lag_time)
        IndicatorHistory.add_result(results, 'v1Count', initial_lag_count)
        IndicatorHistory.add_result(results, 'v1VictimCount', initial_victim_count)
        IndicatorHistory.add_result(results, 'v1Backlog', initial_backlog)
        IndicatorHistory.add_result(results, 'v2TotalLag', tie_lag_time)
        IndicatorHistory.add_result(results, 'v2Count', tie_lag_count)
        IndicatorHistory.add_result(results, 'v2VictimCount', tie_victim_count)
        IndicatorHistory.add_result(results, 'v2Backlog', tie_backlog)
    
    @staticmethod
    def mdf_signed_percent (results, start_date, end_date, country):
        pbs_list = MonthlyDistributionForm.objects.filter(
            border_station__operating_country=country,
            month_year__gte=start_date,
            month_year__lte=end_date)
        total_count = 0
        signed_count = 0
        for pbs in pbs_list:
            total_count += 1
            if pbs.signed_pbs != '':
                signed_count += 1
        
        if total_count > 0:
            result = round(signed_count * 100 / total_count, 2)
        else:
            result = ''
        
        IndicatorHistory.add_result(results, 'mdfSignedPercent', result)
    
    @staticmethod
    def calculate_indicators(start_date, end_date, country, check_photos=None, include_latest_date = False):
        has_blind_verification = IrfCommon.has_blind_verification(country)

        if country.verification_start_year is None or country.verification_start_month is None:
            start_validation_date = None
        else:
            start_validation_date = datetime.date(country.verification_start_year,country.verification_start_month,1)
        station_list = BorderStation.objects.filter(operating_country=country)
        
        pvf_forms = Form.objects.filter(form_type__name='PVF', stations__operating_country=country)
        pvf_form_present = (len(pvf_forms) > 0)
        results = {}
        results['pvf_form_present'] = pvf_form_present
        
        
        
        form_method = {
            'IRF':IndicatorHistory.calculate_irf_indicators,
            'CIF':IndicatorHistory.calculate_cif_indicators,
            'VDF':IndicatorHistory.calculate_vdf_indicators,
            'PVF':IndicatorHistory.calculate_pvf_indicators,
            'SF':IndicatorHistory.calculate_sf_indicators,
            'LF':IndicatorHistory.calculate_lf_indicators,
            }
        
        if check_photos is None:
            check_photos = IndicatorHistory.get_modified_photos(start_date, end_date)
               
        forms_processed = []
        class_cache = {
                'IRF':{},
                'CIF':{},
                'VDF':{},
                'PVF':{},
                'SF':{},
                'LF':{},
                }
        
        storage_cache = {
                'IRF_People':{},
                }
        
        latest_date = None
        
        if pvf_form_present:
            form_types = ['IRF','PVF','SF','LF']
        else:
            form_types = ['IRF','CIF','VDF']
        
        # general form information
        for form_type in form_types:
            for station in station_list:
                form_class = IndicatorHistory.get_class(class_cache, form_type, station)
                if form_class is None or form_class in forms_processed:
                    # If there is no form for this station or we have already processed the form
                    # associated with this station, then skip to the next station
                    continue;
                
                query_set = form_class.objects.filter(station__in=station_list,
                                        logbook_submitted__gte=start_date, logbook_submitted__lte=end_date)
                form_method[form_type](results, query_set, start_date, end_date, class_cache, form_type)
                
                if form_type == 'IRF':
                    if has_blind_verification:
                        IndicatorHistory.compute_blind_verification(results, form_class, station_list, start_date, end_date, start_validation_date)
                    else:
                        IndicatorHistory.compute_pre_blind_verification(results, form_class, station_list, start_date, end_date, start_validation_date)
                        
                    interceptee_storage = IndicatorHistory.get_card_storage(storage_cache, form_type, 'People', station)
                    if interceptee_storage is not None:
                        query_set = interceptee_storage.get_form_storage_class().objects.filter(interception_record__station__in=station_list, person__photo__in=check_photos.keys())
                        IndicatorHistory.process_photos(results, query_set, check_photos, start_date, end_date)
                    
                if include_latest_date:
                    query_set = form_class.objects.filter(station__in=station_list).exclude(logbook_submitted__isnull=True).order_by("-logbook_submitted")[:1]
                    if len(query_set) > 0:
                        if latest_date is None:
                            latest_date = query_set[0].logbook_submitted
                        elif latest_date < query_set[0].logbook_submitted:
                            latest_date = query_set[0].logbook_submitted
                    
                forms_processed.append(form_class)
        
        for prefix in ['irf','vdf', 'cif', 'pvf', 'sf', 'lf', 'photos', 'v1', 'v2']:
            IndicatorHistory.compute_lag(results, prefix)
            
            if prefix + 'Count' in results and prefix + 'OriginalFormCount' in results:
                if  results[prefix + 'Count'] > 0:
                    results[prefix + 'OriginalFormPercent'] = round(results[prefix + 'OriginalFormCount'] * 100 / results [prefix + 'Count'],2)
                else:
                    results[prefix + 'OriginalFormPercent'] = '-'
        
        if include_latest_date:
            if latest_date is None:
                results['latestDate'] = ''
            else:
                results['latestDate'] = str(latest_date)
        
        IndicatorHistory.mdf_signed_percent(results, start_date, end_date, country)

        return results
    
    @staticmethod
    def update_and_export_indicators (country, year, month):
        try:
            entry = IndicatorHistory.objects.get(country=country, year=year, month=month) 
        except:
            return
        
        start_date = datetime.date(year, month, 1)
        if month == 12:
            end_date = datetime.date(year+1, 1, 1) - datetime.timedelta(1)
        else:
            end_date = datetime.date(year, month+1, 1) - datetime.timedelta(1)
        results = IndicatorHistory.calculate_indicators(start_date, end_date, country)
        entry.indicators = results
        entry.save()
        from export_import.data_indicator_io import export_entry_indicators
        export_entry_indicators(year*100 + month) 
    
    @staticmethod
    def date_in_range (the_date, start_date, end_date):
         if the_date is None:
             return False
         
         if start_date is not None and the_date < start_date:
             return False
         
         if end_date is not None and the_date > end_date:
             return False
         
         return True

    @staticmethod
    def get_class(class_cache, type, station):
        if station in class_cache[type]:
            the_class = class_cache[type][station]
        else:
            form = Form.current_form(type, station.id)
            if form is None:
                the_class = None
            else:
                the_class = form.storage.get_form_storage_class()

            class_cache[type][station] = the_class
        
        return the_class
    
    @staticmethod
    def get_card_storage(storage_cache, form_type, form_category_name, station):
        type = form_type + "_" + form_category_name
        if station in storage_cache[type]:
            the_storage = storage_cache[type][station]
        else:
            form = Form.current_form(form_type, station.id)
            form_categories = FormCategory.objects.filter(form=form, name=form_category_name)
            if len(form_categories) == 1 and form_categories[0].storage is not None:
                the_storage = form_categories[0].storage
            else:
                the_storage = None

            storage_cache[type][station] = the_storage
            
        return the_storage
    
    @staticmethod
    def compute_lag(results, prefix):
        if prefix + 'Count' in results and prefix + 'TotalLag' in results:
            count = results[prefix + 'Count']
            total = results[prefix + 'TotalLag']
            if count > 0:
                results[prefix + 'Lag'] =  round(total/count,2)
            else:
                results[prefix + 'Lag'] = '-'

    @staticmethod
    def calculate_irf_first_verification(results, query_set, start_date, end_date):
        lag_time = 0
        lag_count = 0
        victim_count = 0
        
        for irf in query_set:
            if IndicatorHistory.date_in_range(irf.logbook_submitted, None, None):
                lag_count += 1
                lag_time += IndicatorHistory.work_days(irf.logbook_submitted, irf.logbook_first_verification_date, irf.station.operating_country)
                victim_count += IntercepteeCommon.objects.filter(interception_record=irf, person__role='PVOT').count()
        
        IndicatorHistory.add_result(results, 'v1TotalLag', lag_time)
        IndicatorHistory.add_result(results, 'v1Count', lag_count)
        IndicatorHistory.add_result(results, 'v1VictimCount', victim_count)

    @staticmethod
    def calculate_irf_backlog(results, query_set, prefix):
        IndicatorHistory.add_result(results, prefix + 'Backlog', len(query_set))
    
    @staticmethod
    def calculate_irf_second_verification(results, query_set, start_date, end_date):
        lag_time = 0
        lag_count = 0
        victim_count = 0
        change_count = 0
        
        for irf in query_set:
            if IndicatorHistory.date_in_range(irf.logbook_first_verification_date, None, None):
                lag_count += 1
                lag_time += IndicatorHistory.work_days(irf.logbook_first_verification_date, irf.verified_date, irf.station.operating_country)
                victim_count += IntercepteeCommon.objects.filter(interception_record=irf, person__role='PVOT').count()
                if irf.logbook_first_verification != irf.verified_evidence_categorization:
                    change_count += 1
        
        IndicatorHistory.add_result(results, 'v2TotalLag', lag_time)
        IndicatorHistory.add_result(results, 'v2Count', lag_count)
        IndicatorHistory.add_result(results, 'v2VictimCount', victim_count)
        IndicatorHistory.add_result(results, 'v2ChangeCount', change_count)
     
    @staticmethod
    def calculate_form_indicators (results, query_set, form_type):
        storage_cache = {
                form_type + '_Attachments':{},
                }
        submitted_count = 0
        total_lag = 0
        interceptee_count = 0
        interceptee_photo_count = 0
        original_form_attached_count = 0
        
        for entry in query_set:
            submitted_count += 1
            
            if IndicatorHistory.date_in_range(entry.logbook_information_complete, None, None):
                start_date = entry.logbook_information_complete
            elif IndicatorHistory.date_in_range(entry.logbook_received, None, None):
                start_date = entry.logbook_received
            else:
                start_date = entry.date_time_entered_into_system.date()
            
            total_lag += IndicatorHistory.work_days(start_date, entry.logbook_submitted, entry.station.operating_country)
            storage = IndicatorHistory.get_card_storage(storage_cache, form_type, 'Attachments', entry.station)
            if storage is not None:
                orig_attachments = storage.get_form_storage_class().objects.filter(Q((storage.foreign_key_field_parent,entry)) & Q(('option','Original Form')))
                if len(orig_attachments) > 0:
                    original_form_attached_count += 1
            
        
        IndicatorHistory.add_result(results, form_type.lower() + 'Count', submitted_count)
        IndicatorHistory.add_result(results, form_type.lower() + 'TotalLag', total_lag)
        IndicatorHistory.add_result(results, form_type.lower() + 'OriginalFormCount', original_form_attached_count)
    
    @staticmethod
    def calculate_irf_indicators(results, query_set, start_date, end_date, class_cache, form_type):
        IndicatorHistory.calculate_form_indicators(results, query_set, form_type)
    
    @staticmethod
    def calculate_vdf_indicators(results, query_set, start_date, end_date, class_cache, form_type):
        IndicatorHistory.calculate_form_indicators(results, query_set, form_type)
    
    @staticmethod
    def calculate_cif_indicators(results, query_set, start_date, end_date, class_cache, form_type):
        IndicatorHistory.calculate_form_indicators(results, query_set, form_type)
    
    @staticmethod
    def calculate_pvf_indicators(results, query_set, start_date, end_date, class_cache, form_type):
        IndicatorHistory.calculate_form_indicators(results, query_set, form_type)
    
    @staticmethod
    def calculate_sf_indicators(results, query_set, start_date, end_date, class_cache, form_type):
        IndicatorHistory.calculate_form_indicators(results, query_set, form_type)
    
    @staticmethod
    def calculate_lf_indicators(results, query_set, start_date, end_date, class_cache, form_type):
        IndicatorHistory.calculate_form_indicators(results, query_set, form_type)
    
    @staticmethod
    def get_modified_photos(start_date, end_date):
        # file dates are stored in UTC, but we want to filter based on the station's time zone
        # so start with a rough time range and then filter better after we determine the station's
        # time zone.
        one_day = datetime.timedelta(1)
        rough_start_date = start_date - one_day
        rough_end_date = end_date + one_day
        
        check_photos = {}
        for entry in os.scandir(settings.MEDIA_ROOT + '/interceptee_photos/'):
            stat_object = entry.stat ( )
            modification_time = datetime.datetime.fromtimestamp(stat_object.st_mtime)
            if modification_time.date() >= rough_start_date and modification_time.date() <= rough_end_date:
                check_photos['interceptee_photos/' + entry.name] = modification_time
                
        return check_photos
    
    @staticmethod
    def process_photos(results, query_set, check_photos, start_date, end_date):
        photos_uploaded = 0
        photo_lag_total = 0
        
        for interceptee in query_set:
            irf = interceptee.interception_record
            time_zone = pytz.timezone(irf.station.time_zone)
            modification_time = check_photos[interceptee.person.photo]
            local_date = modification_time.astimezone(time_zone).date()
            if local_date >= start_date and local_date <= end_date:
                photos_uploaded += 1
                if IndicatorHistory.date_in_range(irf.logbook_information_complete, None, None):
                    base_date = irf.logbook_information_complete
                elif IndicatorHistory.date_in_range(irf.logbook_received, None, None):
                    base_date = irf.logbook_received
                else:
                    base_date = irf.date_time_entered_into_system.astimezone(time_zone).date()
                
                photo_lag_total += IndicatorHistory.work_days(base_date, local_date, irf.station.operating_country)
            
        IndicatorHistory.add_result(results, 'photosCount', photos_uploaded)
        IndicatorHistory.add_result(results, 'photosTotalLag', photo_lag_total)
            
        
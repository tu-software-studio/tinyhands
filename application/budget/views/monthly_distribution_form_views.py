import datetime
from dateutil.relativedelta import relativedelta
from rest_framework import viewsets, status
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters as fs
from rest_framework.response import Response
from django.apps import apps
from django.db.models import Value, IntegerField, F, Q
from django.core.files.storage import default_storage
from django.contrib.contenttypes.models import ContentType

from dataentry.models import BorderStation, CountryExchange, IndicatorHistory, IntercepteeCommon, StationStatistics, UserLocationPermission
from dataentry.serializers import CountrySerializer
from budget.models import BorderStationBudgetCalculation, MonthlyDistributionForm, MdfCombined, MdfItem, ProjectRequest, ProjectRequestComment, ProjectRequestDiscussion
from budget.serializers import MonthlyDistributionFormSerializer, MdfItemSerializer
from export_import.mdf_io import export_mdf_sheet
from mailbox import MMDF
import budget.mdf_constants as constants
from django.db.models import Sum
import decimal
from decimal import Decimal

class BorderStationOverviewSerializer(serializers.ModelSerializer):
    operating_country = CountrySerializer()
    class Meta:
        fields = [
            'id',
            'station_code',
            'station_name',
            'operating_country',
        ]
        model = BorderStation
        
class MdfCombinedSerializer(serializers.ModelSerializer):
    class Meta:
        model = MdfCombined
        fields = ['month_year', 'border_station', 'status', 'date_time_entered', 'date_time_last_updated', 'mdf_type', 'id']
    
    border_station = BorderStationOverviewSerializer(read_only=True)
    mdf_type = serializers.SerializerMethodField(read_only=True)  
    id = serializers.SerializerMethodField(read_only=True)  
    
    def get_mdf_type(self, obj):
        if isinstance(obj.content_object, BorderStationBudgetCalculation):
            return 'budget'
        return 'mdf-pr'
    
    def get_id(self, obj):
            return obj.content_object.id

def get_national_values(country, year, month):
    ctx = decimal.getcontext()
    ctx.rounding = decimal.ROUND_HALF_UP
    
    result = {}
    request_categories = [
        constants.STAFF_BENEFITS,
        constants.RENT_UTILITIES,
        constants.ADMINISTRATION,
        constants.AWARENESS,
        constants.TRAVEL,
        constants.POTENTIAL_VICTIM_CARE,
        constants.IMPACT_MULTIPLYING
        ]
    
    if month > 1:
        prior_month = month - 1
        prior_year = year
    else:
        prior_month = 12
        prior_year = year - 1
    
    interceptions = IntercepteeCommon.objects.filter(
        interception_record__station__operating_country=country,
        interception_record__verified_date__year=prior_year,
        interception_record__verified_date__month=prior_month,
        person__role = 'PVOT'
        ).exclude(interception_record__verified_evidence_categorization__startswith='Should not')
    result['intercepts'] = len(interceptions)
    
    exchange_entries = CountryExchange.objects.filter(country=country, year_month__lte=year*100+month).order_by('-year_month')
    if len(exchange_entries) > 0:
        exchange = Decimal(exchange_entries[0].exchange_rate)
    else:
        exchange = Decimal(1.0)

    total = 0
    filter_date_time = datetime.datetime(year, month, 15, 0, 0, 0, 0, datetime.timezone.utc)
    for category in request_categories:
        subtotal = Decimal(0)
        requests = ProjectRequest.objects.filter(
            category=category,
            project__operating_country=country,
            monthlydistributionform__month_year__year=year,
            monthlydistributionform__month_year__month=month).exclude(benefit_type_name='Deductions')
        for request in requests:
            if not (request.status == 'Approved-Completed' and request.completed_date_time < filter_date_time):
                subtotal += request.cost

        if category == constants.STAFF_BENEFITS:
            deductions = ProjectRequest.objects.filter(
                category=category,
                project__operating_country=country,
                benefit_type_name='Deductions',
                monthlydistributionform__month_year__year=year,
                monthlydistributionform__month_year__month=month)
            for deduction in deductions:
                if not (deduction.status == 'Approved-Completed' and
                        deduction.completed_date_time < filter_date_time):
                    subtotal -= deduction.cost
            
        total += subtotal
        result[category] = {'local':subtotal, 'USD':round(subtotal/exchange,2)}
    
    
    past_sent = MdfItem.objects.filter(
        category=constants.PAST_MONTH_SENT,
        mdf__border_station__operating_country=country,
        mdf__month_year__year=year,
        mdf__month_year__month=month).aggregate(Sum('cost'))['cost__sum']
    if past_sent is None:
        past_sent = Decimal(0)
    total += past_sent
    result[constants.PAST_MONTH_SENT] = {'local':subtotal, 'USD':round(subtotal/exchange,2)}
    
    subtotal = MdfItem.objects.filter(
        category=constants.MONEY_NOT_SPENT,
        deduct='Yes',
        mdf__border_station__operating_country=country,
        mdf__month_year__year=year,
        mdf__month_year__month=month).aggregate(Sum('cost'))['cost__sum']
    if subtotal is None:
        subtotal = Decimal(0)
    total -= subtotal
    result[constants.MONEY_NOT_SPENT] = {'local':subtotal, 'USD':round(subtotal/exchange,2)}
    
    result['Total'] = {'local':total, 'USD':round(total/exchange,2)}
    distribution = total - past_sent
    result['Distribution'] = {'local':distribution, 'USD':round(distribution/exchange,2)}
    
    return result

def compute_trend(current, prior, threshold):
    result = 0
    change = current - prior
    change_abs = abs(change)
    if (threshold is not None and change_abs > threshold) or threshold is None:
        if prior == 0:
            if current == 0:
                result = 0
            else:
                result = 2
        else:
            percent = change_abs * 100 / abs(prior)
            if percent > 5:
                if percent > 20:
                    result = 2
                else:
                    result = 1
        if change < 0:
            result = result * -1
    
    return result

MONTH_NAME = ['', 'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August','September', 'October', 'November', 'December']

def category_name(category_id):
    result = 'Unknown'
    if category_id == 'Total' or category_id == 'Distribution':
        result = category_id
    elif category_id == constants.MONEY_NOT_SPENT:
        result = 'Money Not Spent (To Deduct)'
    else:
        for cat in constants.CATEGORY_CHOICES:
            if category_id == cat[0]:
                result = cat[1]
                break
    
    return result

def get_national_trend(mdf):
    categories = [
        constants.STAFF_BENEFITS,
        constants.RENT_UTILITIES,
        constants.ADMINISTRATION,
        constants.AWARENESS,
        constants.TRAVEL,
        constants.POTENTIAL_VICTIM_CARE,
        constants.IMPACT_MULTIPLYING,
        constants.PAST_MONTH_SENT,
        constants.MONEY_NOT_SPENT,
        'Total',
        'Distribution'
        ]
    
    year = mdf.month_year.year
    month = mdf.month_year.month
    if month > 1:
        prior_month = month - 1
        prior_year = year
    else:
        prior_month = 12
        prior_year = year - 1
    
    current = get_national_values(mdf.border_station.operating_country, year, month)
    prior = get_national_values(mdf.border_station.operating_country, prior_year, prior_month)
    
    result = {
        'label': mdf.border_station.operating_country.name + ' - National',
        'month':{
            'current':{'year':year,'month':MONTH_NAME[month]},
            'prior':{'year':prior_year,'month':MONTH_NAME[prior_month]},
        },
        'intercepts':{
            'current':current['intercepts'],
            'prior':prior['intercepts'],
            'trend': compute_trend(current['intercepts'], prior['intercepts'], None)
        }
    }
    
    for category in categories:
        the_name = category_name(category)
        result[the_name] = {
            'current':{'local':current[category]['local'], 'USD':current[category]['USD']},
            'prior':{'local':prior[category]['local'], 'USD':prior[category]['USD']},
            'trend': compute_trend(current[category]['USD'], prior[category]['USD'], 20)
        }
    
    return result

def find_prior_mdf_for_project(mdf, project):
    result = None
    items = MdfItem.objects.filter(
            work_project=project,
            mdf__border_station=mdf.border_station,
            mdf__month_year__lt=mdf.month_year
        ).order_by('-mdf__month_year')
    if len(items):
        result = items[0].mdf
        
    requests = ProjectRequest.objects.filter(
                project=project,
                monthlydistributionform__border_station=mdf.border_station,
                monthlydistributionform__month_year__lt=mdf.month_year
            ).order_by('-monthlydistributionform__month_year')
    
    if len(requests):
        # We have the request, but need to determine the mdf
        mdfs = requests[0].monthlydistributionform_set.filter(
            border_station=mdf.border_station,
            month_year__lt=mdf.month_year
            ).order_by('-month_year')
        if len(mdfs) > 0:
            if result is None or mdfs[0].month_year > result.month_year:
                result = mdfs[0]
    
    return result

def get_mdf_project_values(mdf, project):
    full_request_categories = [
        constants.STAFF_BENEFITS,
        constants.RENT_UTILITIES,
        constants.ADMINISTRATION,
        constants.AWARENESS,
        constants.TRAVEL,
        constants.POTENTIAL_VICTIM_CARE
    ]
    impact_request_categories = [
        constants.STAFF_BENEFITS,
        constants.IMPACT_MULTIPLYING
    ]

    if (mdf.border_station == project):
        request_categories = full_request_categories
    else:
        request_categories = impact_request_categories
    
    year = mdf.month_year.year
    month = mdf.month_year.month
    
    if month > 1:
        prior_month = month - 1
        prior_year = year
    else:
        prior_month = 12
        prior_year = year - 1
    
    exchange_entries = CountryExchange.objects.filter(country=mdf.border_station.operating_country, year_month__lte=year*100+month).order_by('-year_month')
    if len(exchange_entries) > 0:
        exchange = Decimal(exchange_entries[0].exchange_rate)
    else:
        exchange = Decimal(1.0)
   
    results = {}
    interceptions = IntercepteeCommon.objects.filter(
        interception_record__station=project,
        interception_record__verified_date__year=prior_year,
        interception_record__verified_date__month=prior_month,
        person__role = 'PVOT'
        ).exclude(interception_record__verified_evidence_categorization__startswith='Should not')
    results['intercepts'] = len(interceptions)
    
    total = Decimal(0)
    for category in request_categories:
        requests = mdf.requests.filter(category=category, project=project).exclude(benefit_type_name='Deductions')
        subtotal = Decimal(0)
        for request in requests:
            if not (request.status == 'Approved-Completed' and request.completed_date_time < mdf.month_year):
                subtotal += request.cost

        if category == constants.STAFF_BENEFITS:
            deductions = mdf.requests.filter(category=category, project=project, benefit_type_name='Deductions')
            for request in deductions:
                if not (request.status == 'Approved-Completed' and request.completed_date_time < mdf.month_year):
                    subtotal -= request.cost

        results[category] = {'local': subtotal, 'USD': round(subtotal/exchange,2)}
        total += subtotal
    
    past_sent = mdf.mdfitem_set.filter(category=constants.PAST_MONTH_SENT, work_project=project).aggregate(Sum('cost'))['cost__sum']
    if past_sent is None:
        past_sent = Decimal(0)
    results[constants.PAST_MONTH_SENT] = {'local': past_sent, 'USD': round(past_sent/exchange,2)}
    total += past_sent
    
    subtotal = mdf.mdfitem_set.filter(category=constants.MONEY_NOT_SPENT, work_project=project, deduct='Yes').aggregate(Sum('cost'))['cost__sum']
    if subtotal is None:
        subtotal = Decimal(0)
    results[constants.MONEY_NOT_SPENT] = {'local': subtotal, 'USD': round(subtotal/exchange,2)}
    total -= subtotal
    
    results['Total'] = {'local':total, 'USD':round(total/exchange,2)}
    distribution = total - past_sent
    results['Distribution'] = {'local':distribution, 'USD':round(distribution/exchange,2)}
    
    
    return results
    
def get_mdf_trend(mdf):
    full_request_categories = [
        constants.STAFF_BENEFITS,
        constants.RENT_UTILITIES,
        constants.ADMINISTRATION,
        constants.AWARENESS,
        constants.TRAVEL,
        constants.POTENTIAL_VICTIM_CARE,
        constants.PAST_MONTH_SENT,
        constants.MONEY_NOT_SPENT,
        'Total',
        'Distribution'
    ]
    impact_request_categories = [
        constants.STAFF_BENEFITS,
        constants.IMPACT_MULTIPLYING,
        constants.PAST_MONTH_SENT,
        constants.MONEY_NOT_SPENT,
        'Total',
        'Distribution'
    ]
    results = {'projects':{},
               'national': get_national_trend(mdf)}
    
    # find all projects in MDF
    projects = []
    for request in mdf.requests.all():
        if request.project not in projects:
            projects.append(request.project)
        
    for item in mdf.mdfitem_set.all():
        if item.work_project not in projects:
            projects.append(request.project)
    
    
    for project in projects:
        prior_mdf = find_prior_mdf_for_project(mdf, project)
        
        current = get_mdf_project_values(mdf, project)
        if prior_mdf is not None:
            prior = get_mdf_project_values(prior_mdf, project)
        else:
            prior = None
        
        result = {
            'month':{'current':{'year':mdf.month_year.year,'month':MONTH_NAME[mdf.month_year.month]}},
            'intercepts':{'current':current['intercepts']}
        }
        if prior_mdf is not None:
            result['month']['prior'] = {'year':prior_mdf.month_year.year,'month':MONTH_NAME[prior_mdf.month_year.month]}
            result['intercepts']['prior'] = prior['intercepts']
            result['intercepts']['trend'] = compute_trend (current['intercepts'], prior['intercepts'], None)
        else:
            result['month']['prior'] = {'year':'','month':''}
            result['intercepts']['prior'] = ''
            result['intercepts']['trend'] = 0
            
        if mdf.border_station == project:
            request_categories = full_request_categories
        else:
            request_categories = impact_request_categories
        
        for category in request_categories:
            if category ==  constants.MONEY_NOT_SPENT:
                the_name = 'Money Not Spent (To Deduct)'
            else:
                the_name = category_name(category)
            if category in current:
                result[the_name] = {'current':{'local':current[category]}}
                if prior_mdf is not None:
                    result[the_name]['prior'] = prior[category]
                    result[the_name]['trend'] = compute_trend(current[category]['USD'], prior[category]['USD'], 20)
                else:
                    result[the_name]['prior'] = {'local':'', 'USD':''}
                    result[the_name]['trend'] = 0
        
        results['projects'][project.id] = result
    
    return results    
    

class MdfCombinedViewSet(viewsets.ModelViewSet):
    queryset = MdfCombined.objects.all()
    serializer_class = MdfCombinedSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = (fs.SearchFilter, fs.OrderingFilter,)
    search_fields = ['border_station__station_name', 'border_station__station_code', 'status']
    ordering_fields = ['border_station__station_name', 'border_station__station_code', 'month_year', 'status', 'date_time_entered', 'date_time_last_updated']
    ordering = ['-month_year']
    
    def get_queryset(self):
        border_stations = UserLocationPermission.get_stations_with_permission(self.request.user.id, 'MDF', 'VIEW')
        queryset = MdfCombined.objects.filter(border_station__in=border_stations)
        in_country = self.request.GET.get('country_ids')
        if in_country is not None and in_country != '':
            country_list = []
            for cntry in in_country.split(','):
                country_list.append(int(cntry))
            queryset = queryset.filter(border_station__operating_country__id__in=country_list)
        status = self.request.GET.get('status')
        if status is not None and status != '':
            queryset = queryset.filter(status=status)
        
        return queryset

class MonthlyDistributionFormViewSet(viewsets.ModelViewSet):
    queryset = MonthlyDistributionForm.objects.all()
    serializer_class = MonthlyDistributionFormSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = (fs.SearchFilter, fs.OrderingFilter,)
    search_fields = ['border_station__station_name', 'border_station__station_code']
    ordering_fields = ['border_station__station_name', 'border_station__station_code', 'month_year', 'date_time_entered', 'date_time_last_updated']
    
    def get_queryset(self):
        queryset = self.queryset
        station_id = self.request.GET.get('station_id')
        if station_id is not None and station_id != '':
            queryset = queryset.filter(border_station__id=station_id)
        status = self.request.GET.get('status')
        if status is not None and status != '':
            queryset = queryset.filter(status=status)
        year = self.request.GET.get('year')
        if year is not None and year != '':
            queryset = queryset.filter(month_year__year=year)
        month = self.request.GET.get('month')
        if month is not None and month != '':
            queryset = queryset.filter(month_year__month=month)
        
        return queryset
    
    def get_last_mdf_date(self, request, station_id):
        mdfs = MonthlyDistributionForm.objects.filter(border_station__id=station_id).order_by('-month_year')
        if len(mdfs) > 0:
            year_month = mdfs[0].month_year.year * 100 + mdfs[0].month_year.month
            rv = {'month':year_month, 'status':mdfs[0].status}
        else:
            rv = {'month':None, 'status':None}
        
        return Response(rv)
    def get_new_mdf(self, request, station_id, year, month):
        station =  BorderStation.objects.get(id=station_id)
        if not UserLocationPermission.has_session_permission(request, 'MDF', 'ADD', station.operating_country.id, station.id):
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        
        active_mdfs = MonthlyDistributionForm.objects.filter(border_station=station).exclude(status='Approved')
        if len(active_mdfs) > 0:
            data = {'error':'There is already an active MDF for this project.  Only one active (not Approved) my be present for a project.'}
            return Response(data, status=status.HTTP_400_BAD_REQUEST)
        existing_mdfs = MonthlyDistributionForm.objects.filter(border_station=station, month_year__year=year, month_year__month=month)
        if len(existing_mdfs) > 0:
            data = {'error':'There is already an MDF for this project for the requested year and month'}
            return Response(data, status=status.HTTP_400_BAD_REQUEST)
        
        mdf_date = datetime.datetime(int(year), int(month), 15, tzinfo=datetime.timezone.utc)
        prior_month = mdf_date.date() - relativedelta(months=1)
        
        interceptees = IntercepteeCommon.objects.filter(
                interception_record__station=station,
                interception_record__verified_date__year=prior_month.year,
                interception_record__verified_date__month=prior_month.month,
                person__role='PVOT').exclude(interception_record__verified_evidence_categorization='Should not count as an Intercept')
        
        mdf = MonthlyDistributionForm()
        mdf.border_station = station
        mdf.status = 'Pending'
        mdf.month_year = mdf_date
        mdf.last_month_number_of_intercepted_pvs = len(interceptees)
        mdf.save()
        
        project_requests = ProjectRequest.objects.filter(override_mdf_project=mdf.border_station, status='Approved')
        for project_request in project_requests:
            mdf.requests.add(project_request)
        project_requests = ProjectRequest.objects.filter(override_mdf_project=mdf.border_station, status='Declined')
        for project_request in project_requests:
            mdf.requests.add(project_request)
        
        request_comments = ProjectRequestComment.objects.filter(mdf__isnull=True, request__override_mdf_project=mdf.border_station)
        for request_comment in request_comments:
            request_comment.mdf = mdf
            request_comment.save()
            try:
                mdf.requests.add(request_comment.request)
            except IntegrityError:
                # request was already added
                pass
        
        serializer = self.serializer_class(mdf)
        return Response(serializer.data)
    
    def approve_mdf(self, request, pk):
        mdf = MonthlyDistributionForm.objects.get(id=pk)
            
        if not ((mdf.status == 'Pending' and UserLocationPermission.has_session_permission(request, 'MDF', 'ADD', mdf.border_station.operating_country.id, mdf.border_station.id)) or
             (mdf.status == 'Submitted' and UserLocationPermission.has_session_permission(request, 'MDF', 'INITIAL_REVIEW', mdf.border_station.operating_country.id, mdf.border_station.id)) or
             (mdf.status == 'Initial Review' and UserLocationPermission.has_session_permission(request, 'MDF', 'FINAL_REVIEW', mdf.border_station.operating_country.id, mdf.border_station.id))):
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        
        if mdf.status == 'Pending':
            mdf.status = 'Submitted'
            mdf.save()
        else:
            # Close open discussions
            project_requests = mdf.requests.filter(discussion_status='Open')
            for project_request in project_requests:
                discussion = ProjectRequestDiscussion()
                discussion.request = project_request
                discussion.author = request.user
                discussion.text = 'Closed on MDF approval'
                discussion.save()
                project_request.discussion_status = 'Closed'
                project_request.save()
            
            if mdf.status == 'Submitted':
                mdf.status = 'Initial Review'
                mdf.save()
            else:
                completed_date_time = mdf.month_year + relativedelta(days=1)
                mdf.status = 'Approved'
                project_requests = mdf.requests.all()
                for project_request in project_requests:
                    if project_request.status == 'Declined':
                        project_request.status = 'Declined-Completed'
                        project_request.completed_date_time = completed_date_time
                        project_request.save()
                    elif project_request.status == 'Approved' and project_request.monthly == False:
                        project_request.status = 'Approved-Completed'
                        project_request.completed_date_time = completed_date_time
                        project_request.save()
                comments = ProjectRequestComment.objects.filter(mdf__isnull=True, request__in = mdf.requests.all())
                for comment in comments:
                    comment.mdf = mdf 
                    comment.save()
                mdf.save()
                staff_class = apps.get_model('static_border_stations', 'Staff')
                staff_class.set_mdf_totals(mdf)
                self.check_update_stats(mdf)
       
        serializer = self.serializer_class(mdf)
        return Response(serializer.data)
    
    def check_update_stats(self, mdf):
        open_mdf_projects = BorderStation.objects.filter(
                operating_country=mdf.border_station.operating_country,
                open=True,
                features__contains='hasMDF')
        approved_mdfs = MonthlyDistributionForm.objects.filter(
                status = 'Approved',
                border_station__in=open_mdf_projects,
                month_year__year = mdf.month_year.year,
                month_year__month = mdf.month_year.month)
        if len(approved_mdfs) < len(open_mdf_projects):
            # Not all of the MDFs for the country have been approved
            return False
        
        open_projects = BorderStation.objects.filter(
                operating_country=mdf.border_station.operating_country,
                open=True)
        
        year_month = mdf.month_year.year * 100 + mdf.month_year.month
        for project in open_projects:
            total_budget = 0
            for approved_mdf in approved_mdfs:
                total_budget += approved_mdf.full_total(project)
            
            try:
                stats = StationStatistics.objects.get(station=project, year_month=year_month)
            except:
                stats = StationStatistics()
                stats.station = project
                stats.year_month = year_month
            
            stats.budget = total_budget
            stats.save()
        
        export_mdf_sheet(mdf.border_station.operating_country, year_month)
        
        return True
    
    def retrieve_pdf(self, request, pk):
        mdf = MonthlyDistributionForm.objects.get(pk=pk)
        border_station = mdf.border_station
        staff = StaffProject.objects.filter(border_station=border_station).exclude(staff__email__isnull=True).value_list('staff', flat=True)
        committee_members = border_station.committeemember_set.exclude(email__isnull=True)
        
        # find all permissions for MDF Notification for the specified border station
        can_receive_mdf = UserLocationPermission.objects.filter(
            Q(permission__permission_group = 'NOTIFICATIONS') & Q(permission__action = 'MDF') &
            (Q(country = None) & Q(station=None) | Q(country__id = border_station.operating_country.id) | Q(station__id = border_station.id)))
        # add outer reference to account for the located permissions
        can_receive_mdf = can_receive_mdf.filter(account=OuterRef('pk'))
        # annotate the accounts that have permissions for receiving the MDF
        account_annotated = Account.objects.annotate(national_staff = Exists(can_receive_mdf))
        # select the annotated accounts
        national_staff = account_annotated.filter(national_staff=True)

        staff_serializer = StaffSerializer(staff, many=True)
        committee_members_serializer = CommitteeMemberSerializer(committee_members, many=True)
        national_staff_serializer = AccountMDFSerializer(national_staff, many=True)

        pdf_url = settings.SITE_DOMAIN + reverse('MdfPdf', kwargs={"uuid": budget.mdf_uuid})

        return Response({"staff_members": staff_serializer.data, "committee_members": committee_members_serializer.data, "national_staff_members": national_staff_serializer.data, "pdf_url": pdf_url})
    
    def get_trend(self, request, pk):
        mdf = MonthlyDistributionForm.objects.get(pk=pk)
        result = get_mdf_trend(mdf)
        return Response(result)
    
    def save_file(self, file_obj, subdirectory):
        with default_storage.open(subdirectory + file_obj.name, 'wb+') as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)
        
        return  subdirectory + file_obj.name
    
    def put_attachment(self, request, pk):
        mdf = MonthlyDistributionForm.objects.get(pk=pk)
        
        if 'attachment_file' in request.data:
            file_obj = request.data['attachment_file']
            pbs_file = self.save_file(file_obj, 'pbs_attachments/')
            mdf.signed_pbs = pbs_file
            print(pbs_file)
            mdf.save()
            IndicatorHistory.update_and_export_indicators(mdf.border_station.operating_country, mdf.month_year.year, mdf.month_year.month)
            return Response(pbs_file)
        else:
            return Response('', status=status.HTTP_400_BAD_REQUEST)
                
class MdfItemViewSet(viewsets.ModelViewSet):
    queryset = MdfItem.objects.all()
    serializer_class = MdfItemSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = (fs.SearchFilter, fs.OrderingFilter,)
    search_fields = ['description']
    ordering_fields = ['category', 'description', 'work_project']
    ordering = ['work_project']

        
        
        
import datetime
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from django.conf import settings

from export_import.google_sheet import GoogleSheet
from dataentry.models import BorderStation, StationStatistics
from export_import.data_indicator_io import get_data_collection_indicator_export_rows, export_entry_indicators

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('indicatorType', nargs='+', type=str)
        parser.add_argument(
            '--year_month',
            action='append',
            type=str,
            help='Specify the year and month for processing. "202003" for March 2020',
        )
    
    def export_collection_indicators(self, year_month):
        spreadsheet = 'Data Indicators' + settings.SPREADSHEET_SUFFIX
        sheet = GoogleSheet(spreadsheet,'Collection', 'year month', get_data_collection_indicator_export_rows)
        sheet.update(year_month, year_month)
        
        indicators = get_data_collection_indicator_export_rows([year_month])
        first = True
        station_code = None
        compliance = None
        for indicator in indicators:
            if first:
                for idx in range(len(indicator)):
                    if indicator[idx] == 'station code':
                        station_code = idx
                    if indicator[idx] == 'Total':
                        compliance = idx
                
                first = False
                continue
            
            if indicator[station_code] == 'Totals':
                continue
            station = BorderStation.objects.get(station_code=indicator[station_code])
            try:
                value = float(indicator[compliance])
                try:
                    operations_data = StationStatistics.objects.get(station=station, year_month=year_month)
                    operations_data.compliance = value
                    operations_data.save()
                except ObjectDoesNotExist:
                    pass
            except:
                pass
        
    def handle(self, *args, **options):
        indicator_type = options.get('indicatorType')[0].lower()
        if options.get('year_month'):
            year_month = options.get('year_month')[0]
        else:
            now = datetime.datetime.now()
            if now.month  == 1:
                year_month = str(now.year - 1)
            else:
                year_month = str(now.year)
            if now.month < 11:
                if now.month == 1:
                    year_month += '12'
                else:
                    year_month += '0' + str(now.month - 1)
            else:
                year_month += str(now.month - 1)
        if indicator_type == 'collection':    
            self.export_collection_indicators(year_month)
        elif indicator_type =='entry':
            export_entry_indicators(year_month)
        else:
            print ('Unknown indicator type:', indicator_type)
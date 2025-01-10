import calendar
import datetime

from django.conf import settings

from export_import.google_sheet import GoogleSheet
from dataentry.models import Country, IndicatorHistory
from dataentry.views.indicators import IndicatorsViewSet
def get_data_collection_indicator_export_rows(year_months):
    headers = [
            'year month',
            'year',
            'month',
            'country name',
            'station code',
            'Number of Victims',
            'IRFs',
            'IRFs in Compliance Number',
            'IRFs in Compliance Percent',
            'IRF Collection Lag Time',
            'CIFs',
            'CIF Percent',
            'CIF in Compliance Number',
            'CIF in Compliance Percent',
            'CIF Collection Lag Time',
            'Number of CIFs with "Evidence"',
            'VDFs',
            'VDFs in Compliance Number',
            'VDFs in Compliance Percent',
            'VDF Collection Lag Time',
            'PVFs',
            'PVFs in Compliance Number',
            'PVFs in Compliance Percent',
            'PVF Collection Lag Time',
            'SFs',
            'SFs in Compliance Number',
            'SFs in Compliance Percent',
            'SF Collection Lag Time',
            'LFs',
            'LFs in Compliance Number',
            'LFs in Compliance Percent',
            'LF Collection Lag Time',
            'Total Number of Verified Forms',
            'Evidence',
            'Evidence Percent',
            'Invalid Intercept',
            'Invalid Intercept Percent',
            'High Risk of Trafficking',
            'High Risk of Trafficking Percent',
            'VDF Percent',
            'PVF Percent',
            'V Photos Percent',
            'Compliance Percent',
            'Collection Lag Time',
            'Evidence Cases with CIF Percent',
            'IRF Suspect SF Percent',
            'Percent of Valid Intercepts',
            'Percent Phone Numbers Verified',
            'Total'
        ]
    
    year_month = year_months[0]
    
    year = int(year_month[:4])
    month = int (year_month[4:])
    
    start_date = datetime.date(year, month,1)
    end_date = datetime.date(year, month, calendar.monthrange(year,month)[1])
    
    rows = []
    rows.append(headers)
    
    countries = Country.objects.all()
    for country in countries:
        results = IndicatorsViewSet.compute_collection_indicators(start_date, end_date, country.id)
        if 'pvf_form' in results[0] and results[0]['pvf_form']:
            pvf_form = True
        else:
            pvf_form = False
        for result in results:
            row = []
            row.append(year_month)
            row.append(year)
            row.append(month)
            row.append(country.name)
            row.append(result['label'])
            row.append(result['victim_count'])
            
            row.append(result['irf_count'])
            row.append(result['irf_compliance_count'])
            row.append(result['irf_compliance_percent'])
            row.append(result['irf_lag'])
            
            if pvf_form:
                # CIFs
                row.append('')
                row.append('')
                row.append('')
                row.append('')
                row.append('')
                row.append('')
                
                #VDF
                row.append('')
                row.append('')
                row.append('')
                row.append('')
                
                #PVF
                row.append(result['vdf_count'])
                row.append(result['vdf_compliance_count'])
                row.append(result['vdf_compliance_percent'])
                row.append(result['vdf_lag'])
                
                #SF
                row.append(result['sf_count'])
                row.append(result['sf_compliance_count'])
                row.append(result['sf_compliance_percent'])
                row.append(result['sf_lag'])
                
                #LF
                row.append(result['lf_count'])
                row.append(result['lf_compliance_count'])
                row.append(result['lf_compliance_percent'])
                row.append(result['lf_lag'])
            else:
                #CIF
                row.append(result['cif_count'])
                row.append(result['cif_percent'])
                row.append(result['cif_compliance_count'])
                row.append(result['cif_compliance_percent'])
                row.append(result['cif_lag'])
                row.append(result['cif_with_evidence_count'])
                
                #VDF
                row.append(result['vdf_count'])
                row.append(result['vdf_compliance_count'])
                row.append(result['vdf_compliance_percent'])
                row.append(result['vdf_lag'])
                
                #PVF
                row.append('')
                row.append('')
                row.append('')
                row.append('')
                
                #SF
                row.append('')
                row.append('')
                row.append('')
                row.append('')
                
                #LF
                row.append('')
                row.append('')
                row.append('')
                row.append('')
            
            row.append(result['verified_forms'])
            row.append(result['evidence_count'])
            row.append(result['evidence_percent'])
            row.append(result['invalid_intercept_count'])
            row.append(result['invalid_intercept_percent'])
            row.append(result['high_risk_count'])
            row.append(result['high_risk_percent'])
            
            if pvf_form:
                row.append('')
                row.append(result['vdf_percent'])
            else:
                row.append(result['vdf_percent'])
                row.append('')
                
            row.append(result['photo_percent'])
            row.append(result['compliance_percent'])
            row.append(result['collection_lag_time'])
            
            if pvf_form:
                row.append('')
                row.append(result['sf_percent'])
            else:
                row.append(result['evidence_cif_percent'])
                row.append('')
                
            row.append(result['valid_intercept_percent'])
            row.append(result['phone_verified_percent'])
            row.append(result['compliance_total'])
            
            rows.append(row)
    
    return rows

def export_entry_indicators (year_month):
        spreadsheet = 'Data Indicators' + settings.SPREADSHEET_SUFFIX
        sheet = GoogleSheet(spreadsheet,'Entry', 'year month', get_data_entry_indicator_export_rows)
        sheet.update(str(year_month), str(year_month))

def get_data_entry_indicator_export_rows(year_months):
    headers = [
        'year month',
        'year',
        'month',
        'country name',
        "IRF Lag Time",
        "IRF Forms Entered",
        "IRF Original Form Attached %",
        "Photo Upload Lag Time",
        "Photos Uploaded",
        "VDF Lag Time",
        "VDF Forms Entered",
        "VDF Original Form Attached %",
        "PVF Lag Time",
        "PVF Forms Entered",
        "PVF Original Form Attached %",
        "SF Lag Time",
        "SF Forms Entered",
        "SF Original Form Attached %",
        "LF Lag Time",
        "LF Forms Entered",
        "LF Original Form Attached %",
        "CIF Lag Time",
        "CIF Forms Entered",
        "CIF Original Form Attached %", 
        "Step 1: Verification Lag time",
        "Step 1: Verifications Completed",
        "Step 1: Verification Backlog",
        "Step 1: Verification Victims",
        "Step 2: Verification Lag time",
        "Step 2: Verifications Completed",
        "Step 2: Verification Backlog",
        "Step 2: Verification Victims",
        "MDF Signed %"
    ]
    indicators = [
        "irfLag",
        "irfCount",
        "irfOriginalFormPercent",
        "photosLag",
        "photosCount",
        "vdfLag",
        "vdfCount",
        "vdfOriginalFormPercent",
        "pvfLag",
        "pvfCount",
        "pvfOriginalFormPercent",
        "sfLag",
        "sfCount",
        "sfOriginalFormPercent",
        "lfLag",
        "lfCount",
        "lfOriginalFormPercent",
        "cifLag",
        "cifCount",
        "cifOriginalFormPercent",
        "v1Lag",
        "v1Count",
        "v1Backlog",
        "v1VictimCount",
        "v2Lag",
        "v2Count",
        "v2Backlog",
        "v2VictimCount",
        "mdfSignedPercent"
        ]
    rows = []
    rows.append(headers)
    
    year_month = year_months[0]

    year = int(year_month[:4])
    month = int (year_month[4:])
    
    start_date = datetime.date(year, month,1)
    end_date = datetime.date(year, month, calendar.monthrange(year,month)[1])
    
    countries = Country.objects.all()
    for country in countries:
        result = IndicatorHistory.calculate_indicators(start_date, end_date, country, include_latest_date=True)
        row = []
        row.append(year_month)
        row.append(year)
        row.append(month)
        row.append(country.name)
        for indicator in indicators:
            if indicator in result and result[indicator] != '-':
                row.append(result[indicator])
            else:
                row.append("")
        rows.append(row)
    
    return rows
            
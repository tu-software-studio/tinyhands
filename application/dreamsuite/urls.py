from django.urls import re_path, include
from django.conf import settings
from django.conf.urls.static import static

from django.contrib import admin

from django.contrib.auth import views as auth_views
from accounts import views as account_views
from dataentry import views as dataentry_views
from static_border_stations import views as static_border_stations_views


admin.autodiscover()

urlpatterns = [
    re_path(r'^$', dataentry_views.home, name='home'),
    re_path(r'^auth', account_views.AuthenticateRequest.as_view(), name='auth'),
    re_path(r'^data-entry/', include('dataentry.urls')),

    re_path(r'^api/', include('accounts.urls')),
    re_path(r'^api/', include('budget.urls')),
    re_path(r'^api/', include('events.urls')),
    re_path(r'^api/', include('face_matching.urls')),
    re_path(r'^api/', include('rest_api.urls')),
    re_path(r'^api/', include('portal.urls')),
    re_path(r'^api/', include('static_border_stations.urls')),
    # Must match MEDIA_URL to pull from cloud
    re_path(r'^cloud-media/', include('azure_storage.urls')),

    re_path(r'^login/$', auth_views.LoginView.as_view(), {'template_name': 'login.html'}, name='login'),
    re_path(r'^logout/$', auth_views.logout_then_login, name='logout'),
    re_path(r'^api-token-auth/', account_views.ObtainExpiringAuthToken.as_view()),

    re_path(r'^admin/', admin.site.urls),
    re_path(r'^interceptee_fuzzy_matching/', dataentry_views.interceptee_fuzzy_matching, name='interceptee_fuzzy_matching'),
    re_path(r'^get_station_id/', static_border_stations_views.get_station_id, name='get_station_id')
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) + static(settings.PUBLIC_URL, document_root=settings.PUBLIC_ROOT)

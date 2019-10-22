import os

from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.views.generic import RedirectView, TemplateView
from wagtail.contrib.wagtailsitemaps.views import sitemap
from wagtail.wagtailadmin import urls as wagtailadmin_urls
from wagtail.wagtailcore import urls as wagtail_urls
from wagtail.wagtaildocs import urls as wagtaildocs_urls
from wagtail.wagtailimages import urls as wagtailimages_urls
from wagtail.wagtailsearch import urls as wagtailsearch_urls
from wagtail.wagtailsearch.signal_handlers import register_signal_handlers as wagtailsearch_register_signal_handlers

from api import urls as api_urls

admin.autodiscover()

# Register search signal handlers
wagtailsearch_register_signal_handlers()

urlpatterns = [
    url(r'^accounts/', include('allauth.urls')),
    # redirect django admin login to allauth login
    url(r'^django-admin/login/$', RedirectView.as_view(pattern_name=settings.LOGIN_URL, query_string=True)),
    url(r'^django-admin/', include(admin.site.urls)),
    # redirect wagtail admin login to allauth login
    url(r'^admin/login/$', RedirectView.as_view(pattern_name=settings.LOGIN_URL, query_string=True)),
    url(r'^admin/', include(wagtailadmin_urls)),
    url(r'^search/', include(wagtailsearch_urls)),
    url(r'^documents/', include(wagtaildocs_urls)),
    url(r'^images/', include(wagtailimages_urls)),
    url(r'^api/', include(api_urls)),
    url(r'^sitemap\.xml$', sitemap),
    url(r'^robots\.txt$', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns.append(url(r'^__debug__', include(debug_toolbar.urls)))

    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL + 'images/', document_root=os.path.join(settings.MEDIA_ROOT, 'images'))
else:
    from django.views.static import serve
    urlpatterns.append(url(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}))

urlpatterns.append(url(r'', include(wagtail_urls)))  # This must always be the last one since it's a catch all.

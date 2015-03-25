from django.conf.urls import patterns, url
from pulp_puppet.forge.views.releases import ReleasesView, ReleasesPost36View
from pulp.server.db import connection

# This is all that is required to start using Manager classes
connection.initialize()

urlpatterns = patterns('',
    url(r'^pulp_puppet/forge/([^/]+)/([^/]+)/api/v1/releases.json', ReleasesView.as_view(),
        name='post_33_releases'),
    url(r'^api/v1/releases.json', ReleasesView.as_view(), name='pre_33_releases'),
    url(r'^v3/releases', ReleasesPost36View.as_view(), name='post_36_releases')
)

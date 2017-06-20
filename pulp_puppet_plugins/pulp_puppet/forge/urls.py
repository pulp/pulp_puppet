from django.conf.urls import url
from pulp_puppet.forge.views.releases import ReleasesView, ReleasesPost36View

urlpatterns = [
    url(r'^pulp_puppet/forge/([^/]+)/([^/]+)/api/v1/releases.json',
        ReleasesView.as_view(),
        name='post_33_releases'),
    url(r'^api/v1/releases.json', ReleasesView.as_view(),
        name='pre_33_releases'),
    url(r'^v3/releases', ReleasesPost36View.as_view(), name='post_36_releases')
]

from django.conf.urls import url
from rest_framework.routers import DefaultRouter

from goods import views

urlpatterns = [
    url(r'^categories/(?P<category_id>\d+)/skus/$', views.SKUListView.as_view()),
    url(r'^categories/(?P<cat>\d+)/$', views.SKUCategoriesView.as_view()),
    url(r"^categories/(?P<cat>\d+)/hotskus/$", views.SKUHotsView.as_view())
]

router = DefaultRouter()
router.register('skus/search', views.SKUSearchViewSet, base_name='skus_search')
urlpatterns += router.urls

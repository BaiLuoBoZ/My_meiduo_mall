from django.conf.urls import url
from rest_framework.routers import DefaultRouter

from areas import views

urlpatterns = [
    # url(r'^areas/$', views.AreasProvinceView.as_view()),
    # url(r'^areas/(?P<pk>\d+)/$', views.AreaSubView.as_view()),
]

router = DefaultRouter()
router.register(r'areas', views.AreasView, base_name='areas')

urlpatterns += router.urls

from django.shortcuts import render

# Create your views here.

from rest_framework.generics import RetrieveAPIView, ListAPIView
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_extensions.cache.mixins import CacheResponseMixin

from areas.models import Area
from areas.serializers import AreasProvinceSerializer, AreaSubSerializer


class AreasView(CacheResponseMixin, ReadOnlyModelViewSet):
    """视图集"""
    pagination_class = None

    def get_serializer_class(self):
        if self.action == 'list':
            return AreasProvinceSerializer
        else:
            return AreaSubSerializer

    def get_queryset(self):
        if self.action == "list":
            return Area.objects.filter(parent_id=None).all()
        else:
            return Area.objects.all()

# class AreasProvinceView(ListAPIView):
#     """获取省份信息"""
#     serializer_class = AreasProvinceSerializer
#     queryset = Area.objects.filter(parent_id=None).all()
#
#
# class AreaSubView(RetrieveAPIView):
#     """获取区县信息"""
#     serializer_class = AreaSubSerializer
#     queryset = Area.objects.all()

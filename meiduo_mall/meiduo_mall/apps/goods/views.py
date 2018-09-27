from django.shortcuts import render

# Create your views here.
from drf_haystack.viewsets import HaystackViewSet
from rest_framework.filters import OrderingFilter
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from goods.models import SKU, GoodsCategory
from goods.serializers import SKUSerializer, SKUIndexSerializer


# GET /categories/(?P<category_id>\d+)/skus?page=xxx&page_size=xxx&ordering=xxx
class SKUListView(ListAPIView):
    """
    商品列表数据
    """
    # 使用指定的序列化器类
    serializer_class = SKUSerializer
    # 排序
    filter_backends = [OrderingFilter]
    # 指定可以进行排序的字段
    ordering_fields = ('create_time', 'price', 'sales')

    def get_queryset(self):
        category_id = self.kwargs.get('category_id')
        return SKU.objects.filter(category_id=category_id, is_launched=True)

    # 使用指定的分页类
    # def get(self, request, category_id):
    #     # 根据category_id查询商品
    #     sku_list = self.get_queryset()
    #     # 将商品进行序列化
    #     serializer = self.get_serializer(sku_list, many=True)
    #
    #     return Response(serializer.data)


class SKUSearchViewSet(HaystackViewSet):
    """
    SKU搜索
    """
    index_models = [SKU]
    serializer_class = SKUIndexSerializer


# GET /categories/(?P<cat>\d)/
class SKUCategoriesView(APIView):
    """查询商品分类"""
    pagination_class = None

    def get(self, request, cat):
        # 查询当前商品的父分类

        cat3 = GoodsCategory.objects.get(id=cat)
        cat2 = GoodsCategory.objects.get(id=cat3.parent_id)
        cat1 = GoodsCategory.objects.get(id=cat2.parent_id)

        data = {
            'cat3': {'name': cat3.name},
            'cat2': {'name': cat2.name},
            'cat1': {"url": cat1.goodschannel_set.all().get().url, "category": {"name": cat1.name, "id": cat1.id}}
        }

        return Response(data=data)

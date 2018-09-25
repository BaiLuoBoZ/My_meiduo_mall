from rest_framework import serializers

from goods.models import SKU


class SKUSerializer(serializers.ModelSerializer):
    """商品展示序列化器"""

    class Meta:
        model = SKU
        fields = ('id', 'name', 'price', 'default_image_url', 'comments')

from rest_framework import serializers

from goods.models import SKU


class CartSerializer(serializers.Serializer):
    """添加购物车序列化器"""
    sku_id = serializers.IntegerField(label="商品sku_id")
    count = serializers.IntegerField(label="商品数量")
    selected = serializers.BooleanField(label="勾选状态", default=True)

    def validate(self, attrs):
        """判断该商品库存是否足够"""
        sku_id = attrs.get('sku_id')

        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            raise serializers.ValidationError("该商品不存在！")

        count = attrs.get('count')
        if count > sku.stock:
            raise serializers.ValidationError("该商品库存不足！")

        return attrs


class CartSKUSerializer(serializers.ModelSerializer):
    """查看购物车序列化器"""
    count = serializers.IntegerField(label="商品数量")
    selected = serializers.BooleanField(label="勾选状态", default=True)

    class Meta:
        model = SKU
        fields = ('id', 'name', 'default_image_url', 'price', 'count', 'selected')

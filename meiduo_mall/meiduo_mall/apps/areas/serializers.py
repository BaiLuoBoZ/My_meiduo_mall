from rest_framework import serializers

from areas.models import Area


class AreasProvinceSerializer(serializers.ModelSerializer):
    """获取省份模型类序列化器"""

    class Meta:
        model = Area
        fields = ('id', 'name')


class AreaSubSerializer(serializers.ModelSerializer):
    """获取区县模型类序列化器"""
    subs = AreasProvinceSerializer(many=True, read_only=True)

    class Meta:
        model = Area
        fields = ('id', 'name', 'subs')

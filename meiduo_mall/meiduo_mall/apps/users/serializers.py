import re

from django_redis import get_redis_connection
from rest_framework import serializers

# 创建用户序列化器类
from users.models import User


class CreateUserSerializer(serializers.ModelSerializer):
    """
    创建用户序列化器
    """
    password2 = serializers.CharField(label="确认密码", write_only=True)  # 表明该字段仅用于反序列化输入
    sms_code = serializers.CharField(label="短信验证码", write_only=True)
    allow = serializers.CharField(label="同意协议", write_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'password2', 'sms_code', 'allow', 'mobile')
        extra_kwargs = {
            "username": {
                "max_length": 20,
                "min_length": 5,
                "error_messages": {
                    "max_length": '仅允许5-20位的用户名',
                    "min_length": '仅允许5-20位的用户名'
                }
            },
            "password": {
                'write_only': True,
                'min_length': 8,
                'max_length': 20,
                'error_messages': {
                    'min_length': '仅允许8-20个字符的密码',
                    'max_length': '仅允许8-20个字符的密码',
                }
            }
        }

    # 测试手机号码
    def validate_mobile(self, value):
        """验证手机号码"""
        if not re.match(r'^1[3-9]\d{9}$', value):
            raise serializers.ValidationError("手机号码格式错误")

        # 判断手机号码是否重复
        count = User.objects.filter(mobile=value).count()

        if count > 0:
            raise serializers.ValidationError("手机号码已存在")

        return value

    def validate_allow(self, value):
        """校验用户是否同意协议"""
        if value != 'true':
            raise serializers.ValidationError("请同意用户协议")

        return value

    def validate(self, data):
        # 判断两次密码是否一致
        if data['password'] != data['password2']:
            raise serializers.ValidationError("两次密码不一致")

        # 判断短信验证码
        redis_conn = get_redis_connection("verify_codes")
        mobile = data['mobile']
        # 从数据库中获取短信验证码
        real_sms_code = redis_conn.get("sms_%s" % mobile)

        if real_sms_code is None:
            raise serializers.ValidationError('无效的短信验证码')

        if real_sms_code.decode() != data['sms_code']:
            raise serializers.ValidationError('短信验证码错误')

        return data

    def create(self, validated_data):
        """创建用户"""
        # 先删除模型类中原本不存在的字段
        del validated_data['password2']
        del validated_data['sms_code']
        del validated_data['allow']

        user = super().create(validated_data)

        # 调用django的认证系统加密密码
        user.set_password(validated_data['password'])
        # 保存用户对象
        user.save()
        # 将user对象返回
        return user

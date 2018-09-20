import re

from django.conf import settings
from django.core.mail import send_mail
from django_redis import get_redis_connection
from rest_framework import serializers

from rest_framework_jwt.settings import api_settings

from celery_tasks.email.tasks import send_verify_email
from users.models import User


# 创建用户序列化器类
class CreateUserSerializer(serializers.ModelSerializer):
    """
    创建用户序列化器
    """
    password2 = serializers.CharField(label="确认密码", write_only=True)  # 表明该字段仅用于反序列化输入
    sms_code = serializers.CharField(label="短信验证码", write_only=True)
    allow = serializers.CharField(label="同意协议", write_only=True)
    token = serializers.CharField(label="登陆状态token", read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'password2', 'sms_code', 'allow', 'mobile', 'token')
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

        # 补充生成记录登录状态的token
        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER
        # 生成载荷
        payload = jwt_payload_handler(user)
        # 生成jwk token
        token = jwt_encode_handler(payload)
        # 给user对象增加属性token，保存服务器签发的jwt token数据
        user.token = token

        # 将user对象返回
        return user


class UserDetailSerializer(serializers.ModelSerializer):
    """
    用户详细信息序列化器
    """

    class Meta:
        model = User
        fields = ('id', 'username', 'mobile', 'email', 'email_active')


class EmailSerializer(serializers.ModelSerializer):
    """保存邮箱序列化器"""

    class Meta:
        model = User
        fields = ('id', 'email')

    def update(self, instance, validated_data):
        """更新邮箱"""
        email = validated_data['email']
        instance.email = email
        # 保存邮箱地址
        instance.save()

        # 生成验证链接
        verify_url = instance.generate_verify_email_url()
        # 发送邮件验证(发布任务)
        send_verify_email.delay(email, verify_url)

        return instance

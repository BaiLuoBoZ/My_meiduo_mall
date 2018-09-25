import re

from django.conf import settings
from django.core.mail import send_mail
from django_redis import get_redis_connection
from rest_framework import serializers

from rest_framework_jwt.settings import api_settings

from celery_tasks.email.tasks import send_verify_email
from goods.models import SKU
from users import constants
from users.models import User, Address


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


class UserAddressSerializer(serializers.ModelSerializer):
    """
    用户地址序列化器
    """

    province = serializers.StringRelatedField(read_only=True)
    city = serializers.StringRelatedField(read_only=True)
    district = serializers.StringRelatedField(read_only=True)
    province_id = serializers.IntegerField(label="省ID", required=True)
    city_id = serializers.IntegerField(label="市ID", required=True)
    district_id = serializers.IntegerField(label="区ID", required=True)

    class Meta:
        model = Address
        exclude = ('is_deleted', 'user', 'update_time', 'create_time')

    def validate_mobile(self, value):
        """验证手机号码是否正确"""
        if not re.match(r'^1[3-8]\d{9}$', value):
            raise serializers.ValidationError("手机号码格式错误")
        return value

    def create(self, validated_data):
        """保存用户地址"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class AddressTitleSerializer(serializers.ModelSerializer):
    """地址标题"""

    class Meta:
        model = Address
        fields = ('title',)


class AddUserBrowsingHistorySerializer(serializers.Serializer):
    """保存用户浏览历史记录序列化器"""
    sku_id = serializers.IntegerField(label="商品id")

    def validate_sku_id(self, value):
        # 校验sku_id是否存在
        try:
            SKU.objects.get(id=value)
        except SKU.DoesNotExist:
            raise serializers.ValidationError("该商品不存在")

        return value

    def create(self, validated_data):
        """保存用户浏览历史记录"""
        # 获取用户id
        user = self.context['request'].user
        user_id = user.id
        sku_id = validated_data.get('sku_id')
        # 创建reids连接对象
        redis_conn = get_redis_connection('history')
        # 使用管道保存命令
        pl = redis_conn.pipeline()
        # 移除有重复sku_id的数据
        pl.lrem('history_%s' % user_id, 0, sku_id)
        # 从redis列表的左侧添加元素
        pl.lpush('history_%s' % user_id, sku_id)
        # 只保存最多5条记录
        pl.ltrim('history_%s' % user_id, 0, constants.USER_BROWSING_HISTORY_COUNTS_LIMIT - 1)

        # 执行管道里面的代码
        pl.execute()

        # 这里不返回user对象，直接返回validated_data也是可以的，在视图函数中得到的request.data就是校验之后的数据
        return validated_data

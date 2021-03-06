from datetime import datetime

from django_redis import get_redis_connection
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import CreateAPIView, RetrieveAPIView, GenericAPIView, UpdateAPIView
from rest_framework.mixins import CreateModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework_jwt.settings import api_settings
from rest_framework_jwt.utils import jwt_response_payload_handler
from rest_framework_jwt.views import ObtainJSONWebToken

from carts.utils import merge_cart_cookie_to_redis
from goods.models import SKU
from goods.serializers import SKUSerializer
from users import serializers, constants
from users.models import User

# usernames/(?P<username>\w{5,20})/count/
from users.serializers import CreateUserSerializer, EmailSerializer, UserAddressSerializer, AddressTitleSerializer, \
    AddUserBrowsingHistorySerializer


class UsernameCountView(APIView):
    """
    判断用户名是否存在
    """

    def get(self, request, username):
        # 根据username在数据库查询username的数量
        count = User.objects.filter(username=username).count()

        data = {
            "username": username,
            "count": count
        }
        # 将数据返回
        return Response(data)


# mobiles/(?P<mobile>1[3-9]\d{9})/count/
class MobileCountView(APIView):
    """
    判断手机号码是否存在
    """

    def get(self, request, mobile):
        count = User.objects.filter(mobile=mobile).count()

        data = {
            "mobile": mobile,
            "count": count
        }

        # 将数据返回
        return Response(data)


# 创建用户模型
# /users/
class UserView(CreateAPIView):
    """
    用户注册
    """
    # 指明该视图使用的序列化器
    serializer_class = CreateUserSerializer


class UserDetailView(RetrieveAPIView):
    """
    用户详情
    """
    serializer_class = serializers.UserDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class EmailView(UpdateAPIView):
    """保存用户邮箱"""
    serializer_class = EmailSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class VerifyEmailView(APIView):
    """邮箱验证"""

    def put(self, request):
        # 获取参数
        token = request.query_params.get('token')

        if token is None:
            return Response({"message": "缺少token"}, status=status.HTTP_400_BAD_REQUEST)

        user = User.check_verify_email(token)

        if user is None:
            return Response({"message": "链接信息无效"}, status=status.HTTP_400_BAD_REQUEST)

        else:
            user.email_active = True
            user.save()

            return Response({"message": "OK"})


class AddressViewSet(CreateModelMixin, UpdateModelMixin, GenericViewSet):
    """用户地址新增和修改"""

    serializer_class = UserAddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.request.user.addresses.filter(is_deleted=False)

    # GET /addresses/
    def list(self, request, *args, **kwargs):
        # 获取用户地址列表
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        user = self.request.user

        # 将数据返回
        return Response({
            'user_id': user.id,
            'default_address_id': user.default_address_id,
            'limit': constants.USER_ADDRESS_COUNTS_LIMIT,
            'addresses': serializer.data,
        })

    def create(self, request, *args, **kwargs):
        # 保存用户地址
        # 检查用户地址数量有没有超过上限
        count = self.request.user.addresses.filter(is_deleted=False).count()

        if count > constants.USER_ADDRESS_COUNTS_LIMIT:
            return Response({"message": "地址数量超过上限"}, status=status.HTTP_400_BAD_REQUEST)

        return super().create(request, *args, **kwargs)

    # delete /addresses/<pk>/
    def destroy(self, request, *args, **kwargs):
        """处理删除"""
        address = self.get_object()
        # 进行逻辑删除
        address.is_deleted = True
        # 保存
        address.save()

        return Response(status=status.HTTP_204_NO_CONTENT)

    # put / addresses / pk / status /
    @action(methods=['put'], detail=True)
    def status(self, request, pk=None):
        """
        设置默认地址
        """

        address = self.get_object()
        # 设置默认地址
        request.user.default_address = address
        request.user.save()

        return Response({"message": "OK"}, status=status.HTTP_200_OK)

    # put /addresses/pk/title/
    @action(methods=['put'], detail=True)
    def title(self, request, pk=None):
        """
        修改标题
        """
        address = self.get_object()

        serializer = AddressTitleSerializer(address, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)


# POST /browse_histories/
class UserBrowsingHistoryView(CreateAPIView):
    """保存/查看历史浏览记录"""
    # 设置只有认证成功的用户才能访问此视图
    permission_classes = [IsAuthenticated]
    # 使用指定的序列化器
    serializer_class = AddUserBrowsingHistorySerializer

    # def post(self, request):
    #     # 使用序列化器校验参数
    #     serializer = self.get_serializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #     # 保存
    #     serializer.save()
    #
    #     return Response(request.data, status=status.HTTP_201_CREATED)

    def get(self, request):
        """查看用户历史浏览记录"""
        # 创建数据库连接对象
        redis_conn = get_redis_connection('history')
        # 拼接key
        history_key = 'history_%s' % request.user.id
        # 获取redis列表指定区间的元素
        sku_id_list = redis_conn.lrange(history_key, 0, constants.USER_BROWSING_HISTORY_COUNTS_LIMIT - 1)

        sku_list = []
        for sku_id in sku_id_list:
            sku = SKU.objects.get(id=sku_id)
            # 将商品对象添加到模型类对象中
            sku_list.append(sku)
        # 将数据进行序列化,并返回
        serializer = SKUSerializer(sku_list, many=True)

        return Response(serializer.data)


class UserAuthorizeView(ObtainJSONWebToken):
    """用户登录"""
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            user = serializer.object.get('user') or request.user
            token = serializer.object.get('token')
            response_data = jwt_response_payload_handler(token, user, request)
            response = Response(response_data)
            if api_settings.JWT_AUTH_COOKIE:
                expiration = (datetime.utcnow() +
                              api_settings.JWT_EXPIRATION_DELTA)
                response.set_cookie(api_settings.JWT_AUTH_COOKIE,
                                    token,
                                    expires=expiration,
                                    httponly=True)
            # 合并购物车数据
            merge_cart_cookie_to_redis(request, user, response)
            return response

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

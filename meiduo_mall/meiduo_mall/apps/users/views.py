from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import CreateAPIView, RetrieveAPIView, GenericAPIView, UpdateAPIView
from rest_framework.mixins import CreateModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from users import serializers, constants
from users.models import User

# usernames/(?P<username>\w{5,20})/count/
from users.serializers import CreateUserSerializer, EmailSerializer, UserAddressSerializer, AddressTitleSerializer


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

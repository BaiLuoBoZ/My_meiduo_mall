from rest_framework import status
from rest_framework.generics import CreateAPIView, RetrieveAPIView, GenericAPIView, UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users import serializers
from users.models import User

# usernames/(?P<username>\w{5,20})/count/
from users.serializers import CreateUserSerializer, EmailSerializer


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

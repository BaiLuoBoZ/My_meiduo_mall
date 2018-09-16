from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import User


# usernames/(?P<username>\w{5,20})/count/
from users.serializers import CreateUserSerializer


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
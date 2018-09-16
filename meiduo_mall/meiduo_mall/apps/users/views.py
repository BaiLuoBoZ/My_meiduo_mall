from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import User


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

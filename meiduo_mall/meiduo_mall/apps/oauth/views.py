from django.shortcuts import render

# Create your views here.
from rest_framework.response import Response
from rest_framework.views import APIView

from oauth.utils import OAuthQQ


#  url(r'^qq/authorization/$', views.QQAuthURLView.as_view()),
class QQAuthURLView(APIView):
    """
    QQ登录的url地址:
    """

    def get(self, request):
        next = request.query_params.get('next', '/')
        # 获取qq登录url地址
        oauth = OAuthQQ(state=next)
        login_url = oauth.get_login_url()

        return Response({'login_url': login_url})

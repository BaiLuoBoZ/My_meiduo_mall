import base64
import pickle

from django.shortcuts import render

# Create your views here.
from django_redis import get_redis_connection
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from carts import constants
from carts.serializers import CartSerializer


class CartView(APIView):
    """
    购物车增删改查
    """

    def perform_authentication(self, request):
        """跳过系统的JWT token检查，让没有登陆的用户也可以访问此视图"""
        pass

    def post(self, request):
        """
        添加购物车
        1. 校验参数(sku_id,count,selected)
        2. 判断用户是否登陆
        3. 根据用户是否登陆将购物车分别进行保存
        """

        # 使用序列化器校验参数
        serializer = CartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 获取校验之后的参数
        sku_id = serializer.validated_data.get('sku_id')
        count = serializer.validated_data.get('count')
        selected = serializer.validated_data.get('selected')

        # 链接redis数据库
        redis_conn = get_redis_connection("cart")

        # 获取登陆用户
        try:
            user = request.user
        except Exception:
            user = None

        if user and user.is_authenticated:
            # 用户登陆状态
            # 创建key
            cart_key = "cart_%s" % user.id

            # 保存购物车中商品以及数量
            redis_conn.hincrby(cart_key, sku_id, count)

            # 创建key
            cart_selected_key = "cart_selected_%s" % user.id
            if selected:
                redis_conn.sadd(cart_selected_key, sku_id)

            # 返回应答，保存购物车记录成功
            return Response(serializer.data)

        else:
            # 用户未登陆
            # 获取客户端发送的cookie信息
            cookie_cart = request.COOKIES.get('cart')

            if cookie_cart:
                # 对cookie进行解析
                cart_dict = pickle.loads(base64.b64decode(cookie_cart))
            else:
                cart_dict = {}

            if sku_id in cart_dict:
                count += cart_dict['sku_id']['count']

            cart_dict[sku_id] = {
                'count': count,
                'selected': selected
            }
            # 转换成字符串
            cart_data = base64.b64encode(pickle.dumps(cart_dict)).decode()

            # 构建响应对象
            response = Response(serializer.data, status=status.HTTP_201_CREATED)

            # 设置cookie
            response.set_cookie('cart', cart_data, max_age=constants.CART_COOKIE_EXPIRES)

            return response

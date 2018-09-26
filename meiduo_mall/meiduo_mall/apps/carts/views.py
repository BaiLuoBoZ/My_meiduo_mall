import base64
import pickle

from django.shortcuts import render

# Create your views here.
from django_redis import get_redis_connection
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from carts import constants
from carts.serializers import CartSerializer, CartSKUSerializer, CartDeleteSerializer, CartSelectAllSerializer
from goods.models import SKU


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

    def get(self, request):
        """
        查询购物车
        1. 先判断用户是否登陆
        2. 根据不同的登陆状态取出客户的购物车数据
        """
        # 获取user
        try:
            user = request.user
        except Exception:
            user = None

        # 链接redis数据库
        redis_conn = get_redis_connection("cart")

        if user and user.is_authenticated:
            # 用户登陆状态
            # 创建key
            cart_key = "cart_%s" % user.id
            # 获取hash中所有的属性和值
            redis_cart = redis_conn.hgetall(cart_key)

            # 获取购物车商品中被选中的商品id
            cart_selected_key = "cart_selected_%s" % user.id
            redis_cart_selected = redis_conn.smembers(cart_selected_key)

            # 组织数据
            # {
            #     '<sku_id>': {
            #         'count': '<count>',
            #         'selected': '<selected>'
            #     },
            #     ...
            # }
            cart_dict = {}
            for sku_id, count in redis_cart.items():
                cart_dict[int(sku_id)] = {
                    'count': count,
                    'selected': sku_id in redis_cart_selected
                }

        else:
            # 用户未登陆
            # 从cookie中获取数据
            cookie_cart = request.COOKIES.get('cart')

            if cookie_cart:
                cart_dict = pickle.loads(base64.b64decode(cookie_cart))
            else:
                cart_dict = {}

        # 根据购物车信息获取商品的信息
        skus = SKU.objects.filter(id__in=cart_dict.keys())

        for sku in skus:
            sku.count = cart_dict[sku.id]['count']
            sku.selected = cart_dict[sku.id]['selected']

        # 将商品数据序列化并进行返回
        serializer = CartSKUSerializer(skus, many=True)
        # serializer.is_valid(raise_exception=True)

        return Response(serializer.data)

    def put(self, request):
        """修改购物车数据"""
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

        if user is not None and user.is_authenticated:
            # 登陆用户
            cart_key = "cart_%s" % user.id
            redis_conn.hset(cart_key, sku_id, count)

            cart_selected_key = "cart_selected_%s" % user.id
            if selected:
                redis_conn.sadd(cart_selected_key, sku_id)
            else:
                redis_conn.srem(cart_selected_key, sku_id)

            # 返回应答
            return Response(serializer.data)
        else:
            # 未登陆用户
            response = Response(serializer.data)
            # 获取客户端发送的cookie信息
            cookie_cart = request.COOKIES.get('cart')

            if not cookie_cart:
                return response

            # 解析cookie
            cart_dict = pickle.loads(base64.b64decode(cookie_cart))

            if not cart_dict:
                return response

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

    def delete(self, request):
        """删除购物车商品"""
        # 校验参数
        serializer = CartDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 获取校验之后的参数
        sku_id = serializer.validated_data.get('sku_id')

        # 链接redis数据库
        redis_conn = get_redis_connection("cart")

        # 获取登陆用户
        try:
            user = request.user
        except Exception:
            user = None

        if user and user.is_authenticated:
            # 登陆状态
            cart_key = 'cart_%s' % user.id
            # 删除hash中指定的属性和值，有则删除，无则忽略
            redis_conn.hdel(cart_key, sku_id)

            cart_selected_key = "cart_selected_%s" % user.id
            # 删除set集合中的元素，有则删除，无则忽略
            redis_conn.srem(cart_selected_key, sku_id)

            # 返回响应
            return Response(status=status.HTTP_204_NO_CONTENT)

        else:
            # 用户未登陆状态
            response = Response(status=status.HTTP_204_NO_CONTENT)
            cookie_cart = request.COOKIES.get('cart')

            if not cookie_cart:
                return response

            # 解析cookie数据
            cart_dict = pickle.loads(base64.b64decode(cookie_cart))

            if not cart_dict:
                return response

            if sku_id in cart_dict:
                del cart_dict[sku_id]

            cart_data = base64.b64encode(pickle.dumps(cart_dict))

            response.set_cookie('cart', cart_data, expires=constants.CART_COOKIE_EXPIRES)

            return response


class CartSelectAllView(APIView):
    """全选/取消全选"""

    def perform_authentication(self, request):
        """跳过系统的JWT token检查，让没有登陆的用户也可以访问此视图"""
        pass

    def put(self, request):
        """全选/取消全选"""

        # 使用序列化器校验参数
        serializer = CartSelectAllSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 获取校验之后的参数
        selected = serializer.validated_data.get('selected')

        # 创建redis链接对象
        redis_conn = get_redis_connection('cart')

        # 获取user对象
        try:
            user = request.user
        except Exception:
            user = None

        if user is not None and user.is_authenticated:
            # 用户登陆状态
            if selected:
                # 全选
                cart_key = 'cart_%s' % user.id
                # 获取hash中所有的属性
                sku_ids = redis_conn.hkeys(cart_key)

                cart_selected_key = "cart_selected_%s" % user.id
                # 向set集合中添加元素，忽略已添加的元素
                redis_conn.sadd(cart_selected_key, *sku_ids)
            else:
                # 取消全选
                cart_key = 'cart_%s' % user.id
                # 获取hash中所有的属性
                sku_ids = redis_conn.hkeys(cart_key)

                cart_selected_key = "cart_selected_%s" % user.id
                # 从set集合中移除元素，存在就移除，不存在就忽略
                redis_conn.srem(cart_selected_key, *sku_ids)

            # 返回状态
            return Response({'message': 'OK'})

        else:
            # 用户未登陆状态
            cart_cookie = request.COOKIES.get('cart')

            if not cart_cookie:
                return Response({'message': 'OK'})

            # 解析cookie
            cart_dict = pickle.loads(base64.b64decode(cart_cookie))

            if not cart_dict:
                return Response({'message': 'OK'})

            for sku_id in cart_dict.keys():
                cart_dict[sku_id]['selected'] = selected

            # 转换为字符串
            cart_data = base64.b64encode(pickle.dumps(cart_dict)).decode()

            # 构建响应对象
            response = Response({'message': 'OK'})

            response.set_cookie('cart', cart_data, expires=constants.CART_COOKIE_EXPIRES)

            return response

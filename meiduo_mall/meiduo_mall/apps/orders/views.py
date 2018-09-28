from decimal import Decimal

from django_redis import get_redis_connection
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

# GET /orders/settlement/
from goods.models import SKU
from orders.serializers import OrderSettlementSerializer


class OrderSettlementView(APIView):
    """订单结算商品信息获取"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """获取商品信息"""

        # 获取当前用户
        user = request.user

        # 链接数据库
        redis_conn = get_redis_connection('cart')

        # 拼接键
        cart_key = 'cart_%s' % user.id

        # 从数据库中获取商品id和数量
        cart_count = redis_conn.hgetall(cart_key)

        # 拼接键
        cart_selected_key = 'cart_selected_%s' % user.id

        # 从数据库中获取已经选中的商品
        cart_selected = redis_conn.smembers(cart_selected_key)

        cart = {}
        for sku_id in cart_selected:
            cart[int(sku_id)] = int(cart_count[sku_id])

        # 查询已勾选的商品的数据
        skus = SKU.objects.filter(id__in=cart.keys())

        for sku in skus:
            # 给商品模型对象添加属性count。
            sku.count = cart[sku.id]

        # 运费
        freight = Decimal('10')

        # 将数据进行序列化
        serializer = OrderSettlementSerializer({'freight': freight, 'skus': skus})

        # 返回序列化之后的数据
        return Response(serializer.data)

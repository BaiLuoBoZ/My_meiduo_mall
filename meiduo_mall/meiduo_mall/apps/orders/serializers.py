import logging
from datetime import datetime
from decimal import Decimal

from django.db import transaction
from django_redis import get_redis_connection
from rest_framework import serializers

from goods.models import SKU
from orders.models import OrderInfo, OrderGoods

# 创建日志器
logger = logging.getLogger('django')


class CartSKUSerializer(serializers.ModelSerializer):
    """结算的商品信息序列化器类"""

    count = serializers.IntegerField(label='商品数量')

    class Meta:
        model = SKU
        fields = ('id', 'name', 'default_image_url', 'price', 'count')


class OrderSettlementSerializer(serializers.Serializer):
    """
    订单结算序列化器类
    """

    freight = serializers.DecimalField(label='运费', max_digits=10, decimal_places=2)
    skus = CartSKUSerializer(many=True)


class SaveOrder(serializers.ModelSerializer):
    """保存订单序列化器"""

    class Meta:
        model = OrderInfo
        fields = ('address', 'pay_method', 'order_id')
        read_only_fields = ('order_id',)
        extra_kwargs = {
            'address': {
                'write_only': True,
                'required': True,
            },
            'pay_method': {
                'write_only': True,
                'required': True
            }
        }

    def create(self, validated_data):
        """将订单信息保存"""
        # 地址
        address = validated_data['address']
        # 支付方式
        pay_method = validated_data['pay_method']
        # 获取用户对象
        user = self.context['request'].user
        # 运费
        freight = Decimal(10)
        # 订单状态
        status = OrderInfo.ORDER_STATUS_ENUM['UNSEND'] if pay_method == OrderInfo.PAY_METHODS_ENUM['CASH'] else \
            OrderInfo.ORDER_STATUS_ENUM['UNPAID']
        # 生成订单号
        order_id = datetime.now().strftime('%Y%m%d%H%M%S') + '%010d' % user.id

        # 商品总数
        total_count = 0
        # 商品总金额
        total_amount = Decimal(0)

        # 链接数据库
        redis_conn = get_redis_connection('cart')
        # 获取键
        cart_selected_key = 'cart_selected_%s' % user.id
        # 获取已经勾选的所有商品sku_id
        sku_ids = redis_conn.smembers(cart_selected_key)
        # 获取键
        cart_key = 'cart_%s' % user.id
        # 获取数量count
        cart_dict = redis_conn.hgetall(cart_key)

        # 生成订单
        with transaction.atomic():
            # 创建一个保存点
            save_id = transaction.savepoint()
            try:
                # 1）向订单基本信息表中添加一条记录。
                order = OrderInfo.objects.create(
                    order_id=order_id,
                    user=user,
                    address=address,
                    total_count=total_count,
                    total_amount=total_amount,
                    freight=freight,
                    pay_method=pay_method,
                    status=status
                )

                for sku_id in sku_ids:
                    count = cart_dict[sku_id]
                    count = int(count)

                    # 根据sku_id获取对应的商品,给该记录加锁，锁住后，别人无法在操作
                    print('user: %s try get lock' % user.id)
                    sku = SKU.objects.select_for_update().get(id=sku_id)
                    print('user: %s get locked' % user.id)
                    # 判断商品的库存
                    if count > sku.stock:
                        raise serializers.ValidationError("商品库存不足")

                    import time
                    time.sleep(10)
                    # 减少商品库存，增加销量
                    sku.stock -= count
                    sku.sales += count
                    sku.save()

                    # 向订单商品表中添加数据
                    OrderGoods.objects.create(
                        order=order,
                        sku=sku,
                        count=count,
                        price=sku.price
                    )
                    # 累加计算订单商品的总数量和总金额
                    total_count += count
                    total_amount += sku.price * count

                # 实付款
                total_amount += freight
                # 更新订单记录中商品的总数量和实付款
                order.total_count = total_count
                order.total_amount = total_amount
                order.save()
            except serializers.ValidationError:
                # 继续向外抛出此异常
                raise

            except Exception as e:
                logger.error(e)
                # 回滚事物到save_id 保存点
                transaction.savepoint_rollback(save_id)
                raise serializers.ValidationError("下单失败")

        # 清除redis中对应的购物车记录。
        pl = redis_conn.pipeline()
        pl.hdel(cart_key, *sku_ids)
        pl.srem(cart_selected_key, *sku_ids)
        pl.execute()

        # 返回订单对象
        return order

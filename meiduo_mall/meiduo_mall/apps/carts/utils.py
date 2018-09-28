# 登陆合并购物车
import base64
import pickle

from django_redis import get_redis_connection


def merge_cart_cookie_to_redis(request, user, response):
    """
    登陆合并购物车的数据，将未登陆时cookie里面的购物车数据合并到redis里面，
    如果cookie里面的数据和redis里面的购物车数据有冲突那么就以cookie里面的
    数据为准。
    """
    # 先获取cookie里面的购物车数据
    cookie_cart = request.COOKIES.get('cart')

    # 判断数据是否为空
    if cookie_cart is None:
        return

    # 解析购物车数据
    cart_dick = pickle.loads(base64.b64decode(cookie_cart))

    # 判断数据是否为空
    if not cart_dick:
        return

        # cookie中保存的购物车数据格式
    # {
    #     sku_id:{
    #         'count':count,
    #         'selected':selected
    #     },
    #     ...
    # }

    # 用于保存向redis中添加的商品数量
    cart = {}

    # 记录redis勾选状态中应该增加的商品id
    redis_cart_selected_add = []

    # 记录redis勾选状态中应该删除的商品id
    redis_cart_selected_remove = []

    # 合并redis和cookie数据库，
    for sku_id, sku_count_selected in cart_dick.items():
        # 处理商品数量
        cart[sku_id] = sku_count_selected['count']  # cart : {'sku_id':'count'}

        if sku_count_selected['selected']:
            # 记录应该增加的商品id
            redis_cart_selected_add.append(sku_id)
        else:
            # 记录应该删除的商品id
            redis_cart_selected_remove.append(sku_id)

    if cart:
        # 链接数据库
        redis_conn = get_redis_connection('cart')

        cart_key = 'cart_%s' % user.id

        pl = redis_conn.pipeline()
        # 将数据保存到redis数据库中
        pl.hmset(cart_key, cart)

        cart_selected_key = 'cart_selected_%s' % user.id

        if redis_cart_selected_add:
            pl.sadd(cart_selected_key, *redis_cart_selected_add)

        if redis_cart_selected_remove:
            pl.srem(cart_selected_key, *redis_cart_selected_remove)

        pl.execute()

    # 将cookie中的购物车数据删除
    response.delete_cookie('cart')

    return response

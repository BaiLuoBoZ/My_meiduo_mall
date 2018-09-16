import random

from django_redis import get_redis_connection
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from meiduo_mall.libs.yuntongxun.sms import CCP
from verifications import constants
import logging

logger = logging.getLogger('django')


class SMSCodeView(APIView):
    """
    短信验证码
    """

    def get(self, request, mobile):
        """发送短信验证码"""

        # 获取redis连接对象,传入要保存到哪个缓存空间
        redis_conn = get_redis_connection("verify_codes")

        # 判断在60s内是否发送过验证码
        if redis_conn.get("send_flag_%s" % mobile):
            return Response({"message": "请求次数过于频繁"}, status=status.HTTP_400_BAD_REQUEST)

        # 生成6位随机短信验证码
        sms_code = "%06d" % random.randint(0, 999999)
        # 打印一下短信验证码
        logger.info("短信验证码为： %s" % sms_code)

        # 创建一个管道对象
        pl = redis_conn.pipeline()
        # 将所有要连接数据库的操作全部加到管道中
        pl.setex("sms_%s" % mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)  # 将短信验证码保存到redis中
        pl.setex("send_flag_%s" % mobile, constants.SEND_SMS_CODE_INTERVAL, 1)  # 将发送短信的标记保存，有效时间为一分钟
        # 一起执行管道中的命令
        pl.execute()

        # 发送短信验证码
        sms_code_expires = constants.SMS_CODE_REDIS_EXPIRES // 60
        # 通过云通讯发送短信
        try:
            ccp = CCP()
            res = ccp.send_template_sms(mobile, [sms_code, sms_code_expires], constants.SMS_CODE_TEMP_ID)
        except Exception as e:
            # 打印日志
            logger.error(e)
            return Response({"message": "发送短信异常"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        if res != 0:
            return Response({"message": "发送短信失败"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response({"message": "OK"})

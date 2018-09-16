import logging

from celery_tasks.main import app
from .yuntongxun.sms import CCP

# 创建一个日志器
logger = logging.getLogger('django')

# 短信验证码模板
SMS_CODE_TEMP_ID = 1


@app.task(name='send_sms_code')
def send_sms_code(mobile, code, expires):
    """
    发送短信验证码
    :param mobile: 手机号
    :param code: 验证码
    :param expires: 有效时间
    :return: Nono
    """
    # 通过云通讯发送短信
    try:
        ccp = CCP()
        res = ccp.send_template_sms(mobile, [code, expires], SMS_CODE_TEMP_ID)
    except Exception as e:
        # 打印日志
        logger.error("发送验证码短信[异常][mobile: %s, message: %s ]" % (mobile, e))
    else:
        if res != 0:
            logger.warning("发送验证码短信[失败][mobile: %s]" % mobile)
        else:
            logger.info("发送短信验证码[成功][mobile: %s]" % mobile)

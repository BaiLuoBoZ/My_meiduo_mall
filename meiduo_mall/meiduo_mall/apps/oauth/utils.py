from urllib.parse import urlencode

from django.conf import settings


class OAuthQQ(object):
    # 对openid进行加密的秘钥
    SECRET_KEY = settings.SECRET_KEY
    # 对openid加密之后生成的access_token的有效时间
    EXPIRES_IN = 10 * 60

    def __init__(self, client_id=None, client_secret=None, redirect_uri=None, state=None):
        # QQ网站应用客户端id
        self.client_id = client_id or settings.QQ_CLIENT_ID
        # QQ网站应用客户端安全密钥
        self.client_secret = client_secret or settings.QQ_CLIENT_SECRET
        # 网站回调url网址
        self.redirect_uri = redirect_uri or settings.QQ_REDIRECT_URI
        self.state = state or settings.QQ_STATE

    def get_login_url(self):
        """
        获取QQ的登陆网址
        """

        # 组织参数
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'state': self.state,
            'scope': 'get_user_info'
        }

        # 拼接url地址
        url = 'https://graph.qq.com/oauth2.0/authorize?' + urlencode(params)

        return url

from django.conf import settings
from django.core.files.storage import Storage
from fdfs_client.client import Fdfs_client


class FDFSStorage(Storage):
    """FDFS文件存储类"""

    def _save(self, name, content):
        """
        name: 用户选择上传文件的名称 1.txt
        content: 包含用户上传文件内容的一个File对象，可以通过content.read()获取上传文件内容
        """
        # 创建Fdfs_client对象，参数传入fdfs_client客户端配置文件路径
        client = Fdfs_client(settings.FDFS_CLIENT_CONF)

        # 上传文件到fastdfs文件存储系统
        res = client.append_by_buffer(content.read())

        if res.get('Status') != "Upload successed.":
            raise Exception("上传文件到FastDFS文件系统出错")

        # 获取文件id
        file_id = res.get('Remote file_id')

        # Django会将该方法的返回值保存到数据库中对应的文件字段
        return file_id

    def exists(self, name):
        """
        判断用户上传的文件在文件系统中是否存在，防止文件同名
        :param name: 用户上传的文件名称
        """

        return False

    def url(self, name):
        """
        获取可以访问到文件的完整url路径
        :param name: 数据表中图片字段保存的内容
        """
        return settings.FDFS_URL + name

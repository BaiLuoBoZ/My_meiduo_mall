from django.db import models


# Create your models here.

class Pics(models.Model):
    image = models.ImageField(verbose_name="测试图片")

    class Meta:
        db_table = 'tb_pics'
        verbose_name = "FastDFS上传文件测试"
        verbose_name_plural = verbose_name

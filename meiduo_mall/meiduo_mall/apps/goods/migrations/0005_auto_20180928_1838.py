# -*- coding: utf-8 -*-
# Generated by Django 1.11.11 on 2018-09-28 10:38
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('goods', '0004_auto_20180928_1735'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='goods',
            name='desc_detail',
        ),
        migrations.RemoveField(
            model_name='goods',
            name='desc_pack',
        ),
        migrations.RemoveField(
            model_name='goods',
            name='desc_service',
        ),
    ]
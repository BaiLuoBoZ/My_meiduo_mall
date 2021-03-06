from django.conf import settings
from django.core.mail import send_mail

from celery_tasks.main import app


@app.task(name="send_verify_email")
def send_verify_email(email, verify_url):
    # 使用celery异步发送验证邮件
    subject = "美多商城邮箱验证"
    html_message = '<p>尊敬的用户您好！</p>' \
                   '<p>感谢您使用美多商城。</p>' \
                   '<p>您的邮箱为：%s 。请点击此链接激活您的邮箱：</p>' \
                   '<p><a href="%s">%s<a></p>' % (email, verify_url, verify_url)
    # 发送邮件
    send_mail(subject, '', settings.EMAIL_FROM, [email], html_message=html_message)

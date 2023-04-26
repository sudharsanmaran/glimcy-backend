from django.dispatch import receiver
from .models import Notification
from .views import subscription_notification


@receiver(subscription_notification)
def handle_subscription(sender, **kwargs):
    title = kwargs.get('title')
    message = kwargs.get('message')
    user = kwargs.get('user')
    Notification.objects.create(message=message, title=title, user=user)

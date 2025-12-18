from django.db import transaction
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import Order
from .services.delivery import generate_google_maps_link
from .services.telegram import send_order_created


@receiver(pre_save, sender=Order)
def set_maps_link(sender, instance: Order, **kwargs):
    """Ensure maps_link is generated server-side when coordinates are present."""
    if instance.maps_link:
        return
    if instance.latitude is not None and instance.longitude is not None:
        instance.maps_link = generate_google_maps_link(float(instance.latitude), float(instance.longitude))


@receiver(post_save, sender=Order)
def notify_new_order(sender, instance: Order, created: bool, **kwargs):
    """
    When a customer submits a new order (checkout), send it to Telegram.
    Uses transaction.on_commit so OrderItem rows are already created.
    """
    if not created:
        return
    order_id = instance.pk
    transaction.on_commit(lambda: send_order_created(order_id))

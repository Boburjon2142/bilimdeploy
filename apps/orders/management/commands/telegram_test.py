from django.core.management.base import BaseCommand

from apps.orders.services.telegram import send_message


class Command(BaseCommand):
    help = "Send a test message to Telegram using TELEGRAM_* env vars."

    def add_arguments(self, parser):
        parser.add_argument("--text", default="Test message from Django", help="Message text to send")

    def handle(self, *args, **options):
        send_message(options["text"])
        self.stdout.write(self.style.SUCCESS("telegram_test: done (check your Telegram)."))


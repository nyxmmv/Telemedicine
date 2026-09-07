import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create the deployment superuser when configured and not already present.'

    def handle(self, *args, **options):
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '')

        if not username or not password:
            self.stdout.write(
                'Superuser creation skipped because deployment credentials are not configured.'
            )
            return

        user_model = get_user_model()
        if user_model.objects.filter(username=username).exists():
            self.stdout.write(f'Superuser {username} already exists.')
            return

        user_model.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
        self.stdout.write(self.style.SUCCESS(f'Superuser {username} created.'))

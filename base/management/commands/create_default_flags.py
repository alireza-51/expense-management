from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from base.models import FlagIcon
import os


class Command(BaseCommand):
    help = 'Create default flag icons for languages'

    def handle(self, *args, **options):
        # Create default flag icons
        flags_data = [
            {
                'language_code': 'en',
                'description': 'English flag'
            },
            {
                'language_code': 'fa',
                'description': 'Persian flag'
            }
        ]

        for flag_data in flags_data:
            flag, created = FlagIcon.objects.get_or_create(
                language_code=flag_data['language_code'],
                defaults={
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created flag for {flag_data["language_code"]}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Flag for {flag_data["language_code"]} already exists')
                )

        self.stdout.write(
            self.style.SUCCESS('Default flag icons setup completed!')
        ) 
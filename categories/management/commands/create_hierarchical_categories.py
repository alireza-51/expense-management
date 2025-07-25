from django.core.management.base import BaseCommand
from categories.models import Category


class Command(BaseCommand):
    help = 'Create hierarchical categories for testing'

    def handle(self, *args, **options):
        # Create main expense categories
        main_categories = [
            {
                'name': 'Food & Dining',
                'color': '#FF6B6B',
                'children': [
                    {'name': 'Groceries', 'color': '#FF8E8E'},
                    {'name': 'Restaurants', 'color': '#FFB3B3'},
                    {'name': 'Takeout', 'color': '#FFD8D8'},
                ]
            },
            {
                'name': 'Transportation',
                'color': '#4ECDC4',
                'children': [
                    {'name': 'Fuel', 'color': '#6ED7CF'},
                    {'name': 'Public Transport', 'color': '#8EE1D9'},
                    {'name': 'Maintenance', 'color': '#AEEBE3'},
                ]
            },
            {
                'name': 'Entertainment',
                'color': '#45B7D1',
                'children': [
                    {'name': 'Movies', 'color': '#65C7E1'},
                    {'name': 'Games', 'color': '#85D7F1'},
                    {'name': 'Hobbies', 'color': '#A5E7F1'},
                ]
            },
            {
                'name': 'Healthcare',
                'color': '#96CEB4',
                'children': [
                    {'name': 'Medical', 'color': '#B6DED4'},
                    {'name': 'Dental', 'color': '#D6EEE4'},
                    {'name': 'Pharmacy', 'color': '#F6FEF4'},
                ]
            },
            {
                'name': 'Shopping',
                'color': '#FFEAA7',
                'children': [
                    {'name': 'Clothing', 'color': '#FFF2C7'},
                    {'name': 'Electronics', 'color': '#FFFAD7'},
                    {'name': 'Home & Garden', 'color': '#FFFFE7'},
                ]
            },
            {
                'name': 'Education',
                'color': '#DDA0DD',
                'children': [
                    {'name': 'Tuition', 'color': '#EDB0ED'},
                    {'name': 'Books', 'color': '#FDC0FD'},
                    {'name': 'Courses', 'color': '#FFD0FF'},
                ]
            },
            {
                'name': 'Travel',
                'color': '#98D8C8',
                'children': [
                    {'name': 'Accommodation', 'color': '#B8E8D8'},
                    {'name': 'Flights', 'color': '#D8F8E8'},
                    {'name': 'Activities', 'color': '#F8FFF8'},
                ]
            },
            {
                'name': 'Personal Care',
                'color': '#F7DC6F',
                'children': [
                    {'name': 'Hair & Beauty', 'color': '#F7EC8F'},
                    {'name': 'Fitness', 'color': '#F7FCAF'},
                    {'name': 'Wellness', 'color': '#F7FFCF'},
                ]
            }
        ]

        # Create main income categories
        main_income_categories = [
            {
                'name': 'Employment',
                'color': '#2ECC71',
                'children': [
                    {'name': 'Salary', 'color': '#4EDC91'},
                    {'name': 'Bonus', 'color': '#6EECB1'},
                    {'name': 'Overtime', 'color': '#8EFCD1'},
                ]
            },
            {
                'name': 'Business',
                'color': '#3498DB',
                'children': [
                    {'name': 'Freelance', 'color': '#54A8FB'},
                    {'name': 'Side Business', 'color': '#74B8FF'},
                    {'name': 'Consulting', 'color': '#94C8FF'},
                ]
            },
            {
                'name': 'Investments',
                'color': '#F39C12',
                'children': [
                    {'name': 'Dividends', 'color': '#F3BC32'},
                    {'name': 'Interest', 'color': '#F3DC52'},
                    {'name': 'Capital Gains', 'color': '#F3FC72'},
                ]
            },
            {
                'name': 'Other Income',
                'color': '#E74C3C',
                'children': [
                    {'name': 'Rental Income', 'color': '#E7645C'},
                    {'name': 'Gifts', 'color': '#E7847C'},
                    {'name': 'Refunds', 'color': '#E7A49C'},
                ]
            }
        ]

        created_count = 0

        # Create expense categories
        for main_cat_data in main_categories:
            main_category, created = Category.objects.get_or_create(
                name=main_cat_data['name'],
                type=Category.CategoryType.EXPENSE,
                parent=None,
                defaults={
                    'color': main_cat_data['color'],
                    'description': f'Main category for {main_cat_data["name"].lower()} expenses'
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f'Created main expense category: {main_category.name}')
            
            # Create child categories
            for child_data in main_cat_data['children']:
                child_category, child_created = Category.objects.get_or_create(
                    name=child_data['name'],
                    type=Category.CategoryType.EXPENSE,
                    parent=main_category,
                    defaults={
                        'color': child_data['color'],
                        'description': f'Subcategory of {main_category.name}'
                    }
                )
                
                if child_created:
                    created_count += 1
                    self.stdout.write(f'  Created child category: {child_category.name}')

        # Create income categories
        for main_cat_data in main_income_categories:
            main_category, created = Category.objects.get_or_create(
                name=main_cat_data['name'],
                type=Category.CategoryType.INCOME,
                parent=None,
                defaults={
                    'color': main_cat_data['color'],
                    'description': f'Main category for {main_cat_data["name"].lower()} income'
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f'Created main income category: {main_category.name}')
            
            # Create child categories
            for child_data in main_cat_data['children']:
                child_category, child_created = Category.objects.get_or_create(
                    name=child_data['name'],
                    type=Category.CategoryType.INCOME,
                    parent=main_category,
                    defaults={
                        'color': child_data['color'],
                        'description': f'Subcategory of {main_category.name}'
                    }
                )
                
                if child_created:
                    created_count += 1
                    self.stdout.write(f'  Created child category: {child_category.name}')

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} hierarchical categories')
        ) 
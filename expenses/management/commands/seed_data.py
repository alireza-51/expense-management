from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta
import random
from categories.models import Category
from expenses.models import Expense, Income


class Command(BaseCommand):
    help = 'Generate 6 months worth of seed data for testing'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to generate seed data...'))
        
        with transaction.atomic():
            # Create categories if they don't exist
            self.create_categories()
            
            # Generate 6 months of data
            self.generate_expense_data()
            self.generate_income_data()
            
        self.stdout.write(self.style.SUCCESS('Successfully generated seed data!'))

    def create_categories(self):
        """Create expense and income categories"""
        self.stdout.write('Creating categories...')
        
        # Expense categories
        expense_categories = [
            'Food & Dining',
            'Transportation',
            'Shopping',
            'Entertainment',
            'Utilities',
            'Healthcare',
            'Education',
            'Travel',
            'Home & Garden',
            'Personal Care'
        ]
        
        # Income categories
        income_categories = [
            'Salary',
            'Freelance',
            'Investment',
            'Bonus',
            'Side Business',
            'Rental Income'
        ]
        
        # Create expense categories
        for name in expense_categories:
            Category.objects.get_or_create(
                name=name,
                defaults={
                    'type': Category.CategoryType.EXPENSE,
                }
            )
        
        # Create income categories
        for name in income_categories:
            Category.objects.get_or_create(
                name=name,
                defaults={
                    'type': Category.CategoryType.INCOME,
                }
            )
        
        self.stdout.write(f'Created {len(expense_categories)} expense and {len(income_categories)} income categories')

    def generate_expense_data(self):
        """Generate daily expenses for 6 months"""
        self.stdout.write('Generating expense data...')
        
        # Get expense categories
        expense_categories = Category.objects.filter(type=Category.CategoryType.EXPENSE)
        
        # Generate data for the last 6 months
        end_date = timezone.now()
        start_date = end_date - timedelta(days=180)
        
        current_date = start_date
        expense_count = 0
        
        while current_date <= end_date:
            # Generate 1 expense per day (with some randomness)
            if random.random() < 0.8:  # 80% chance of having an expense each day
                category = random.choice(expense_categories)
                
                # Generate realistic amounts based on category
                amount = self.get_realistic_expense_amount(category.name)
                
                # Generate realistic notes
                note = self.get_expense_note(category.name)
                
                # Create expense
                Expense.objects.create(
                    amount=amount,
                    category=category,
                    note=note,
                    transacted_at=current_date.replace(
                        hour=random.randint(8, 20),
                        minute=random.randint(0, 59)
                    )
                )
                expense_count += 1
            
            current_date += timedelta(days=1)
        
        self.stdout.write(f'Generated {expense_count} expenses')

    def generate_income_data(self):
        """Generate weekly income for 6 months"""
        self.stdout.write('Generating income data...')
        
        # Get income categories
        income_categories = Category.objects.filter(type=Category.CategoryType.INCOME)
        
        # Generate data for the last 6 months
        end_date = timezone.now()
        start_date = end_date - timedelta(days=180)
        
        current_date = start_date
        income_count = 0
        
        while current_date <= end_date:
            # Generate weekly income (every 7 days)
            if current_date.weekday() == 0:  # Monday
                category = random.choice(income_categories)
                
                # Generate realistic amounts based on category
                amount = self.get_realistic_income_amount(category.name)
                
                # Generate realistic notes
                note = self.get_income_note(category.name)
                
                # Create income
                Income.objects.create(
                    amount=amount,
                    category=category,
                    note=note,
                    transacted_at=current_date.replace(
                        hour=random.randint(9, 17),
                        minute=random.randint(0, 59)
                    )
                )
                income_count += 1
            
            current_date += timedelta(days=1)
        
        self.stdout.write(f'Generated {income_count} income records')

    def get_realistic_expense_amount(self, category_name):
        """Generate realistic expense amounts based on category"""
        amount_ranges = {
            'Food & Dining': (5000, 25000),  # $5-25
            'Transportation': (2000, 15000),  # $2-15
            'Shopping': (3000, 50000),        # $3-50
            'Entertainment': (2000, 20000),   # $2-20
            'Utilities': (5000, 30000),       # $5-30
            'Healthcare': (1000, 25000),      # $1-25
            'Education': (5000, 100000),      # $5-100
            'Travel': (10000, 100000),        # $10-100
            'Home & Garden': (2000, 30000),   # $2-30
            'Personal Care': (1000, 15000),   # $1-15
        }
        
        min_amount, max_amount = amount_ranges.get(category_name, (1000, 10000))
        return random.randint(min_amount, max_amount)

    def get_realistic_income_amount(self, category_name):
        """Generate realistic income amounts based on category"""
        amount_ranges = {
            'Salary': (500000, 800000),       # $500-800
            'Freelance': (50000, 200000),     # $50-200
            'Investment': (10000, 100000),    # $10-100
            'Bonus': (100000, 500000),        # $100-500
            'Side Business': (20000, 150000), # $20-150
            'Rental Income': (100000, 300000), # $100-300
        }
        
        min_amount, max_amount = amount_ranges.get(category_name, (10000, 100000))
        return random.randint(min_amount, max_amount)

    def get_expense_note(self, category_name):
        """Generate realistic expense notes"""
        notes = {
            'Food & Dining': [
                'Lunch at restaurant',
                'Grocery shopping',
                'Coffee break',
                'Dinner with friends',
                'Fast food',
                'Takeout order',
                'Weekend brunch',
                'Office lunch',
                'Snacks',
                'Dinner date'
            ],
            'Transportation': [
                'Gas station',
                'Public transport',
                'Uber ride',
                'Parking fee',
                'Car maintenance',
                'Taxi fare',
                'Bus ticket',
                'Train ticket',
                'Fuel refill',
                'Car wash'
            ],
            'Shopping': [
                'Clothing purchase',
                'Electronics',
                'Books',
                'Gift for friend',
                'Home decor',
                'Sport equipment',
                'Accessories',
                'Online purchase',
                'Mall shopping',
                'Department store'
            ],
            'Entertainment': [
                'Movie tickets',
                'Concert tickets',
                'Gym membership',
                'Netflix subscription',
                'Game purchase',
                'Theater show',
                'Sports event',
                'Hobby supplies',
                'Music subscription',
                'Outdoor activity'
            ],
            'Utilities': [
                'Electricity bill',
                'Water bill',
                'Internet service',
                'Phone bill',
                'Gas bill',
                'Garbage service',
                'Cable TV',
                'Home insurance',
                'Property tax',
                'Maintenance fee'
            ],
            'Healthcare': [
                'Doctor visit',
                'Pharmacy',
                'Dental checkup',
                'Eye exam',
                'Prescription',
                'Health insurance',
                'Medical supplies',
                'Therapy session',
                'Lab test',
                'Emergency room'
            ],
            'Education': [
                'Online course',
                'Textbooks',
                'Workshop fee',
                'Certification exam',
                'Tutoring session',
                'Language class',
                'Professional training',
                'Conference ticket',
                'Study materials',
                'Academic subscription'
            ],
            'Travel': [
                'Hotel booking',
                'Flight tickets',
                'Car rental',
                'Vacation expenses',
                'Travel insurance',
                'Tour guide',
                'Souvenirs',
                'Restaurant abroad',
                'Local transport',
                'Activity booking'
            ],
            'Home & Garden': [
                'Furniture purchase',
                'Garden supplies',
                'Home improvement',
                'Cleaning supplies',
                'Kitchen items',
                'Bedding',
                'Tools',
                'Paint supplies',
                'Lighting fixtures',
                'Storage solutions'
            ],
            'Personal Care': [
                'Haircut',
                'Spa treatment',
                'Cosmetics',
                'Skincare products',
                'Hair products',
                'Nail salon',
                'Massage therapy',
                'Beauty products',
                'Personal hygiene',
                'Wellness products'
            ]
        }
        
        return random.choice(notes.get(category_name, ['General expense']))

    def get_income_note(self, category_name):
        """Generate realistic income notes"""
        notes = {
            'Salary': [
                'Monthly salary',
                'Bi-weekly paycheck',
                'Regular salary',
                'Payroll deposit',
                'Salary payment'
            ],
            'Freelance': [
                'Web development project',
                'Design work',
                'Consulting fee',
                'Writing assignment',
                'Graphic design',
                'Programming work',
                'Translation service',
                'Photography job',
                'Marketing project',
                'Content creation'
            ],
            'Investment': [
                'Stock dividends',
                'Interest payment',
                'Bond coupon',
                'Mutual fund distribution',
                'Real estate dividend',
                'Investment return',
                'Portfolio income',
                'Capital gains',
                'Dividend payment',
                'Investment income'
            ],
            'Bonus': [
                'Performance bonus',
                'Year-end bonus',
                'Sales commission',
                'Achievement bonus',
                'Incentive payment',
                'Quarterly bonus',
                'Special bonus',
                'Recognition bonus',
                'Project completion bonus',
                'Milestone bonus'
            ],
            'Side Business': [
                'Online store sales',
                'Tutoring income',
                'Consulting work',
                'Product sales',
                'Service fees',
                'Business income',
                'Side hustle',
                'Part-time work',
                'Entrepreneurial income',
                'Business profit'
            ],
            'Rental Income': [
                'Apartment rent',
                'Property rental',
                'Room rental',
                'Office space rent',
                'Equipment rental',
                'Parking space rent',
                'Storage unit rent',
                'Commercial property rent',
                'Vacation rental',
                'Rental property income'
            ]
        }
        
        return random.choice(notes.get(category_name, ['Income payment'])) 
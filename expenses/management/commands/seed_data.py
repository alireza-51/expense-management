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
        """Create hierarchical expense and income categories"""
        self.stdout.write('Creating hierarchical categories...')
        
        # Main expense categories with their children
        expense_categories = [
            {
                'name': 'Food & Dining',
                'color': '#FF6B6B',
                'description': 'Restaurants, groceries, and dining expenses',
                'children': [
                    {'name': 'Groceries', 'color': '#FF8E8E'},
                    {'name': 'Restaurants', 'color': '#FFB3B3'},
                    {'name': 'Takeout', 'color': '#FFD8D8'},
                ]
            },
            {
                'name': 'Transportation',
                'color': '#4ECDC4',
                'description': 'Gas, public transport, and vehicle expenses',
                'children': [
                    {'name': 'Fuel', 'color': '#6ED7CF'},
                    {'name': 'Public Transport', 'color': '#8EE1D9'},
                    {'name': 'Maintenance', 'color': '#AEEBE3'},
                ]
            },
            {
                'name': 'Entertainment',
                'color': '#45B7D1',
                'description': 'Movies, concerts, and leisure activities',
                'children': [
                    {'name': 'Movies', 'color': '#65C7E1'},
                    {'name': 'Games', 'color': '#85D7F1'},
                    {'name': 'Hobbies', 'color': '#A5E7F1'},
                ]
            },
            {
                'name': 'Healthcare',
                'color': '#96CEB4',
                'description': 'Medical expenses, prescriptions, and health services',
                'children': [
                    {'name': 'Medical', 'color': '#B6DED4'},
                    {'name': 'Dental', 'color': '#D6EEE4'},
                    {'name': 'Pharmacy', 'color': '#F6FEF4'},
                ]
            },
            {
                'name': 'Shopping',
                'color': '#FFEAA7',
                'description': 'Clothing, electronics, and general shopping',
                'children': [
                    {'name': 'Clothing', 'color': '#FFF2C7'},
                    {'name': 'Electronics', 'color': '#FFFAD7'},
                    {'name': 'Home & Garden', 'color': '#FFFFE7'},
                ]
            },
            {
                'name': 'Education',
                'color': '#DDA0DD',
                'description': 'Courses, books, and educational materials',
                'children': [
                    {'name': 'Tuition', 'color': '#EDB0ED'},
                    {'name': 'Books', 'color': '#FDC0FD'},
                    {'name': 'Courses', 'color': '#FFD0FF'},
                ]
            },
            {
                'name': 'Travel',
                'color': '#98D8C8',
                'description': 'Vacations, business trips, and travel expenses',
                'children': [
                    {'name': 'Accommodation', 'color': '#B8E8D8'},
                    {'name': 'Flights', 'color': '#D8F8E8'},
                    {'name': 'Activities', 'color': '#F8FFF8'},
                ]
            },
            {
                'name': 'Personal Care',
                'color': '#F7DC6F',
                'description': 'Haircuts, spa, and personal hygiene products',
                'children': [
                    {'name': 'Hair & Beauty', 'color': '#F7EC8F'},
                    {'name': 'Fitness', 'color': '#F7FCAF'},
                    {'name': 'Wellness', 'color': '#F7FFCF'},
                ]
            }
        ]
        
        # Main income categories with their children
        income_categories = [
            {
                'name': 'Employment',
                'color': '#2ECC71',
                'description': 'Regular employment income',
                'children': [
                    {'name': 'Salary', 'color': '#4EDC91'},
                    {'name': 'Bonus', 'color': '#6EECB1'},
                    {'name': 'Overtime', 'color': '#8EFCD1'},
                ]
            },
            {
                'name': 'Business',
                'color': '#3498DB',
                'description': 'Freelance and business income',
                'children': [
                    {'name': 'Freelance', 'color': '#54A8FB'},
                    {'name': 'Side Business', 'color': '#74B8FF'},
                    {'name': 'Consulting', 'color': '#94C8FF'},
                ]
            },
            {
                'name': 'Investments',
                'color': '#F39C12',
                'description': 'Dividends, interest, and investment returns',
                'children': [
                    {'name': 'Dividends', 'color': '#F3BC32'},
                    {'name': 'Interest', 'color': '#F3DC52'},
                    {'name': 'Capital Gains', 'color': '#F3FC72'},
                ]
            },
            {
                'name': 'Other Income',
                'color': '#E74C3C',
                'description': 'Other sources of income',
                'children': [
                    {'name': 'Rental Income', 'color': '#E7645C'},
                    {'name': 'Gifts', 'color': '#E7847C'},
                    {'name': 'Refunds', 'color': '#E7A49C'},
                ]
            }
        ]
        
        # Create expense categories
        for main_cat_data in expense_categories:
            main_category, created = Category.objects.get_or_create(
                name=main_cat_data['name'],
                type=Category.CategoryType.EXPENSE,
                parent=None,
                defaults={
                    'color': main_cat_data['color'],
                    'description': main_cat_data['description']
                }
            )
            
            if created:
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
                    self.stdout.write(f'  Created child category: {child_category.name}')
        
        # Create income categories
        for main_cat_data in income_categories:
            main_category, created = Category.objects.get_or_create(
                name=main_cat_data['name'],
                type=Category.CategoryType.INCOME,
                parent=None,
                defaults={
                    'color': main_cat_data['color'],
                    'description': main_cat_data['description']
                }
            )
            
            if created:
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
                    self.stdout.write(f'  Created child category: {child_category.name}')
        
        self.stdout.write('Successfully created hierarchical categories')

    def generate_expense_data(self):
        """Generate daily expenses for 6 months"""
        self.stdout.write('Generating expense data...')
        
        # Get child expense categories (categories with parents)
        expense_categories = Category.objects.filter(
            type=Category.CategoryType.EXPENSE,
            parent__isnull=False
        )
        
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
                notes = self.get_expense_note(category.name)
                
                # Create expense
                Expense.objects.create(
                    amount=amount,
                    category=category,
                    notes=notes,
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
        
        # Get child income categories (categories with parents)
        income_categories = Category.objects.filter(
            type=Category.CategoryType.INCOME,
            parent__isnull=False
        )
        
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
                notes = self.get_income_note(category.name)
                
                # Create income
                Income.objects.create(
                    amount=amount,
                    category=category,
                    notes=notes,
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
            # Food & Dining children
            'Groceries': (8000, 35000),       # $8-35
            'Restaurants': (12000, 45000),    # $12-45
            'Takeout': (5000, 25000),         # $5-25
            
            # Transportation children
            'Fuel': (15000, 35000),           # $15-35
            'Public Transport': (2000, 8000), # $2-8
            'Maintenance': (5000, 50000),     # $5-50
            
            # Entertainment children
            'Movies': (3000, 15000),          # $3-15
            'Games': (2000, 25000),           # $2-25
            'Hobbies': (1000, 30000),         # $1-30
            
            # Healthcare children
            'Medical': (5000, 50000),         # $5-50
            'Dental': (8000, 80000),          # $8-80
            'Pharmacy': (1000, 15000),        # $1-15
            
            # Shopping children
            'Clothing': (5000, 50000),        # $5-50
            'Electronics': (10000, 100000),   # $10-100
            'Home & Garden': (2000, 40000),   # $2-40
            
            # Education children
            'Tuition': (50000, 500000),       # $50-500
            'Books': (2000, 25000),           # $2-25
            'Courses': (10000, 100000),       # $10-100
            
            # Travel children
            'Accommodation': (20000, 200000), # $20-200
            'Flights': (50000, 300000),       # $50-300
            'Activities': (5000, 50000),      # $5-50
            
            # Personal Care children
            'Hair & Beauty': (3000, 25000),   # $3-25
            'Fitness': (2000, 20000),         # $2-20
            'Wellness': (1000, 15000),        # $1-15
        }
        
        min_amount, max_amount = amount_ranges.get(category_name, (1000, 10000))
        return random.randint(min_amount, max_amount)

    def get_realistic_income_amount(self, category_name):
        """Generate realistic income amounts based on category"""
        amount_ranges = {
            # Employment children
            'Salary': (500000, 800000),       # $500-800
            'Bonus': (100000, 500000),        # $100-500
            'Overtime': (50000, 200000),      # $50-200
            
            # Business children
            'Freelance': (50000, 200000),     # $50-200
            'Side Business': (20000, 150000), # $20-150
            'Consulting': (100000, 300000),   # $100-300
            
            # Investments children
            'Dividends': (10000, 100000),     # $10-100
            'Interest': (5000, 50000),        # $5-50
            'Capital Gains': (20000, 200000), # $20-200
            
            # Other Income children
            'Rental Income': (100000, 300000), # $100-300
            'Gifts': (5000, 50000),           # $5-50
            'Refunds': (1000, 25000),         # $1-25
        }
        
        min_amount, max_amount = amount_ranges.get(category_name, (10000, 100000))
        return random.randint(min_amount, max_amount)

    def get_expense_note(self, category_name):
        """Generate realistic expense notes"""
        notes = {
            # Food & Dining children
            'Groceries': [
                'Weekly grocery shopping',
                'Supermarket visit',
                'Fresh produce',
                'Pantry items',
                'Household essentials',
                'Organic groceries',
                'Bulk purchase',
                'Local market',
                'Food staples',
                'Kitchen supplies'
            ],
            'Restaurants': [
                'Dinner at restaurant',
                'Lunch with colleagues',
                'Date night dinner',
                'Business lunch',
                'Family dinner out',
                'Celebration meal',
                'Fine dining',
                'Casual dining',
                'Weekend brunch',
                'Special occasion'
            ],
            'Takeout': [
                'Food delivery',
                'Takeout order',
                'Fast food',
                'Pizza delivery',
                'Chinese takeout',
                'Burger order',
                'Sushi delivery',
                'Late night food',
                'Office lunch delivery',
                'Quick meal'
            ],
            
            # Transportation children
            'Fuel': [
                'Gas station fill-up',
                'Fuel refill',
                'Diesel purchase',
                'Premium gas',
                'Regular unleaded',
                'Fuel for trip',
                'Gas station visit',
                'Fuel purchase',
                'Tank refill',
                'Gasoline'
            ],
            'Public Transport': [
                'Bus fare',
                'Train ticket',
                'Metro pass',
                'Subway fare',
                'Public transport',
                'Commuter ticket',
                'Transit card',
                'Bus pass',
                'Train fare',
                'Public transportation'
            ],
            'Maintenance': [
                'Car maintenance',
                'Oil change',
                'Tire replacement',
                'Car repair',
                'Vehicle service',
                'Car wash',
                'Auto parts',
                'Mechanic service',
                'Car inspection',
                'Vehicle maintenance'
            ],
            
            # Entertainment children
            'Movies': [
                'Movie tickets',
                'Cinema visit',
                'Film screening',
                'Movie night',
                'Theater tickets',
                'Film festival',
                'Movie rental',
                'Streaming service',
                'Cinema snacks',
                'Movie date'
            ],
            'Games': [
                'Video game purchase',
                'Gaming subscription',
                'Board games',
                'Mobile games',
                'Gaming accessories',
                'Game console',
                'Online gaming',
                'Gaming tournament',
                'Game download',
                'Gaming equipment'
            ],
            'Hobbies': [
                'Hobby supplies',
                'Craft materials',
                'Art supplies',
                'Sports equipment',
                'Musical instruments',
                'Photography gear',
                'Gardening supplies',
                'DIY materials',
                'Collection items',
                'Hobby workshop'
            ],
            
            # Healthcare children
            'Medical': [
                'Doctor visit',
                'Medical consultation',
                'Health checkup',
                'Specialist appointment',
                'Medical procedure',
                'Health insurance',
                'Medical supplies',
                'Lab tests',
                'Emergency room',
                'Medical treatment'
            ],
            'Dental': [
                'Dental checkup',
                'Dental cleaning',
                'Dental procedure',
                'Tooth extraction',
                'Dental filling',
                'Dental insurance',
                'Orthodontic treatment',
                'Dental surgery',
                'Dental consultation',
                'Dental care'
            ],
            'Pharmacy': [
                'Prescription medication',
                'Over-the-counter drugs',
                'Pharmacy visit',
                'Medicine purchase',
                'Health supplements',
                'First aid supplies',
                'Pharmacy consultation',
                'Medication refill',
                'Health products',
                'Pharmacy items'
            ],
            
            # Shopping children
            'Clothing': [
                'Clothing purchase',
                'New outfit',
                'Shoes purchase',
                'Accessories',
                'Fashion items',
                'Work clothes',
                'Casual wear',
                'Formal attire',
                'Seasonal clothing',
                'Clothing store'
            ],
            'Electronics': [
                'Electronics purchase',
                'Phone upgrade',
                'Computer parts',
                'Gadgets',
                'Tech accessories',
                'Electronic devices',
                'Smartphone',
                'Laptop purchase',
                'Tech equipment',
                'Electronics store'
            ],
            'Home & Garden': [
                'Home decor',
                'Furniture purchase',
                'Garden supplies',
                'Home improvement',
                'Kitchen items',
                'Bedding',
                'Home accessories',
                'Garden tools',
                'Home renovation',
                'Household items'
            ],
            
            # Education children
            'Tuition': [
                'University tuition',
                'School fees',
                'Course tuition',
                'Educational program',
                'Academic fees',
                'Training program',
                'Workshop fee',
                'Certification course',
                'Professional training',
                'Educational institution'
            ],
            'Books': [
                'Textbook purchase',
                'Educational books',
                'Reference materials',
                'Study guides',
                'Academic books',
                'Learning materials',
                'Course books',
                'Educational resources',
                'Study materials',
                'Book purchase'
            ],
            'Courses': [
                'Online course',
                'Professional course',
                'Skill development',
                'Training course',
                'Educational workshop',
                'Learning program',
                'Certification course',
                'Skill training',
                'Educational course',
                'Professional development'
            ],
            
            # Travel children
            'Accommodation': [
                'Hotel booking',
                'Vacation rental',
                'Resort stay',
                'Hostel booking',
                'Lodging expenses',
                'Accommodation fee',
                'Hotel room',
                'Vacation accommodation',
                'Travel lodging',
                'Stay booking'
            ],
            'Flights': [
                'Flight tickets',
                'Airplane tickets',
                'Air travel',
                'Flight booking',
                'Airline tickets',
                'Flight reservation',
                'Air travel expenses',
                'Flight purchase',
                'Airline booking',
                'Flight fare'
            ],
            'Activities': [
                'Tourist activities',
                'Sightseeing tour',
                'Adventure activities',
                'Travel experiences',
                'Tour guide',
                'Travel activities',
                'Vacation activities',
                'Tourist attractions',
                'Travel experiences',
                'Activity booking'
            ],
            
            # Personal Care children
            'Hair & Beauty': [
                'Haircut',
                'Hair styling',
                'Beauty salon',
                'Hair treatment',
                'Beauty services',
                'Hair coloring',
                'Beauty treatment',
                'Salon visit',
                'Hair care',
                'Beauty appointment'
            ],
            'Fitness': [
                'Gym membership',
                'Fitness class',
                'Personal training',
                'Sports membership',
                'Fitness equipment',
                'Workout session',
                'Fitness program',
                'Gym fees',
                'Fitness training',
                'Sports activities'
            ],
            'Wellness': [
                'Spa treatment',
                'Massage therapy',
                'Wellness products',
                'Health supplements',
                'Wellness services',
                'Relaxation treatment',
                'Wellness program',
                'Health products',
                'Wellness consultation',
                'Self-care items'
            ]
        }
        
        return random.choice(notes.get(category_name, ['General expense']))

    def get_income_note(self, category_name):
        """Generate realistic income notes"""
        notes = {
            # Employment children
            'Salary': [
                'Monthly salary',
                'Bi-weekly paycheck',
                'Regular salary',
                'Payroll deposit',
                'Salary payment',
                'Base salary',
                'Regular income',
                'Employment salary',
                'Monthly paycheck',
                'Salary deposit'
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
            'Overtime': [
                'Overtime pay',
                'Extra hours',
                'Additional work',
                'Overtime compensation',
                'Extra time pay',
                'Extended hours',
                'Overtime hours',
                'Additional compensation',
                'Extra work pay',
                'Overtime income'
            ],
            
            # Business children
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
            'Consulting': [
                'Consulting services',
                'Professional advice',
                'Business consulting',
                'Expert consultation',
                'Advisory services',
                'Professional consulting',
                'Business advice',
                'Consulting project',
                'Expert services',
                'Professional guidance'
            ],
            
            # Investments children
            'Dividends': [
                'Stock dividends',
                'Dividend payment',
                'Investment dividends',
                'Share dividends',
                'Portfolio dividends',
                'Stock income',
                'Dividend income',
                'Investment return',
                'Shareholder dividend',
                'Dividend distribution'
            ],
            'Interest': [
                'Interest payment',
                'Bank interest',
                'Savings interest',
                'Investment interest',
                'Bond interest',
                'Interest income',
                'Financial interest',
                'Interest return',
                'Interest payment',
                'Interest earnings'
            ],
            'Capital Gains': [
                'Capital gains',
                'Investment profit',
                'Stock gains',
                'Portfolio gains',
                'Investment return',
                'Capital appreciation',
                'Investment profit',
                'Gains on investment',
                'Portfolio return',
                'Investment gains'
            ],
            
            # Other Income children
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
            ],
            'Gifts': [
                'Monetary gift',
                'Birthday gift',
                'Holiday gift',
                'Wedding gift',
                'Gift money',
                'Cash gift',
                'Present money',
                'Gift payment',
                'Gift income',
                'Gift received'
            ],
            'Refunds': [
                'Purchase refund',
                'Tax refund',
                'Insurance refund',
                'Service refund',
                'Product refund',
                'Overpayment refund',
                'Refund payment',
                'Money back',
                'Refund received',
                'Refund income'
            ]
        }
        
        return random.choice(notes.get(category_name, ['Income payment'])) 
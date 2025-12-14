from django.core.management.base import BaseCommand
from categories.models import Category
import colorsys


def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    """Convert RGB tuple to hex color"""
    return '#{:02X}{:02X}{:02X}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2]))


def lighten_color(hex_color, factor=0.15):
    """Lighten a color by a factor (0-1)"""
    rgb = hex_to_rgb(hex_color)
    # Convert to HSL
    h, s, l = colorsys.rgb_to_hls(rgb[0]/255.0, rgb[1]/255.0, rgb[2]/255.0)
    # Lighten
    l = min(1.0, l + factor)
    # Convert back to RGB
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return rgb_to_hex((r*255, g*255, b*255))


def get_color_for_level(base_color, level):
    """Get color for a specific hierarchy level (0=parent, 1=child, 2=grandchild)"""
    if level == 0:
        return base_color
    elif level == 1:
        return lighten_color(base_color, factor=0.15)
    else:
        return lighten_color(base_color, factor=0.25)


def get_color_for_child_index(base_color, index, total_children):
    """Get color for a child category based on its index (0-based)
    First child (index 0) is darker, last child is lighter"""
    if total_children <= 1:
        # Only one child, use standard child color
        return lighten_color(base_color, factor=0.15)
    
    # Calculate lightening factor: from 0.10 (darker) to 0.20 (lighter)
    # First child gets 0.10, last child gets 0.20
    min_factor = 0.10
    max_factor = 0.20
    factor = min_factor + (max_factor - min_factor) * (index / (total_children - 1))
    return lighten_color(base_color, factor=factor)


class Command(BaseCommand):
    help = '''Restructure categories to match new tree structure while preserving existing data.
    
    This command will:
    - Find and update existing matching categories (by name or mapping)
    - Create new categories that don't exist
    - Preserve all existing categories and their data
    - Update colors, parent relationships, and descriptions for matching categories
    
    Usage:
    - python manage.py restructure_categories  # Updates matching categories, creates missing ones
    - python manage.py restructure_categories --no-update-colors  # Don't update colors
    - python manage.py restructure_categories --no-update-parents  # Don't update parent relationships
    '''

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-update-colors',
            action='store_true',
            help='Do NOT update colors of existing categories',
        )
        parser.add_argument(
            '--no-update-parents',
            action='store_true',
            help='Do NOT update parent relationships of existing categories',
        )

    def find_existing_category(self, name, category_type, parent=None, name_mappings=None):
        """Find existing category by name (with case-insensitive matching and mappings)"""
        if name_mappings is None:
            name_mappings = {}
        
        # Try exact match first
        try:
            if parent:
                return Category.objects.get(name=name, type=category_type, parent=parent)
            else:
                return Category.objects.get(name=name, type=category_type, parent__isnull=True)
        except Category.DoesNotExist:
            pass
        
        # Try case-insensitive match
        try:
            if parent:
                return Category.objects.get(name__iexact=name, type=category_type, parent=parent)
            else:
                return Category.objects.get(name__iexact=name, type=category_type, parent__isnull=True)
        except Category.DoesNotExist:
            pass
        
        # Try mapping
        mapped_name = name_mappings.get(name)
        if mapped_name:
            try:
                if parent:
                    return Category.objects.get(name=mapped_name, type=category_type, parent=parent)
                else:
                    return Category.objects.get(name=mapped_name, type=category_type, parent__isnull=True)
            except Category.DoesNotExist:
                pass
        
        # Try reverse mapping (check if any existing category maps to this name)
        reverse_mapping = {v: k for k, v in name_mappings.items()}
        if name in reverse_mapping:
            old_name = reverse_mapping[name]
            try:
                if parent:
                    return Category.objects.get(name__iexact=old_name, type=category_type, parent=parent)
                else:
                    return Category.objects.get(name__iexact=old_name, type=category_type, parent__isnull=True)
            except Category.DoesNotExist:
                pass
        
        return None

    def handle(self, *args, **options):
        update_colors = not options.get('no_update_colors', False)  # Default to True
        update_parents = not options.get('no_update_parents', False)  # Default to True

        # Comprehensive name mappings for existing categories
        # Format: {'old_name': 'new_name'}
        name_mappings = {
            # Expense parent mappings
            'Entertainment': 'Entertainment & Lifestyle',
            'Education': 'Education & Growth',
            'Investment': 'Investments (Expense)',
            
            # Expense child mappings
            'Movies': 'Movies & Cinema',
            'Maintenance': 'Vehicle Maintenance',  # Under Transportation - rename existing
            'gifts': 'Gifts & Occasions',  # Lowercase gifts
            'Basic Items': 'Staple Foods',  # Under Groceries
            'Subscription': 'Subscriptions (Personal)',
            
            # Income parent mappings
            'Business': 'Business & Freelance',  # For income
            'Investments': 'Investments (Income)',  # For income type
        }
        
        # Special category moves: categories that should be moved to different parents
        # Format: {'category_name': 'new_parent_name'}
        category_moves = {
            # Move from "Subscription" to "Work & Business Expenses"
            'Internet': 'Work & Business Expenses',
            'Host & Server': 'Work & Business Expenses',
            'VPN': 'Work & Business Expenses',
            # Move standalone categories to become children
            'Charity': 'Charity & Donations',  # Move standalone "Charity" to be child of "Charity & Donations"
            'Debt': 'Financial Obligations',  # Move standalone "Debt" to be child of "Financial Obligations"
        }

        # Define new expense category structure with base colors
        expense_categories = {
            'Food & Dining': {
                'color': '#FF6B6B',
                'description': 'Main category for food & dining expenses',
                'children': {
                    'Groceries': {
                        'description': 'Subcategory of Food & Dining',
                        'children': {
                            'Staple Foods': {},
                            'Snacks & Drinks': {},
                            'Detergents & Cleaning Supplies': {},
                        }
                    },
                    'Restaurants': {'description': 'Subcategory of Food & Dining'},
                    'Takeout': {'description': 'Subcategory of Food & Dining'},
                    'Order In': {'description': 'Subcategory of Food & Dining'},
                }
            },
            'Housing & Home': {
                'color': '#9B59B6',
                'description': 'Main category for housing & home expenses',
                'children': {
                    'Rent / Mortgage': {},
                    'Utilities': {
                        'children': {
                            'Electricity': {},
                            'Water': {},
                            'Gas': {},
                            'Waste & HOA': {},
                        }
                    },
                    'Home Tools & Equipment': {},
                    'Furniture': {},
                    'Home Decor': {
                        'children': {
                            'Plants': {},
                            'Decorative Items': {},
                        }
                    },
                    'Maintenance & Repairs': {},
                }
            },
            'Transportation': {
                'color': '#4ECDC4',
                'description': 'Main category for transportation expenses',
                'children': {
                    'Fuel': {'description': 'Subcategory of Transportation'},
                    'Public Transport': {'description': 'Subcategory of Transportation'},
                    'Ride Hailing': {},
                    'Parking & Tolls': {},
                    'Vehicle Maintenance': {},
                }
            },
            'Healthcare': {
                'color': '#96CEB4',
                'description': 'Main category for healthcare expenses',
                'children': {
                    'Medical': {'description': 'Subcategory of Healthcare'},
                    'Dental': {'description': 'Subcategory of Healthcare'},
                    'Pharmacy': {'description': 'Subcategory of Healthcare'},
                    'Mental Health': {},
                    'Health Insurance': {},
                }
            },
            'Shopping': {
                'color': '#FFEAA7',
                'description': 'Main category for shopping expenses',
                'children': {
                    'Clothing': {'description': 'Subcategory of Shopping'},
                    'Electronics': {'description': 'Subcategory of Shopping'},
                    'Accessories': {},
                    'Gifts & Occasions': {
                        'children': {
                            'Flowers': {},
                            'Chocolates': {},
                            'Small Presents': {},
                        }
                    },
                    'Personal Gadgets': {},
                }
            },
            'Personal Care': {
                'color': '#F7DC6F',
                'description': 'Main category for personal care expenses',
                'children': {
                    'Hair & Beauty': {'description': 'Subcategory of Personal Care'},
                    'Fitness': {'description': 'Subcategory of Personal Care'},
                    'Wellness': {'description': 'Subcategory of Personal Care'},
                    'Cosmetics & Skincare': {},
                }
            },
            'Entertainment & Lifestyle': {
                'color': '#45B7D1',
                'description': 'Main category for entertainment & lifestyle expenses',
                'children': {
                    'Movies & Cinema': {},
                    'Games': {'description': 'Subcategory of Entertainment'},
                    'Hobbies': {'description': 'Subcategory of Entertainment'},
                    'Events & Concerts': {},
                    'Subscriptions (Personal)': {},
                }
            },
            'Education & Growth': {
                'color': '#DDA0DD',
                'description': 'Main category for education & growth expenses',
                'children': {
                    'Tuition': {'description': 'Subcategory of Education'},
                    'Books': {'description': 'Subcategory of Education'},
                    'Courses': {'description': 'Subcategory of Education'},
                    'Certifications': {},
                    'Workshops': {},
                }
            },
            'Travel': {
                'color': '#98D8C8',
                'description': 'Main category for travel expenses',
                'children': {
                    'Flights': {'description': 'Subcategory of Travel'},
                    'Accommodation': {'description': 'Subcategory of Travel'},
                    'Activities': {'description': 'Subcategory of Travel'},
                    'Travel Insurance': {},
                    'Visa & Documents': {},
                }
            },
            'Work & Business Expenses': {
                'color': '#3498DB',
                'description': 'Main category for work & business expenses',
                'children': {
                    'Internet (Work)': {},
                    'Host & Server': {},
                    'VPN': {},
                    'Software & SaaS': {},
                    'Office Equipment': {},
                }
            },
            'Financial Obligations': {
                'color': '#E67E22',
                'description': 'Main category for financial obligations',
                'children': {
                    'Debt': {
                        'children': {
                            'Loan': {},
                            'Cheque': {},
                            'BNPL': {},
                        }
                    },
                    'Taxes': {},
                    'Fines & Penalties': {},
                }
            },
            'Investments (Expense)': {
                'color': '#F39C12',
                'description': 'Main category for investment expenses',
                'children': {
                    'Gold': {},
                    'Stocks': {},
                    'Crypto': {},
                    'Real Estate Investment': {},
                    'Collectibles': {},
                }
            },
            'Family & Dependents': {
                'color': '#E91E63',
                'description': 'Main category for family & dependents expenses',
                'children': {
                    'Childcare': {},
                    'School Fees': {},
                    'Elder Care': {},
                    'Allowances': {},
                }
            },
            'Pets': {
                'color': '#00BCD4',
                'description': 'Main category for pet expenses',
                'children': {
                    'Food': {},
                    'Vet': {},
                    'Grooming': {},
                    'Accessories': {},
                }
            },
            'Insurance': {
                'color': '#607D8B',
                'description': 'Main category for insurance expenses',
                'children': {
                    'Health': {},
                    'Vehicle': {},
                    'Home': {},
                    'Travel': {},
                    'Life': {},
                }
            },
            'Charity & Donations': {
                'color': '#16a34a',
                'description': 'Main category for charity & donations',
                'children': {
                    'Charity': {},
                    'Community Support': {},
                }
            },
            'Miscellaneous': {
                'color': '#95A5A6',
                'description': 'Main category for miscellaneous expenses',
                'children': {
                    'Emergency Expenses': {},
                    'Unexpected Purchases': {},
                    'Adjustments': {},
                }
            },
        }

        # Define new income category structure
        income_categories = {
            'Employment': {
                'color': '#2ECC71',
                'description': 'Main category for employment income',
                'children': {
                    'Salary': {'description': 'Subcategory of Employment'},
                    'Bonus': {'description': 'Subcategory of Employment'},
                    'Overtime': {'description': 'Subcategory of Employment'},
                    'Allowances': {},
                }
            },
            'Business & Freelance': {
                'color': '#3498DB',
                'description': 'Main category for business & freelance income',
                'children': {
                    'Freelance': {'description': 'Subcategory of Business'},
                    'Consulting': {'description': 'Subcategory of Business'},
                    'Side Business': {'description': 'Subcategory of Business'},
                    'Online Services': {},
                }
            },
            'Investments (Income)': {
                'color': '#F39C12',
                'description': 'Main category for investment income',
                'children': {
                    'Dividends': {'description': 'Subcategory of Investments'},
                    'Interest': {'description': 'Subcategory of Investments'},
                    'Capital Gains': {'description': 'Subcategory of Investments'},
                    'Rental Income': {},
                }
            },
            'Digital Income': {
                'color': '#9B59B6',
                'description': 'Main category for digital income',
                'children': {
                    'Ads Revenue': {},
                    'Affiliate Income': {},
                    'Content Monetization': {},
                    'Online Sales': {},
                }
            },
            'Other Income': {
                'color': '#E74C3C',
                'description': 'Main category for other income',
                'children': {
                    'Gifts Received': {},
                    'Refunds': {'description': 'Subcategory of Other Income'},
                    'Cashback': {},
                    'Grants & Aid': {},
                    'Royalties': {},
                }
            },
        }

        created_count = 0
        updated_count = 0

        # Process expense categories
        self.stdout.write(self.style.SUCCESS('\n=== Processing Expense Categories ===\n'))
        for parent_name, parent_data in expense_categories.items():
            # Try to find existing parent category
            existing_parent = self.find_existing_category(
                parent_name, 
                Category.CategoryType.EXPENSE, 
                parent=None,
                name_mappings=name_mappings
            )
            
            if existing_parent:
                # Update existing category
                parent_category = existing_parent
                updated = False
                renamed = False
                old_name = parent_category.name
                
                # Check if category needs to be renamed
                # If the found category's name is different from target, and it maps to target, rename it
                if parent_category.name != parent_name:
                    # Check if old name maps to new name
                    if name_mappings.get(parent_category.name) == parent_name:
                        # Category was found via mapping, needs to be renamed
                        parent_category.name = parent_name
                        updated = True
                        renamed = True
                
                if update_colors and parent_category.color != parent_data['color']:
                    parent_category.color = parent_data['color']
                    updated = True
                
                new_description = parent_data.get('description', f'Main category for {parent_name.lower()} expenses')
                if parent_category.description != new_description:
                    parent_category.description = new_description
                    updated = True
                
                if updated:
                    parent_category.save()
                    updated_count += 1
                    if renamed:
                        self.stdout.write(f'↻ Renamed & updated parent: {old_name} -> {parent_category.name}')
                    else:
                        self.stdout.write(f'↻ Updated parent: {parent_category.name}')
                else:
                    self.stdout.write(f'✓ Found existing parent: {parent_category.name}')
            else:
                # Create new parent category
                parent_category = Category.objects.create(
                    name=parent_name,
                    type=Category.CategoryType.EXPENSE,
                    parent=None,
                    color=parent_data['color'],
                    description=parent_data.get('description', f'Main category for {parent_name.lower()} expenses')
                )
                created_count += 1
                self.stdout.write(f'✓ Created parent: {parent_category.name}')

            # Process children
            for child_name, child_data in parent_data.get('children', {}).items():
                child_color = get_color_for_level(parent_data['color'], 1)
                
                # Check if this category should be moved to this parent
                should_move_here = category_moves.get(child_name) == parent_name
                
                # FIRST: Check if there's a standalone category that should become this child
                # This handles cases like "Charity" (standalone) -> "Charity & Donations" -> "Charity" (child)
                existing_child = None
                standalone_to_merge = None
                
                if should_move_here:
                    # Look for standalone category first (parent=None)
                    try:
                        standalone_to_merge = Category.objects.get(
                            name__iexact=child_name,
                            type=Category.CategoryType.EXPENSE,
                            parent__isnull=True
                        )
                    except Category.DoesNotExist:
                        standalone_to_merge = None
                    except Category.MultipleObjectsReturned:
                        # Multiple standalone found, use the first one
                        standalone_to_merge = Category.objects.filter(
                            name__iexact=child_name,
                            type=Category.CategoryType.EXPENSE,
                            parent__isnull=True
                        ).first()
                    
                    # Check if there's already a child with this name under the parent
                    try:
                        existing_child = Category.objects.get(
                            name__iexact=child_name,
                            type=Category.CategoryType.EXPENSE,
                            parent=parent_category
                        )
                    except Category.DoesNotExist:
                        existing_child = None
                    except Category.MultipleObjectsReturned:
                        existing_child = Category.objects.filter(
                            name__iexact=child_name,
                            type=Category.CategoryType.EXPENSE,
                            parent=parent_category
                        ).first()
                    
                    # If we found both standalone and existing child, merge them
                    if standalone_to_merge and existing_child:
                        # Merge: move expenses/incomes from standalone to existing child
                        from expenses.models import Expense, Income
                        standalone_id = standalone_to_merge.id
                        Expense.objects.filter(category=standalone_to_merge).update(category=existing_child)
                        Income.objects.filter(category=standalone_to_merge).update(category=existing_child)
                        # Move children of standalone to existing child
                        Category.objects.filter(parent=standalone_to_merge).update(parent=existing_child)
                        # Delete standalone
                        standalone_to_merge.delete()
                        self.stdout.write(f'  ↻ Merged standalone "{child_name}" (id: {standalone_id}) into existing child (id: {existing_child.id}) under {parent_category.name}')
                    elif standalone_to_merge:
                        # Use standalone, will be moved to become child
                        existing_child = standalone_to_merge
                    # If only existing_child found, use it (already in place)
                
                # If not found yet, try normal search
                if not existing_child:
                    existing_child = self.find_existing_category(
                        child_name,
                        Category.CategoryType.EXPENSE,
                        parent=parent_category,
                        name_mappings=name_mappings
                    )
                    
                    # Also try to find by name only (might be under different parent)
                    if not existing_child:
                        # For non-move candidates, only search if there's exactly one match
                        count = Category.objects.filter(name__iexact=child_name, type=Category.CategoryType.EXPENSE).count()
                        if count == 1:
                            try:
                                existing_child = Category.objects.get(name__iexact=child_name, type=Category.CategoryType.EXPENSE)
                                # Don't use parent categories (parent=None) as children unless explicitly moved
                                if existing_child.parent is None:
                                    existing_child = None
                                elif existing_child.parent == parent_category:
                                    pass  # Use it, already in correct place
                                else:
                                    existing_child = None  # Don't use it, might be wrong category
                            except Category.DoesNotExist:
                                existing_child = None
                        # If count > 1, don't search by name only (too ambiguous)
                
                if existing_child:
                    # Update existing category
                    child_category = existing_child
                    old_parent = child_category.parent
                    old_name = child_category.name
                    updated = False
                    moved = False
                    renamed = False
                    
                    # Check if category needs to be renamed
                    # If the found category's name is different from target, and it maps to target, rename it
                    if child_category.name != child_name:
                        # Check if old name maps to new name
                        if name_mappings.get(child_category.name) == child_name:
                            # Category was found via mapping, needs to be renamed
                            child_category.name = child_name
                            updated = True
                            renamed = True
                    
                    if update_colors and child_category.color != child_color:
                        child_category.color = child_color
                        updated = True
                    
                    # Only move if explicitly should_move_here (category_moves) or if update_parents and parent doesn't match
                    # But don't move if it's already in the right place
                    if should_move_here:
                        # Explicit move requested (standalone -> child)
                        if old_parent != parent_category:
                            child_category.parent = parent_category
                            updated = True
                            moved = True
                            # If this category has children, they will automatically move with it
                            # (because parent FK cascades)
                    elif update_parents and old_parent != parent_category:
                        # Only move if parent doesn't match AND update_parents is enabled
                        # But check if this category name matches exactly (avoid wrong moves)
                        if child_category.name == child_name or child_category.name.lower() == child_name.lower():
                            child_category.parent = parent_category
                            updated = True
                            moved = True
                    
                    new_description = child_data.get('description', f'Subcategory of {parent_category.name}')
                    if child_category.description != new_description:
                        child_category.description = new_description
                        updated = True
                    
                    if updated:
                        child_category.save()
                        updated_count += 1
                        if renamed and moved:
                            old_parent_name = old_parent.name if old_parent else 'None'
                            self.stdout.write(f'  ↻ Renamed & moved child: {old_name} -> {child_category.name} ({old_parent_name} -> {parent_category.name})')
                        elif renamed:
                            self.stdout.write(f'  ↻ Renamed child: {old_name} -> {child_category.name}')
                        elif moved:
                            old_parent_name = old_parent.name if old_parent else 'None'
                            self.stdout.write(f'  ↻ Moved child: {child_category.name} ({old_parent_name} -> {parent_category.name})')
                        else:
                            self.stdout.write(f'  ↻ Updated child: {child_category.name}')
                    else:
                        self.stdout.write(f'  ✓ Found existing child: {child_category.name}')
                else:
                    # Create new child category
                    child_category = Category.objects.create(
                        name=child_name,
                        type=Category.CategoryType.EXPENSE,
                        parent=parent_category,
                        color=child_color,
                        description=child_data.get('description', f'Subcategory of {parent_category.name}')
                    )
                    created_count += 1
                    self.stdout.write(f'  ✓ Created child: {child_category.name}')

                # Process grandchildren with gradient colors
                grandchildren_items = list(child_data.get('children', {}).items())
                total_grandchildren = len(grandchildren_items)
                
                for grandchild_index, (grandchild_name, grandchild_data) in enumerate(grandchildren_items):
                    # Generate gradient color for grandchildren based on their parent (child) color
                    # Use the child's current color as base (might have been updated)
                    # child_category is always defined at this point (either found or created)
                    grandchild_base_color = child_category.color
                    
                    # Generate gradient color for grandchildren
                    grandchild_color = get_color_for_child_index(grandchild_base_color, grandchild_index, total_grandchildren)
                    # Additional lightening for grandchild level (make them lighter than children)
                    grandchild_color = lighten_color(grandchild_color, factor=0.08)
                    
                    # Try to find existing grandchild category
                    existing_grandchild = self.find_existing_category(
                        grandchild_name,
                        Category.CategoryType.EXPENSE,
                        parent=child_category,
                        name_mappings=name_mappings
                    )
                    
                    # Also try to find by name only (might be under different parent)
                    if not existing_grandchild:
                        try:
                            existing_grandchild = Category.objects.get(name__iexact=grandchild_name, type=Category.CategoryType.EXPENSE)
                        except (Category.DoesNotExist, Category.MultipleObjectsReturned):
                            existing_grandchild = None
                    
                    if existing_grandchild:
                        # Update existing category
                        grandchild_category = existing_grandchild
                        updated = False
                        
                        if update_colors and grandchild_category.color != grandchild_color:
                            grandchild_category.color = grandchild_color
                            updated = True
                        
                        if update_parents and grandchild_category.parent != child_category:
                            grandchild_category.parent = child_category
                            updated = True
                        
                        new_description = f'Subcategory of {child_category.name}'
                        if grandchild_category.description != new_description:
                            grandchild_category.description = new_description
                            updated = True
                        
                        if updated:
                            grandchild_category.save()
                            updated_count += 1
                            if grandchild_category.parent != child_category:
                                self.stdout.write(f'    ↻ Updated grandchild: {grandchild_category.name} -> {child_category.name}')
                            else:
                                self.stdout.write(f'    ↻ Updated grandchild: {grandchild_category.name}')
                        else:
                            self.stdout.write(f'    ✓ Found existing grandchild: {grandchild_category.name}')
                    else:
                        # Create new grandchild category
                        grandchild_category = Category.objects.create(
                            name=grandchild_name,
                            type=Category.CategoryType.EXPENSE,
                            parent=child_category,
                            color=grandchild_color,
                            description=f'Subcategory of {child_category.name}'
                        )
                        created_count += 1
                        self.stdout.write(f'    ✓ Created grandchild: {grandchild_category.name}')

        # Process income categories
        self.stdout.write(self.style.SUCCESS('\n=== Processing Income Categories ===\n'))
        for parent_name, parent_data in income_categories.items():
            # Try to find existing parent category
            existing_parent = self.find_existing_category(
                parent_name,
                Category.CategoryType.INCOME,
                parent=None,
                name_mappings=name_mappings
            )
            
            if existing_parent:
                # Update existing category
                parent_category = existing_parent
                updated = False
                renamed = False
                old_name = parent_category.name
                
                # Check if category needs to be renamed
                # If the found category's name is different from target, and it maps to target, rename it
                if parent_category.name != parent_name:
                    # Check if old name maps to new name
                    if name_mappings.get(parent_category.name) == parent_name:
                        # Category was found via mapping, needs to be renamed
                        parent_category.name = parent_name
                        updated = True
                        renamed = True
                
                if update_colors and parent_category.color != parent_data['color']:
                    parent_category.color = parent_data['color']
                    updated = True
                
                new_description = parent_data.get('description', f'Main category for {parent_name.lower()} income')
                if parent_category.description != new_description:
                    parent_category.description = new_description
                    updated = True
                
                if updated:
                    parent_category.save()
                    updated_count += 1
                    if renamed:
                        self.stdout.write(f'↻ Renamed & updated parent: {old_name} -> {parent_category.name}')
                    else:
                        self.stdout.write(f'↻ Updated parent: {parent_category.name}')
                else:
                    self.stdout.write(f'✓ Found existing parent: {parent_category.name}')
            else:
                # Create new parent category
                parent_category = Category.objects.create(
                    name=parent_name,
                    type=Category.CategoryType.INCOME,
                    parent=None,
                    color=parent_data['color'],
                    description=parent_data.get('description', f'Main category for {parent_name.lower()} income')
                )
                created_count += 1
                self.stdout.write(f'✓ Created parent: {parent_category.name}')

            # Process children with gradient colors
            children_items = list(parent_data.get('children', {}).items())
            total_children = len(children_items)
            
            for child_index, (child_name, child_data) in enumerate(children_items):
                # Generate gradient color: darker for first child, lighter for last child
                child_color = get_color_for_child_index(parent_data['color'], child_index, total_children)
                
                # Try to find existing child category
                existing_child = self.find_existing_category(
                    child_name,
                    Category.CategoryType.INCOME,
                    parent=parent_category,
                    name_mappings=name_mappings
                )
                
                # Also try to find by name only (might be under different parent)
                if not existing_child:
                    try:
                        existing_child = Category.objects.get(name__iexact=child_name, type=Category.CategoryType.INCOME)
                    except (Category.DoesNotExist, Category.MultipleObjectsReturned):
                        existing_child = None
                
                if existing_child:
                    # Update existing category
                    child_category = existing_child
                    updated = False
                    
                    if update_colors and child_category.color != child_color:
                        child_category.color = child_color
                        updated = True
                    
                    if update_parents and child_category.parent != parent_category:
                        child_category.parent = parent_category
                        updated = True
                    
                    new_description = child_data.get('description', f'Subcategory of {parent_category.name}')
                    if child_category.description != new_description:
                        child_category.description = new_description
                        updated = True
                    
                    if updated:
                        child_category.save()
                        updated_count += 1
                        if child_category.parent != parent_category:
                            self.stdout.write(f'  ↻ Updated child: {child_category.name} -> {parent_category.name}')
                        else:
                            self.stdout.write(f'  ↻ Updated child: {child_category.name}')
                    else:
                        self.stdout.write(f'  ✓ Found existing child: {child_category.name}')
                else:
                    # Create new child category
                    child_category = Category.objects.create(
                        name=child_name,
                        type=Category.CategoryType.INCOME,
                        parent=parent_category,
                        color=child_color,
                        description=child_data.get('description', f'Subcategory of {parent_category.name}')
                    )
                    created_count += 1
                    self.stdout.write(f'  ✓ Created child: {child_category.name}')

        # Summary
        self.stdout.write(self.style.SUCCESS(
            f'\n=== Summary ===\n'
            f'Created: {created_count} categories\n'
            f'Updated: {updated_count} categories\n'
            f'Total processed: {created_count + updated_count} categories'
        ))


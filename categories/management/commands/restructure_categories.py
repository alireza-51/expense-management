from django.core.management.base import BaseCommand
from categories.models import Category
from categories.color_utils import calculate_child_color


class Command(BaseCommand):
    help = '''Restructure categories to match new tree structure while preserving existing data.
    
    This command will:
    - Find and update existing matching categories (by name or mapping)
    - Create new categories that don't exist
    - Preserve all existing categories and their data
    - Update colors, parent relationships, and descriptions for matching categories
    
    Usage:
    - python manage.py restructure_categories  # Updates matching categories, creates missing ones
    - python manage.py restructure_categories --colors-only  # Only update colors, don't change other data
    - python manage.py restructure_categories --no-update-colors  # Don't update colors
    - python manage.py restructure_categories --no-update-parents  # Don't update parent relationships
    '''

    def add_arguments(self, parser):
        parser.add_argument(
            '--colors-only',
            action='store_true',
            help='ONLY update colors. Do not change names, descriptions, parent relationships, or create new categories.',
        )
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
    
    def recalculate_sibling_colors(self, parent_category, category_type, update_colors=True):
        """
        Recalculate colors for all children of a parent based on their actual IDs.
        
        This ensures colors are calculated correctly based on sibling ID order,
        which is required for the deterministic color algorithm.
        """
        if not update_colors:
            return
        
        # Get all siblings sorted by ID
        siblings = Category.objects.filter(
            parent=parent_category,
            type=category_type
        ).order_by('id')
        
        if not siblings.exists():
            return
        
        parent_color = parent_category.color
        sibling_ids = list(siblings.values_list('id', flat=True))
        
        # Update colors for all siblings
        updated_any = False
        for sibling in siblings:
            new_color = calculate_child_color(
                parent_color=parent_color,
                sibling_id=sibling.pk,
                sibling_ids=sibling_ids
            )
            if sibling.color != new_color:
                Category.objects.filter(pk=sibling.pk).update(color=new_color)
                updated_any = True
        
        return updated_any

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
        except Category.MultipleObjectsReturned:
            # If multiple found, return the first one
            if parent:
                return Category.objects.filter(name=name, type=category_type, parent=parent).first()
            else:
                return Category.objects.filter(name=name, type=category_type, parent__isnull=True).first()
        
        # Try case-insensitive match
        try:
            if parent:
                return Category.objects.get(name__iexact=name, type=category_type, parent=parent)
            else:
                return Category.objects.get(name__iexact=name, type=category_type, parent__isnull=True)
        except Category.DoesNotExist:
            pass
        except Category.MultipleObjectsReturned:
            # If multiple found, return the first one
            if parent:
                return Category.objects.filter(name__iexact=name, type=category_type, parent=parent).first()
            else:
                return Category.objects.filter(name__iexact=name, type=category_type, parent__isnull=True).first()
        
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
            except Category.MultipleObjectsReturned:
                # If multiple found, return the first one
                if parent:
                    return Category.objects.filter(name=mapped_name, type=category_type, parent=parent).first()
                else:
                    return Category.objects.filter(name=mapped_name, type=category_type, parent__isnull=True).first()
        
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
            except Category.MultipleObjectsReturned:
                # If multiple found, return the first one
                if parent:
                    return Category.objects.filter(name__iexact=old_name, type=category_type, parent=parent).first()
                else:
                    return Category.objects.filter(name__iexact=old_name, type=category_type, parent__isnull=True).first()
        
        return None

    def handle(self, *args, **options):
        colors_only = options.get('colors_only', False)
        update_colors = not options.get('no_update_colors', False)  # Default to True
        update_parents = not options.get('no_update_parents', False)  # Default to True
        
        # If colors_only is set, only update colors
        if colors_only:
            update_colors = True
            update_parents = False
            self.stdout.write(self.style.WARNING(
                '\n⚠ COLORS-ONLY MODE: Only updating colors. No other data will be modified.\n'
            ))

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
        merged_count = 0

        # Check if any categories exist in the database
        total_existing = Category.objects.count()
        if total_existing == 0:
            self.stdout.write(self.style.WARNING(
                '\n⚠ WARNING: No categories found in database. All categories will be created new.\n'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'\n✓ Found {total_existing} existing categories in database\n'
            ))

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
                
                # Skip renaming and description updates in colors-only mode
                if not colors_only:
                    # Check if category needs to be renamed
                    # If the found category's name is different from target, and it maps to target, rename it
                    if parent_category.name != parent_name:
                        # Check if old name maps to new name
                        if name_mappings.get(parent_category.name) == parent_name:
                            # Category was found via mapping, needs to be renamed
                            parent_category.name = parent_name
                            updated = True
                            renamed = True
                    
                    new_description = parent_data.get('description', f'Main category for {parent_name.lower()} expenses')
                    if parent_category.description != new_description:
                        parent_category.description = new_description
                        updated = True
                
                if update_colors and parent_category.color != parent_data['color']:
                    parent_category.color = parent_data['color']
                    updated = True
                
                if updated:
                    parent_category.save()
                    updated_count += 1
                    if renamed:
                        self.stdout.write(f'↻ Renamed & updated parent: {old_name} -> {parent_category.name}')
                    elif update_colors and parent_category.color == parent_data['color']:
                        self.stdout.write(f'↻ Updated color for parent: {parent_category.name}')
                    else:
                        self.stdout.write(f'↻ Updated parent: {parent_category.name}')
                else:
                    self.stdout.write(f'✓ Found existing parent: {parent_category.name}')
            else:
                # Create new parent category (skip in colors-only mode)
                if colors_only:
                    self.stdout.write(f'⊘ Skipped creating parent (colors-only mode): {parent_name}')
                    # Skip processing children if parent doesn't exist in colors-only mode
                    continue
                
                parent_category = Category.objects.create(
                    name=parent_name,
                    type=Category.CategoryType.EXPENSE,
                    parent=None,
                    color=parent_data['color'],
                    description=parent_data.get('description', f'Main category for {parent_name.lower()} expenses')
                )
                created_count += 1
                self.stdout.write(f'✓ Created parent: {parent_category.name}')

            # Process children - colors will be recalculated after all are created/updated
            children_items = list(parent_data.get('children', {}).items())
            
            for child_name, child_data in children_items:
                # Temporary color - will be recalculated based on actual sibling IDs
                child_color = parent_data['color']  # Will be recalculated
                
                # Check if this category should be moved to this parent
                should_move_here = category_moves.get(child_name) == parent_name
                
                # FIRST: Check if there's already a child with this name under this parent
                existing_child = Category.objects.filter(
                    name__iexact=child_name,
                    type=Category.CategoryType.EXPENSE,
                    parent_id=parent_category.id
                ).first()
                
                # ALWAYS check for standalone category (not just when should_move_here)
                # This helps catch cases where standalone should be used
                standalone_category = Category.objects.filter(
                    name__iexact=child_name,
                    type=Category.CategoryType.EXPENSE,
                    parent__isnull=True
                ).first()
                
                # Handle standalone category merging/moving
                if standalone_category:
                    if existing_child and existing_child.id != standalone_category.id:
                        # We have both an existing child and a standalone - merge standalone into child
                        from expenses.models import Expense, Income
                        standalone_id = standalone_category.id
                        # Merge all expenses and income from standalone to existing child
                        Expense.objects.filter(category=standalone_category).update(category=existing_child)
                        Income.objects.filter(category=standalone_category).update(category=existing_child)
                        # Move children of standalone to existing child
                        Category.objects.filter(parent=standalone_category).update(parent=existing_child)
                        # Delete standalone
                        standalone_category.delete()
                        merged_count += 1
                        self.stdout.write(f'  ↻ Merged standalone "{child_name}" (id: {standalone_id}) into existing child (id: {existing_child.id}) under {parent_category.name}')
                    elif not existing_child and should_move_here:
                        # We have standalone but no existing child, and this is a move operation
                        # Use standalone as the child - it will be moved to the correct parent below
                        existing_child = standalone_category
                
                # If still not found, try normal search with mappings
                if not existing_child:
                    existing_child = self.find_existing_category(
                        child_name,
                        Category.CategoryType.EXPENSE,
                        parent=parent_category,
                        name_mappings=name_mappings
                    )
                    
                    # Also try to find by name only (might be under different parent)
                    if not existing_child:
                        # Search for any category with this name (but be careful)
                        candidates = Category.objects.filter(
                            name__iexact=child_name,
                            type=Category.CategoryType.EXPENSE
                        )
                        count = candidates.count()
                        
                        if count == 1:
                            # Only one match, safe to use
                            existing_child = candidates.first()
                            # Don't use if it's a parent category (unless explicitly moving)
                            if existing_child.parent is None and not should_move_here:
                                existing_child = None
                        elif count > 1:
                            # Multiple matches - prefer one that's already under this parent (by ID)
                            existing_child = candidates.filter(parent_id=parent_category.id).first()
                            if not existing_child and should_move_here:
                                # Prefer standalone if should_move_here is True
                                existing_child = candidates.filter(parent__isnull=True).first()
                            if not existing_child:
                                # For non-move cases, prefer one under a parent with the same name
                                # This helps find "Groceries" that might be under "Food & Dining" already
                                existing_child = candidates.filter(
                                    parent__name__iexact=parent_name,
                                    parent__type=Category.CategoryType.EXPENSE
                                ).first()
                            if not existing_child:
                                # Use any that's not already under this parent
                                existing_child = candidates.exclude(parent_id=parent_category.id).first()
                
                if existing_child:
                    # Update existing category
                    child_category = existing_child
                    old_parent = child_category.parent
                    old_name = child_category.name
                    updated = False
                    moved = False
                    renamed = False
                    
                    # Skip renaming, moving, and description updates in colors-only mode
                    if not colors_only:
                        # Check if category needs to be renamed
                        # If the found category's name is different from target, and it maps to target, rename it
                        if child_category.name != child_name:
                            # Check if old name maps to new name
                            if name_mappings.get(child_category.name) == child_name:
                                # Category was found via mapping, needs to be renamed
                                child_category.name = child_name
                                updated = True
                                renamed = True
                        
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
                    
                    # Color will be recalculated after all siblings are processed
                    # Don't update color here - it will be done in batch
                    
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
                    # Create new child category (skip in colors-only mode)
                    if colors_only:
                        self.stdout.write(f'  ⊘ Skipped creating child (colors-only mode): {child_name}')
                        continue
                    
                    # Use parent color temporarily - will be recalculated
                    child_category = Category.objects.create(
                        name=child_name,
                        type=Category.CategoryType.EXPENSE,
                        parent=parent_category,
                        color=parent_data['color'],  # Temporary - will be recalculated
                        description=child_data.get('description', f'Subcategory of {parent_category.name}')
                    )
                    created_count += 1
                    self.stdout.write(f'  ✓ Created child: {child_category.name}')

                # Process grandchildren with gradient colors
                grandchildren_items = list(child_data.get('children', {}).items())
                total_grandchildren = len(grandchildren_items)
                
                for grandchild_name, grandchild_data in grandchildren_items:
                    # Color will be recalculated after all grandchildren are processed
                    # Use child color temporarily
                    grandchild_base_color = child_category.color
                    grandchild_color = grandchild_base_color  # Temporary - will be recalculated
                    
                    # Try to find existing grandchild category - first check under the child_category
                    existing_grandchild = Category.objects.filter(
                        name__iexact=grandchild_name,
                        type=Category.CategoryType.EXPENSE,
                        parent_id=child_category.id
                    ).first()
                    
                    # If not found, try using find_existing_category method
                    if not existing_grandchild:
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
                        
                        # Color will be recalculated after all siblings are processed
                        # Don't update color here
                        
                        # Skip moving and description updates in colors-only mode
                        if not colors_only:
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
                        # Create new grandchild category (skip in colors-only mode)
                        if colors_only:
                            self.stdout.write(f'    ⊘ Skipped creating grandchild (colors-only mode): {grandchild_name}')
                            # Continue to next grandchild
                            continue
                        
                        # Use child color temporarily - will be recalculated
                        grandchild_category = Category.objects.create(
                            name=grandchild_name,
                            type=Category.CategoryType.EXPENSE,
                            parent=child_category,
                            color=child_category.color,  # Temporary - will be recalculated
                            description=f'Subcategory of {child_category.name}'
                        )
                        created_count += 1
                        self.stdout.write(f'    ✓ Created grandchild: {grandchild_category.name}')
                
                # Recalculate colors for all grandchildren of this child
                if update_colors:
                    self.recalculate_sibling_colors(child_category, Category.CategoryType.EXPENSE, update_colors)
            
            # Recalculate colors for all children of this parent
            # This ensures colors are based on actual sibling IDs
            if update_colors:
                self.recalculate_sibling_colors(parent_category, Category.CategoryType.EXPENSE, update_colors)

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
                
                # Skip renaming and description updates in colors-only mode
                if not colors_only:
                    # Check if category needs to be renamed
                    # If the found category's name is different from target, and it maps to target, rename it
                    if parent_category.name != parent_name:
                        # Check if old name maps to new name
                        if name_mappings.get(parent_category.name) == parent_name:
                            # Category was found via mapping, needs to be renamed
                            parent_category.name = parent_name
                            updated = True
                            renamed = True
                    
                    new_description = parent_data.get('description', f'Main category for {parent_name.lower()} income')
                    if parent_category.description != new_description:
                        parent_category.description = new_description
                        updated = True
                
                if update_colors and parent_category.color != parent_data['color']:
                    parent_category.color = parent_data['color']
                    updated = True
                
                if updated:
                    parent_category.save()
                    updated_count += 1
                    if renamed:
                        self.stdout.write(f'↻ Renamed & updated parent: {old_name} -> {parent_category.name}')
                    elif update_colors and parent_category.color == parent_data['color']:
                        self.stdout.write(f'↻ Updated color for parent: {parent_category.name}')
                    else:
                        self.stdout.write(f'↻ Updated parent: {parent_category.name}')
                else:
                    self.stdout.write(f'✓ Found existing parent: {parent_category.name}')
            else:
                # Create new parent category (skip in colors-only mode)
                if colors_only:
                    self.stdout.write(f'⊘ Skipped creating parent (colors-only mode): {parent_name}')
                    # Skip processing children if parent doesn't exist in colors-only mode
                    continue
                
                parent_category = Category.objects.create(
                    name=parent_name,
                    type=Category.CategoryType.INCOME,
                    parent=None,
                    color=parent_data['color'],
                    description=parent_data.get('description', f'Main category for {parent_name.lower()} income')
                )
                created_count += 1
                self.stdout.write(f'✓ Created parent: {parent_category.name}')

            # Process children - colors will be recalculated after all are created/updated
            children_items = list(parent_data.get('children', {}).items())
            
            for child_name, child_data in children_items:
                # Temporary color - will be recalculated based on actual sibling IDs
                child_color = parent_data['color']  # Will be recalculated
                
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
                    
                    # Skip moving and description updates in colors-only mode
                    if not colors_only:
                        if update_parents and child_category.parent != parent_category:
                            child_category.parent = parent_category
                            updated = True
                        
                        new_description = child_data.get('description', f'Subcategory of {parent_category.name}')
                        if child_category.description != new_description:
                            child_category.description = new_description
                            updated = True
                    
                    # Color will be recalculated after all siblings are processed
                    # Don't update color here
                    
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
                    # Create new child category (skip in colors-only mode)
                    if colors_only:
                        self.stdout.write(f'  ⊘ Skipped creating child (colors-only mode): {child_name}')
                        continue
                    
                    # Use parent color temporarily - will be recalculated
                    child_category = Category.objects.create(
                        name=child_name,
                        type=Category.CategoryType.INCOME,
                        parent=parent_category,
                        color=parent_data['color'],  # Temporary - will be recalculated
                        description=child_data.get('description', f'Subcategory of {parent_category.name}')
                    )
                    created_count += 1
                    self.stdout.write(f'  ✓ Created child: {child_category.name}')
            
            # Recalculate colors for all children of this parent
            # This ensures colors are based on actual sibling IDs
            if update_colors:
                self.recalculate_sibling_colors(parent_category, Category.CategoryType.INCOME, update_colors)

        # Summary
        self.stdout.write(self.style.SUCCESS(
            f'\n=== Summary ===\n'
            f'Created: {created_count} categories\n'
            f'Updated: {updated_count} categories\n'
            f'Merged: {merged_count} categories\n'
            f'Total processed: {created_count + updated_count} categories'
        ))


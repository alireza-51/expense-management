from django import forms
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import Category


class HierarchicalCategoryWidget(forms.Select):
    """Custom widget for hierarchical category selection with hover effects"""
    
    def __init__(self, category_type=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.category_type = category_type
    
    def render(self, name, value, attrs=None, renderer=None):
        try:
            # Get all categories of the specified type
            if self.category_type is None:
                categories = Category.objects.all().order_by('parent__name', 'name')
            else:
                categories = Category.objects.filter(type=self.category_type).order_by('parent__name', 'name')
            
            # Build hierarchical structure
            main_categories = categories.filter(parent__isnull=True)
            
            # Build the hierarchical display
            output = []
            output.append(f'<div class="hierarchical-category-container" data-field-name="{name}">')
            output.append('<div class="category-list">')
            
            if main_categories.exists():
                for main_cat in main_categories:
                    # Get children for this main category
                    children = categories.filter(parent=main_cat)
                    
                    # Main category item
                    selected = 'selected' if str(main_cat.id) == str(value) else ''
                    has_children = 'has-children' if children.exists() else ''
                    
                    output.append(f'''
                        <div class="category-item main-category {has_children} {selected}" 
                             data-category-id="{main_cat.id}" 
                             data-category-name="{main_cat.name}"
                             style="border-left-color: {main_cat.color};">
                            <div class="category-content">
                                <div class="color-square" style="background-color: {main_cat.color};"></div>
                                <span class="category-name" style="font-weight: bold;">
                                    {main_cat.name}
                                </span>
                                {f'<span class="child-count">({children.count()})</span>' if children.exists() else ''}
                            </div>
                            <input type="radio" name="{name}" value="{main_cat.id}" {selected} class="category-radio">
                    ''')
                    
                    # Fly-out menu for children
                    if children.exists():
                        output.append(f'''
                            <div class="flyout-menu">
                                <div class="flyout-header">All {main_cat.name} Categories</div>
                                <div class="flyout-grid">
                        ''')
                        
                        # Single section with all children
                        output.append('<div class="flyout-section">')
                        for child in children:
                            selected = 'selected' if str(child.id) == str(value) else ''
                            output.append(f'''
                                <div class="flyout-child-item" 
                                     data-category-id="{child.id}" 
                                     data-category-name="{child.name}"
                                     data-parent-id="{main_cat.id}">
                                    <input type="radio" name="{name}" value="{child.id}" {selected} class="category-radio">
                                    <div class="color-square" style="background-color: {child.color};"></div>
                                    {child.name}
                                </div>
                            ''')
                        output.append('</div>')
                        
                        output.append('</div></div>')
                    
                    output.append('</div>')
            else:
                # No categories found - show a message
                output.append('<div class="category-item">')
                output.append('<div class="category-content">')
                output.append('<span class="category-name" style="color: #666; font-style: italic;">No categories found</span>')
                output.append('</div>')
                output.append('</div>')
            
            output.append('</div>')
            output.append('</div>')
            
            # Add CSS and JavaScript for the fly-out hierarchical display
            css_js = """
            <style>
                    .hierarchical-category-container {
            position: relative;
            border: 2px solid #999;
            border-radius: 8px;
            background: #fff;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            min-height: 200px;
            width: 250px;
        }
            
            .category-list {
                padding: 0;
                margin: 0;
            }
            
            .category-item {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 12px 16px;
                margin: 0;
                border-bottom: 2px solid #e0e0e0;
                cursor: pointer;
                transition: all 0.2s ease;
                position: relative;
                color: #000;
            }
            
            .category-item:last-child {
                border-bottom: none;
            }
            
            .category-item:hover {
                background-color: #f8f9fa;
            }
            
            .category-item.selected {
                background-color: #e3f2fd;
                border-left: 4px solid #2196f3;
            }
            
            .main-category {
                font-weight: 500;
                position: relative;
            }
            
            .main-category.has-children::after {
                content: '▶';
                position: absolute;
                right: 16px;
                color: #666;
                transition: transform 0.2s ease;
            }
            
            .main-category.has-children:hover::after {
                transform: rotate(90deg);
            }
            
            /* Fly-out menu styling */
            .flyout-menu {
                position: absolute;
                left: 100%;
                top: 0;
                background: white;
                border: 2px solid #999;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                min-width: 400px;
                max-width: 600px;
                z-index: 1000;
                display: none;
                padding: 16px;
            }
            
            .main-category:hover .flyout-menu {
                display: block;
                animation: flyoutSlide 0.3s ease;
            }
            
            .flyout-menu:hover {
                display: block;
            }
            
            .flyout-header {
                font-size: 16px;
                font-weight: bold;
                color: #333;
                margin-bottom: 16px;
                padding-bottom: 8px;
                border-bottom: 2px solid #ccc;
            }
            
            .flyout-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                gap: 16px;
            }
            
            .flyout-section {
                display: flex;
                flex-direction: column;
            }
            
            .flyout-child-item {
                padding: 8px 12px;
                cursor: pointer;
                transition: all 0.2s ease;
                font-size: 14px;
                border-radius: 4px;
                margin: 2px 0;
                background-color: #f8f9fa;
                border: 2px solid #ccc;
                color: #000;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .flyout-child-item:hover {
                background-color: #e3f2fd;
                border-color: #2196f3;
            }
            
            .flyout-child-item.selected {
                background-color: #e3f2fd;
                border-color: #2196f3;
            }
            
            .category-content {
                display: flex;
                align-items: center;
                gap: 8px;
                flex: 1;
            }
            
            .category-name {
                flex: 1;
            }
            
            .child-count {
                background-color: #e0e0e0;
                color: #666;
                padding: 2px 6px;
                border-radius: 10px;
                font-size: 0.8em;
                font-weight: normal;
            }
            
            .category-radio {
                opacity: 0;
                position: absolute;
            }
            
            .category-item.selected .category-radio {
                opacity: 1;
            }
            
            .color-square {
                width: 12px;
                height: 12px;
                border-radius: 2px;
                flex-shrink: 0;
            }
            
            @keyframes flyoutSlide {
                from {
                    opacity: 0;
                    transform: translateX(-10px);
                }
                to {
                    opacity: 1;
                    transform: translateX(0);
                }
            }
            
            /* Responsive design */
            @media (max-width: 768px) {
                .flyout-menu {
                    position: fixed;
                    left: 50%;
                    top: 50%;
                    transform: translate(-50%, -50%);
                    max-width: 90vw;
                    max-height: 80vh;
                    overflow-y: auto;
                }
            }
            
            /* Enhanced input borders for better visibility */
            input[type="text"], input[type="email"], input[type="password"], 
            input[type="number"], input[type="url"], input[type="tel"], 
            input[type="search"], input[type="date"], input[type="datetime-local"],
            textarea, select {
                border: 2px solid #666 !important;
                border-radius: 6px !important;
                padding: 8px 12px !important;
                font-size: 14px !important;
                transition: border-color 0.2s ease !important;
            }
            
            input[type="text"]:focus, input[type="email"]:focus, input[type="password"]:focus,
            input[type="number"]:focus, input[type="url"]:focus, input[type="tel"]:focus,
            input[type="search"]:focus, input[type="date"]:focus, input[type="datetime-local"]:focus,
            textarea:focus, select:focus {
                border-color: #3b82f6 !important;
                outline: none !important;
                box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
            }
            
            /* Color picker input enhancement */
            .color-picker-input {
                border: 2px solid #666 !important;
                border-radius: 6px !important;
                padding: 8px 12px !important;
                font-size: 14px !important;
                background-color: #fff !important;
            }
            
            .color-picker-input:focus {
                border-color: #3b82f6 !important;
                outline: none !important;
                box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
            }
            
            /* Custom color input enhancement */
            .custom-color-input {
                border: 2px solid #666 !important;
                border-radius: 6px !important;
                padding: 4px !important;
                cursor: pointer !important;
            }
            
            .custom-color-input:focus {
                border-color: #3b82f6 !important;
                outline: none !important;
                box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
            }
            </style>
            
            <script>
            document.addEventListener('DOMContentLoaded', function() {
                const containers = document.querySelectorAll('.hierarchical-category-container');
                
                containers.forEach(function(container) {
                    const categoryItems = container.querySelectorAll('.category-item');
                    const radios = container.querySelectorAll('.category-radio');
                    const flyoutItems = container.querySelectorAll('.flyout-child-item');
                    
                    // Handle main category item clicks
                    categoryItems.forEach(function(item) {
                        item.addEventListener('click', function(e) {
                            if (e.target.type === 'radio') return;
                            
                            // Remove selected class from all items
                            categoryItems.forEach(i => i.classList.remove('selected'));
                            flyoutItems.forEach(i => i.classList.remove('selected'));
                            
                            // Add selected class to clicked item
                            this.classList.add('selected');
                            
                            // Check the radio button
                            const radio = this.querySelector('.category-radio');
                            if (radio) {
                                radio.checked = true;
                                radio.click(); // Trigger change event
                            }
                        });
                    });
                    
                    // Handle flyout child item clicks
                    flyoutItems.forEach(function(item) {
                        item.addEventListener('click', function(e) {
                            if (e.target.type === 'radio') return;
                            
                            // Remove selected class from all items
                            categoryItems.forEach(i => i.classList.remove('selected'));
                            flyoutItems.forEach(i => i.classList.remove('selected'));
                            
                            // Add selected class to clicked item
                            this.classList.add('selected');
                            
                            // Check the radio button
                            const radio = this.querySelector('.category-radio');
                            if (radio) {
                                radio.checked = true;
                                radio.click(); // Trigger change event
                            }
                        });
                    });
                    
                    // Handle radio button changes
                    radios.forEach(function(radio) {
                        radio.addEventListener('change', function() {
                            // Remove selected class from all items
                            categoryItems.forEach(item => item.classList.remove('selected'));
                            flyoutItems.forEach(item => item.classList.remove('selected'));
                            
                            // Add selected class to parent item
                            const parentItem = this.closest('.category-item, .flyout-child-item');
                            if (parentItem) {
                                parentItem.classList.add('selected');
                            }
                        });
                    });
                    
                    // Initialize selected state
                    const checkedRadio = container.querySelector('.category-radio:checked');
                    if (checkedRadio) {
                        const parentItem = checkedRadio.closest('.category-item, .flyout-child-item');
                        if (parentItem) {
                            parentItem.classList.add('selected');
                        }
                    }
                    
                    // Handle flyout menu positioning
                    const flyoutMenus = container.querySelectorAll('.flyout-menu');
                    flyoutMenus.forEach(function(menu) {
                        const parentItem = menu.closest('.category-item');
                        if (parentItem) {
                            // Position the flyout menu at the same height as the parent item
                            menu.style.top = '0px';
                        }
                    });
                });
            });
            </script>
            """
            
            return mark_safe(css_js + ''.join(output))
        except Exception as e:
            # Fallback to simple select if there's an error
            return f'<select name="{name}"><option value="">Error loading categories: {str(e)}</option></select>'


class HierarchicalCategoryField(forms.ModelChoiceField):
    """Custom form field for hierarchical category selection"""
    
    def __init__(self, category_type=None, *args, **kwargs):
        # Filter queryset based on category type
        if category_type:
            queryset = Category.objects.filter(type=category_type).order_by('parent__name', 'name')
        else:
            queryset = Category.objects.all().order_by('parent__name', 'name')
        
        kwargs['queryset'] = queryset
        kwargs['widget'] = HierarchicalCategoryWidget(category_type=category_type)
        super().__init__(*args, **kwargs)
    
    def label_from_instance(self, obj):
        """Custom label formatting for hierarchical display"""
        if obj is None:
            return ""
        if obj.parent:
            return f"{obj.parent.name} → {obj.name}"
        return obj.name 
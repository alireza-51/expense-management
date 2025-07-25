#!/bin/bash

# Expense Management System - Complete Setup Script
# This script sets up the entire project from scratch

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if virtual environment exists
venv_exists() {
    [ -d "venv" ] && [ -f "venv/bin/activate" ]
}

# Function to install system dependencies
install_system_deps() {
    print_status "Installing system dependencies..."
    
    if [ -f "install_system_dependencies.sh" ]; then
        chmod +x install_system_dependencies.sh
        ./install_system_dependencies.sh
    else
        print_error "install_system_dependencies.sh not found!"
        print_status "Please run the system dependencies installation manually."
        return 1
    fi
}

# Function to setup Python virtual environment
setup_python_env() {
    print_status "Setting up Python virtual environment..."
    
    if ! command_exists python3; then
        print_error "Python3 is not installed!"
        return 1
    fi
    
    if venv_exists; then
        print_warning "Virtual environment already exists. Removing old one..."
        rm -rf venv
    fi
    
    python3 -m venv venv
    print_success "Virtual environment created!"
}

# Function to install Python dependencies
install_python_deps() {
    print_status "Installing Python dependencies..."
    
    if ! venv_exists; then
        print_error "Virtual environment not found!"
        return 1
    fi
    
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install requirements
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        print_success "Python dependencies installed!"
    else
        print_error "requirements.txt not found!"
        return 1
    fi
}

# Function to setup database
setup_database() {
    print_status "Setting up database..."
    
    source venv/bin/activate
    
    # Run migrations
    python manage.py migrate
    
    print_success "Database setup completed!"
}

# Function to create superuser
create_superuser() {
    print_status "Creating superuser..."
    
    source venv/bin/activate
    
    # Check if superuser already exists
    if python manage.py shell -c "from django.contrib.auth.models import User; print('Superuser exists:', User.objects.filter(is_superuser=True).exists())" 2>/dev/null | grep -q "True"; then
        print_warning "Superuser already exists. Skipping creation."
        return 0
    fi
    
    # Create superuser with default credentials
    echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'admin123') if not User.objects.filter(username='admin').exists() else None" | python manage.py shell
    
    print_success "Superuser created with username: admin, password: admin123"
    print_warning "Please change the password after first login!"
}

# Function to generate sample data
generate_sample_data() {
    print_status "Generating sample data..."
    
    source venv/bin/activate
    
    # Check if seed_data command exists
    if python manage.py help | grep -q "seed_data"; then
        python manage.py seed_data
        print_success "Sample data generated!"
    else
        print_warning "seed_data command not found. Skipping sample data generation."
    fi
}

# Function to compile translations
compile_translations() {
    print_status "Compiling translations..."
    
    source venv/bin/activate
    
    # Check if locale directory exists
    if [ -d "locale" ]; then
        python manage.py compilemessages
        print_success "Translations compiled!"
    else
        print_warning "No translation files found. Skipping compilation."
    fi
}

# Function to show final instructions
show_final_instructions() {
    echo
    print_success "Expense Management System setup completed!"
    echo
    print_status "Your system is now ready to use!"
    echo
    print_status "To start the development server:"
    echo "1. Activate the virtual environment:"
    echo "   source venv/bin/activate"
    echo
    echo "2. Run the development server:"
    echo "   python manage.py runserver"
    echo
    echo "3. Open your browser and go to:"
    echo "   http://127.0.0.1:8000/admin/"
    echo
    echo "4. Login with:"
    echo "   Username: admin"
    echo "   Password: admin123"
    echo
    print_warning "Remember to change the default password!"
    echo
    print_status "For more information, see the README.md file."
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if running as root
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should not be run as root!"
        print_status "Please run it as a regular user with sudo privileges."
        exit 1
    fi
    
    # Check if we're in the project directory
    if [ ! -f "manage.py" ]; then
        print_error "manage.py not found! Please run this script from the project root directory."
        exit 1
    fi
    
    print_success "Prerequisites check passed!"
}

# Main setup function
main() {
    echo "=========================================="
    echo "Expense Management System - Setup"
    echo "=========================================="
    echo
    
    # Check prerequisites
    check_prerequisites
    
    # Ask user if they want to install system dependencies
    echo "Do you want to install system dependencies (gettext, postgresql, etc.)? [y/N]"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        install_system_deps
    else
        print_status "Skipping system dependencies installation."
    fi
    
    # Setup Python environment
    setup_python_env
    
    # Install Python dependencies
    install_python_deps
    
    # Setup database
    setup_database
    
    # Compile translations
    compile_translations
    
    # Create superuser
    create_superuser
    
    # Generate sample data
    echo "Do you want to generate sample data? [y/N]"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        generate_sample_data
    else
        print_status "Skipping sample data generation."
    fi
    
    # Show final instructions
    show_final_instructions
}

# Run main function
main "$@" 
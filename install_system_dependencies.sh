#!/bin/bash

# Expense Management System - System Dependencies Installer
# This script installs all required system packages for the Django expense management project

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

# Function to detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command_exists apt-get; then
            echo "debian"
        elif command_exists yum; then
            echo "rhel"
        elif command_exists dnf; then
            echo "fedora"
        elif command_exists pacman; then
            echo "arch"
        else
            echo "unknown"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    else
        echo "unknown"
    fi
}

# Function to install packages on Debian/Ubuntu
install_debian() {
    print_status "Installing packages on Debian/Ubuntu system..."
    
    # Update package list
    sudo apt-get update
    
    # Install required packages
    sudo apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        gettext \
        postgresql \
        postgresql-contrib \
        libpq-dev \
        build-essential \
        git \
        curl \
        wget \
        unzip \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        gnupg \
        lsb-release
    
    print_success "Debian/Ubuntu packages installed successfully!"
}

# Function to install packages on RHEL/CentOS
install_rhel() {
    print_status "Installing packages on RHEL/CentOS system..."
    
    # Update package list
    sudo yum update -y
    
    # Install EPEL repository
    sudo yum install -y epel-release
    
    # Install required packages
    sudo yum install -y \
        python3 \
        python3-pip \
        python3-devel \
        gettext \
        postgresql \
        postgresql-server \
        postgresql-devel \
        gcc \
        gcc-c++ \
        make \
        git \
        curl \
        wget \
        unzip \
        openssl-devel \
        libffi-devel
    
    print_success "RHEL/CentOS packages installed successfully!"
}

# Function to install packages on Fedora
install_fedora() {
    print_status "Installing packages on Fedora system..."
    
    # Update package list
    sudo dnf update -y
    
    # Install required packages
    sudo dnf install -y \
        python3 \
        python3-pip \
        python3-devel \
        gettext \
        postgresql \
        postgresql-server \
        postgresql-devel \
        gcc \
        gcc-c++ \
        make \
        git \
        curl \
        wget \
        unzip \
        openssl-devel \
        libffi-devel
    
    print_success "Fedora packages installed successfully!"
}

# Function to install packages on Arch Linux
install_arch() {
    print_status "Installing packages on Arch Linux system..."
    
    # Update package list
    sudo pacman -Syu --noconfirm
    
    # Install required packages
    sudo pacman -S --noconfirm \
        python \
        python-pip \
        gettext \
        postgresql \
        base-devel \
        git \
        curl \
        wget \
        unzip \
        openssl \
        libffi
    
    print_success "Arch Linux packages installed successfully!"
}

# Function to install packages on macOS
install_macos() {
    print_status "Installing packages on macOS system..."
    
    # Check if Homebrew is installed
    if ! command_exists brew; then
        print_status "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    
    # Install required packages
    brew install \
        python3 \
        gettext \
        postgresql \
        git \
        curl \
        wget
    
    print_success "macOS packages installed successfully!"
}

# Function to setup PostgreSQL
setup_postgresql() {
    print_status "Setting up PostgreSQL..."
    
    OS=$(detect_os)
    
    case $OS in
        "debian")
            # Start and enable PostgreSQL service
            sudo systemctl start postgresql
            sudo systemctl enable postgresql
            
            # Create database and user
            sudo -u postgres psql -c "CREATE DATABASE expense;"
            sudo -u postgres psql -c "CREATE USER postgres WITH PASSWORD 'postgres';"
            sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE expense TO postgres;"
            ;;
        "rhel"|"fedora")
            # Initialize and start PostgreSQL
            sudo postgresql-setup initdb
            sudo systemctl start postgresql
            sudo systemctl enable postgresql
            
            # Create database and user
            sudo -u postgres psql -c "CREATE DATABASE expense;"
            sudo -u postgres psql -c "CREATE USER postgres WITH PASSWORD 'postgres';"
            sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE expense TO postgres;"
            ;;
        "arch")
            # Initialize and start PostgreSQL
            sudo -u postgres initdb -D /var/lib/postgres/data
            sudo systemctl start postgresql
            sudo systemctl enable postgresql
            
            # Create database and user
            sudo -u postgres psql -c "CREATE DATABASE expense;"
            sudo -u postgres psql -c "CREATE USER postgres WITH PASSWORD 'postgres';"
            sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE expense TO postgres;"
            ;;
        "macos")
            # Start PostgreSQL service
            brew services start postgresql
            
            # Create database and user
            createdb expense
            createuser -s postgres
            psql -d expense -c "ALTER USER postgres WITH PASSWORD 'postgres';"
            ;;
    esac
    
    print_success "PostgreSQL setup completed!"
}

# Function to verify installations
verify_installations() {
    print_status "Verifying installations..."
    
    # Check Python
    if command_exists python3; then
        print_success "Python3 is installed: $(python3 --version)"
    else
        print_error "Python3 is not installed!"
        return 1
    fi
    
    # Check pip
    if command_exists pip3; then
        print_success "pip3 is installed: $(pip3 --version)"
    else
        print_error "pip3 is not installed!"
        return 1
    fi
    
    # Check gettext
    if command_exists gettext; then
        print_success "gettext is installed: $(gettext --version | head -n1)"
    else
        print_error "gettext is not installed!"
        return 1
    fi
    
    # Check PostgreSQL
    if command_exists psql; then
        print_success "PostgreSQL is installed: $(psql --version)"
    else
        print_error "PostgreSQL is not installed!"
        return 1
    fi
    
    # Check git
    if command_exists git; then
        print_success "Git is installed: $(git --version)"
    else
        print_error "Git is not installed!"
        return 1
    fi
    
    print_success "All verifications passed!"
}

# Function to show next steps
show_next_steps() {
    echo
    print_success "System dependencies installation completed!"
    echo
    print_status "Next steps to complete the setup:"
    echo "1. Create a Python virtual environment:"
    echo "   python3 -m venv venv"
    echo
    echo "2. Activate the virtual environment:"
    echo "   source venv/bin/activate  # On Linux/macOS"
    echo "   venv\\Scripts\\activate     # On Windows"
    echo
    echo "3. Install Python dependencies:"
    echo "   pip install -r requirements.txt"
    echo
    echo "4. Run Django migrations:"
    echo "   python manage.py migrate"
    echo
    echo "5. Create a superuser:"
    echo "   python manage.py createsuperuser"
    echo
    echo "6. Generate sample data (optional):"
    echo "   python manage.py seed_data"
    echo
    echo "7. Run the development server:"
    echo "   python manage.py runserver"
    echo
    print_status "For more information, see the README.md file."
}

# Main installation function
main() {
    echo "=========================================="
    echo "Expense Management System - Dependencies"
    echo "=========================================="
    echo
    
    # Check if running as root
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should not be run as root!"
        print_status "Please run it as a regular user with sudo privileges."
        exit 1
    fi
    
    # Detect OS
    OS=$(detect_os)
    print_status "Detected OS: $OS"
    
    # Install packages based on OS
    case $OS in
        "debian")
            install_debian
            ;;
        "rhel")
            install_rhel
            ;;
        "fedora")
            install_fedora
            ;;
        "arch")
            install_arch
            ;;
        "macos")
            install_macos
            ;;
        "unknown")
            print_error "Unsupported operating system!"
            print_status "Please install the following packages manually:"
            echo "  - python3"
            echo "  - python3-pip"
            echo "  - gettext"
            echo "  - postgresql"
            echo "  - git"
            exit 1
            ;;
    esac
    
    # Setup PostgreSQL
    setup_postgresql
    
    # Verify installations
    verify_installations
    
    # Show next steps
    show_next_steps
}

# Run main function
main "$@" 
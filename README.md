# Expense Management System

A modern, multilingual expense management system built with Django and django-unfold.

## 🌍 Internationalization (i18n)

This project supports multiple languages:

- **English** (en) - Default language
- **Farsi/Persian** (fa) - فارسی

### Language Switching

The admin interface includes a language switcher in the top-right corner that allows users to switch between English and Farsi.

### Adding New Languages

To add support for additional languages:

1. Add the language code to `LANGUAGES` in `config/settings.py`:
   ```python
   LANGUAGES = [
       ('en', 'English'),
       ('fa', 'فارسی'),
       ('es', 'Español'),  # Example: Spanish
   ]
   ```

2. Create translation files:
   ```bash
   python manage.py makemessages -l es
   ```

3. Edit the generated `.po` file in `locale/es/LC_MESSAGES/django.po`

4. Compile the translations:
   ```bash
   python manage.py compilemessages
   ```

## 🚀 Features

- **Modern Admin Interface**: Beautiful admin panel using django-unfold
- **Financial Dashboard**: Interactive charts and statistics
- **Multi-language Support**: English and Farsi with easy language switching
- **DRY Architecture**: Proxy models for Expense and Income
- **Category Management**: Flexible categorization system
- **Data Visualization**: Chart.js integration for financial trends
- **Responsive Design**: Works on desktop and mobile devices

## 🛠️ Installation

### Quick Setup (Recommended)

For a complete automated setup, use the provided installation script:

```bash
# Make the setup script executable
chmod +x setup.sh

# Run the complete setup
./setup.sh
```

This script will:
- Install all system dependencies (gettext, postgresql, etc.)
- Create a Python virtual environment
- Install Python dependencies
- Set up the database
- Compile translations
- Create a superuser
- Generate sample data (optional)

### Manual Installation

If you prefer to install manually or the automated script doesn't work for your system:

#### 1. System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv python3-dev gettext postgresql postgresql-contrib libpq-dev build-essential git curl wget
```

**CentOS/RHEL/Fedora:**
```bash
sudo yum update -y
sudo yum install -y python3 python3-pip python3-devel gettext postgresql postgresql-server postgresql-devel gcc gcc-c++ make git curl wget
```

**macOS:**
```bash
brew install python3 gettext postgresql git curl wget
```

**Arch Linux:**
```bash
sudo pacman -S python python-pip gettext postgresql base-devel git curl wget
```

#### 2. Database Setup

```bash
# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql -c "CREATE DATABASE expense;"
sudo -u postgres psql -c "CREATE USER postgres WITH PASSWORD 'postgres';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE expense TO postgres;"
```

#### 3. Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Linux/macOS
# venv\Scripts\activate   # On Windows

# Install Python dependencies
pip install -r requirements.txt
```

#### 4. Django Setup

```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Generate sample data (optional)
python manage.py seed_data

# Compile translations
python manage.py compilemessages
```

#### 5. Run the Server

```bash
python manage.py runserver
```

Access the admin interface at: http://127.0.0.1:8000/admin/

## 📊 Admin Features

### Financial Dashboard
- **Statistics Cards**: Total expenses, income, and net amount
- **Interactive Charts**: Line charts showing expense vs income trends
- **Category Breakdown**: Top expense and income categories
- **Real-time Data**: Live updates from your database

### Language Support
- **Language Switcher**: Easy switching between English and Farsi
- **Translated Interface**: All text elements are translatable
- **RTL Support**: Proper support for right-to-left languages like Farsi

## 🏗️ Architecture

### Models
- **BaseModel**: Abstract base model with common fields
- **Category**: Categorization system with expense/income types
- **Transaction**: Base model for all financial transactions
- **Expense**: Proxy model for expense transactions
- **Income**: Proxy model for income transactions

### Admin Customization
- **Custom Admin Site**: Enhanced admin interface with dashboard
- **Model Admins**: Optimized admin views for each model
- **Template Overrides**: Custom admin templates with modern styling

## 🌐 Internationalization Details

### Translation Files
- **English**: `locale/en/LC_MESSAGES/django.po`
- **Farsi**: `locale/fa/LC_MESSAGES/django.po`

### Translation Workflow
1. **Extract**: `python manage.py makemessages -l <language_code>`
2. **Translate**: Edit the `.po` files
3. **Compile**: `python manage.py compilemessages`

### Adding New Translatable Strings
1. Wrap strings with `_()` function:
   ```python
   from django.utils.translation import gettext_lazy as _
   name = models.CharField(_('Name'), max_length=100)
   ```

2. Use `{% translate %}` in templates:
   ```html
   <h1>{% translate "Welcome" %}</h1>
   ```

## 🎨 Styling

The admin interface uses:
- **django-unfold**: Modern admin theme
- **Chart.js**: Interactive charts
- **Custom CSS**: Enhanced styling for better UX
- **Responsive Design**: Mobile-friendly interface

## 📝 Contributing

This project is open source! To contribute:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

### Translation Contributions

To contribute translations:

1. Create translation files for your language
2. Translate all strings in the `.po` file
3. Test the translations
4. Submit a pull request with the translation files

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Support

For support and questions:
- Create an issue on GitHub
- Check the documentation
- Review the code comments

## 🔄 Updates

To update the project:

1. Pull the latest changes:
   ```bash
   git pull origin main
   ```

2. Update dependencies:
   ```bash
   pip install -r requirements.txt --upgrade
   ```

3. Run migrations:
   ```bash
   python manage.py migrate
   ```

4. Compile translations:
   ```bash
   python manage.py compilemessages
   ```

## 📋 Installation Scripts

### System Dependencies Script
- **File**: `install_system_dependencies.sh`
- **Purpose**: Installs all required system packages
- **Usage**: `./install_system_dependencies.sh`

### Complete Setup Script
- **File**: `setup.sh`
- **Purpose**: Complete project setup from scratch
- **Usage**: `./setup.sh`

### Requirements File
- **File**: `requirements.txt`
- **Purpose**: Lists all Python dependencies
- **Usage**: `pip install -r requirements.txt`

---

**Built with ❤️ using Django and django-unfold** 
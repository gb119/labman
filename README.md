# LabMan - Laboratory Management System

A Django-based laboratory management system for managing equipment, bookings, users,
and costs in research facilities.

## Overview

LabMan is a comprehensive web application designed to help research laboratories
manage their resources, equipment, and users efficiently. Built on Django 4.x with
PostgreSQL, it provides a complete solution for equipment booking, user management,
cost tracking, and hierarchical organisation of laboratory resources.

## Key Features

### Equipment Management

- **Equipment tracking**: Comprehensive equipment database with detailed
  specifications
- **Location management**: Hierarchical organisation of physical locations
  (buildings, rooms, sub-locations)
- **Equipment booking**: Sophisticated booking system with time slots and user permissions
- **User lists**: Manage equipment access permissions and user roles

### Booking System

- **Booking policies**: Flexible rules for who can book equipment and when
- **Time quantisation**: Configure booking time slots and minimum/maximum durations
- **Role-based access**: Different booking permissions based on user roles
- **Shift management**: Define time periods for equipment availability

### Cost Management

- **Cost centres**: Hierarchical cost centre structure for financial tracking
- **Charging rates**: Multiple rate structures for different users and equipment
- **Chargeable items**: Track costs associated with equipment usage
- **Financial reporting**: Monitor equipment usage costs

### User Management

- **Account system**: Extended user accounts with laboratory-specific attributes
- **Research groups**: Organise users into research groups
- **Role hierarchy**: Trainee, User, Advanced User, Instructor, and Manager roles
- **Microsoft authentication**: Integration with Microsoft ADFS/Azure AD via OAuth2

### Additional Features

- **Document management**: Attach documents and safety information to equipment
- **Sign-off tracking**: Track user acknowledgements of safety documents
- **Photo management**: Equipment and location photos via Photologue
- **RESTful API**: Django REST Framework integration for programmatic access
- **Import/Export**: Bulk data import and export capabilities

## Technology Stack

- **Framework**: Django 4.x
- **Database**: PostgreSQL with PostGIS support
- **Python**: 3.13
- **Authentication**: Microsoft ADFS via django-auth-adfs
- **Frontend**: Bootstrap 5, HTMX for dynamic interactions
- **Tree structures**: django-mptt for hierarchical models
- **Static files**: WhiteNoise for efficient static file serving
- **Rich text editing**: TinyMCE for content management
- **API**: Django REST Framework

## Project Structure

```text
labman/
├── apps/                   # Django applications
│   ├── accounts/          # User accounts and research groups
│   ├── autocomplete/      # Autocomplete widgets
│   ├── bookings/          # Equipment booking system
│   ├── costings/          # Cost centres and charging rates
│   ├── equipment/         # Equipment and location models
│   ├── htmx_views/        # HTMX-powered views
│   └── labman_utils/      # Shared utilities and base models
├── configs/               # Server configuration files
├── fixtures/              # Initial data fixtures
├── labman/                # Main Django project
│   ├── settings/          # Split settings (common, development, production)
│   ├── api.py            # REST API configuration
│   └── urls.py           # URL routing
├── static/                # Static assets
├── templates/             # Django templates
└── manage.py              # Django management script
```

## Installation

### Prerequisites

- Python 3.13
- PostgreSQL database
- Conda or Mamba (recommended) or pip

### Using Conda/Mamba (Recommended)

```bash
# Create and activate environment
mamba env create -f environment.yaml
conda activate django

# Set up database (PostgreSQL)
# Configure database credentials in labman/settings/secrets.py

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic

# Run development server
python manage.py runserver
```

### Using pip

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements/development.txt

# Follow remaining steps from conda installation
```

## Configuration

### Settings

The project uses split settings:

- `labman/settings/common.py`: Shared settings
- `labman/settings/development.py`: Development-specific settings
- `labman/settings/production.py`: Production-specific settings

### Secrets Management

Create `labman/settings/secrets.py` for sensitive configuration:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'labman_db',
        'USER': 'labman_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### Microsoft Authentication

Configure ADFS/Azure AD in settings:

- Set up application registration in Azure AD
- Configure redirect URIs
- Add credentials to secrets.py

## Usage

### Admin Interface

Access the admin interface at `/riaradh/` (requires superuser account).

### Main Features

- **Equipment booking**: Navigate to equipment listings and select time slots
- **User management**: Manage users, roles, and research groups via admin
- **Cost tracking**: Set up cost centres and rates for equipment usage
- **Document management**: Attach safety documents and track user sign-offs

## Development

### Running Tests

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test apps.bookings
```

### Code Quality

```bash
# Format code
black .
isort .
djhtml templates/

# Check spelling
codespell
```

### Database Migrations

```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Show migration status
python manage.py showmigrations
```

## Deployment

### Production Checklist

1. Set `DEBUG = False` in production settings
2. Configure proper `SECRET_KEY`
3. Set up SSL/TLS certificates
4. Configure `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`
5. Use production database (PostgreSQL)
6. Set up static file serving
7. Configure logging
8. Enable security settings (see `production.py`)

### WSGI Deployment

The project includes WSGI configuration for deployment with Gunicorn or Apache/mod_wsgi.

```bash
# Using Gunicorn
gunicorn labman.wsgi:application --bind 0.0.0.0:8000
```

## Contributing

This is a research facility management system. Contributions should:

- Follow PEP 8 style guidelines
- Include docstrings (Google style)
- Use British English in documentation
- Pass all existing tests
- Include tests for new features

## License

MIT License - see LICENSE file for details.

Copyright (c) 2024 Gavin Burnell

## Authors

- **Gavin Burnell** - Primary maintainer
- Built on django-project-skeleton by Mischback

## Support

For issues and questions:

- Check the issue tracker on GitHub
- Review inline code documentation
- Contact laboratory administrators

## Acknowledgements

- Based on django-project-skeleton
- Uses django-mptt for hierarchical structures
- Integrates with University of Leeds authentication systems

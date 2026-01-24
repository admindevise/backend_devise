# Installation Guide - Backend Devise

This guide will help you install and configure the Backend Devise project step by step.

## Prerequisites

- Python 3.10 or higher
- Git
- pip (Python package manager)

## Step 1: Clone the Repository

```bash
git clone <REPOSITORY_URL>
cd backend_devise
```

## Step 2: Create Virtual Environment

```bash
python3 -m venv env
```

## Step 3: Activate Virtual Environment

### On Linux/macOS:
```bash
source env/bin/activate
```

### On Windows:
```bash
env\Scripts\activate
```

You should see `(env)` at the beginning of your command line.

## Step 4: Update pip

```bash
pip install --upgrade pip
```

## Step 5: Install Dependencies

```bash
pip install -r requirements.txt
```

This command will install all necessary project dependencies, including:
- Django 5.2.1
- Django REST Framework
- JWT for authentication
- Libraries for PDF, Excel, QR codes
- And many more...

## Step 6: Configure Environment Variables

1. Copy the example file (if it exists):
```bash
cp .env.example .env
```

2. Or create a new `.env` file in the project root:
```bash
touch .env
```

3. Edit the `.env` file with your configurations:
```env
SECRET_KEY=your-very-long-and-random-secret-key
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
ALLOWED_HOSTS=localhost,127.0.0.1
```

## Step 7: Prepare the Database

### Create migrations:
```bash
python manage.py makemigrations
```

### Apply migrations:
```bash
python manage.py migrate
```

## Step 8: Create Superuser (Optional)

To access Django's admin panel:

```bash
python manage.py createsuperuser
```

Follow the instructions to create an administrator user.

## Step 9: Collect Static Files

```bash
python manage.py collectstatic --noinput
```

## Step 10: Verify Installation

```bash
python manage.py check
```

If there are no errors, continue to the next step.

## Step 11: Run Development Server

```bash
python manage.py runserver
```

The server will run at: `http://127.0.0.1:8000/`

## Step 12: Verify Everything Works

1. Open your browser and go to `http://127.0.0.1:8000/`
2. To access admin: `http://127.0.0.1:8000/admin/`
3. For API documentation: `http://127.0.0.1:8000/swagger/`

## Useful Commands

### Activate virtual environment:
```bash
source env/bin/activate  # Linux/macOS
env\Scripts\activate     # Windows
```

### Deactivate virtual environment:
```bash
deactivate
```

### Run the server:
```bash
python manage.py runserver
```

### Run the server on a specific port:
```bash
python manage.py runserver 8080
```

### View all migrations:
```bash
python manage.py showmigrations
```

### Create a new application:
```bash
python manage.py startapp app_name
```

## Common Troubleshooting

### `ugettext_lazy` import error:
This project is already updated for Django 5.2. If you encounter this error, make sure you have the correct Django version installed.

### `six` module not found error:
```bash
pip install six
```

### `pkg_resources` warnings:
These are normal warnings in development. To silence them:
```bash
python -W ignore::UserWarning manage.py runserver
```

### Database error:
Make sure you have run the migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

## Project Structure

```
backend_devise/
├── manage.py                      # Django management command
├── requirements.txt               # Project dependencies
├── INSTALLATION.md               # This file
├── README.md                     # Project documentation
├── config/                       # Main configuration
│   ├── settings.py               # Django settings
│   ├── urls.py                   # Main URL patterns
│   └── wsgi.py                   # WSGI configuration
├── apps/                         # Django applications
│   ├── user/                     # User management
│   ├── fund/                     # Investment fund management
│   ├── druo/                     # Banking module
│   ├── financial_institution/    # Financial institutions
│   ├── kaleido/                  # Blockchain integration
│   ├── trading/                  # Trading operations
│   ├── audit/                    # Audit trails
│   ├── security/                 # Security module
│   └── utils/                    # Utilities and CSV data
│       ├── Institutions.csv      # Bank data
│       ├── account_type.csv      # Account types
│       ├── account_subtype.csv   # Account subtypes
│       └── identification_types.csv  # ID types
├── static/                       # Static files (CSS, JS, images)
├── templates/                    # HTML templates
├── media/                        # User-uploaded files
└── env/                          # Virtual environment (not in git)
```

## Initial Data Files

The project includes the following CSV files for initial data:

- **`apps/utils/Institutions.csv`**: Banks from Colombia and Peru (46 institutions)
- **`apps/utils/account_type.csv`**: Banking account types
- **`apps/utils/account_subtype.csv`**: Account subtypes (Savings, Checking, Electronic Deposit)
- **`apps/utils/identification_types.csv`**: Identification document types

## Security Recommendations

### For Production:

1. **Change SECRET_KEY**: Generate a new secret key
   ```bash
   python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
   ```

2. **Disable DEBUG mode**:
   ```env
   DEBUG=False
   ```

3. **Configure ALLOWED_HOSTS**:
   ```env
   ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
   ```

4. **Use a production database** (PostgreSQL recommended):
   ```env
   DATABASE_URL=postgresql://user:password@localhost:5432/devise_db
   ```

5. **Configure HTTPS** and SSL certificates

6. **Set up proper CORS headers** in `config/settings.py`

## Next Steps

Once you have the project running:

1. ✅ Explore the API documentation at `/docs/`
2. ✅ Review the different applications in the `apps` folder
3. ✅ Configure your production database
4. ✅ Load sample data or create test records
5. ✅ Set up JWT authentication for API access
6. ✅ Configure email settings for notifications
7. ✅ Review and customize permission settings

## Additional Resources

- Django Documentation: https://docs.djangoproject.com/
- Django REST Framework: https://www.django-rest-framework.org/
- Project GitHub: <REPOSITORY_URL>

## Support

If you encounter any problems during installation:

1. Check the **Common Troubleshooting** section above
2. Review the application logs
3. Verify all dependencies are correctly installed
4. Contact the development team

---

**Last Updated**: October 2025  
**Django Version**: 5.2.1  
**Python Version**: 3.10+

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
├── manage.py              # Main Django command
├── requirements.txt       # Project dependencies
├── config/               # Main configuration
│   ├── settings.py       # Django settings
│   ├── urls.py          # Main URLs
│   └── wsgi.py          # WSGI configuration
├── apps/                # Project applications
│   ├── user/            # User management
│   ├── dashboard/       # Dashboard
│   ├── asset/           # Asset management
│   ├── fiducia/         # Fiduciary module
│   └── ...              # Other applications
├── static/              # Static files
├── templates/           # HTML templates
└── env/                 # Virtual environment
```

## Next Steps

Once you have the project running, you can:

1. Explore the API documentation at `/swagger/`
2. Review the different applications in the `apps/` folder
3. Configure your production database
4. Customize the settings according to your needs

## Contact

If you encounter any problems during installation, check the troubleshooting section or contact the development team.

# Zeno Time Flow - Django Backend

Django REST API backend for Zeno Time Flow application, replacing Supabase.

## Features

- JWT Authentication
- User Management & Role-Based Access Control
- Organization & Company Management
- Employee Scheduling System
- Time Clock Tracking
- Calendar & Task Management
- Habits & Focus Sessions
- RESTful API with Django REST Framework
- WebSocket support (via Django Channels)

## Setup Instructions

### Prerequisites

- Python 3.10+
- PostgreSQL 12+
- Redis (for WebSocket support, optional)

### Installation

1. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Create PostgreSQL database:**
```sql
CREATE DATABASE zeno_time;
```

4. **Configure environment variables:**
```bash
cp .env.example .env
# Edit .env with your database credentials and settings
```

5. **Run migrations:**
```bash
python manage.py makemigrations
python manage.py migrate
```

6. **Create superuser:**
```bash
python manage.py createsuperuser
```

7. **Run development server:**
```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000/api/`

## API Endpoints

### Authentication
- `POST /api/auth/register/` - Register new user
- `POST /api/auth/login/` - Login user
- `POST /api/auth/logout/` - Logout user
- `GET /api/auth/me/` - Get current user
- `PUT /api/auth/profile/` - Update profile

### Scheduler
- `/api/scheduler/organizations/` - Organization CRUD
- `/api/scheduler/companies/` - Company CRUD
- `/api/scheduler/employees/` - Employee CRUD
- `/api/scheduler/shifts/` - Shift CRUD
- `/api/scheduler/time-clock/` - Time clock operations
- `/api/scheduler/availability/` - Employee availability

### Calendar & Tasks
- `/api/calendar/events/` - Calendar events
- `/api/tasks/` - Task management

### Habits & Focus
- `/api/habits/` - Habit tracking
- `/api/focus/` - Focus sessions

## Project Structure

```
zeno-time-backend/
├── accounts/          # User authentication & profiles
├── scheduler/         # Organizations, companies, employees, shifts
├── calendar_app/      # Calendar events
├── tasks/             # Task management
├── habits/            # Habit tracking
├── focus/             # Focus sessions
└── zeno_time/         # Project settings
```

## Database Models

### Core Models
- `User` - Custom user model
- `Profile` - User profile information
- `UserRole` - User roles and permissions

### Scheduler Models
- `Organization` - Top-level organizations
- `Company` - Companies within organizations
- `Department` - Departments within companies
- `ScheduleTeam` - Teams for scheduling
- `Employee` - Employee records
- `Shift` - Work shifts
- `ShiftReplacementRequest` - Shift swap requests
- `EmployeeAvailability` - Employee availability
- `TimeClock` - Clock in/out records
- `ScheduleTemplate` - Saved schedule templates
- `AppSettings` - Application settings

## Authentication

The API uses JWT (JSON Web Tokens) for authentication. Include the token in the Authorization header:

```
Authorization: Bearer <access_token>
```

## CORS Configuration

CORS is configured to allow requests from the frontend. Update `CORS_ALLOWED_ORIGINS` in settings.py or .env file.

## Development

### Running Tests
```bash
python manage.py test
```

### Creating Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Django Admin
Access admin panel at `http://localhost:8000/admin/`

## Production Deployment

1. Set `DEBUG=False` in settings
2. Configure proper `ALLOWED_HOSTS`
3. Set up proper database (PostgreSQL)
4. Configure static files serving
5. Set up SSL/HTTPS
6. Configure proper CORS origins
7. Set up Redis for WebSocket support

## Migration from Supabase

See `MIGRATION_GUIDE.md` for detailed instructions on migrating from Supabase to this Django backend.


# Django Backend Setup Instructions

## Quick Start

1. **Navigate to backend directory:**
```bash
cd zeno-time-backend
```

2. **Create and activate virtual environment:**
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Set up PostgreSQL database:**
```sql
CREATE DATABASE zeno_time;
CREATE USER zeno_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE zeno_time TO zeno_user;
```

5. **Configure environment:**
```bash
# Copy .env.example to .env and update values
cp .env.example .env
# Edit .env with your database credentials
```

6. **Run migrations:**
```bash
python manage.py makemigrations accounts scheduler calendar_app tasks habits focus
python manage.py migrate
```

7. **Create superuser:**
```bash
python manage.py createsuperuser
```

8. **Run server:**
```bash
python manage.py runserver
```

## Next Steps

### 1. Complete Model Implementations

The following apps need their models, serializers, views, and URLs completed:

- ✅ `accounts` - User, Profile, UserRole (DONE)
- ✅ `scheduler` - Models created, need serializers/views/URLs
- ⏳ `calendar_app` - Need to create
- ⏳ `tasks` - Need to create
- ⏳ `habits` - Need to create
- ⏳ `focus` - Need to create

### 2. Create Remaining Apps

For each app, create:
- `models.py` - Database models
- `serializers.py` - DRF serializers
- `views.py` - API views
- `urls.py` - URL routing
- `admin.py` - Django admin registration

### 3. Implement API Endpoints

Based on Supabase usage, implement:

**Scheduler:**
- Organizations CRUD
- Companies CRUD
- Employees CRUD
- Shifts CRUD
- Time Clock operations
- Employee Availability
- Shift Replacement Requests
- Schedule Templates

**Calendar:**
- Calendar Events CRUD
- Event filtering and search

**Tasks:**
- Tasks CRUD
- Subtasks
- Task assignments
- Task templates

**Habits:**
- Habits CRUD
- Habit completions
- Streak tracking

**Focus:**
- Focus sessions CRUD
- Session tracking

### 4. Update Frontend

1. Replace Supabase imports with API client
2. Update authentication hooks
3. Update all data fetching hooks
4. Update components to use new API

### 5. Testing

- Test all API endpoints
- Test authentication flow
- Test permissions and roles
- Test real-time features (if implemented)

## File Structure Created

```
zeno-time-backend/
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── MIGRATION_GUIDE.md
├── SETUP_INSTRUCTIONS.md
├── zeno_time/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── accounts/
│   ├── __init__.py
│   ├── models.py ✅
│   ├── serializers.py ✅
│   ├── views.py ✅
│   ├── urls.py ✅
│   └── admin.py ✅
└── scheduler/
    ├── __init__.py
    └── models.py ✅
```

## Important Notes

1. **Database**: Uses PostgreSQL (same as Supabase)
2. **Authentication**: JWT tokens instead of Supabase Auth
3. **Real-time**: Can use Django Channels for WebSocket support
4. **CORS**: Configured for frontend communication
5. **Permissions**: Role-based access control via UserRole model

## Development Tips

- Use Django admin at `/admin/` for data management
- Use Django REST Framework browsable API for testing
- Check `settings.py` for all configuration options
- Use `python manage.py shell` for database queries


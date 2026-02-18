# Migration Guide: Supabase to Django Backend

This guide will help you migrate from Supabase to the Django backend.

## Overview

The Django backend provides the same functionality as Supabase but with:
- Full control over the backend
- Custom business logic
- Better performance for complex queries
- Easier deployment and scaling

## Key Differences

### Authentication
- **Supabase**: Uses Supabase Auth with magic links, OAuth, etc.
- **Django**: Uses JWT tokens with email/password authentication

### Database
- **Supabase**: PostgreSQL hosted on Supabase
- **Django**: Your own PostgreSQL database

### Real-time
- **Supabase**: Built-in real-time subscriptions
- **Django**: WebSocket support via Django Channels (optional)

### API
- **Supabase**: Auto-generated REST API from database
- **Django**: Custom REST API with Django REST Framework

## Migration Steps

### 1. Database Migration

Export data from Supabase and import to Django:

```bash
# Export from Supabase (using Supabase CLI or pg_dump)
pg_dump -h <supabase-host> -U postgres -d postgres > supabase_backup.sql

# Import to Django database
psql -h localhost -U postgres -d zeno_time < supabase_backup.sql
```

### 2. Update Frontend

Replace Supabase client calls with Django API calls. See `FRONTEND_MIGRATION.md` for details.

### 3. Environment Variables

Update frontend `.env`:
```env
VITE_API_URL=http://localhost:8000/api
```

Remove Supabase variables:
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`

### 4. Authentication Flow

Update authentication to use Django JWT:
- Login: `POST /api/auth/login/`
- Register: `POST /api/auth/register/`
- Store JWT token in localStorage
- Include token in Authorization header

## API Mapping

### Supabase → Django

| Supabase | Django |
|----------|--------|
| `supabase.auth.signInWithPassword()` | `POST /api/auth/login/` |
| `supabase.auth.signUp()` | `POST /api/auth/register/` |
| `supabase.from('table').select()` | `GET /api/app/table/` |
| `supabase.from('table').insert()` | `POST /api/app/table/` |
| `supabase.from('table').update()` | `PUT /api/app/table/{id}/` |
| `supabase.from('table').delete()` | `DELETE /api/app/table/{id}/` |

## Testing

1. Test all authentication flows
2. Test CRUD operations for all models
3. Test role-based permissions
4. Test real-time features (if using WebSockets)

## Rollback Plan

Keep Supabase instance running during migration for rollback if needed.


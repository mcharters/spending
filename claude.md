# Spending Tracker - Claude Context

## Project Overview

This is a full-stack spending tracker web application for managing personal expenses. The application uses a Flask backend with SQLAlchemy/SQLite for persistence and a React frontend that builds to static files served by Flask.

## Architecture

### Backend (Python/Flask)
- **Location**: `backend/` directory
- **Framework**: Flask 3.0
- **Database**: SQLite with SQLAlchemy ORM
- **API**: RESTful JSON API under `/api` prefix
- **Static Files**: Serves built React app from `backend/static/`

### Frontend (React)
- **Location**: `frontend/` directory
- **Framework**: Vanilla React 18 (no additional state management libraries)
- **Build Tool**: Webpack 5 with Babel
- **Build Output**: Compiles to `backend/static/` for production deployment

### Deployment Model
The application is designed for single-server deployment where Flask serves both:
1. The REST API at `/api/*` endpoints
2. The static React frontend at all other routes

## File Structure

```
spending/
├── backend/
│   ├── app.py                  # Main Flask application (routes, config, auth)
│   ├── models.py               # SQLAlchemy database models
│   ├── requirements.txt        # Python dependencies
│   ├── .env                    # Authentication credentials (gitignored)
│   ├── .env.example            # Template for .env file
│   ├── generate_password.py    # Helper script to generate password hashes
│   ├── database.db             # SQLite database (auto-created, gitignored)
│   ├── venv/                   # Python virtual environment (gitignored)
│   ├── migrations/             # Alembic database migrations
│   │   └── versions/           # Migration version files
│   └── static/                 # React build output (gitignored)
├── frontend/
│   ├── src/
│   │   ├── index.js            # React app entry point
│   │   ├── App.js              # Main app component with auth state
│   │   └── styles.css          # Global styles
│   ├── public/
│   │   └── index.html          # HTML template
│   ├── package.json            # Node.js dependencies and scripts
│   └── webpack.config.js       # Webpack build configuration
├── .gitignore
├── .claude/                    # Claude Code configuration (gitignored)
├── README.md                   # User-facing documentation
└── claude.md                   # This file - Claude context
```

## Current Data Model

### Category Model (backend/models.py)
- `id` (Integer, PK): Auto-incrementing primary key
- `name` (String(50), Unique): Category name
- `parent_type` (String(20)): Parent category type ("Personal" or "Shared")

**Available Categories:**
- Personal: Beauty, Clothing, Counselling, Entertainment, Media, Misc, Workouts
- Shared: Car, Dining, Groceries, House, Kids, Outings, Utilities

### Expense Model (backend/models.py)
- `id` (Integer, PK): Auto-incrementing primary key
- `description` (String(200), Nullable): Optional expense description
- `amount` (Float): Expense amount in currency
- `category_id` (Integer, FK): Foreign key to Category model
- `created_by` (String(50)): Username of user who created the expense
- `expense_date` (Date): Date of the expense (defaults to today)
- `created_at` (DateTime): Timestamp, auto-set to UTC now
- `category` (Relationship): SQLAlchemy relationship to Category

## API Endpoints

**Authentication**: All API endpoints require HTTP Basic Authentication. Send credentials in the `Authorization` header.

### GET /api/expenses
Returns expenses visible to the authenticated user:
- All expenses created by the current user (Personal or Shared)
- All Shared expenses created by any user

**Response**: `200 OK`
```json
[
  {
    "id": 1,
    "description": null,
    "amount": 45.99,
    "category": "Groceries",
    "category_id": 10,
    "parent_type": "Shared",
    "created_by": "user1",
    "expense_date": "2025-01-15",
    "created_at": "2025-01-15T10:30:00"
  }
]
```

### POST /api/expenses
Creates a new expense. The `created_by` field is automatically set to the authenticated user.

**Request Body**:
```json
{
  "amount": 4.50,
  "category_id": 9,
  "expense_date": "2025-01-15"
}
```

**Response**: `201 Created`
```json
{
  "id": 2,
  "description": null,
  "amount": 4.50,
  "category": "Dining",
  "category_id": 9,
  "parent_type": "Shared",
  "created_by": "user1",
  "expense_date": "2025-01-15",
  "created_at": "2025-01-15T14:20:00"
}
```

### GET /api/categories
Returns all categories as JSON array.

**Response**: `200 OK`
```json
[
  {
    "id": 1,
    "name": "Beauty",
    "parent_type": "Personal"
  },
  {
    "id": 8,
    "name": "Car",
    "parent_type": "Shared"
  }
]
```

## Development Workflow

### Running in Development Mode

1. **Backend**: Activate virtual environment and run Flask dev server
   ```bash
   cd backend
   venv\Scripts\activate  # Windows
   source venv/bin/activate  # Mac/Linux
   python app.py  # Runs on http://localhost:5000
   ```

2. **Frontend**: Run Webpack dev server
   ```bash
   cd frontend
   npm start  # Runs on http://localhost:3000
   ```

In dev mode, the React dev server proxies `/api` requests to Flask backend.

### Building for Production

```bash
cd frontend
npm run build  # Outputs to backend/static/
```

Then run Flask which serves both API and static files:
```bash
cd backend
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux
python app.py  # Everything served from http://localhost:5000
```

## Database Migrations

This project uses Flask-Migrate (Alembic) for database schema management.

### Common Migration Commands

**Windows**:
```bash
cd backend
venv\Scripts\activate
set FLASK_APP=app.py

# Create a new migration after model changes
flask db migrate -m "Description of changes"

# Apply migrations to database
flask db upgrade

# Rollback last migration
flask db downgrade

# Seed categories (run after initial migration)
flask seed-categories
```

**Mac/Linux**:
```bash
cd backend
source venv/bin/activate
export FLASK_APP=app.py

# Create a new migration after model changes
flask db migrate -m "Description of changes"

# Apply migrations to database
flask db upgrade

# Rollback last migration
flask db downgrade

# Seed categories (run after initial migration)
flask seed-categories
```

### Migration Workflow

1. **Make changes to models** in `backend/models.py`
2. **Activate virtual environment**: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac/Linux)
3. **Generate migration**: `flask db migrate -m "Add new field"`
4. **Review migration** in `backend/migrations/versions/`
5. **Apply migration**: `flask db upgrade`
6. **Commit migration files** to git

### Initial Setup (Fresh Database)

```bash
cd backend
venv\Scripts\activate     # Windows
source venv/bin/activate  # Mac/Linux
flask db upgrade          # Apply all migrations
flask seed-categories     # Seed initial categories
python app.py            # Start server
```

## Coding Conventions

### Python (Backend)
- Always work within the virtual environment (`venv`)
- Use Flask blueprints if adding more route groups
- Import models after `db` initialization to avoid circular imports
- Use `db.session` for all database transactions
- Models should have `to_dict()` method for JSON serialization
- All API routes require `@auth.login_required` decorator
- Use `auth.current_user()` to get the authenticated username
- CORS is configured to allow Authorization header

### JavaScript (Frontend)
- Use functional components with hooks (no class components)
- Keep components in `frontend/src/` directory
- Use `fetch` API for HTTP requests (no axios dependency)
- Include Basic Auth header in all API requests: `Authorization: Basic ${btoa(username:password)}`
- API URL switches based on `process.env.NODE_ENV`
- CSS in separate files, imported in JS
- Authentication state managed in App.js

### Database
- Migrations: Using Flask-Migrate (Alembic) for schema versioning
- Database file is gitignored and created automatically
- Migration files in `backend/migrations/` should be committed to git
- Use SQLAlchemy ORM, avoid raw SQL queries

## Common Tasks

### Adding a New Database Model
1. Define model class in `backend/models.py` inheriting from `db.Model`
2. Add `to_dict()` method for JSON serialization
3. Activate venv: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac/Linux)
4. Generate migration: `flask db migrate -m "Add NewModel"`
5. Review migration file in `backend/migrations/versions/`
6. Apply migration: `flask db upgrade`
7. Restart Flask server

### Adding a New API Endpoint
1. Add route decorator and function in `backend/app.py`
2. Add `@auth.login_required` decorator to protect the endpoint
3. Use `auth.current_user()` to get the authenticated username if needed
4. Use `jsonify()` for JSON responses
5. Import Flask utilities as needed (`request`, `abort`, etc.)

### Adding a New React Component
1. Create new `.js` file in `frontend/src/`
2. Import and use in `App.js` or other components
3. Keep styling in `styles.css` or create component-specific CSS

### Installing New Dependencies

**Python**:
```bash
cd backend
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux
pip install <package>
pip freeze > requirements.txt
```

**Node**:
```bash
cd frontend
npm install <package>
# package.json updates automatically
```

## Important Notes

### Security Considerations
- **Authentication**: HTTP Basic Auth with 2 hardcoded users (user1, user2)
- **Credentials**: Stored in `.env` file with password hashes (never commit this file!)
- **CORS**: Enabled for all origins with Authorization header allowed (restrict in production)
- **Input validation**: Minimal (add validation for production)
- **SQL injection**: Protected by SQLAlchemy ORM
- **User separation**: Personal expenses filtered by user, Shared expenses visible to all

### Authentication Setup
The app uses HTTP Basic Authentication with credentials stored in `backend/.env`:
- Default users: `user1` and `user2`
- Passwords are hashed using werkzeug's scrypt
- Use `backend/generate_password.py` to generate new password hashes
- Frontend stores credentials in state and sends with each API request

### Future Enhancements to Consider
- Input validation and error handling
- Expense editing and deletion endpoints
- Date filtering and expense search
- Category management UI
- Data export functionality
- Better error messages and loading states in UI
- Responsive mobile design improvements
- Environment-based configuration (dev/staging/prod)
- More robust user management (database-backed users)

## Environment Setup

### Python Virtual Environment
Always use a virtual environment in the backend directory:
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
```

### Node Version
Project developed with Node.js 18+. Check compatibility if using different version.

## Testing

Currently no tests implemented. Consider adding:
- Backend: pytest with Flask test client
- Frontend: Jest + React Testing Library
- Integration: End-to-end tests with Playwright/Cypress

## Deployment Checklist

Before deploying to production:
- [ ] Build frontend: `npm run build`
- [ ] Set `app.debug = False` in production
- [ ] Configure CORS to specific origins only
- [ ] Use production WSGI server (gunicorn/waitress), not Flask dev server
- [ ] Set up proper environment variables
- [ ] Enable HTTPS
- [ ] Set up database backups
- [ ] Add input validation
- [ ] Implement rate limiting
- [ ] Add logging and monitoring

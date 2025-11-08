# Spending Tracker

A full-stack web application for tracking expenses with a Flask backend and React frontend.

## Architecture

- **Backend**: Python Flask with SQLAlchemy ORM and SQLite database
- **Frontend**: Vanilla React with Webpack bundler
- **Deployment**: React builds to Flask's static directory for single-server deployment

## Project Structure

```
spending/
├── backend/
│   ├── app.py              # Flask application and routes
│   ├── models.py           # SQLAlchemy models
│   ├── requirements.txt    # Python dependencies
│   ├── database.db         # SQLite database (created on first run)
│   └── static/             # Built React files (created by build)
├── frontend/
│   ├── src/
│   │   ├── index.js        # React entry point
│   │   ├── App.js          # Main React component
│   │   └── styles.css      # Application styles
│   ├── public/
│   │   └── index.html      # HTML template
│   ├── package.json        # Node dependencies
│   └── webpack.config.js   # Webpack configuration
└── README.md
```

## Setup Instructions

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

## Development

### Running in Development Mode

1. **Start the Flask backend** (from `backend/` directory):
   ```bash
   python app.py
   ```
   The API will run on http://localhost:5000

2. **Start the React dev server** (from `frontend/` directory):
   ```bash
   npm start
   ```
   The frontend will run on http://localhost:3000

The webpack dev server is configured to proxy API requests to the Flask backend.

## Production Build

### Building for Production

1. **Build the React frontend** (from `frontend/` directory):
   ```bash
   npm run build
   ```
   This compiles React and outputs to `backend/static/`

2. **Run the Flask server** (from `backend/` directory):
   ```bash
   python app.py
   ```

Now the Flask server serves both the API and the React frontend from http://localhost:5000

### Deployment

For production deployment:

1. Build the frontend: `cd frontend && npm run build`
2. Deploy the `backend/` directory to your hosting service
3. Ensure the hosting service runs `python app.py`
4. The app will serve both API and frontend from a single server

**Recommended hosting options:**
- Heroku
- PythonAnywhere
- DigitalOcean App Platform
- AWS Elastic Beanstalk
- Google Cloud Run

## API Endpoints

- `GET /api/expenses` - Get all expenses
- `POST /api/expenses` - Create a new expense
  ```json
  {
    "description": "Groceries",
    "amount": 45.99,
    "category": "Food"
  }
  ```

## Database

The application uses SQLite with the following schema:

**Expense Model:**
- `id`: Integer (Primary Key)
- `description`: String(200)
- `amount`: Float
- `category`: String(50)
- `created_at`: DateTime

The database is automatically created when you first run the Flask application.

## Technologies Used

- **Backend**: Flask 3.0, SQLAlchemy 2.0, Flask-CORS
- **Frontend**: React 18, Webpack 5, Babel
- **Database**: SQLite

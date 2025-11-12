# Deployment Workflow

This project uses a pre-build deployment strategy where the frontend is built locally and committed to git.

## Local Build Process

### Windows
```bash
build.bat
```

### Mac/Linux
```bash
chmod +x build.sh
./build.sh
```

This script will:
1. Install npm dependencies in `frontend/`
2. Build the React app
3. Output the built files to `backend/static/`

## Railway Deployment

### Initial Setup

1. In Railway dashboard, go to your service settings
2. Set **Root Directory** to `backend/`
3. Railpack will automatically:
   - Detect Python from `requirements.txt`
   - Install Python dependencies
   - Use the pre-built static files in `backend/static/`

### Deploy Workflow

1. Make changes to your code
2. Build the frontend: `build.bat` (Windows) or `./build.sh` (Mac/Linux)
3. Commit everything including `backend/static/`:
   ```bash
   git add .
   git commit -m "Your changes"
   git push
   ```
4. Railway will automatically deploy the backend with the pre-built frontend

### Environment Variables

Set these in Railway dashboard under Variables:

```
AUTH_USER1=user1:scrypt:32768:8:1$HASH_HERE
AUTH_USER2=user2:scrypt:32768:8:1$HASH_HERE
FLASK_APP=app.py
```

To generate password hashes:
```bash
cd backend
python generate_password.py
```

### First Deployment

After the first successful deployment, seed the categories:

**Option A: Railway CLI**
```bash
railway login
railway link
railway run flask seed-categories
```

**Option B: Temporary start command**
In Railway dashboard, temporarily change the start command to:
```
flask db upgrade && flask seed-categories && gunicorn app:app
```

After one deployment, change it back to:
```
flask db upgrade && gunicorn app:app
```

## Why This Approach?

Railway works best when focused on a single directory/language. By building the frontend locally:

- Railway only needs to handle Python/Flask deployment
- Simpler configuration (just set root directory to `backend/`)
- Faster deployments (no Node.js build step on Railway)
- Frontend build output is version controlled alongside code

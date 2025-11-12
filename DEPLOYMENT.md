# Deploying to Railway

This guide walks you through deploying the Spending Tracker application to Railway.

## Prerequisites

1. A [Railway](https://railway.app/) account
2. A GitHub account (for connecting your repository)
3. Your code pushed to a GitHub repository

## Deployment Steps

### 1. Create a New Railway Project

1. Go to [railway.app](https://railway.app/) and sign in
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Authorize Railway to access your GitHub account if prompted
5. Select your spending tracker repository

### 2. Configure Environment Variables

After the project is created, you need to set up environment variables:

1. In your Railway project dashboard, click on your service
2. Go to the "Variables" tab
3. Add the following environment variables:

**Required Variables:**

```
AUTH_USER1=user1:scrypt:32768:8:1$HASH_HERE
AUTH_USER2=user2:scrypt:32768:8:1$HASH_HERE
FLASK_APP=app.py
```

**To generate password hashes:**

On your local machine, run:

```bash
cd backend
python generate_password.py
```

Enter your desired password when prompted, and it will output the hash in the format needed for the environment variables.

### 3. Initial Database Setup

Railway will automatically:
- Build the frontend (React app)
- Install Python dependencies
- Run database migrations (`flask db upgrade`)
- Start the gunicorn server

However, you need to seed the categories manually after the first deployment:

1. Go to your Railway project dashboard
2. Click on your service
3. Go to the "Settings" tab and copy your deployment URL
4. Open the Railway service logs (under "Deployments")
5. Once the deployment is successful, you need to run the seed command

**Option A: Using Railway CLI** (recommended)

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login to Railway
railway login

# Link to your project
railway link

# Run the seed command
railway run flask seed-categories
```

**Option B: One-time execution**

You can temporarily modify the `startCommand` in `railway.json` to include seeding, deploy, then change it back:

```json
"startCommand": "cd backend && flask db upgrade && flask seed-categories && gunicorn app:app"
```

After one successful deployment, revert it back to:

```json
"startCommand": "cd backend && flask db upgrade && gunicorn app:app"
```

### 4. Access Your Application

1. Go to your Railway project dashboard
2. Click on your service
3. Go to the "Settings" tab
4. Under "Domains", click "Generate Domain"
5. Railway will provide a public URL (e.g., `your-app.up.railway.app`)
6. Visit that URL to access your deployed application

## Application Structure

The deployment process uses Nixpacks with a custom `nixpacks.toml` configuration:

1. **Setup Phase:**
   - Installs Node.js and Python 3.9

2. **Install Phase:**
   - Installs Node.js dependencies in `frontend/`
   - Installs Python dependencies from `backend/requirements.txt`

3. **Build Phase:**
   - Builds React app with `npm run build` (outputs to `backend/static/`)

4. **Deploy Phase:**
   - Changes to `backend/` directory
   - Runs database migrations (`flask db upgrade`)
   - Starts gunicorn server

5. **Runtime:**
   - Flask serves the React app from `backend/static/`
   - API endpoints available at `/api/*`
   - All other routes serve the React app

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `AUTH_USER1` | First user credentials | `user1:scrypt:32768:8:1$HASH` |
| `AUTH_USER2` | Second user credentials | `user2:scrypt:32768:8:1$HASH` |
| `FLASK_APP` | Flask application entry point | `app.py` |

## Database

Railway provides persistent storage for SQLite by default. Your database file (`database.db`) will be stored in the `backend/` directory and will persist across deployments.

**Important:** Railway's free tier includes 512MB of persistent storage. Make sure your database doesn't exceed this limit.

## Troubleshooting

### Build Fails

- Check the build logs in Railway dashboard
- Ensure `frontend/package.json` and `backend/requirements.txt` are up to date
- Verify Node.js and Python versions are compatible

### Database Migration Issues

- Check if migrations folder exists in `backend/migrations/`
- Ensure `FLASK_APP` environment variable is set to `app.py`
- Verify database file has write permissions

### Categories Not Showing Up

- Make sure you ran `flask seed-categories` after the first deployment
- Check the application logs for any errors

### Authentication Not Working

- Verify `AUTH_USER1` and `AUTH_USER2` environment variables are set correctly
- Ensure password hashes were generated with `backend/generate_password.py`
- Check that the format is: `username:scrypt:32768:8:1$HASH`

### Application Won't Start

- Check the deployment logs in Railway
- Verify gunicorn is in `requirements.txt`
- Ensure the `Procfile` and `railway.json` are in the root directory

## Updating Your Deployment

Railway automatically redeploys when you push to your connected GitHub branch:

1. Make changes locally
2. Commit and push to GitHub
3. Railway will automatically detect changes and redeploy

## Railway CLI Commands

```bash
# View logs
railway logs

# Open deployed app
railway open

# Run a command in the Railway environment
railway run <command>

# SSH into the Railway container
railway shell
```

## Costs

As of January 2025, Railway offers:
- **Free Trial:** $5 in credits (no credit card required)
- **Starter Plan:** $5/month + usage-based pricing
- **Pro Plan:** $20/month + usage-based pricing

Your spending tracker app should run comfortably within the Starter plan for personal use.

## Security Considerations for Production

1. **CORS:** Consider restricting CORS origins in `app.py` to your Railway domain
2. **HTTPS:** Railway provides HTTPS by default
3. **Environment Variables:** Never commit `.env` files - use Railway's environment variables
4. **Database Backups:** Consider periodic backups of your SQLite database
5. **Rate Limiting:** Add rate limiting for production use

## Next Steps

After deployment:
1. Test all functionality (login, adding expenses, viewing budgets)
2. Set up database backup schedule
3. Monitor application logs for errors
4. Consider adding a custom domain (available in Railway settings)

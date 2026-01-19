#!/bin/bash
# e:/python_timetable_generation/pa_setup.sh
# Run this script ONCE in your PythonAnywhere Bash Console to setup GitHub-based deployment.

GITHUB_URL="https://github.com/ahtesham-clcbws/school_timetable_generator_python"
PROJECT_DIR="/home/$USER/mysite" # Adjust if your site is elsewhere
BRANCH="master"

echo "🚀 Setting up GitHub Deployment for PythonAnywhere..."

# 1. Navigate to project directory
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# 2. Initialize or Update Git
if [ ! -d ".git" ]; then
    echo "📦 Initializing Git in non-empty directory..."
    git init
    git remote add origin $GITHUB_URL
    git fetch
    git checkout -f $BRANCH
else
    echo "📦 Repository already exists. Updating origin..."
    git remote set-url origin $GITHUB_URL
fi

# 3. Create a quick deploy script
cat <<EOF > deploy.sh
#!/bin/bash
PROJECT_DIR="$PROJECT_DIR"
WSGI_FILE="/var/www/\${USER}_pythonanywhere_com_wsgi.py"

echo "🚀 Pulling latest code from GitHub ($BRANCH)..."
cd \$PROJECT_DIR
git fetch origin
git reset --hard origin/$BRANCH

echo "📦 Installing/Updating dependencies..."
if [ -f "requirements.txt" ]; then
    pip install --user -r requirements.txt
fi

echo "🔄 Reloading Web App..."
if [ -f "\$WSGI_FILE" ]; then
    touch "\$WSGI_FILE"
    echo "✅ WSGI file touched for reload."
else
    pa_reload_webapp.py \${USER}.pythonanywhere.com || echo "⚠️ Could not reload automatically. Please reload manually in the Web tab."
fi

echo "✅ Done!"
EOF

chmod +x deploy.sh

echo "--------------------------------------------------"
echo "✅ Setup complete!"
echo "To deploy latest changes from GitHub, just run:"
echo "cd $PROJECT_DIR && ./deploy.sh"
echo "--------------------------------------------------"

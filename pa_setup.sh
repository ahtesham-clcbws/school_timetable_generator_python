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

# 2. Initialize or Clone
if [ ! -d ".git" ]; then
    echo "📦 Cloning repository from GitHub..."
    git clone $GITHUB_URL .
else
    echo "📦 Repository already exists. Updating origin..."
    git remote set-url origin $GITHUB_URL
fi

# 3. Create a quick deploy script
cat <<EOF > deploy.sh
#!/bin/bash
echo "🚀 Pulling latest code from GitHub ($BRANCH)..."
git pull origin $BRANCH

echo "📦 Installing/Updating dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi

echo "🔄 Reloading Web App..."
pa_reload_webapp.py \${USER}.pythonanywhere.com

echo "✅ Done!"
EOF

chmod +x deploy.sh

echo "--------------------------------------------------"
echo "✅ Setup complete!"
echo "To deploy latest changes from GitHub, just run:"
echo "cd $PROJECT_DIR && ./deploy.sh"
echo "--------------------------------------------------"

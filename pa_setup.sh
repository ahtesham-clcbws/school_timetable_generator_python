#!/bin/bash
# e:/python_timetable_generation/pa_setup.sh
# Run this script ONCE in your PythonAnywhere Bash Console to setup Push-to-Deploy.

PROJECT_DIR="/home/$USER/mysite" # Adjust if your site is elsewhere
REPO_DIR="/home/$USER/timetable_gen.git"

echo "🚀 Setting up Git Deployment for PythonAnywhere..."

# 1. Create a bare repository
mkdir -p $REPO_DIR
cd $REPO_DIR
git init --bare

# 2. Create the post-receive hook
cat <<EOF > hooks/post-receive
#!/bin/bash
GIT_MAIN_DIR="$PROJECT_DIR"
echo "📦 Code received... Deploying to \$GIT_MAIN_DIR"

# Checkout the code to the project directory
git --work-tree=\$GIT_MAIN_DIR --git-dir=$REPO_DIR checkout -f main

# Install/Update dependencies
cd \$GIT_MAIN_DIR
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi

# Reload the PythonAnywhere web app
echo "🔄 Reloading Web App..."
touch /var/www/\${USER}_pythonanywhere_com_wsgi.py 2>/dev/null || pa_reload_webapp.py \${USER}.pythonanywhere.com

echo "✅ Deployment complete!"
EOF

chmod +x hooks/post-receive

echo "--------------------------------------------------"
echo "✅ Server setup complete!"
echo "Now, run this command on your LOCAL machine (inside e:/python_timetable_generation):"
echo "git remote add pythonanywhere $USER@ssh.pythonanywhere.com:$REPO_DIR"
echo "--------------------------------------------------"
echo "Then deploy anytime with: git push pythonanywhere main"

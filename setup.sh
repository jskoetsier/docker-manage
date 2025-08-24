#!/bin/bash

# Docker Swarm Manager Setup Script for Ubuntu 24.04

set -e

echo "🐳 Docker Swarm Manager Setup Script"
echo "======================================"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install packages
install_package() {
    if ! dpkg -l | grep -q "^ii  $1 "; then
        echo "Installing $1..."
        sudo apt-get install -y "$1"
    else
        echo "$1 is already installed"
    fi
}

# Update system
echo "📦 Updating system packages..."
sudo apt-get update

# Install Python and pip
echo "🐍 Installing Python and pip..."
install_package python3
install_package python3-pip
install_package python3-venv

# Install Redis
echo "📊 Installing Redis..."
install_package redis-server

# Start and enable Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Install Docker if not present
if ! command_exists docker; then
    echo "🐳 Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo "Docker installed. You may need to log out and back in for group changes to take effect."
else
    echo "Docker is already installed"
fi

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Create virtual environment
echo "🏗️ Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Copy environment file
if [ ! -f .env ]; then
    echo "⚙️ Creating environment configuration..."
    cp .env.example .env

    # Generate a random secret key
    SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
    sed -i "s/your-secret-key-here/$SECRET_KEY/" .env

    echo "Please edit .env file to configure your settings"
fi

# Run Django migrations
echo "🗃️ Setting up database..."
python manage.py migrate

# Create static files directory
echo "📁 Setting up static files..."
python manage.py collectstatic --noinput

# Create superuser prompt
echo ""
echo "🔐 Create Django superuser (optional):"
read -p "Would you like to create a superuser account? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python manage.py createsuperuser
fi

# Service file for systemd
echo "⚙️ Creating systemd service file..."
sudo tee /etc/systemd/system/swarm-manager.service > /dev/null <<EOF
[Unit]
Description=Docker Swarm Manager
After=network.target docker.service redis.service
Requires=docker.service redis.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/python manage.py runserver 0.0.0.0:8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable swarm-manager.service

echo ""
echo "✅ Setup completed successfully!"
echo ""
echo "🚀 To start the application:"
echo "   1. Manual start: source venv/bin/activate && python manage.py runserver 0.0.0.0:8000"
echo "   2. Service start: sudo systemctl start swarm-manager"
echo ""
echo "🌐 Access the web interface at: http://localhost:8000"
echo ""
echo "📋 Next steps:"
echo "   - Initialize Docker Swarm: docker swarm init"
echo "   - Edit .env file for custom configuration"
echo "   - Start the service: sudo systemctl start swarm-manager"
echo ""
echo "📖 For more information, check the README.md file"

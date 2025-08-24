# Docker Swarm Manager

A comprehensive web-based management interface for Docker Swarm clusters built with Django and Bootstrap 5.

## Features

- 🔍 **Real-time monitoring** of Docker Swarm cluster status
- ⚙️ **Service management** - Create, start, restart, stop, and scale services
- 🖥️ **Node monitoring** - View cluster nodes, their roles, and resource usage
- 📊 **Health monitoring** - Track container health and status
- 🌐 **Modern web interface** built with Bootstrap 5
- 🔄 **Real-time updates** using WebSockets
- 📱 **Responsive design** for desktop and mobile

## Screenshots

![Dashboard](docs/dashboard.png)
*Main dashboard showing cluster overview*

![Services](docs/services.png)
*Service management interface*

## Requirements

### System Requirements
- Ubuntu 24.04 LTS (recommended)
- Python 3.8 or higher
- Docker Engine 20.10 or higher
- Redis 6.0 or higher
- At least 1GB RAM
- 2GB disk space

### Python Dependencies
All Python dependencies are listed in `requirements.txt` and will be installed automatically during setup.

## Quick Start

### Automated Installation

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd docker-manage
   ```

2. **Run the setup script:**
   ```bash
   ./setup.sh
   ```

3. **Initialize Docker Swarm (if not already done):**
   ```bash
   docker swarm init
   ```

4. **Start the application:**
   ```bash
   sudo systemctl start swarm-manager
   ```

5. **Access the web interface:**
   Open your browser and navigate to `http://localhost:8000`

### Manual Installation

If you prefer to install manually or the automated script doesn't work for your system:

1. **Install system dependencies:**
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3 python3-pip python3-venv redis-server
   ```

2. **Install Docker:**
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER
   ```

3. **Create Python virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

4. **Install Python dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env file with your settings
   ```

6. **Setup database:**
   ```bash
   python manage.py migrate
   python manage.py collectstatic --noinput
   ```

7. **Create superuser (optional):**
   ```bash
   python manage.py createsuperuser
   ```

8. **Start the application:**
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

## Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Django Configuration
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True

# Docker Configuration
DOCKER_HOST=unix:///var/run/docker.sock
DOCKER_TLS_VERIFY=False
DOCKER_CERT_PATH=

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
```

### Docker Swarm Setup

To use this application, you need a Docker Swarm cluster:

1. **Initialize Swarm (single node):**
   ```bash
   docker swarm init
   ```

2. **Join additional nodes:**
   ```bash
   # On manager node, get join token:
   docker swarm join-token worker
   
   # On worker nodes, run the provided command
   docker swarm join --token <token> <manager-ip>:2377
   ```

## Usage

### Dashboard
- View cluster overview with real-time metrics
- Monitor node status and resource usage
- Quick access to services and their health status

### Service Management
- **Create services** with custom configurations
- **Scale services** up or down
- **Restart services** for updates or troubleshooting
- **Remove services** when no longer needed
- **Monitor health** and resource usage

### Node Management
- View all nodes in the cluster
- Monitor node roles (manager/worker)
- Check node availability and status
- View resource allocation

## API Endpoints

The application provides REST API endpoints for programmatic access:

- `GET /api/services/` - List all services
- `GET /api/nodes/` - List all nodes
- `GET /api/system/` - Get system information
- `POST /api/services/create/` - Create a new service
- `POST /services/<id>/restart/` - Restart a service
- `POST /services/<id>/scale/` - Scale a service
- `POST /services/<id>/remove/` - Remove a service

## Production Deployment

### Using systemd service

The setup script creates a systemd service for production deployment:

```bash
# Start the service
sudo systemctl start swarm-manager

# Enable automatic startup
sudo systemctl enable swarm-manager

# Check status
sudo systemctl status swarm-manager

# View logs
sudo journalctl -u swarm-manager -f
```

### Using Docker

You can also run the application in a Docker container:

```bash
# Build the image
docker build -t swarm-manager .

# Run the container
docker run -d \
  --name swarm-manager \
  -p 8000:8000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e REDIS_URL=redis://host.docker.internal:6379/0 \
  swarm-manager
```

### Reverse Proxy Setup

For production, use a reverse proxy like Nginx:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

## Security Considerations

- **Change default secret key** in production
- **Use HTTPS** in production environments
- **Restrict network access** to the management interface
- **Keep Docker and system packages updated**
- **Use proper authentication** for multi-user environments
- **Monitor logs** for suspicious activity

## Troubleshooting

### Common Issues

1. **Docker connection errors:**
   ```bash
   # Check Docker is running
   sudo systemctl status docker
   
   # Check user permissions
   groups $USER  # Should include 'docker'
   ```

2. **Redis connection errors:**
   ```bash
   # Check Redis is running
   sudo systemctl status redis-server
   
   # Test Redis connection
   redis-cli ping
   ```

3. **WebSocket connection issues:**
   - Ensure Redis is running
   - Check firewall settings
   - Verify proxy configuration for WebSocket support

4. **Permission denied errors:**
   ```bash
   # Fix file permissions
   sudo chown -R $USER:$USER /path/to/project
   
   # Add user to docker group
   sudo usermod -aG docker $USER
   ```

### Logs

Check application logs:

```bash
# Systemd service logs
sudo journalctl -u swarm-manager -f

# Django logs (when running manually)
python manage.py runserver --verbosity=2

# Docker logs
docker logs <container-name>
```

## Development

### Setting up development environment

1. **Clone the repository**
2. **Install dependencies** (see Manual Installation)
3. **Run in development mode:**
   ```bash
   source venv/bin/activate
   export DEBUG=True
   python manage.py runserver
   ```

### Running tests

```bash
python manage.py test
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:

- Check the troubleshooting section
- Review the logs for error messages
- Create an issue on the project repository

## Changelog

### v1.0.0
- Initial release
- Basic Docker Swarm management functionality
- Real-time monitoring with WebSockets
- Bootstrap 5 UI
- Service and node management
- API endpoints
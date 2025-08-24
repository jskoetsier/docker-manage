# Docker Swarm Manager

A comprehensive web-based management interface for Docker Swarm clusters built with Django and Bootstrap 5.

## Features

### 🔍 **Monitoring & Management**
- **Real-time cluster monitoring** with live status updates
- **Service lifecycle management** - Create, deploy, scale, restart, and remove services
- **Node monitoring** - View cluster topology, roles, and resource allocation
- **Health monitoring** - Track container health and service status
- **Resource tracking** - Monitor CPU, memory, and storage usage

### 🚀 **Import & Deployment**
- **Docker Compose import** - Import services directly from Git repositories
- **GitHub/GitLab integration** - Clone and deploy from popular Git platforms
- **Service validation** - Preview and validate services before deployment
- **Batch deployment** - Deploy multiple services at once
- **Popular examples** - Pre-configured templates for common applications

### 🔐 **Security & Access Control**
- **Role-based authentication** - Admin, Manager, and Viewer roles
- **User management** - Create, modify, and deactivate user accounts
- **API key authentication** - Secure API access for automation
- **Audit logging** - Track all user actions and system changes
- **Session management** - Monitor and control active user sessions

### 🌐 **Modern Interface**
- **Bootstrap 5 UI** - Modern, responsive design for all devices
- **Real-time updates** - WebSocket-powered live data refresh
- **Interactive dashboards** - Comprehensive system overview
- **Mobile-optimized** - Full functionality on tablets and phones
- **Dark mode support** - Eye-friendly interface options

### ⚙️ **Administration**
- **Settings dashboard** - Centralized system configuration
- **Version management** - Built-in version tracking with Git integration
- **System maintenance** - Database cleanup and service management tools
- **Export capabilities** - Download audit logs and system data
- **Health monitoring** - System uptime and performance metrics

## Testing Status

✅ **Successfully tested and deployed on production server**
- **Platform**: Ubuntu 24.04.3 LTS
- **Cluster**: 4-node Docker Swarm (1 manager + 3 workers)
- **Resources**: 36 CPUs, 56GB RAM total
- **All Features**: Service creation, scaling, restart, removal - fully functional
- **API Endpoints**: All REST APIs working correctly
- **Web Interface**: Accessible and responsive
- **Git Integration**: Docker Compose import from repositories working

## Screenshots

*Screenshots will be added in future updates*

## Requirements

### System Requirements
- **Operating System**: Ubuntu 24.04 LTS (recommended), Ubuntu 22.04 LTS, Ubuntu 20.04 LTS
- **Python**: 3.8 or higher (tested with Python 3.11)
- **Docker**: Engine 20.10 or higher with Swarm mode enabled
- **Redis**: 6.0 or higher for WebSocket and session management
- **Git**: Required for Docker Compose import functionality
- **Hardware**: Minimum 1GB RAM, 2GB disk space (4GB+ recommended)
- **Network**: Internet access for Docker image pulls and Git repository access

### Python Dependencies
All Python dependencies are listed in `requirements.txt` and will be installed automatically during setup.

## Quick Start

### Automated Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/jskoetsier/docker-manage.git
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
   sudo apt-get install -y python3 python3-pip python3-venv redis-server git
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
- **Create services** with custom configurations or import from Git repositories
- **Scale services** up or down
- **Restart services** for updates or troubleshooting
- **Remove services** when no longer needed
- **Monitor health** and resource usage

### Docker Compose Import
- **Import from Git** - Clone repositories and deploy compose services
- **Service validation** - Preview services with compatibility warnings
- **Selective deployment** - Choose which services to deploy
- **Popular templates** - Quick access to common application stacks

### Node Management
- View all nodes in the cluster
- Monitor node roles (manager/worker)
- Check node availability and status
- View resource allocation

### User Management (Admin)
- **Create and manage users** with role-based permissions
- **API key management** for automation
- **Audit logging** to track all system activities
- **Session management** for security monitoring

## API Endpoints

The application provides REST API endpoints for programmatic access:

- `GET /api/services/` - List all services
- `GET /api/nodes/` - List all nodes
- `GET /api/system/` - Get system information
- `POST /api/services/create/` - Create a new service
- `POST /services/<id>/restart/` - Restart a service
- `POST /services/<id>/scale/` - Scale a service
- `POST /services/<id>/remove/` - Remove a service

### API Authentication
Use API keys for programmatic access. Include the key in the request header:
```bash
curl -H "X-API-Key: your_api_key_here" http://localhost:8000/api/services/
```

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
- **Regular security audits** of user access and API keys

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

3. **Git not found errors:**
   ```bash
   # Install Git
   sudo apt-get install git

   # Verify installation
   git --version
   ```

4. **WebSocket connection issues:**
   - Ensure Redis is running
   - Check firewall settings
   - Verify proxy configuration for WebSocket support

5. **Permission denied errors:**
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

### Testing Docker Compose Import

```bash
# Test with management command
python manage.py test_compose_import https://github.com/docker/awesome-compose --path wordpress-mysql/compose.yaml
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Documentation

This project includes comprehensive documentation:

- **[CHANGELOG.md](CHANGELOG.md)** - Detailed version history and changes
- **[ROADMAP.md](ROADMAP.md)** - Future features and development plans
- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Technical overview and architecture

## Version History

See [CHANGELOG.md](CHANGELOG.md) for detailed version information.

**Current Version: v1.2.0** - Complete Docker Swarm management with version control and Git-based compose import

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:

- Check the troubleshooting section
- Review the logs for error messages
- Create an issue on the project repository

## Changelog

### v1.2.0 - Current Release
- Version management with Git integration
- Docker Compose import from repositories
- Enhanced authentication and user management
- Admin settings dashboard
- Production-tested deployment

### v1.1.0-beta
- Authentication & authorization system
- Role-based access control
- User management interface
- API key authentication

### v1.0.0
- Initial release
- Basic Docker Swarm management functionality
- Real-time monitoring with WebSockets
- Bootstrap 5 UI
- Service and node management
- API endpoints

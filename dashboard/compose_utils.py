"""
Docker Compose import and conversion utilities
"""

import logging
import os
import shutil
import subprocess
import tempfile
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import yaml
from django.conf import settings

logger = logging.getLogger(__name__)


class ComposeImporter:
    """Import and convert Docker Compose files from Git repositories"""

    def __init__(self):
        self.temp_dir = None

    def __enter__(self):
        self.temp_dir = tempfile.mkdtemp()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def clone_repository(self, repo_url: str, branch: str = "main") -> str:
        """Clone a Git repository to temporary directory"""
        try:
            if not self.temp_dir:
                raise ValueError("ComposeImporter must be used as context manager")

            # Check if git is available
            try:
                subprocess.run(["git", "--version"], capture_output=True, timeout=5)
            except (FileNotFoundError, subprocess.TimeoutExpired):
                raise RuntimeError(
                    "Git is not installed or not available in PATH. Please install Git to use compose import functionality."
                )

            repo_dir = os.path.join(self.temp_dir, "repo")

            # Try common branch names if the specified one fails
            branches_to_try = [branch]
            if branch not in ["main", "master"]:
                branches_to_try.extend(["main", "master"])
            else:
                branches_to_try.extend(["master", "main"])

            # Remove duplicates while preserving order
            branches_to_try = list(dict.fromkeys(branches_to_try))

            last_error = None
            for branch_name in branches_to_try:
                try:
                    cmd = [
                        "git",
                        "clone",
                        "--depth",
                        "1",
                        "-b",
                        branch_name,
                        repo_url,
                        repo_dir,
                    ]
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=60
                    )

                    if result.returncode == 0:
                        logger.info(
                            f"Successfully cloned repository {repo_url} (branch: {branch_name})"
                        )
                        return repo_dir

                    last_error = result.stderr

                    # Clean up failed attempt
                    if os.path.exists(repo_dir):
                        shutil.rmtree(repo_dir)

                except subprocess.TimeoutExpired:
                    if os.path.exists(repo_dir):
                        shutil.rmtree(repo_dir)
                    raise RuntimeError("Repository clone timed out")

            # If all branches failed, try without specifying branch
            try:
                cmd = ["git", "clone", "--depth", "1", repo_url, repo_dir]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

                if result.returncode == 0:
                    logger.info(
                        f"Successfully cloned repository {repo_url} (default branch)"
                    )
                    return repo_dir

                last_error = result.stderr
            except subprocess.TimeoutExpired:
                raise RuntimeError("Repository clone timed out")

            raise RuntimeError(
                f"Failed to clone repository after trying multiple branches. Last error: {last_error}"
            )

        except Exception as e:
            logger.error(f"Error cloning repository {repo_url}: {e}")
            raise

    def find_compose_files(self, directory: str) -> List[str]:
        """Find Docker Compose files in a directory"""
        compose_files = []

        # Common compose file names
        compose_names = [
            "docker-compose.yml",
            "docker-compose.yaml",
            "compose.yml",
            "compose.yaml",
            "docker-compose.override.yml",
            "docker-compose.override.yaml",
        ]

        for root, dirs, files in os.walk(directory):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith(".")]

            for filename in files:
                if filename in compose_names:
                    compose_files.append(os.path.join(root, filename))

        logger.info(f"Found {len(compose_files)} compose files")
        return sorted(compose_files)

    def parse_compose_file(self, file_path: str) -> Dict:
        """Parse a Docker Compose file"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)

            if not isinstance(content, dict):
                raise ValueError("Invalid compose file format")

            # Ensure we have services section
            if "services" not in content:
                raise ValueError("No services found in compose file")

            logger.info(
                f"Parsed compose file with {len(content.get('services', {}))} services"
            )
            return content

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format: {e}")
        except Exception as e:
            logger.error(f"Error parsing compose file {file_path}: {e}")
            raise

    def convert_compose_to_swarm_services(self, compose_data: Dict) -> List[Dict]:
        """Convert Docker Compose services to Swarm service configurations"""
        swarm_services = []

        services = compose_data.get("services", {})
        networks = compose_data.get("networks", {})
        volumes = compose_data.get("volumes", {})

        for service_name, service_config in services.items():
            try:
                swarm_service = self._convert_single_service(
                    service_name, service_config, networks, volumes
                )
                swarm_services.append(swarm_service)
            except Exception as e:
                logger.error(f"Error converting service {service_name}: {e}")
                # Continue with other services
                continue

        logger.info(f"Converted {len(swarm_services)} services for Swarm deployment")
        return swarm_services

    def _convert_single_service(
        self, name: str, config: Dict, networks: Dict, volumes: Dict
    ) -> Dict:
        """Convert a single compose service to Swarm service config"""
        service = {
            "name": name,
            "image": config.get("image"),
            "replicas": config.get("deploy", {}).get("replicas", 1),
            "environment": {},
            "ports": [],
            "volumes": [],
            "networks": [],
            "labels": config.get("labels", {}),
            "restart_policy": "any",
            "constraints": [],
            "resources": {},
        }

        # Handle image
        if not service["image"]:
            if "build" in config:
                # For build contexts, we'll need to specify the image name
                service["image"] = f"{name}:latest"
                service["build_context"] = config["build"]
            else:
                raise ValueError(f"Service {name} has no image or build context")

        # Handle environment variables
        env_config = config.get("environment", [])
        if isinstance(env_config, list):
            for env_var in env_config:
                if "=" in env_var:
                    key, value = env_var.split("=", 1)
                    service["environment"][key] = value
        elif isinstance(env_config, dict):
            service["environment"] = env_config

        # Handle ports
        ports_config = config.get("ports", [])
        for port in ports_config:
            if isinstance(port, str):
                # Format: "host:container" or "container"
                if ":" in port:
                    host_port, container_port = port.split(":", 1)
                    if "/" in container_port:
                        container_port, protocol = container_port.split("/", 1)
                    else:
                        protocol = "tcp"
                else:
                    host_port = container_port = port
                    protocol = "tcp"

                service["ports"].append(
                    {
                        "published_port": int(host_port),
                        "target_port": int(container_port),
                        "protocol": protocol,
                        "publish_mode": "ingress",
                    }
                )
            elif isinstance(port, dict):
                service["ports"].append(
                    {
                        "published_port": port.get("published"),
                        "target_port": port.get("target"),
                        "protocol": port.get("protocol", "tcp"),
                        "publish_mode": port.get("mode", "ingress"),
                    }
                )

        # Handle volumes
        volumes_config = config.get("volumes", [])
        for volume in volumes_config:
            if isinstance(volume, str):
                if ":" in volume:
                    source, target = volume.split(":", 1)
                    service["volumes"].append(
                        {
                            "source": source,
                            "target": target,
                            "type": "bind" if source.startswith("/") else "volume",
                        }
                    )

        # Handle networks
        networks_config = config.get("networks", [])
        if isinstance(networks_config, list):
            service["networks"] = networks_config
        elif isinstance(networks_config, dict):
            service["networks"] = list(networks_config.keys())

        # Handle deploy configuration
        deploy_config = config.get("deploy", {})

        # Replicas
        service["replicas"] = deploy_config.get("replicas", 1)

        # Restart policy
        restart_policy = deploy_config.get("restart_policy", {})
        if restart_policy:
            service["restart_policy"] = restart_policy.get("condition", "any")

        # Resource constraints
        resources = deploy_config.get("resources", {})
        if resources:
            service["resources"] = {
                "cpu_limit": resources.get("limits", {}).get("cpus"),
                "memory_limit": resources.get("limits", {}).get("memory"),
                "cpu_reservation": resources.get("reservations", {}).get("cpus"),
                "memory_reservation": resources.get("reservations", {}).get("memory"),
            }

        # Placement constraints
        placement = deploy_config.get("placement", {})
        if placement and "constraints" in placement:
            service["constraints"] = placement["constraints"]

        return service

    def import_from_git(
        self, repo_url: str, branch: str = "main", compose_file_path: str = None
    ) -> Tuple[List[Dict], Dict]:
        """
        Import Docker Compose services from a Git repository

        Returns:
            Tuple of (services_list, metadata)
        """
        repo_dir = self.clone_repository(repo_url, branch)

        # Find compose files
        if compose_file_path:
            compose_files = [os.path.join(repo_dir, compose_file_path)]
            if not os.path.exists(compose_files[0]):
                raise FileNotFoundError(f"Compose file not found: {compose_file_path}")
        else:
            compose_files = self.find_compose_files(repo_dir)
            if not compose_files:
                raise FileNotFoundError("No Docker Compose files found in repository")

        all_services = []
        metadata = {
            "repository_url": repo_url,
            "branch": branch,
            "compose_files": [],
            "total_services": 0,
            "networks": set(),
            "volumes": set(),
        }

        for compose_file in compose_files:
            try:
                compose_data = self.parse_compose_file(compose_file)
                services = self.convert_compose_to_swarm_services(compose_data)

                # Update metadata
                metadata["compose_files"].append(
                    {
                        "path": os.path.relpath(compose_file, repo_dir),
                        "services_count": len(services),
                    }
                )

                # Collect networks and volumes
                metadata["networks"].update(compose_data.get("networks", {}).keys())
                metadata["volumes"].update(compose_data.get("volumes", {}).keys())

                all_services.extend(services)

            except Exception as e:
                logger.error(f"Error processing compose file {compose_file}: {e}")
                continue

        metadata["total_services"] = len(all_services)
        metadata["networks"] = list(metadata["networks"])
        metadata["volumes"] = list(metadata["volumes"])

        return all_services, metadata

    def validate_service_for_swarm(self, service: Dict) -> List[str]:
        """Validate a service configuration for Swarm deployment"""
        warnings = []

        # Check required fields
        if not service.get("name"):
            warnings.append("Service name is required")

        if not service.get("image"):
            warnings.append("Docker image is required")

        # Check for unsupported features
        if service.get("build_context"):
            warnings.append(
                "Build contexts are not supported in Swarm mode. Pre-built images are required."
            )

        if service.get("depends_on"):
            warnings.append(
                "depends_on is not directly supported in Swarm mode. Consider using healthchecks."
            )

        # Check resource limits format
        resources = service.get("resources", {})
        if resources.get("memory_limit"):
            memory = resources["memory_limit"]
            if isinstance(memory, str) and not any(
                unit in memory.lower() for unit in ["k", "m", "g"]
            ):
                warnings.append(
                    "Memory limit should include units (e.g., '512m', '1g')"
                )

        return warnings


def get_popular_compose_repositories():
    """Get a list of popular Docker Compose repositories for examples"""
    return [
        {
            "name": "WordPress with MySQL",
            "url": "https://github.com/docker/awesome-compose",
            "path": "wordpress-mysql/compose.yaml",
            "description": "WordPress with MySQL database",
        },
        {
            "name": "NGINX + PHP + MySQL",
            "url": "https://github.com/docker/awesome-compose",
            "path": "nginx-php-mysql/compose.yaml",
            "description": "LEMP stack with NGINX, PHP-FPM and MySQL",
        },
        {
            "name": "Nextcloud with Redis",
            "url": "https://github.com/docker/awesome-compose",
            "path": "nextcloud-redis-mariadb/compose.yaml",
            "description": "Nextcloud with Redis and MariaDB",
        },
        {
            "name": "GitLab CE",
            "url": "https://github.com/sameersbn/docker-gitlab",
            "path": "docker-compose.yml",
            "description": "GitLab Community Edition (comprehensive setup)",
        },
        {
            "name": "Prometheus + Grafana",
            "url": "https://github.com/docker/awesome-compose",
            "path": "prometheus-grafana/compose.yaml",
            "description": "Monitoring stack with Prometheus and Grafana",
        },
        {
            "name": "PostgreSQL + Adminer",
            "url": "https://github.com/docker/awesome-compose",
            "path": "postgresql-pgadmin/compose.yaml",
            "description": "PostgreSQL database with pgAdmin web interface",
        },
        {
            "name": "Simple Web App",
            "url": "https://github.com/docker/awesome-compose",
            "path": "nginx-wsgi-flask/docker-compose.yml",
            "description": "Simple Flask web application with NGINX",
        },
    ]

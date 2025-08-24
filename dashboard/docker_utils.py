"""
Docker Swarm management utilities
"""

import logging
from typing import Dict, List, Optional

import docker
from django.conf import settings

logger = logging.getLogger(__name__)


class DockerSwarmManager:
    def __init__(self):
        try:
            # Try to connect to Docker without TLS first
            try:
                self.client = docker.DockerClient(base_url='unix://var/run/docker.sock')
                self.client.ping()
                logger.info("Docker client connected successfully via Unix socket")
            except Exception:
                # Fallback to from_env for other configurations
                self.client = docker.from_env()
                self.client.ping()
                logger.info("Docker client connected successfully via environment")
        except Exception as e:
            logger.error(f"Failed to connect to Docker: {e}")
            self.client = None

    def is_swarm_active(self) -> bool:
        """Check if Docker Swarm mode is active"""
        try:
            if not self.client:
                return False
            swarm_info = self.client.info().get("Swarm", {})
            return swarm_info.get("LocalNodeState") == "active"
        except Exception as e:
            logger.error(f"Error checking swarm status: {e}")
            return False

    def get_swarm_info(self) -> Dict:
        """Get detailed swarm information"""
        try:
            if not self.client or not self.is_swarm_active():
                return {}

            info = self.client.info()
            swarm_info = info.get("Swarm", {})

            return {
                "node_id": swarm_info.get("NodeID"),
                "node_addr": swarm_info.get("NodeAddr"),
                "local_node_state": swarm_info.get("LocalNodeState"),
                "control_available": swarm_info.get("ControlAvailable"),
                "managers": swarm_info.get("Managers"),
                "nodes": swarm_info.get("Nodes"),
                "cluster_id": swarm_info.get("Cluster", {}).get("ID"),
                "version": swarm_info.get("Cluster", {})
                .get("Version", {})
                .get("Index"),
            }
        except Exception as e:
            logger.error(f"Error getting swarm info: {e}")
            return {}

    def get_nodes(self) -> List[Dict]:
        """Get all nodes in the swarm"""
        try:
            if not self.client or not self.is_swarm_active():
                return []

            nodes = []
            for node in self.client.nodes.list():
                node_info = {
                    "id": node.id,
                    "hostname": node.attrs["Description"]["Hostname"],
                    "status": node.attrs["Status"]["State"],
                    "availability": node.attrs["Spec"]["Availability"],
                    "role": node.attrs["Spec"]["Role"],
                    "engine_version": node.attrs["Description"]["Engine"][
                        "EngineVersion"
                    ],
                    "platform": node.attrs["Description"]["Platform"]["OS"],
                    "architecture": node.attrs["Description"]["Platform"][
                        "Architecture"
                    ],
                    "resources": {
                        "cpu": node.attrs["Description"]["Resources"]["NanoCPUs"]
                        / 1000000000,
                        "memory": node.attrs["Description"]["Resources"]["MemoryBytes"]
                        / (1024**3),
                    },
                    "leader": node.attrs.get("ManagerStatus", {}).get("Leader", False),
                    "manager_addr": node.attrs.get("ManagerStatus", {}).get("Addr"),
                }
                nodes.append(node_info)
            return nodes
        except Exception as e:
            logger.error(f"Error getting nodes: {e}")
            return []

    def get_services(self) -> List[Dict]:
        """Get all services in the swarm"""
        try:
            if not self.client or not self.is_swarm_active():
                return []

            services = []
            for service in self.client.services.list():
                service_info = {
                    "id": service.id,
                    "name": service.name,
                    "image": service.attrs["Spec"]["TaskTemplate"]["ContainerSpec"][
                        "Image"
                    ],
                    "replicas": service.attrs["Spec"].get("Replicas", 0),
                    "mode": (
                        "replicated"
                        if "Replicas" in service.attrs["Spec"]
                        else "global"
                    ),
                    "created": service.attrs["CreatedAt"],
                    "updated": service.attrs["UpdatedAt"],
                    "ports": self._extract_ports(
                        service.attrs["Spec"].get("EndpointSpec", {})
                    ),
                    "networks": [
                        net["Target"]
                        for net in service.attrs["Spec"]["TaskTemplate"].get(
                            "Networks", []
                        )
                    ],
                    "labels": service.attrs["Spec"].get("Labels", {}),
                }

                # Get task information
                tasks = service.tasks()
                running_tasks = sum(
                    1 for task in tasks if task["Status"]["State"] == "running"
                )
                service_info["running_tasks"] = running_tasks
                service_info["total_tasks"] = len(tasks)

                services.append(service_info)
            return services
        except Exception as e:
            logger.error(f"Error getting services: {e}")
            return []

    def get_service_details(self, service_id: str) -> Optional[Dict]:
        """Get detailed information about a specific service"""
        try:
            if not self.client:
                return None

            service = self.client.services.get(service_id)
            tasks = service.tasks()

            return {"service": service.attrs, "tasks": [task for task in tasks]}
        except Exception as e:
            logger.error(f"Error getting service details: {e}")
            return None

    def restart_service(self, service_id: str) -> bool:
        """Restart a service"""
        try:
            if not self.client:
                return False

            service = self.client.services.get(service_id)
            service.force_update()
            logger.info(f"Service {service_id} restarted successfully")
            return True
        except Exception as e:
            logger.error(f"Error restarting service {service_id}: {e}")
            return False

    def scale_service(self, service_id: str, replicas: int) -> bool:
        """Scale a service to specified number of replicas"""
        try:
            if not self.client:
                return False

            service = self.client.services.get(service_id)
            service.scale(replicas)
            logger.info(f"Service {service_id} scaled to {replicas} replicas")
            return True
        except Exception as e:
            logger.error(f"Error scaling service {service_id}: {e}")
            return False

    def remove_service(self, service_id: str) -> bool:
        """Remove a service"""
        try:
            if not self.client:
                return False

            service = self.client.services.get(service_id)
            service.remove()
            logger.info(f"Service {service_id} removed successfully")
            return True
        except Exception as e:
            logger.error(f"Error removing service {service_id}: {e}")
            return False

    def create_service(
        self, image: str, name: str, replicas: int = 1, **kwargs
    ) -> bool:
        """Create a new service"""
        try:
            if not self.client or not self.is_swarm_active():
                return False

            self.client.services.create(
                image=image, name=name, replicas=replicas, **kwargs
            )
            logger.info(f"Service {name} created successfully")
            return True
        except Exception as e:
            logger.error(f"Error creating service {name}: {e}")
            return False

    def get_system_info(self) -> Dict:
        """Get system information"""
        try:
            if not self.client:
                return {}

            info = self.client.info()
            return {
                "containers": info.get("Containers", 0),
                "containers_running": info.get("ContainersRunning", 0),
                "containers_paused": info.get("ContainersPaused", 0),
                "containers_stopped": info.get("ContainersStopped", 0),
                "images": info.get("Images", 0),
                "server_version": info.get("ServerVersion"),
                "kernel_version": info.get("KernelVersion"),
                "operating_system": info.get("OperatingSystem"),
                "architecture": info.get("Architecture"),
                "cpus": info.get("NCPU", 0),
                "memory": info.get("MemTotal", 0),
            }
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return {}

    def _extract_ports(self, endpoint_spec: Dict) -> List[Dict]:
        """Extract port information from service endpoint spec"""
        ports = []
        for port in endpoint_spec.get("Ports", []):
            ports.append(
                {
                    "target_port": port.get("TargetPort"),
                    "published_port": port.get("PublishedPort"),
                    "protocol": port.get("Protocol"),
                    "publish_mode": port.get("PublishMode"),
                }
            )
        return ports

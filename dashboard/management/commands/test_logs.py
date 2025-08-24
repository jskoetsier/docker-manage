"""
Django management command to test Docker logging functionality
"""

from dashboard.docker_utils import DockerSwarmManager
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Test Docker logging functionality"

    def add_arguments(self, parser):
        parser.add_argument("--service", type=str, help="Service name or ID to test")
        parser.add_argument("--container", type=str, help="Container ID to test")

    def handle(self, *args, **options):
        docker_manager = DockerSwarmManager()

        if options.get("service"):
            service_name = options["service"]
            self.stdout.write(f"Testing service logs for: {service_name}")

            # Try to find service by name or ID
            try:
                if docker_manager.client:
                    services = docker_manager.client.services.list()
                    service = None

                    for s in services:
                        if s.name == service_name or s.id.startswith(service_name):
                            service = s
                            break

                    if service:
                        self.stdout.write(
                            f"Found service: {service.name} (ID: {service.id})"
                        )

                        # Test logs
                        logs_data = docker_manager.get_service_logs(
                            service.id, lines=10
                        )

                        self.stdout.write(
                            f"Logs result: {len(logs_data.get('logs', []))} lines"
                        )
                        if logs_data.get("error"):
                            self.stdout.write(
                                self.style.ERROR(f"Error: {logs_data['error']}")
                            )
                        elif logs_data.get("logs"):
                            self.stdout.write("Sample logs:")
                            for i, log in enumerate(logs_data["logs"][:3]):
                                self.stdout.write(f"  {i+1}: {log[:100]}...")
                    else:
                        self.stdout.write(
                            self.style.ERROR(f"Service '{service_name}' not found")
                        )
                        self.stdout.write("Available services:")
                        for s in services:
                            self.stdout.write(f"  - {s.name} ({s.id})")
                else:
                    self.stdout.write(self.style.ERROR("Docker client not available"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error: {e}"))

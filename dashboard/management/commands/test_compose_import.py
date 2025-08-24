"""
Django management command to test Docker Compose import functionality
"""
from django.core.management.base import BaseCommand
from dashboard.compose_utils import ComposeImporter


class Command(BaseCommand):
    help = 'Test Docker Compose import functionality'

    def add_arguments(self, parser):
        parser.add_argument('repo_url', type=str, help='Git repository URL')
        parser.add_argument('--branch', type=str, default='main', help='Git branch (default: main)')
        parser.add_argument('--path', type=str, help='Path to compose file within repository')

    def handle(self, *args, **options):
        repo_url = options['repo_url']
        branch = options['branch']
        compose_path = options.get('path')

        self.stdout.write(f"Testing import from: {repo_url}")
        self.stdout.write(f"Branch: {branch}")
        if compose_path:
            self.stdout.write(f"Compose file path: {compose_path}")

        try:
            with ComposeImporter() as importer:
                self.stdout.write("🔄 Cloning repository...")
                services, metadata = importer.import_from_git(repo_url, branch, compose_path)

                self.stdout.write(self.style.SUCCESS("✅ Import successful!"))
                self.stdout.write(f"Found {len(services)} services:")

                for service in services:
                    self.stdout.write(f"  - {service['name']}: {service['image']} ({service['replicas']} replicas)")

                    if service.get('warnings'):
                        for warning in service['warnings']:
                            self.stdout.write(f"    ⚠️  {warning}")

                self.stdout.write(f"\nMetadata:")
                self.stdout.write(f"  Total services: {metadata['total_services']}")
                self.stdout.write(f"  Compose files: {len(metadata['compose_files'])}")
                self.stdout.write(f"  Networks: {len(metadata['networks'])}")
                self.stdout.write(f"  Volumes: {len(metadata['volumes'])}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Import failed: {e}"))

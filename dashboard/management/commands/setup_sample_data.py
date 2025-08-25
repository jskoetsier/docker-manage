"""
Management command to set up sample metrics data for testing
"""
import logging
import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from dashboard.models import Metric

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate sample metrics data for testing the analytics dashboard'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days of sample data to generate (default: 7)',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=300,  # 5 minutes
            help='Interval between data points in seconds (default: 300)',
        )

    def handle(self, *args, **options):
        days = options['days']
        interval = options['interval']
        
        self.stdout.write(
            self.style.SUCCESS(f'Generating {days} days of sample metrics data...')
        )

        # Clear existing sample data
        Metric.objects.all().delete()
        self.stdout.write('Cleared existing metrics data')

        # Generate time series data
        end_time = timezone.now()
        start_time = end_time - timedelta(days=days)
        current_time = start_time
        
        metrics_created = 0
        
        # Base values for realistic data
        base_cpu = 30.0
        base_memory = 60.0
        base_disk = 45.0
        base_network_sent = 1000000
        base_network_recv = 2000000
        
        while current_time <= end_time:
            # Generate system resource metrics with realistic variations
            cpu_usage = base_cpu + random.uniform(-15, 25)
            cpu_usage = max(0, min(100, cpu_usage))  # Clamp between 0-100
            
            memory_usage = base_memory + random.uniform(-20, 30)
            memory_usage = max(0, min(100, memory_usage))
            
            disk_usage = base_disk + random.uniform(-10, 15)
            disk_usage = max(0, min(100, disk_usage))
            
            network_sent = base_network_sent + random.uniform(-500000, 1500000)
            network_recv = base_network_recv + random.uniform(-800000, 2000000)
            
            # CPU metric
            Metric.objects.create(
                measurement='system_resources',
                tags={'resource': 'cpu'},
                fields={'usage': cpu_usage},
                timestamp=current_time
            )
            
            # Memory metric
            Metric.objects.create(
                measurement='system_resources',
                tags={'resource': 'memory'},
                fields={
                    'usage_percent': memory_usage,
                    'usage_bytes': int(memory_usage * 8589934592 / 100),  # 8GB total
                    'total_bytes': 8589934592
                },
                timestamp=current_time
            )
            
            # Disk metric
            Metric.objects.create(
                measurement='system_resources',
                tags={'resource': 'disk'},
                fields={
                    'usage_percent': disk_usage,
                    'usage_bytes': int(disk_usage * 107374182400 / 100),  # 100GB total
                    'total_bytes': 107374182400
                },
                timestamp=current_time
            )
            
            # Network metric
            Metric.objects.create(
                measurement='system_resources',
                tags={'resource': 'network'},
                fields={
                    'bytes_sent': int(network_sent),
                    'bytes_recv': int(network_recv),
                    'packets_sent': int(network_sent / 1000),
                    'packets_recv': int(network_recv / 1000)
                },
                timestamp=current_time
            )
            
            # Generate service replica metrics (sample services)
            service_names = ['web-app', 'database', 'cache', 'api-server', 'worker']
            for i, service_name in enumerate(service_names):
                service_id = f"service_{i+1}"
                desired_replicas = random.choice([2, 3, 4, 5])
                running_replicas = desired_replicas
                
                # Occasionally simulate service issues
                if random.random() < 0.05:  # 5% chance of issues
                    running_replicas = max(0, desired_replicas - random.randint(1, 2))
                
                Metric.objects.create(
                    measurement='service_replicas',
                    tags={
                        'service_id': service_id,
                        'service_name': service_name
                    },
                    fields={
                        'replicas_running': running_replicas,
                        'replicas_desired': desired_replicas
                    },
                    timestamp=current_time
                )
                
                # Service health metrics
                health_score = running_replicas / desired_replicas if desired_replicas > 0 else 0
                is_healthy = running_replicas == desired_replicas
                
                Metric.objects.create(
                    measurement='service_health',
                    tags={
                        'service_id': service_id,
                        'service_name': service_name
                    },
                    fields={
                        'health_score': health_score,
                        'is_healthy': 1 if is_healthy else 0,
                        'replicas_ratio': health_score
                    },
                    timestamp=current_time
                )
            
            # Generate node resource metrics (sample nodes)
            node_names = ['manager-1', 'worker-1', 'worker-2']
            for i, node_name in enumerate(node_names):
                node_id = f"node_{i+1}"
                
                Metric.objects.create(
                    measurement='node_resources',
                    tags={
                        'node_id': node_id,
                        'node_hostname': node_name
                    },
                    fields={
                        'cpu_cores': 4.0,
                        'memory_bytes': 8589934592  # 8GB
                    },
                    timestamp=current_time
                )
                
                # Node status metrics
                is_available = random.random() > 0.02  # 98% uptime
                is_ready = is_available and random.random() > 0.01  # 99% ready when available
                
                Metric.objects.create(
                    measurement='node_status',
                    tags={
                        'node_id': node_id,
                        'node_hostname': node_name
                    },
                    fields={
                        'is_available': 1 if is_available else 0,
                        'is_ready': 1 if is_ready else 0,
                        'availability': 'active' if is_available else 'drain',
                        'state': 'ready' if is_ready else 'down'
                    },
                    timestamp=current_time
                )
            
            metrics_created += 4 + (len(service_names) * 2) + (len(node_names) * 2)  # Count all metrics
            current_time += timedelta(seconds=interval)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Generated {metrics_created} sample metrics over {days} days '
                f'with {interval}s intervals'
            )
        )
        
        # Show some statistics
        total_metrics = Metric.objects.count()
        measurements = Metric.objects.values('measurement').distinct().count()
        
        self.stdout.write(f'Total metrics in database: {total_metrics}')
        self.stdout.write(f'Different measurements: {measurements}')
        
        # Show measurement breakdown
        for measurement in Metric.objects.values_list('measurement', flat=True).distinct():
            count = Metric.objects.filter(measurement=measurement).count()
            self.stdout.write(f'  {measurement}: {count} metrics')
        
        self.stdout.write(
            self.style.SUCCESS('Sample data generation completed!')
        )
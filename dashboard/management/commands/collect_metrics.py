"""
Management command to collect and store Docker Swarm metrics
"""
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from dashboard.metrics import MetricsCollector

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Collect and store Docker Swarm metrics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--continuous',
            action='store_true',
            help='Run continuously collecting metrics every 30 seconds',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=30,
            help='Collection interval in seconds (default: 30)',
        )
        parser.add_argument(
            '--measurements',
            nargs='+',
            default=['system_resources', 'service_replicas', 'service_health', 'node_resources', 'node_status'],
            help='Measurements to collect (default: all)',
        )

    def handle(self, *args, **options):
        collector = MetricsCollector()
        measurements = options['measurements']
        interval = options['interval']
        continuous = options['continuous']

        self.stdout.write(
            self.style.SUCCESS(f'Starting metrics collection for: {", ".join(measurements)}')
        )

        if continuous:
            self.stdout.write(f'Running continuously with {interval}s interval. Press Ctrl+C to stop.')
            try:
                import time
                while True:
                    self.collect_all_metrics(collector, measurements)
                    time.sleep(interval)
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING('\nStopping metrics collection...'))
        else:
            self.collect_all_metrics(collector, measurements)

        self.stdout.write(self.style.SUCCESS('Metrics collection completed'))

    def collect_all_metrics(self, collector, measurements):
        """Collect all specified measurements"""
        start_time = timezone.now()
        self.stdout.write(f'[{start_time.strftime("%Y-%m-%d %H:%M:%S")}] Collecting metrics...')

        metrics_collected = 0

        for measurement in measurements:
            try:
                if measurement == 'system_resources':
                    count = self.collect_system_resources(collector)
                elif measurement == 'service_replicas':
                    count = self.collect_service_replicas(collector)
                elif measurement == 'service_health':
                    count = self.collect_service_health(collector)
                elif measurement == 'node_resources':
                    count = self.collect_node_resources(collector)
                elif measurement == 'node_status':
                    count = self.collect_node_status(collector)
                else:
                    self.stdout.write(
                        self.style.WARNING(f'Unknown measurement: {measurement}')
                    )
                    continue

                metrics_collected += count
                self.stdout.write(f'  ✓ {measurement}: {count} metrics')

            except Exception as e:
                logger.error(f'Error collecting {measurement}: {e}')
                self.stdout.write(
                    self.style.ERROR(f'  ✗ {measurement}: Error - {e}')
                )

        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        self.stdout.write(
            f'Collected {metrics_collected} total metrics in {duration:.2f}s'
        )

    def collect_system_resources(self, collector):
        """Collect system resource metrics"""
        try:
            # Get system stats using psutil
            import psutil
            
            timestamp = timezone.now()
            metrics_count = 0

            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            collector.store_metric('system_resources', {'resource': 'cpu'}, {'usage': cpu_percent}, timestamp)
            metrics_count += 1

            # Memory usage
            memory = psutil.virtual_memory()
            collector.store_metric('system_resources', {'resource': 'memory'}, {
                'usage_bytes': memory.used,
                'total_bytes': memory.total,
                'usage_percent': memory.percent
            }, timestamp)
            metrics_count += 1

            # Disk usage
            disk = psutil.disk_usage('/')
            collector.store_metric('system_resources', {'resource': 'disk'}, {
                'usage_bytes': disk.used,
                'total_bytes': disk.total,
                'usage_percent': (disk.used / disk.total) * 100
            }, timestamp)
            metrics_count += 1

            # Network I/O
            network = psutil.net_io_counters()
            collector.store_metric('system_resources', {'resource': 'network'}, {
                'bytes_sent': network.bytes_sent,
                'bytes_recv': network.bytes_recv,
                'packets_sent': network.packets_sent,
                'packets_recv': network.packets_recv
            }, timestamp)
            metrics_count += 1

            return metrics_count

        except Exception as e:
            logger.error(f'Error collecting system resources: {e}')
            return 0

    def collect_service_replicas(self, collector):
        """Collect service replica metrics"""
        try:
            services_data = collector.get_services_data()
            timestamp = timezone.now()
            metrics_count = 0

            for service in services_data:
                collector.store_metric('service_replicas', {
                    'service_id': service['ID'],
                    'service_name': service['Spec']['Name']
                }, {
                    'replicas_running': service.get('replicas_running', 0),
                    'replicas_desired': service.get('replicas_desired', 0)
                }, timestamp)
                metrics_count += 1

            return metrics_count

        except Exception as e:
            logger.error(f'Error collecting service replicas: {e}')
            return 0

    def collect_service_health(self, collector):
        """Collect service health metrics"""
        try:
            services_data = collector.get_services_data()
            timestamp = timezone.now()
            metrics_count = 0

            for service in services_data:
                # Simple health check based on replicas
                replicas_running = service.get('replicas_running', 0)
                replicas_desired = service.get('replicas_desired', 0)
                
                health_score = (replicas_running / replicas_desired) if replicas_desired > 0 else 0
                is_healthy = replicas_running == replicas_desired and replicas_desired > 0

                collector.store_metric('service_health', {
                    'service_id': service['ID'],
                    'service_name': service['Spec']['Name']
                }, {
                    'health_score': health_score,
                    'is_healthy': 1 if is_healthy else 0,
                    'replicas_ratio': health_score
                }, timestamp)
                metrics_count += 1

            return metrics_count

        except Exception as e:
            logger.error(f'Error collecting service health: {e}')
            return 0

    def collect_node_resources(self, collector):
        """Collect node resource metrics"""
        try:
            nodes_data = collector.get_nodes_data()
            timestamp = timezone.now()
            metrics_count = 0

            for node in nodes_data:
                # Get resource information from node
                resources = node.get('Description', {}).get('Resources', {})
                
                collector.store_metric('node_resources', {
                    'node_id': node['ID'],
                    'node_hostname': node.get('Description', {}).get('Hostname', 'unknown')
                }, {
                    'cpu_cores': resources.get('NanoCPUs', 0) / 1000000000,  # Convert from nanocores
                    'memory_bytes': resources.get('MemoryBytes', 0)
                }, timestamp)
                metrics_count += 1

            return metrics_count

        except Exception as e:
            logger.error(f'Error collecting node resources: {e}')
            return 0

    def collect_node_status(self, collector):
        """Collect node status metrics"""
        try:
            nodes_data = collector.get_nodes_data()
            timestamp = timezone.now()
            metrics_count = 0

            for node in nodes_data:
                status = node.get('Status', {})
                availability = node.get('Spec', {}).get('Availability', 'unknown')
                
                is_available = availability == 'active'
                is_ready = status.get('State') == 'ready'

                collector.store_metric('node_status', {
                    'node_id': node['ID'],
                    'node_hostname': node.get('Description', {}).get('Hostname', 'unknown')
                }, {
                    'is_available': 1 if is_available else 0,
                    'is_ready': 1 if is_ready else 0,
                    'availability': availability,
                    'state': status.get('State', 'unknown')
                }, timestamp)
                metrics_count += 1

            return metrics_count

        except Exception as e:
            logger.error(f'Error collecting node status: {e}')
            return 0
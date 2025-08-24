"""
Metrics collection and storage for Docker Swarm monitoring
"""
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from django.utils import timezone
from django.conf import settings
from .docker_utils import DockerSwarmManager

logger = logging.getLogger(__name__)

try:
    from influxdb_client import InfluxDBClient, Point, WritePrecision
    from influxdb_client.client.write_api import SYNCHRONOUS
    INFLUXDB_AVAILABLE = True
except ImportError:
    INFLUXDB_AVAILABLE = False

try:
    from prometheus_client import CollectorRegistry, Gauge, Counter, Histogram, push_to_gateway
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


class MetricsCollector:
    """Collect and store Docker Swarm metrics"""
    
    def __init__(self, storage_backend='database'):
        self.docker_manager = DockerSwarmManager()
        self.storage_backend = storage_backend
        
        if storage_backend == 'influxdb' and INFLUXDB_AVAILABLE:
            self._init_influxdb()
        elif storage_backend == 'prometheus' and PROMETHEUS_AVAILABLE:
            self._init_prometheus()
    
    def _init_influxdb(self):
        """Initialize InfluxDB client"""
        try:
            influxdb_url = getattr(settings, 'INFLUXDB_URL', 'http://localhost:8086')
            influxdb_token = getattr(settings, 'INFLUXDB_TOKEN', '')
            influxdb_org = getattr(settings, 'INFLUXDB_ORG', 'docker-swarm')
            influxdb_bucket = getattr(settings, 'INFLUXDB_BUCKET', 'metrics')
            
            self.influxdb_client = InfluxDBClient(
                url=influxdb_url,
                token=influxdb_token,
                org=influxdb_org
            )
            self.influxdb_bucket = influxdb_bucket
            self.influxdb_org = influxdb_org
            
            # Test connection
            self.influxdb_client.ping()
            logger.info("InfluxDB client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize InfluxDB: {e}")
            self.storage_backend = 'database'
    
    def _init_prometheus(self):
        """Initialize Prometheus metrics"""
        try:
            self.prometheus_registry = CollectorRegistry()
            
            # Define metrics
            self.prom_service_replicas = Gauge(
                'swarm_service_replicas_running',
                'Number of running replicas for service',
                ['service_name', 'service_id'],
                registry=self.prometheus_registry
            )
            
            self.prom_service_replicas_desired = Gauge(
                'swarm_service_replicas_desired',
                'Desired number of replicas for service',
                ['service_name', 'service_id'],
                registry=self.prometheus_registry
            )
            
            self.prom_node_cpu = Gauge(
                'swarm_node_cpu_cores',
                'CPU cores available on node',
                ['node_id', 'hostname', 'role'],
                registry=self.prometheus_registry
            )
            
            self.prom_node_memory = Gauge(
                'swarm_node_memory_bytes',
                'Memory available on node',
                ['node_id', 'hostname', 'role'],
                registry=self.prometheus_registry
            )
            
            self.prom_system_containers = Gauge(
                'swarm_system_containers_total',
                'Total containers in system',
                ['state'],
                registry=self.prometheus_registry
            )
            
            logger.info("Prometheus metrics initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Prometheus: {e}")
            self.storage_backend = 'database'
    
    def collect_metrics(self):
        """Collect all metrics and store them"""
        timestamp = timezone.now()
        
        try:
            # Collect system metrics
            system_metrics = self._collect_system_metrics(timestamp)
            
            # Collect service metrics
            service_metrics = self._collect_service_metrics(timestamp)
            
            # Collect node metrics
            node_metrics = self._collect_node_metrics(timestamp)
            
            # Store metrics based on backend
            if self.storage_backend == 'influxdb':
                self._store_to_influxdb(system_metrics + service_metrics + node_metrics)
            elif self.storage_backend == 'prometheus':
                self._store_to_prometheus(system_metrics, service_metrics, node_metrics)
            else:
                self._store_to_database(system_metrics + service_metrics + node_metrics)
            
            logger.info(f"Collected and stored metrics: {len(system_metrics + service_metrics + node_metrics)} points")
            
            return {
                'success': True,
                'metrics_collected': len(system_metrics + service_metrics + node_metrics),
                'timestamp': timestamp
            }
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': timestamp
            }
    
    def _collect_system_metrics(self, timestamp):
        """Collect system-wide metrics"""
        metrics = []
        
        try:
            system_info = self.docker_manager.get_system_info()
            swarm_info = self.docker_manager.get_swarm_info()
            
            # System container metrics
            metrics.extend([
                {
                    'measurement': 'system_containers',
                    'tags': {'state': 'total'},
                    'fields': {'value': system_info.get('containers', 0)},
                    'timestamp': timestamp
                },
                {
                    'measurement': 'system_containers',
                    'tags': {'state': 'running'},
                    'fields': {'value': system_info.get('containers_running', 0)},
                    'timestamp': timestamp
                },
                {
                    'measurement': 'system_containers',
                    'tags': {'state': 'stopped'},
                    'fields': {'value': system_info.get('containers_stopped', 0)},
                    'timestamp': timestamp
                },
                {
                    'measurement': 'system_containers',
                    'tags': {'state': 'paused'},
                    'fields': {'value': system_info.get('containers_paused', 0)},
                    'timestamp': timestamp
                }
            ])
            
            # System resource metrics
            if system_info.get('cpus'):
                metrics.append({
                    'measurement': 'system_resources',
                    'tags': {'resource': 'cpu'},
                    'fields': {'cores': system_info['cpus']},
                    'timestamp': timestamp
                })
            
            if system_info.get('memory'):
                metrics.append({
                    'measurement': 'system_resources',
                    'tags': {'resource': 'memory'},
                    'fields': {'bytes': system_info['memory']},
                    'timestamp': timestamp
                })
            
            # Swarm metrics
            if swarm_info:
                metrics.extend([
                    {
                        'measurement': 'swarm_info',
                        'tags': {'metric': 'nodes'},
                        'fields': {'value': swarm_info.get('nodes', 0)},
                        'timestamp': timestamp
                    },
                    {
                        'measurement': 'swarm_info',
                        'tags': {'metric': 'managers'},
                        'fields': {'value': swarm_info.get('managers', 0)},
                        'timestamp': timestamp
                    }
                ])
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
        
        return metrics
    
    def _collect_service_metrics(self, timestamp):
        """Collect service-specific metrics"""
        metrics = []
        
        try:
            services = self.docker_manager.get_services()
            
            for service in services:
                # Service replica metrics
                metrics.extend([
                    {
                        'measurement': 'service_replicas',
                        'tags': {
                            'service_name': service['name'],
                            'service_id': service['id']
                        },
                        'fields': {
                            'running': service.get('running_tasks', 0),
                            'total': service.get('total_tasks', 0),
                            'desired': service.get('replicas', 0)
                        },
                        'timestamp': timestamp
                    }
                ])
                
                # Service status metric (1 for healthy, 0 for unhealthy)
                is_healthy = (service.get('running_tasks', 0) == service.get('total_tasks', 0) 
                             and service.get('total_tasks', 0) > 0)
                
                metrics.append({
                    'measurement': 'service_health',
                    'tags': {
                        'service_name': service['name'],
                        'service_id': service['id']
                    },
                    'fields': {'healthy': 1 if is_healthy else 0},
                    'timestamp': timestamp
                })
            
        except Exception as e:
            logger.error(f"Error collecting service metrics: {e}")
        
        return metrics
    
    def _collect_node_metrics(self, timestamp):
        """Collect node-specific metrics"""
        metrics = []
        
        try:
            nodes = self.docker_manager.get_nodes()
            
            for node in nodes:
                # Node resource metrics
                metrics.extend([
                    {
                        'measurement': 'node_resources',
                        'tags': {
                            'node_id': node['id'],
                            'hostname': node['hostname'],
                            'role': node['role']
                        },
                        'fields': {
                            'cpu_cores': node.get('resources', {}).get('cpu', 0),
                            'memory_gb': node.get('resources', {}).get('memory', 0)
                        },
                        'timestamp': timestamp
                    }
                ])
                
                # Node status metric (1 for ready, 0 for not ready)
                is_ready = node.get('status') == 'ready'
                is_available = node.get('availability') == 'active'
                
                metrics.append({
                    'measurement': 'node_status',
                    'tags': {
                        'node_id': node['id'],
                        'hostname': node['hostname'],
                        'role': node['role']
                    },
                    'fields': {
                        'ready': 1 if is_ready else 0,
                        'available': 1 if is_available else 0
                    },
                    'timestamp': timestamp
                })
            
        except Exception as e:
            logger.error(f"Error collecting node metrics: {e}")
        
        return metrics
    
    def _store_to_influxdb(self, metrics):
        """Store metrics to InfluxDB"""
        if not hasattr(self, 'influxdb_client'):
            return
        
        try:
            write_api = self.influxdb_client.write_api(write_options=SYNCHRONOUS)
            
            points = []
            for metric in metrics:
                point = Point(metric['measurement'])
                
                # Add tags
                for tag_key, tag_value in metric.get('tags', {}).items():
                    point = point.tag(tag_key, str(tag_value))
                
                # Add fields
                for field_key, field_value in metric.get('fields', {}).items():
                    point = point.field(field_key, field_value)
                
                # Set timestamp
                point = point.time(metric['timestamp'], WritePrecision.S)
                
                points.append(point)
            
            write_api.write(bucket=self.influxdb_bucket, record=points)
            logger.info(f"Stored {len(points)} metrics to InfluxDB")
            
        except Exception as e:
            logger.error(f"Error storing metrics to InfluxDB: {e}")
    
    def _store_to_prometheus(self, system_metrics, service_metrics, node_metrics):
        """Store metrics to Prometheus"""
        if not hasattr(self, 'prometheus_registry'):
            return
        
        try:
            # Update service metrics
            for metric in service_metrics:
                if metric['measurement'] == 'service_replicas':
                    tags = metric['tags']
                    fields = metric['fields']
                    
                    self.prom_service_replicas.labels(
                        service_name=tags['service_name'],
                        service_id=tags['service_id']
                    ).set(fields['running'])
                    
                    self.prom_service_replicas_desired.labels(
                        service_name=tags['service_name'],
                        service_id=tags['service_id']
                    ).set(fields['desired'])
            
            # Update node metrics
            for metric in node_metrics:
                if metric['measurement'] == 'node_resources':
                    tags = metric['tags']
                    fields = metric['fields']
                    
                    self.prom_node_cpu.labels(
                        node_id=tags['node_id'],
                        hostname=tags['hostname'],
                        role=tags['role']
                    ).set(fields['cpu_cores'])
                    
                    self.prom_node_memory.labels(
                        node_id=tags['node_id'],
                        hostname=tags['hostname'],
                        role=tags['role']
                    ).set(fields['memory_gb'] * 1024 * 1024 * 1024)  # Convert GB to bytes
            
            # Update system metrics
            for metric in system_metrics:
                if metric['measurement'] == 'system_containers':
                    self.prom_system_containers.labels(
                        state=metric['tags']['state']
                    ).set(metric['fields']['value'])
            
            # Push to gateway if configured
            prometheus_gateway = getattr(settings, 'PROMETHEUS_PUSHGATEWAY_URL', None)
            if prometheus_gateway:
                push_to_gateway(
                    prometheus_gateway,
                    job='swarm-manager',
                    registry=self.prometheus_registry
                )
            
            logger.info("Updated Prometheus metrics")
            
        except Exception as e:
            logger.error(f"Error storing metrics to Prometheus: {e}")
    
    def _store_to_database(self, metrics):
        """Store metrics to Django database"""
        from .models import Metric
        
        try:
            metric_objects = []
            
            for metric_data in metrics:
                metric_obj = Metric(
                    measurement=metric_data['measurement'],
                    tags=metric_data.get('tags', {}),
                    fields=metric_data.get('fields', {}),
                    timestamp=metric_data['timestamp']
                )
                metric_objects.append(metric_obj)
            
            # Bulk create for performance
            Metric.objects.bulk_create(metric_objects, batch_size=1000)
            logger.info(f"Stored {len(metric_objects)} metrics to database")
            
        except Exception as e:
            logger.error(f"Error storing metrics to database: {e}")
    
    def get_historical_data(self, measurement: str, tags: Dict = None, 
                           start_time: datetime = None, end_time: datetime = None) -> List[Dict]:
        """Get historical metrics data"""
        if not start_time:
            start_time = timezone.now() - timedelta(hours=24)
        if not end_time:
            end_time = timezone.now()
        
        if self.storage_backend == 'influxdb':
            return self._query_influxdb(measurement, tags, start_time, end_time)
        elif self.storage_backend == 'database':
            return self._query_database(measurement, tags, start_time, end_time)
        else:
            return []
    
    def _query_influxdb(self, measurement: str, tags: Dict, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Query InfluxDB for historical data"""
        if not hasattr(self, 'influxdb_client'):
            return []
        
        try:
            query_api = self.influxdb_client.query_api()
            
            # Build query
            query = f'''
                from(bucket: "{self.influxdb_bucket}")
                |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
                |> filter(fn: (r) => r._measurement == "{measurement}")
            '''
            
            # Add tag filters
            if tags:
                for tag_key, tag_value in tags.items():
                    query += f'\n|> filter(fn: (r) => r.{tag_key} == "{tag_value}")'
            
            query += '\n|> aggregateWindow(every: 5m, fn: mean, createEmpty: false)'
            
            result = query_api.query(org=self.influxdb_org, query=query)
            
            data = []
            for table in result:
                for record in table.records:
                    data.append({
                        'timestamp': record.get_time(),
                        'value': record.get_value(),
                        'field': record.get_field(),
                        'tags': {k: v for k, v in record.values.items() 
                                if k not in ['_time', '_value', '_field', '_measurement']}
                    })
            
            return data
            
        except Exception as e:
            logger.error(f"Error querying InfluxDB: {e}")
            return []
    
    def _query_database(self, measurement: str, tags: Dict, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Query Django database for historical data"""
        from .models import Metric
        
        try:
            queryset = Metric.objects.filter(
                measurement=measurement,
                timestamp__gte=start_time,
                timestamp__lte=end_time
            )
            
            # Apply tag filters
            if tags:
                for tag_key, tag_value in tags.items():
                    queryset = queryset.filter(tags__contains={tag_key: tag_value})
            
            queryset = queryset.order_by('timestamp')
            
            data = []
            for metric in queryset:
                for field_key, field_value in metric.fields.items():
                    data.append({
                        'timestamp': metric.timestamp,
                        'value': field_value,
                        'field': field_key,
                        'tags': metric.tags
                    })
            
            return data
            
        except Exception as e:
            logger.error(f"Error querying database: {e}")
            return []
    
    def get_service_metrics_summary(self, service_id: str, hours: int = 24) -> Dict:
        """Get metrics summary for a specific service"""
        start_time = timezone.now() - timedelta(hours=hours)
        
        # Get service replica data
        replica_data = self.get_historical_data(
            'service_replicas',
            {'service_id': service_id},
            start_time
        )
        
        # Get service health data
        health_data = self.get_historical_data(
            'service_health',
            {'service_id': service_id},
            start_time
        )
        
        # Calculate summary statistics
        summary = {
            'service_id': service_id,
            'time_range': f'{hours} hours',
            'replica_metrics': {
                'data_points': len(replica_data),
                'avg_running': 0,
                'min_running': 0,
                'max_running': 0
            },
            'health_metrics': {
                'data_points': len(health_data),
                'uptime_percentage': 0,
                'downtime_minutes': 0
            }
        }
        
        # Calculate replica statistics
        running_values = [d['value'] for d in replica_data if d['field'] == 'running']
        if running_values:
            summary['replica_metrics'].update({
                'avg_running': sum(running_values) / len(running_values),
                'min_running': min(running_values),
                'max_running': max(running_values)
            })
        
        # Calculate health statistics
        healthy_values = [d['value'] for d in health_data if d['field'] == 'healthy']
        if healthy_values:
            uptime_percentage = (sum(healthy_values) / len(healthy_values)) * 100
            downtime_minutes = (len([v for v in healthy_values if v == 0]) * 5)  # Assuming 5-minute intervals
            
            summary['health_metrics'].update({
                'uptime_percentage': uptime_percentage,
                'downtime_minutes': downtime_minutes
            })
        
        return summary
    
    def cleanup_old_metrics(self, days: int = 30):
        """Clean up old metrics data"""
        cutoff_date = timezone.now() - timedelta(days=days)
        
        if self.storage_backend == 'database':
            from .models import Metric
            deleted_count, _ = Metric.objects.filter(timestamp__lt=cutoff_date).delete()
            logger.info(f"Cleaned up {deleted_count} old metrics from database")
            return deleted_count
        
        # For InfluxDB and Prometheus, cleanup is typically handled by retention policies
        return 0


class DashboardBuilder:
    """Build custom dashboards for metrics visualization"""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
    
    def get_dashboard_data(self, dashboard_config: Dict, time_range: str = '24h') -> Dict:
        """Get data for a custom dashboard"""
        
        # Parse time range
        if time_range.endswith('h'):
            hours = int(time_range[:-1])
            start_time = timezone.now() - timedelta(hours=hours)
        elif time_range.endswith('d'):
            days = int(time_range[:-1])
            start_time = timezone.now() - timedelta(days=days)
        else:
            start_time = timezone.now() - timedelta(hours=24)
        
        dashboard_data = {
            'time_range': time_range,
            'generated_at': timezone.now(),
            'panels': []
        }
        
        # Process each panel in the dashboard
        for panel in dashboard_config.get('panels', []):
            panel_data = self._get_panel_data(panel, start_time)
            dashboard_data['panels'].append(panel_data)
        
        return dashboard_data
    
    def _get_panel_data(self, panel_config: Dict, start_time: datetime) -> Dict:
        """Get data for a specific dashboard panel"""
        panel_type = panel_config.get('type', 'line')
        measurement = panel_config.get('measurement')
        tags = panel_config.get('tags', {})
        
        data = self.metrics_collector.get_historical_data(measurement, tags, start_time)
        
        # Format data based on panel type
        if panel_type == 'line':
            return self._format_line_chart_data(data, panel_config)
        elif panel_type == 'bar':
            return self._format_bar_chart_data(data, panel_config)
        elif panel_type == 'gauge':
            return self._format_gauge_data(data, panel_config)
        else:
            return {'type': panel_type, 'data': data, 'config': panel_config}
    
    def _format_line_chart_data(self, data: List[Dict], config: Dict) -> Dict:
        """Format data for line charts"""
        # Group data by field and tags
        series = {}
        
        for point in data:
            field = point['field']
            timestamp = point['timestamp']
            value = point['value']
            
            series_key = f"{field}"
            if series_key not in series:
                series[series_key] = {
                    'name': field,
                    'data': []
                }
            
            series[series_key]['data'].append({
                'x': timestamp.isoformat(),
                'y': value
            })
        
        return {
            'type': 'line',
            'title': config.get('title', 'Chart'),
            'series': list(series.values()),
            'config': config
        }
    
    def _format_bar_chart_data(self, data: List[Dict], config: Dict) -> Dict:
        """Format data for bar charts"""
        # Aggregate data by tags
        aggregated = {}
        
        for point in data:
            tags = point.get('tags', {})
            key = '_'.join([f"{k}:{v}" for k, v in tags.items()])
            
            if key not in aggregated:
                aggregated[key] = {'label': key, 'value': 0, 'count': 0}
            
            aggregated[key]['value'] += point['value']
            aggregated[key]['count'] += 1
        
        # Calculate averages
        for item in aggregated.values():
            if item['count'] > 0:
                item['value'] = item['value'] / item['count']
        
        return {
            'type': 'bar',
            'title': config.get('title', 'Chart'),
            'data': list(aggregated.values()),
            'config': config
        }
    
    def _format_gauge_data(self, data: List[Dict], config: Dict) -> Dict:
        """Format data for gauge charts"""
        if not data:
            return {
                'type': 'gauge',
                'title': config.get('title', 'Gauge'),
                'value': 0,
                'config': config
            }
        
        # Use the latest value
        latest_point = max(data, key=lambda x: x['timestamp'])
        
        return {
            'type': 'gauge',
            'title': config.get('title', 'Gauge'),
            'value': latest_point['value'],
            'timestamp': latest_point['timestamp'].isoformat(),
            'config': config
        }
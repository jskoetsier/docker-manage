"""
Advanced Analytics and Historical Data Processing for Docker Swarm metrics
"""
import json
import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from django.utils import timezone
from django.conf import settings
from django.db.models import Q, Avg, Max, Min, Count
from django.core.cache import cache
from .models import Metric, ServiceLog
from .metrics import MetricsCollector

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """Advanced analytics engine for historical metrics analysis"""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
    
    def get_resource_usage_trends(self, time_range: str = '7d', granularity: str = '1h') -> Dict:
        """Get historical resource usage trends with statistical analysis"""
        start_time, end_time = self._parse_time_range(time_range)
        
        # Get CPU, Memory, Network, Disk metrics
        metrics_data = {
            'cpu': self._get_aggregated_metrics('system_resources', {'resource': 'cpu'}, start_time, end_time, granularity),
            'memory': self._get_aggregated_metrics('system_resources', {'resource': 'memory'}, start_time, end_time, granularity),
            'network': self._get_network_metrics(start_time, end_time, granularity),
            'disk': self._get_disk_metrics(start_time, end_time, granularity)
        }
        
        # Calculate trends and statistics
        trends = {}
        for resource, data in metrics_data.items():
            if data:
                trends[resource] = self._calculate_trends(data)
        
        return {
            'time_range': time_range,
            'granularity': granularity,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'data': metrics_data,
            'trends': trends,
            'summary': self._generate_summary(trends)
        }
    
    def get_service_performance_analysis(self, service_id: str = None, time_range: str = '24h') -> Dict:
        """Analyze service performance metrics over time"""
        start_time, end_time = self._parse_time_range(time_range)
        
        if service_id:
            services_filter = {'service_id': service_id}
            services = [service_id]
        else:
            services_filter = {}
            # Get all unique services from metrics
            services = self._get_unique_services(start_time, end_time)
        
        analysis = {}
        
        for service in services[:10]:  # Limit to 10 services for performance
            service_filter = dict(services_filter)
            if not service_id:
                service_filter['service_id'] = service
            
            # Get replica metrics
            replica_data = self._get_aggregated_metrics('service_replicas', service_filter, start_time, end_time, '5m')
            
            # Get health metrics
            health_data = self._get_aggregated_metrics('service_health', service_filter, start_time, end_time, '5m')
            
            # Calculate performance metrics
            performance_stats = self._calculate_service_performance(replica_data, health_data)
            
            analysis[service] = {
                'replica_data': replica_data[-50:],  # Last 50 points for visualization
                'health_data': health_data[-50:],
                'stats': performance_stats,
                'alerts': self._generate_service_alerts(performance_stats)
            }
        
        return {
            'time_range': time_range,
            'analysis': analysis,
            'summary': self._generate_service_summary(analysis)
        }
    
    def get_node_capacity_analysis(self, time_range: str = '7d') -> Dict:
        """Analyze node capacity and utilization trends"""
        start_time, end_time = self._parse_time_range(time_range)
        
        # Get unique nodes
        nodes = self._get_unique_nodes(start_time, end_time)
        
        capacity_analysis = {}
        
        for node in nodes:
            node_filter = {'node_id': node}
            
            # Get node resource data
            resource_data = self._get_aggregated_metrics('node_resources', node_filter, start_time, end_time, '1h')
            
            # Get node status data
            status_data = self._get_aggregated_metrics('node_status', node_filter, start_time, end_time, '5m')
            
            capacity_analysis[node] = {
                'resource_data': resource_data,
                'status_data': status_data,
                'capacity_stats': self._calculate_node_capacity_stats(resource_data, status_data),
                'recommendations': self._generate_node_recommendations(resource_data, status_data)
            }
        
        return {
            'time_range': time_range,
            'nodes': capacity_analysis,
            'cluster_summary': self._generate_cluster_summary(capacity_analysis)
        }
    
    def get_predictive_analytics(self, metric_type: str, time_range: str = '30d') -> Dict:
        """Generate predictive analytics based on historical trends"""
        start_time, end_time = self._parse_time_range(time_range)
        
        # Get historical data
        if metric_type == 'resource_usage':
            data = self._get_aggregated_metrics('system_resources', {}, start_time, end_time, '1h')
        elif metric_type == 'service_health':
            data = self._get_aggregated_metrics('service_health', {}, start_time, end_time, '1h')
        else:
            return {'error': f'Unknown metric type: {metric_type}'}
        
        if not data or len(data) < 10:
            return {'error': 'Insufficient data for prediction'}
        
        # Simple linear regression prediction
        predictions = self._calculate_predictions(data)
        
        return {
            'metric_type': metric_type,
            'time_range': time_range,
            'historical_data': data[-100:],  # Last 100 points
            'predictions': predictions,
            'confidence': self._calculate_prediction_confidence(data, predictions),
            'recommendations': self._generate_prediction_recommendations(predictions)
        }
    
    def export_metrics_data(self, measurements: List[str], tags_filter: Dict = None, 
                           start_time: datetime = None, end_time: datetime = None, 
                           format: str = 'json') -> Dict:
        """Export metrics data for external analysis"""
        if not start_time:
            start_time = timezone.now() - timedelta(days=7)
        if not end_time:
            end_time = timezone.now()
        
        exported_data = {}
        
        for measurement in measurements:
            data = self.metrics_collector.get_historical_data(
                measurement, tags_filter or {}, start_time, end_time
            )
            
            if format == 'csv':
                exported_data[measurement] = self._format_as_csv(data)
            else:
                exported_data[measurement] = data
        
        return {
            'format': format,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'measurements': measurements,
            'data': exported_data,
            'total_points': sum(len(data) for data in exported_data.values())
        }
    
    def _parse_time_range(self, time_range: str) -> Tuple[datetime, datetime]:
        """Parse time range string to datetime objects"""
        end_time = timezone.now()
        
        if time_range.endswith('h'):
            hours = int(time_range[:-1])
            start_time = end_time - timedelta(hours=hours)
        elif time_range.endswith('d'):
            days = int(time_range[:-1])
            start_time = end_time - timedelta(days=days)
        elif time_range.endswith('w'):
            weeks = int(time_range[:-1])
            start_time = end_time - timedelta(weeks=weeks)
        else:
            # Default to 24 hours
            start_time = end_time - timedelta(hours=24)
        
        return start_time, end_time
    
    def _get_aggregated_metrics(self, measurement: str, tags_filter: Dict, 
                               start_time: datetime, end_time: datetime, 
                               granularity: str) -> List[Dict]:
        """Get metrics data aggregated by time intervals"""
        cache_key = f"metrics_{measurement}_{hash(str(tags_filter))}_{start_time}_{end_time}_{granularity}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        # Get raw data
        raw_data = self.metrics_collector.get_historical_data(measurement, tags_filter, start_time, end_time)
        
        if not raw_data:
            return []
        
        # Parse granularity
        if granularity.endswith('m'):
            minutes = int(granularity[:-1])
            interval = timedelta(minutes=minutes)
        elif granularity.endswith('h'):
            hours = int(granularity[:-1])
            interval = timedelta(hours=hours)
        else:
            interval = timedelta(minutes=5)  # Default
        
        # Aggregate data
        aggregated = []
        current_time = start_time
        
        while current_time < end_time:
            next_time = current_time + interval
            
            # Get data points in this interval
            interval_data = [
                point for point in raw_data 
                if current_time <= point['timestamp'] < next_time
            ]
            
            if interval_data:
                # Calculate aggregated values
                values = [point['value'] for point in interval_data]
                aggregated.append({
                    'timestamp': current_time.isoformat(),
                    'value': statistics.mean(values) if values else 0,
                    'min': min(values) if values else 0,
                    'max': max(values) if values else 0,
                    'count': len(values)
                })
            
            current_time = next_time
        
        # Cache for 5 minutes
        cache.set(cache_key, aggregated, 300)
        
        return aggregated
    
    def _get_network_metrics(self, start_time: datetime, end_time: datetime, granularity: str) -> List[Dict]:
        """Get network metrics (placeholder - extend based on actual network monitoring)"""
        # This would be implemented based on your network monitoring setup
        return []
    
    def _get_disk_metrics(self, start_time: datetime, end_time: datetime, granularity: str) -> List[Dict]:
        """Get disk metrics (placeholder - extend based on actual disk monitoring)"""
        # This would be implemented based on your disk monitoring setup
        return []
    
    def _get_unique_services(self, start_time: datetime, end_time: datetime) -> List[str]:
        """Get unique service IDs from metrics data"""
        try:
            metrics = Metric.objects.filter(
                measurement='service_replicas',
                timestamp__gte=start_time,
                timestamp__lte=end_time
            ).values('tags').distinct()
            
            services = set()
            for metric in metrics:
                service_id = metric['tags'].get('service_id')
                if service_id:
                    services.add(service_id)
            
            return list(services)
        except Exception as e:
            logger.error(f"Error getting unique services: {e}")
            return []
    
    def _get_unique_nodes(self, start_time: datetime, end_time: datetime) -> List[str]:
        """Get unique node IDs from metrics data"""
        try:
            metrics = Metric.objects.filter(
                measurement='node_resources',
                timestamp__gte=start_time,
                timestamp__lte=end_time
            ).values('tags').distinct()
            
            nodes = set()
            for metric in metrics:
                node_id = metric['tags'].get('node_id')
                if node_id:
                    nodes.add(node_id)
            
            return list(nodes)
        except Exception as e:
            logger.error(f"Error getting unique nodes: {e}")
            return []
    
    def _calculate_trends(self, data: List[Dict]) -> Dict:
        """Calculate trend statistics for time series data"""
        if not data or len(data) < 2:
            return {'trend': 'insufficient_data'}
        
        values = [point['value'] for point in data]
        
        # Simple linear trend calculation
        n = len(values)
        x_values = list(range(n))
        
        # Calculate slope
        x_mean = statistics.mean(x_values)
        y_mean = statistics.mean(values)
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, values))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        slope = numerator / denominator if denominator != 0 else 0
        
        # Determine trend direction
        if slope > 0.1:
            trend = 'increasing'
        elif slope < -0.1:
            trend = 'decreasing'
        else:
            trend = 'stable'
        
        return {
            'trend': trend,
            'slope': slope,
            'current': values[-1] if values else 0,
            'average': statistics.mean(values),
            'min': min(values),
            'max': max(values),
            'std_dev': statistics.stdev(values) if len(values) > 1 else 0
        }
    
    def _calculate_service_performance(self, replica_data: List[Dict], health_data: List[Dict]) -> Dict:
        """Calculate service performance statistics"""
        stats = {
            'uptime_percentage': 0,
            'avg_replicas': 0,
            'replica_stability': 'stable',
            'performance_score': 0
        }
        
        if health_data:
            healthy_values = [point['value'] for point in health_data]
            stats['uptime_percentage'] = (sum(healthy_values) / len(healthy_values)) * 100
        
        if replica_data:
            replica_values = [point['value'] for point in replica_data]
            stats['avg_replicas'] = statistics.mean(replica_values)
            
            # Check replica stability
            if len(replica_values) > 1:
                replica_std = statistics.stdev(replica_values)
                if replica_std > 1:
                    stats['replica_stability'] = 'unstable'
        
        # Calculate overall performance score (0-100)
        stats['performance_score'] = min(100, (stats['uptime_percentage'] + (100 if stats['replica_stability'] == 'stable' else 50)) / 2)
        
        return stats
    
    def _calculate_node_capacity_stats(self, resource_data: List[Dict], status_data: List[Dict]) -> Dict:
        """Calculate node capacity statistics"""
        stats = {
            'cpu_utilization': 0,
            'memory_utilization': 0,
            'availability': 100,
            'capacity_trend': 'stable'
        }
        
        if resource_data:
            cpu_values = [point['value'] for point in resource_data if 'cpu' in str(point).lower()]
            memory_values = [point['value'] for point in resource_data if 'memory' in str(point).lower()]
            
            if cpu_values:
                stats['cpu_utilization'] = statistics.mean(cpu_values)
            if memory_values:
                stats['memory_utilization'] = statistics.mean(memory_values)
        
        if status_data:
            available_values = [point['value'] for point in status_data]
            stats['availability'] = (sum(available_values) / len(available_values)) * 100
        
        return stats
    
    def _calculate_predictions(self, data: List[Dict]) -> List[Dict]:
        """Calculate simple predictions based on linear trend"""
        if len(data) < 5:
            return []
        
        values = [point['value'] for point in data]
        n = len(values)
        
        # Simple moving average prediction
        window_size = min(10, n // 2)
        recent_values = values[-window_size:]
        trend = (recent_values[-1] - recent_values[0]) / window_size
        
        predictions = []
        last_timestamp = datetime.fromisoformat(data[-1]['timestamp'].replace('Z', '+00:00'))
        
        for i in range(1, 25):  # Predict next 24 hours
            future_time = last_timestamp + timedelta(hours=i)
            predicted_value = recent_values[-1] + (trend * i)
            
            predictions.append({
                'timestamp': future_time.isoformat(),
                'predicted_value': max(0, predicted_value),  # Ensure non-negative
                'confidence': max(0.1, 1.0 - (i * 0.05))  # Decreasing confidence
            })
        
        return predictions
    
    def _calculate_prediction_confidence(self, historical_data: List[Dict], predictions: List[Dict]) -> float:
        """Calculate confidence score for predictions"""
        if not historical_data or len(historical_data) < 10:
            return 0.1
        
        # Calculate historical trend stability
        values = [point['value'] for point in historical_data[-20:]]
        if len(values) > 1:
            std_dev = statistics.stdev(values)
            mean_val = statistics.mean(values)
            cv = std_dev / mean_val if mean_val > 0 else 1
            
            # Higher coefficient of variation = lower confidence
            confidence = max(0.1, 1.0 - min(1.0, cv))
        else:
            confidence = 0.5
        
        return confidence
    
    def _generate_summary(self, trends: Dict) -> Dict:
        """Generate summary of trends analysis"""
        summary = {
            'overall_status': 'healthy',
            'alerts': [],
            'recommendations': []
        }
        
        for resource, trend_data in trends.items():
            if trend_data.get('trend') == 'increasing':
                if trend_data.get('current', 0) > trend_data.get('average', 0) * 1.5:
                    summary['alerts'].append(f"High {resource} usage detected")
                    summary['overall_status'] = 'warning'
        
        return summary
    
    def _generate_service_alerts(self, performance_stats: Dict) -> List[str]:
        """Generate alerts based on service performance"""
        alerts = []
        
        if performance_stats.get('uptime_percentage', 100) < 95:
            alerts.append('Low uptime detected')
        
        if performance_stats.get('replica_stability') == 'unstable':
            alerts.append('Replica count fluctuating')
        
        if performance_stats.get('performance_score', 100) < 70:
            alerts.append('Poor overall performance')
        
        return alerts
    
    def _generate_service_summary(self, analysis: Dict) -> Dict:
        """Generate summary of service analysis"""
        total_services = len(analysis)
        healthy_services = sum(1 for stats in analysis.values() if stats['stats'].get('performance_score', 0) >= 80)
        
        return {
            'total_services': total_services,
            'healthy_services': healthy_services,
            'health_percentage': (healthy_services / total_services * 100) if total_services > 0 else 0,
            'critical_services': [service for service, data in analysis.items() 
                                if data['stats'].get('performance_score', 0) < 50]
        }
    
    def _generate_node_recommendations(self, resource_data: List[Dict], status_data: List[Dict]) -> List[str]:
        """Generate recommendations for node optimization"""
        recommendations = []
        
        # Placeholder recommendations - extend based on actual analysis
        recommendations.append("Monitor resource utilization trends")
        recommendations.append("Consider load balancing if CPU usage consistently high")
        
        return recommendations
    
    def _generate_cluster_summary(self, capacity_analysis: Dict) -> Dict:
        """Generate cluster-wide capacity summary"""
        total_nodes = len(capacity_analysis)
        
        return {
            'total_nodes': total_nodes,
            'nodes_status': 'healthy',  # Placeholder
            'recommendations': ['Regular capacity planning', 'Monitor node health']
        }
    
    def _generate_prediction_recommendations(self, predictions: List[Dict]) -> List[str]:
        """Generate recommendations based on predictions"""
        recommendations = []
        
        if predictions:
            future_values = [p['predicted_value'] for p in predictions]
            if any(v > 80 for v in future_values[:12]):  # Next 12 hours
                recommendations.append("Consider scaling resources in the next 12 hours")
        
        return recommendations
    
    def _format_as_csv(self, data: List[Dict]) -> str:
        """Format data as CSV string"""
        if not data:
            return ""
        
        headers = list(data[0].keys())
        csv_lines = [','.join(headers)]
        
        for row in data:
            csv_lines.append(','.join(str(row.get(header, '')) for header in headers))
        
        return '\n'.join(csv_lines)
"""
Advanced Dashboard Views for Interactive Metrics and Analytics
"""
import json
import logging
from datetime import datetime, timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Dashboard, DashboardPanel, Metric
from .analytics import AnalyticsEngine
from .metrics import MetricsCollector, DashboardBuilder

logger = logging.getLogger(__name__)


@login_required
def analytics_dashboard(request):
    """Main analytics dashboard with overview metrics"""
    try:
        analytics = AnalyticsEngine()
        
        # Get overview data
        resource_trends = analytics.get_resource_usage_trends('24h', '1h')
        service_analysis = analytics.get_service_performance_analysis(None, '24h')
        
        context = {
            'resource_trends': resource_trends,
            'service_analysis': service_analysis,
            'time_ranges': ['1h', '6h', '24h', '7d', '30d'],
            'page_title': 'Analytics Dashboard'
        }
        
        return render(request, 'dashboard/analytics.html', context)
        
    except Exception as e:
        logger.error(f"Error loading analytics dashboard: {e}")
        messages.error(request, f"Error loading analytics: {str(e)}")
        return render(request, 'dashboard/analytics.html', {'error': str(e)})


@login_required
def historical_metrics(request):
    """Historical metrics view with time-series charts"""
    time_range = request.GET.get('range', '24h')
    measurement = request.GET.get('measurement', 'resource_usage')
    
    try:
        analytics = AnalyticsEngine()
        
        if measurement == 'resource_usage' or measurement == 'system_resources':
            data = analytics.get_resource_usage_trends(time_range, '1h')
        elif measurement == 'service_performance':
            data = analytics.get_service_performance_analysis(None, time_range)
        elif measurement == 'node_capacity':
            data = analytics.get_node_capacity_analysis(time_range)
        else:
            data = {'error': f'Unknown measurement: {measurement}'}
        
        context = {
            'data': data,
            'time_range': time_range,
            'measurement': measurement,
            'available_measurements': [
                ('resource_usage', 'Resource Usage'),
                ('service_performance', 'Service Performance'),
                ('node_capacity', 'Node Capacity')
            ],
            'time_ranges': [
                ('1h', '1 Hour'),
                ('6h', '6 Hours'),
                ('24h', '24 Hours'),
                ('7d', '7 Days'),
                ('30d', '30 Days')
            ],
            'page_title': 'Historical Metrics'
        }
        
        return render(request, 'dashboard/historical_metrics.html', context)
        
    except Exception as e:
        logger.error(f"Error loading historical metrics: {e}")
        messages.error(request, f"Error loading metrics: {str(e)}")
        return render(request, 'dashboard/historical_metrics.html', {'error': str(e)})


@login_required
def custom_dashboards(request):
    """List and manage custom dashboards"""
    # Get user's dashboards and shared dashboards
    user_dashboards = Dashboard.objects.filter(created_by=request.user)
    shared_dashboards = Dashboard.objects.filter(
        Q(shared_with=request.user) | Q(is_public=True)
    ).exclude(created_by=request.user)
    
    context = {
        'user_dashboards': user_dashboards,
        'shared_dashboards': shared_dashboards,
        'page_title': 'Custom Dashboards'
    }
    
    return render(request, 'dashboard/custom_dashboards.html', context)


@login_required
def dashboard_builder(request, dashboard_id=None):
    """Dashboard builder interface"""
    dashboard = None
    
    if dashboard_id:
        dashboard = get_object_or_404(Dashboard, id=dashboard_id)
        if not dashboard.can_edit(request.user):
            messages.error(request, "You don't have permission to edit this dashboard")
            return redirect('dashboard:custom_dashboards')
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '')
            description = request.POST.get('description', '')
            config = json.loads(request.POST.get('config', '{}'))
            is_public = request.POST.get('is_public') == 'on'
            
            if dashboard:
                dashboard.name = name
                dashboard.description = description
                dashboard.config = config
                dashboard.is_public = is_public
                dashboard.save()
                messages.success(request, 'Dashboard updated successfully')
            else:
                dashboard = Dashboard.objects.create(
                    name=name,
                    description=description,
                    config=config,
                    is_public=is_public,
                    created_by=request.user
                )
                messages.success(request, 'Dashboard created successfully')
            
            return redirect('dashboard:view_dashboard', dashboard_id=dashboard.id)
            
        except json.JSONDecodeError:
            messages.error(request, 'Invalid dashboard configuration')
        except Exception as e:
            logger.error(f"Error saving dashboard: {e}")
            messages.error(request, f"Error saving dashboard: {str(e)}")
    
    # Get available metrics for the builder
    available_metrics = [
        ('system_resources', 'System Resources'),
        ('service_replicas', 'Service Replicas'),
        ('service_health', 'Service Health'),
        ('node_resources', 'Node Resources'),
        ('node_status', 'Node Status'),
    ]
    
    panel_types = [
        ('line', 'Line Chart'),
        ('bar', 'Bar Chart'),
        ('gauge', 'Gauge'),
        ('stat', 'Stat'),
        ('table', 'Table'),
    ]
    
    context = {
        'dashboard': dashboard,
        'available_metrics': available_metrics,
        'panel_types': panel_types,
        'page_title': 'Dashboard Builder'
    }
    
    return render(request, 'dashboard/dashboard_builder.html', context)


@login_required
def view_dashboard(request, dashboard_id):
    """View a custom dashboard"""
    dashboard = get_object_or_404(Dashboard, id=dashboard_id)
    
    if not dashboard.can_view(request.user):
        messages.error(request, "You don't have permission to view this dashboard")
        return redirect('dashboard:custom_dashboards')
    
    time_range = request.GET.get('range', '24h')
    
    try:
        # Get dashboard data
        dashboard_builder = DashboardBuilder()
        dashboard_data = dashboard_builder.get_dashboard_data(dashboard.config, time_range)
        
        context = {
            'dashboard': dashboard,
            'dashboard_data': dashboard_data,
            'time_range': time_range,
            'time_ranges': [
                ('1h', '1 Hour'),
                ('6h', '6 Hours'), 
                ('24h', '24 Hours'),
                ('7d', '7 Days'),
                ('30d', '30 Days')
            ],
            'can_edit': dashboard.can_edit(request.user),
            'page_title': dashboard.name
        }
        
        return render(request, 'dashboard/view_dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error loading dashboard {dashboard_id}: {e}")
        messages.error(request, f"Error loading dashboard: {str(e)}")
        return render(request, 'dashboard/view_dashboard.html', {
            'dashboard': dashboard,
            'error': str(e)
        })


@login_required
def predictive_analytics(request):
    """Predictive analytics view"""
    metric_type = request.GET.get('type', 'resource_usage')
    time_range = request.GET.get('range', '30d')
    
    try:
        analytics = AnalyticsEngine()
        predictions = analytics.get_predictive_analytics(metric_type, time_range)
        
        context = {
            'predictions': predictions,
            'metric_type': metric_type,
            'time_range': time_range,
            'metric_types': [
                ('resource_usage', 'Resource Usage'),
                ('service_health', 'Service Health'),
            ],
            'time_ranges': [
                ('7d', '7 Days'),
                ('30d', '30 Days'),
                ('90d', '90 Days'),
            ],
            'page_title': 'Predictive Analytics'
        }
        
        return render(request, 'dashboard/predictive_analytics.html', context)
        
    except Exception as e:
        logger.error(f"Error loading predictive analytics: {e}")
        messages.error(request, f"Error loading predictions: {str(e)}")
        return render(request, 'dashboard/predictive_analytics.html', {'error': str(e)})


# API Views for AJAX requests

@login_required
def api_metrics_data(request):
    """API endpoint for real-time metrics data"""
    measurement = request.GET.get('measurement', 'system_resources')
    tags_filter = json.loads(request.GET.get('tags', '{}'))
    time_range = request.GET.get('range', '1h')
    
    try:
        collector = MetricsCollector()
        
        # Parse time range
        if time_range.endswith('h'):
            hours = int(time_range[:-1])
            start_time = timezone.now() - timedelta(hours=hours)
        elif time_range.endswith('d'):
            days = int(time_range[:-1])
            start_time = timezone.now() - timedelta(days=days)
        else:
            start_time = timezone.now() - timedelta(hours=1)
        
        data = collector.get_historical_data(measurement, tags_filter, start_time)
        
        return JsonResponse({
            'success': True,
            'data': data[-100:],  # Last 100 points
            'measurement': measurement,
            'time_range': time_range
        })
        
    except Exception as e:
        logger.error(f"Error getting metrics data: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def api_dashboard_data(request, dashboard_id):
    """API endpoint for dashboard data"""
    dashboard = get_object_or_404(Dashboard, id=dashboard_id)
    
    if not dashboard.can_view(request.user):
        return JsonResponse({
            'success': False,
            'error': 'Permission denied'
        }, status=403)
    
    time_range = request.GET.get('range', '24h')
    
    try:
        dashboard_builder = DashboardBuilder()
        dashboard_data = dashboard_builder.get_dashboard_data(dashboard.config, time_range)
        
        return JsonResponse({
            'success': True,
            'data': dashboard_data,
            'dashboard_id': dashboard_id
        })
        
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def api_share_dashboard(request, dashboard_id):
    """API endpoint to share dashboard with users"""
    dashboard = get_object_or_404(Dashboard, id=dashboard_id)
    
    if not dashboard.can_edit(request.user):
        return JsonResponse({
            'success': False,
            'error': 'Permission denied'
        }, status=403)
    
    try:
        data = json.loads(request.body)
        user_ids = data.get('user_ids', [])
        
        # Add users to shared_with
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        users = User.objects.filter(id__in=user_ids)
        dashboard.shared_with.add(*users)
        
        return JsonResponse({
            'success': True,
            'shared_count': len(user_ids)
        })
        
    except Exception as e:
        logger.error(f"Error sharing dashboard: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def api_export_data(request):
    """API endpoint to export metrics data"""
    try:
        data = json.loads(request.body)
        measurements = data.get('measurements', [])
        tags_filter = data.get('tags_filter', {})
        time_range = data.get('time_range', '7d')
        format_type = data.get('format', 'json')
        
        # Parse time range
        if time_range.endswith('h'):
            hours = int(time_range[:-1])
            start_time = timezone.now() - timedelta(hours=hours)
        elif time_range.endswith('d'):
            days = int(time_range[:-1])
            start_time = timezone.now() - timedelta(days=days)
        else:
            start_time = timezone.now() - timedelta(days=7)
        
        analytics = AnalyticsEngine()
        exported_data = analytics.export_metrics_data(
            measurements, tags_filter, start_time, timezone.now(), format_type
        )
        
        if format_type == 'csv':
            # Return CSV as file download
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="metrics_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
            
            # Combine all CSV data
            csv_content = []
            for measurement, csv_data in exported_data['data'].items():
                csv_content.append(f"# {measurement}")
                csv_content.append(csv_data)
                csv_content.append("")
            
            response.write('\n'.join(csv_content))
            return response
        else:
            return JsonResponse(exported_data)
        
    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required 
def api_dashboard_templates(request):
    """API endpoint to get dashboard templates"""
    try:
        templates = Dashboard.objects.filter(is_template=True, is_public=True)
        
        template_data = []
        for template in templates:
            template_data.append({
                'id': template.id,
                'name': template.name,
                'description': template.description,
                'config': template.config,
                'created_by': template.created_by.username,
                'created_at': template.created_at.isoformat()
            })
        
        return JsonResponse({
            'success': True,
            'templates': template_data
        })
        
    except Exception as e:
        logger.error(f"Error getting dashboard templates: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def api_create_from_template(request, template_id):
    """API endpoint to create dashboard from template"""
    template = get_object_or_404(Dashboard, id=template_id, is_template=True)
    
    try:
        data = json.loads(request.body)
        name = data.get('name', f"{template.name} - Copy")
        
        # Create new dashboard from template
        new_dashboard = Dashboard.objects.create(
            name=name,
            description=template.description,
            config=template.config,
            created_by=request.user
        )
        
        return JsonResponse({
            'success': True,
            'dashboard_id': new_dashboard.id,
            'dashboard_name': new_dashboard.name
        })
        
    except Exception as e:
        logger.error(f"Error creating dashboard from template: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["DELETE"])
def api_delete_dashboard(request, dashboard_id):
    """API endpoint to delete a dashboard"""
    dashboard = get_object_or_404(Dashboard, id=dashboard_id)
    
    if not dashboard.can_edit(request.user):
        return JsonResponse({
            'success': False,
            'error': 'Permission denied'
        }, status=403)
    
    try:
        dashboard_name = dashboard.name
        dashboard.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Dashboard "{dashboard_name}" deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error deleting dashboard: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
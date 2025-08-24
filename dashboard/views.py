"""
Dashboard views for Docker Swarm management
"""
import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from accounts.decorators import role_required, permission_required, audit_action, service_permission_required
from .docker_utils import DockerSwarmManager


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        docker_manager = DockerSwarmManager()

        context.update({
            'swarm_active': docker_manager.is_swarm_active(),
            'swarm_info': docker_manager.get_swarm_info(),
            'system_info': docker_manager.get_system_info(),
            'nodes': docker_manager.get_nodes(),
            'services': docker_manager.get_services(),
        })

        return context


@login_required
def services_view(request):
    """Services management view"""
    docker_manager = DockerSwarmManager()

    context = {
        'services': docker_manager.get_services(),
        'swarm_active': docker_manager.is_swarm_active(),
    }

    return render(request, 'dashboard/services.html', context)


def nodes_view(request):
    """Nodes management view"""
    docker_manager = DockerSwarmManager()

    context = {
        'nodes': docker_manager.get_nodes(),
        'swarm_active': docker_manager.is_swarm_active(),
    }

    return render(request, 'dashboard/nodes.html', context)


def service_detail_view(request, service_id):
    """Service detail view"""
    docker_manager = DockerSwarmManager()
    service_details = docker_manager.get_service_details(service_id)

    if not service_details:
        messages.error(request, "Service not found")
        return redirect('services')

    context = {
        'service': service_details['service'],
        'tasks': service_details['tasks'],
    }

    return render(request, 'dashboard/service_detail.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def restart_service(request, service_id):
    """Restart a service"""
    docker_manager = DockerSwarmManager()

    if docker_manager.restart_service(service_id):
        return JsonResponse({'status': 'success', 'message': 'Service restarted successfully'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Failed to restart service'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def scale_service(request, service_id):
    """Scale a service"""
    try:
        data = json.loads(request.body)
        replicas = int(data.get('replicas', 1))

        docker_manager = DockerSwarmManager()

        if docker_manager.scale_service(service_id, replicas):
            return JsonResponse({'status': 'success', 'message': f'Service scaled to {replicas} replicas'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Failed to scale service'}, status=500)
    except (ValueError, KeyError) as e:
        return JsonResponse({'status': 'error', 'message': 'Invalid request data'}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def remove_service(request, service_id):
    """Remove a service"""
    docker_manager = DockerSwarmManager()

    if docker_manager.remove_service(service_id):
        return JsonResponse({'status': 'success', 'message': 'Service removed successfully'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Failed to remove service'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def create_service(request):
    """Create a new service"""
    try:
        data = json.loads(request.body)

        image = data.get('image')
        name = data.get('name')
        replicas = int(data.get('replicas', 1))

        if not image or not name:
            return JsonResponse({'status': 'error', 'message': 'Image and name are required'}, status=400)

        docker_manager = DockerSwarmManager()

        # Prepare additional arguments
        kwargs = {}
        if data.get('ports'):
            kwargs['ports'] = data['ports']
        if data.get('env'):
            kwargs['env'] = data['env']
        if data.get('labels'):
            kwargs['labels'] = data['labels']

        if docker_manager.create_service(image, name, replicas, **kwargs):
            return JsonResponse({'status': 'success', 'message': 'Service created successfully'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Failed to create service'}, status=500)
    except (ValueError, KeyError) as e:
        return JsonResponse({'status': 'error', 'message': 'Invalid request data'}, status=400)


def api_services(request):
    """API endpoint for services data"""
    docker_manager = DockerSwarmManager()
    services = docker_manager.get_services()
    return JsonResponse({'services': services})


def api_nodes(request):
    """API endpoint for nodes data"""
    docker_manager = DockerSwarmManager()
    nodes = docker_manager.get_nodes()
    return JsonResponse({'nodes': nodes})


def api_system_info(request):
    """API endpoint for system information"""
    docker_manager = DockerSwarmManager()
    system_info = docker_manager.get_system_info()
    swarm_info = docker_manager.get_swarm_info()

    return JsonResponse({
        'system_info': system_info,
        'swarm_info': swarm_info,
        'swarm_active': docker_manager.is_swarm_active()
    })


def create_service_view(request):
    """Create service form view"""
    if request.method == 'POST':
        try:
            image = request.POST.get('image')
            name = request.POST.get('name')
            replicas = int(request.POST.get('replicas', 1))

            if not image or not name:
                messages.error(request, 'Image and name are required')
                return render(request, 'dashboard/create_service.html')

            docker_manager = DockerSwarmManager()

            # Prepare additional arguments
            kwargs = {}
            if request.POST.get('ports'):
                try:
                    ports = json.loads(request.POST.get('ports'))
                    kwargs['ports'] = ports
                except json.JSONDecodeError:
                    pass

            if request.POST.get('env'):
                env_vars = {}
                for line in request.POST.get('env').split('\n'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
                if env_vars:
                    kwargs['env'] = env_vars

            if docker_manager.create_service(image, name, replicas, **kwargs):
                messages.success(request, f'Service "{name}" created successfully')
                return redirect('services')
            else:
                messages.error(request, 'Failed to create service')
        except ValueError:
            messages.error(request, 'Invalid replicas number')
        except Exception as e:
            messages.error(request, f'Error creating service: {str(e)}')

    return render(request, 'dashboard/create_service.html')

"""
Dashboard views for Docker Swarm management
"""

import json
import subprocess
from django.utils import timezone

from accounts.decorators import (
    audit_action,
    permission_required,
    role_required,
    service_permission_required,
)
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView

from .compose_utils import ComposeImporter, get_popular_compose_repositories
from .docker_utils import DockerSwarmManager


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        docker_manager = DockerSwarmManager()

        context.update(
            {
                "swarm_active": docker_manager.is_swarm_active(),
                "swarm_info": docker_manager.get_swarm_info(),
                "system_info": docker_manager.get_system_info(),
                "nodes": docker_manager.get_nodes(),
                "services": docker_manager.get_services(),
            }
        )

        return context


@login_required
def services_view(request):
    """Services management view"""
    docker_manager = DockerSwarmManager()

    context = {
        "services": docker_manager.get_services(),
        "swarm_active": docker_manager.is_swarm_active(),
    }

    return render(request, "dashboard/services.html", context)


def nodes_view(request):
    """Nodes management view"""
    docker_manager = DockerSwarmManager()

    context = {
        "nodes": docker_manager.get_nodes(),
        "swarm_active": docker_manager.is_swarm_active(),
    }

    return render(request, "dashboard/nodes.html", context)


def service_detail_view(request, service_id):
    """Service detail view"""
    docker_manager = DockerSwarmManager()
    service_details = docker_manager.get_service_details(service_id)

    if not service_details:
        messages.error(request, "Service not found")
        return redirect("services")

    context = {
        "service": service_details["service"],
        "tasks": service_details["tasks"],
    }

    return render(request, "dashboard/service_detail.html", context)


@csrf_exempt
@require_http_methods(["POST"])
def restart_service(request, service_id):
    """Restart a service"""
    docker_manager = DockerSwarmManager()

    if docker_manager.restart_service(service_id):
        return JsonResponse(
            {"status": "success", "message": "Service restarted successfully"}
        )
    else:
        return JsonResponse(
            {"status": "error", "message": "Failed to restart service"}, status=500
        )


@csrf_exempt
@require_http_methods(["POST"])
def scale_service(request, service_id):
    """Scale a service"""
    try:
        data = json.loads(request.body)
        replicas = int(data.get("replicas", 1))

        docker_manager = DockerSwarmManager()

        if docker_manager.scale_service(service_id, replicas):
            return JsonResponse(
                {
                    "status": "success",
                    "message": f"Service scaled to {replicas} replicas",
                }
            )
        else:
            return JsonResponse(
                {"status": "error", "message": "Failed to scale service"}, status=500
            )
    except (ValueError, KeyError) as e:
        return JsonResponse(
            {"status": "error", "message": "Invalid request data"}, status=400
        )


@csrf_exempt
@require_http_methods(["POST"])
def remove_service(request, service_id):
    """Remove a service"""
    docker_manager = DockerSwarmManager()

    if docker_manager.remove_service(service_id):
        return JsonResponse(
            {"status": "success", "message": "Service removed successfully"}
        )
    else:
        return JsonResponse(
            {"status": "error", "message": "Failed to remove service"}, status=500
        )


@csrf_exempt
@require_http_methods(["POST"])
def create_service(request):
    """Create a new service"""
    try:
        data = json.loads(request.body)

        image = data.get("image")
        name = data.get("name")
        replicas = int(data.get("replicas", 1))

        if not image or not name:
            return JsonResponse(
                {"status": "error", "message": "Image and name are required"},
                status=400,
            )

        docker_manager = DockerSwarmManager()

        # Prepare additional arguments
        kwargs = {}
        if data.get("ports"):
            kwargs["ports"] = data["ports"]
        if data.get("env"):
            kwargs["env"] = data["env"]
        if data.get("labels"):
            kwargs["labels"] = data["labels"]

        if docker_manager.create_service(image, name, replicas, **kwargs):
            return JsonResponse(
                {"status": "success", "message": "Service created successfully"}
            )
        else:
            return JsonResponse(
                {"status": "error", "message": "Failed to create service"}, status=500
            )
    except (ValueError, KeyError) as e:
        return JsonResponse(
            {"status": "error", "message": "Invalid request data"}, status=400
        )


def api_services(request):
    """API endpoint for services data"""
    docker_manager = DockerSwarmManager()
    services = docker_manager.get_services()
    return JsonResponse({"services": services})


def api_nodes(request):
    """API endpoint for nodes data"""
    docker_manager = DockerSwarmManager()
    nodes = docker_manager.get_nodes()
    return JsonResponse({"nodes": nodes})


def api_system_info(request):
    """API endpoint for system information"""
    docker_manager = DockerSwarmManager()
    system_info = docker_manager.get_system_info()
    swarm_info = docker_manager.get_swarm_info()

    return JsonResponse(
        {
            "system_info": system_info,
            "swarm_info": swarm_info,
            "swarm_active": docker_manager.is_swarm_active(),
        }
    )


def create_service_view(request):
    """Create service form view"""
    if request.method == "POST":
        try:
            image = request.POST.get("image")
            name = request.POST.get("name")
            replicas = int(request.POST.get("replicas", 1))

            if not image or not name:
                messages.error(request, "Image and name are required")
                return render(request, "dashboard/create_service.html")

            docker_manager = DockerSwarmManager()

            # Prepare additional arguments
            kwargs = {}
            if request.POST.get("ports"):
                try:
                    ports = json.loads(request.POST.get("ports"))
                    kwargs["ports"] = ports
                except json.JSONDecodeError:
                    pass

            if request.POST.get("env"):
                env_vars = {}
                for line in request.POST.get("env").split("\n"):
                    if "=" in line:
                        key, value = line.split("=", 1)
                        env_vars[key.strip()] = value.strip()
                if env_vars:
                    kwargs["env"] = env_vars

            if docker_manager.create_service(image, name, replicas, **kwargs):
                messages.success(request, f'Service "{name}" created successfully')
                return redirect("services")
            else:
                messages.error(request, "Failed to create service")
        except ValueError:
            messages.error(request, "Invalid replicas number")
        except Exception as e:
            messages.error(request, f"Error creating service: {str(e)}")

    return render(request, "dashboard/create_service.html")


@login_required
def import_compose_view(request):
    """Import Docker Compose from Git repository"""
    popular_repos = get_popular_compose_repositories()

    if request.method == "POST":
        try:
            repo_url = request.POST.get("repo_url", "").strip()
            branch = request.POST.get("branch", "main").strip()
            compose_file_path = (
                request.POST.get("compose_file_path", "").strip() or None
            )

            if not repo_url:
                messages.error(request, "Repository URL is required")
                return render(
                    request,
                    "dashboard/import_compose.html",
                    {"popular_repos": popular_repos},
                )

            # Import compose services
            with ComposeImporter() as importer:
                services, metadata = importer.import_from_git(
                    repo_url, branch, compose_file_path
                )

            # Store in session for review
            request.session["compose_import"] = {
                "services": services,
                "metadata": metadata,
            }

            return redirect("dashboard:review_compose_import")

        except FileNotFoundError as e:
            if "No Docker Compose files found" in str(e):
                messages.error(
                    request,
                    "No Docker Compose files found in the repository. Make sure the repository contains docker-compose.yml or docker-compose.yaml files.",
                )
            else:
                messages.error(request, f"File not found: {str(e)}")
        except RuntimeError as e:
            if "Failed to clone repository" in str(e):
                messages.error(
                    request,
                    f"Unable to clone repository. Please check the URL and ensure it's a valid Git repository. {str(e)}",
                )
            else:
                messages.error(request, f"Repository error: {str(e)}")
        except ValueError as e:
            messages.error(request, f"Invalid compose file format: {str(e)}")
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                f"Unexpected error importing compose file from {repo_url}: {e}"
            )
            messages.error(
                request, f"Unexpected error importing compose file: {str(e)}"
            )

    context = {"popular_repos": popular_repos}

    return render(request, "dashboard/import_compose.html", context)


@login_required
def review_compose_import_view(request):
    """Review imported compose services before deployment"""
    compose_data = request.session.get("compose_import")

    if not compose_data:
        messages.error(
            request, "No compose data found. Please import a compose file first."
        )
        return redirect("dashboard:import_compose")

    services = compose_data["services"]
    metadata = compose_data["metadata"]

    if request.method == "POST":
        try:
            selected_services = request.POST.getlist("selected_services")
            docker_manager = DockerSwarmManager()

            if not selected_services:
                messages.error(request, "Please select at least one service to deploy")
                return render(
                    request,
                    "dashboard/review_compose_import.html",
                    {"services": services, "metadata": metadata},
                )

            deployed_count = 0
            failed_services = []

            for service_data in services:
                if service_data["name"] in selected_services:
                    try:
                        # Deploy service
                        success = docker_manager.create_service(
                            image=service_data["image"],
                            name=service_data["name"],
                            replicas=service_data.get("replicas", 1),
                            env=service_data.get("environment", {}),
                            ports=service_data.get("ports", []),
                            labels=service_data.get("labels", {}),
                        )

                        if success:
                            deployed_count += 1
                        else:
                            failed_services.append(service_data["name"])

                    except Exception as e:
                        failed_services.append(f"{service_data['name']} ({str(e)})")

            # Clear session data
            del request.session["compose_import"]

            if deployed_count > 0:
                messages.success(
                    request, f"Successfully deployed {deployed_count} services"
                )

            if failed_services:
                messages.warning(
                    request, f'Failed to deploy: {", ".join(failed_services)}'
                )

            return redirect("services")

        except Exception as e:
            messages.error(request, f"Error during deployment: {str(e)}")

    # Add validation warnings for each service
    for service in services:
        with ComposeImporter() as importer:
            service["warnings"] = importer.validate_service_for_swarm(service)

    context = {"services": services, "metadata": metadata}

    return render(request, "dashboard/review_compose_import.html", context)


@login_required
def clear_compose_import_view(request):
    """Clear compose import session data"""
    if "compose_import" in request.session:
        del request.session["compose_import"]

    messages.info(request, "Compose import data cleared")
    return redirect("import_compose")


@login_required
def service_logs_view(request, service_id):
    """View logs for a specific service"""
    from django.shortcuts import get_object_or_404

    docker_manager = DockerSwarmManager()

    lines = int(request.GET.get('lines', 100))
    since = request.GET.get('since', '')

    # Get service details
    service_details = docker_manager.get_service_details(service_id)
    if not service_details:
        messages.error(request, "Service not found")
        return redirect('services')

    # Get service logs
    logs_data = docker_manager.get_service_logs(service_id, lines=lines, since=since or None)

    # Get service tasks with containers
    tasks = docker_manager.get_service_tasks_with_containers(service_id)

    context = {
        'service': service_details['service'],
        'service_id': service_id,
        'logs_data': logs_data,
        'tasks': tasks,
        'lines_requested': lines,
        'since_requested': since,
    }

    return render(request, 'dashboard/service_logs.html', context)


@login_required
def api_service_logs(request, service_id):
    """API endpoint for service logs"""
    docker_manager = DockerSwarmManager()

    lines = int(request.GET.get('lines', 100))
    since = request.GET.get('since', '')

    logs_data = docker_manager.get_service_logs(service_id, lines=lines, since=since or None)

    return JsonResponse(logs_data)


@login_required
def api_container_logs(request, container_id):
    """API endpoint for container logs"""
    docker_manager = DockerSwarmManager()

    lines = int(request.GET.get('lines', 100))
    since = request.GET.get('since', '')

    logs_data = docker_manager.get_container_logs(container_id, lines=lines, since=since or None)

    return JsonResponse(logs_data)


@login_required
def service_groups_view(request):
    """Manage service groups"""
    from .models import ServiceGroup

    groups = ServiceGroup.objects.all()

    context = {
        'groups': groups,
    }

    return render(request, 'dashboard/service_groups.html', context)


@login_required
def stacks_view(request):
    """View and manage Docker Compose stacks"""
    from .models import ComposeStack
    import yaml

    if request.method == 'POST':
        stack_name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        compose_content = request.POST.get('compose_content', '').strip()

        if not stack_name:
            messages.error(request, 'Stack name is required')
        elif not compose_content:
            messages.error(request, 'Compose content is required')
        else:
            try:
                # Validate YAML content
                yaml.safe_load(compose_content)
                
                # Create stack
                stack = ComposeStack.objects.create(
                    name=stack_name,
                    description=description,
                    compose_content=compose_content,
                    created_by=request.user
                )
                
                # Update metadata
                stack.update_metadata()
                
                messages.success(request, f'Stack "{stack_name}" created successfully')
                return redirect('dashboard:stack_detail', stack_id=stack.id)
                
            except yaml.YAMLError as e:
                messages.error(request, f'Invalid YAML format: {str(e)}')
            except Exception as e:
                messages.error(request, f'Error creating stack: {str(e)}')

    stacks = ComposeStack.objects.all().order_by('-created_at')

    context = {
        'stacks': stacks,
    }

    return render(request, 'dashboard/stacks.html', context)


@login_required
def save_compose_as_stack_view(request):
    """Save imported compose data as an editable stack"""
    from .models import ComposeStack
    import yaml

    compose_data = request.session.get('compose_import')

    if not compose_data:
        messages.error(request, 'No compose data found. Please import a compose file first.')
        return redirect('dashboard:import_compose')

    if request.method == 'POST':
        stack_name = request.POST.get('stack_name', '').strip()
        description = request.POST.get('description', '').strip()

        if not stack_name:
            messages.error(request, 'Stack name is required')
            return render(request, 'dashboard/save_compose_stack.html', {
                'metadata': compose_data['metadata']
            })

        try:
            # Convert services back to compose format
            services_dict = {}
            for service in compose_data['services']:
                service_config = {
                    'image': service['image'],
                }

                if service.get('replicas', 1) != 1:
                    service_config['deploy'] = {'replicas': service['replicas']}

                if service.get('ports'):
                    service_config['ports'] = []
                    for port in service['ports']:
                        if port.get('published_port') and port.get('target_port'):
                            service_config['ports'].append(f"{port['published_port']}:{port['target_port']}")

                if service.get('environment'):
                    service_config['environment'] = service['environment']

                if service.get('volumes'):
                    service_config['volumes'] = []
                    for vol in service['volumes']:
                        service_config['volumes'].append(f"{vol['source']}:{vol['target']}")

                if service.get('networks'):
                    service_config['networks'] = service['networks']

                services_dict[service['name']] = service_config

            # Build complete compose structure
            compose_structure = {
                'version': '3.8',
                'services': services_dict
            }

            if compose_data['metadata'].get('networks'):
                compose_structure['networks'] = {
                    net: {} for net in compose_data['metadata']['networks']
                }

            if compose_data['metadata'].get('volumes'):
                compose_structure['volumes'] = {
                    vol: {} for vol in compose_data['metadata']['volumes']
                }

            # Convert to YAML
            compose_yaml = yaml.dump(compose_structure, default_flow_style=False, sort_keys=False)

            # Create stack
            stack = ComposeStack.objects.create(
                name=stack_name,
                description=description,
                compose_content=compose_yaml,
                source_repository=compose_data['metadata'].get('repository_url', ''),
                source_branch=compose_data['metadata'].get('branch', ''),
                created_by=request.user
            )

            stack.update_metadata()

            # Clear session data
            del request.session['compose_import']

            messages.success(request, f'Stack "{stack_name}" saved successfully')
            return redirect('dashboard:stacks')

        except Exception as e:
            messages.error(request, f'Error saving stack: {str(e)}')

    context = {
        'metadata': compose_data['metadata'],
        'services_count': len(compose_data['services'])
    }

    return render(request, 'dashboard/save_compose_stack.html', context)


@login_required
def stack_detail_view(request, stack_id):
    """View stack details"""
    from .models import ComposeStack
    from django.shortcuts import get_object_or_404
    
    stack = get_object_or_404(ComposeStack, id=stack_id)
    
    context = {
        'stack': stack,
    }
    
    return render(request, 'dashboard/stack_detail.html', context)


@login_required
def stack_edit_view(request, stack_id):
    """Edit a stack"""
    from .models import ComposeStack
    from django.shortcuts import get_object_or_404
    import yaml
    
    stack = get_object_or_404(ComposeStack, id=stack_id)
    
    if request.method == 'POST':
        stack_name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        compose_content = request.POST.get('compose_content', '').strip()
        
        if not stack_name:
            messages.error(request, 'Stack name is required')
        elif not compose_content:
            messages.error(request, 'Compose content is required')
        else:
            try:
                # Validate YAML content
                yaml.safe_load(compose_content)
                
                # Update stack
                stack.name = stack_name
                stack.description = description
                stack.compose_content = compose_content
                stack.save()
                
                # Update metadata
                stack.update_metadata()
                
                messages.success(request, f'Stack "{stack_name}" updated successfully')
                return redirect('dashboard:stack_detail', stack_id=stack.id)
                
            except yaml.YAMLError as e:
                messages.error(request, f'Invalid YAML format: {str(e)}')
            except Exception as e:
                messages.error(request, f'Error updating stack: {str(e)}')
    
    context = {
        'stack': stack,
    }
    
    return render(request, 'dashboard/stack_edit.html', context)


@login_required
def stack_deploy_view(request, stack_id):
    """Deploy a stack"""
    from .models import ComposeStack
    from django.shortcuts import get_object_or_404
    import yaml
    import tempfile
    import subprocess
    import os
    
    stack = get_object_or_404(ComposeStack, id=stack_id)
    
    if request.method == 'POST':
        try:
            # Create temporary compose file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as temp_file:
                temp_file.write(stack.compose_content)
                temp_file_path = temp_file.name
            
            try:
                # Deploy using docker stack deploy
                result = subprocess.run([
                    'docker', 'stack', 'deploy', 
                    '--compose-file', temp_file_path,
                    stack.name
                ], capture_output=True, text=True, check=True)
                
                # Update stack status
                stack.status = 'deployed'
                stack.last_deployed = timezone.now()
                stack.save()
                
                messages.success(request, f'Stack "{stack.name}" deployed successfully')
                
            finally:
                # Clean up temporary file
                os.unlink(temp_file_path)
                
        except subprocess.CalledProcessError as e:
            messages.error(request, f'Failed to deploy stack: {e.stderr}')
            stack.status = 'failed'
            stack.save()
        except Exception as e:
            messages.error(request, f'Error during deployment: {str(e)}')
            stack.status = 'failed'
            stack.save()
    
    return redirect('dashboard:stack_detail', stack_id=stack.id)


@login_required
def stack_delete_view(request, stack_id):
    """Delete a stack"""
    from .models import ComposeStack
    from django.shortcuts import get_object_or_404
    
    stack = get_object_or_404(ComposeStack, id=stack_id)
    
    if request.method == 'POST':
        try:
            stack_name = stack.name
            
            # Try to remove from Docker Swarm if deployed
            if stack.status == 'deployed':
                try:
                    subprocess.run(['docker', 'stack', 'rm', stack.name], 
                                 capture_output=True, text=True, check=True)
                except subprocess.CalledProcessError:
                    # Continue with deletion even if stack removal fails
                    pass
            
            # Delete from database
            stack.delete()
            
            messages.success(request, f'Stack "{stack_name}" deleted successfully')
            
        except Exception as e:
            messages.error(request, f'Error deleting stack: {str(e)}')
    
    return redirect('dashboard:stacks')

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import json

User = get_user_model()


class ServiceGroup(models.Model):
    """Group services together for better organization"""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#007bff', help_text='Hex color code')
    icon = models.CharField(max_length=50, default='bi-folder', help_text='Bootstrap icon class')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_services_count(self):
        """Get count of services in this group"""
        return self.service_group_mappings.count()


class ServiceGroupMapping(models.Model):
    """Map services to groups"""
    
    group = models.ForeignKey(ServiceGroup, on_delete=models.CASCADE, related_name='service_group_mappings')
    service_name = models.CharField(max_length=100)  # Docker service name
    service_id = models.CharField(max_length=100, blank=True)  # Docker service ID
    added_by = models.ForeignKey(User, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['group', 'service_name']
        ordering = ['service_name']
    
    def __str__(self):
        return f"{self.group.name} -> {self.service_name}"


class ComposeStack(models.Model):
    """Store Docker Compose configurations for editing and re-deployment"""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    compose_content = models.TextField(help_text='Docker Compose YAML content')
    original_content = models.TextField(help_text='Original imported content', blank=True)
    source_repository = models.URLField(blank=True, help_text='Git repository URL if imported')
    source_branch = models.CharField(max_length=100, blank=True)
    source_path = models.CharField(max_length=500, blank=True)
    
    # Metadata
    services_count = models.IntegerField(default=0)
    networks_list = models.JSONField(default=list, blank=True)
    volumes_list = models.JSONField(default=list, blank=True)
    
    # Management
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_deployed = models.DateTimeField(null=True, blank=True)
    deployed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='deployed_stacks')
    
    # Status
    DRAFT = 'draft'
    DEPLOYED = 'deployed'
    FAILED = 'failed'
    STATUS_CHOICES = [
        (DRAFT, 'Draft'),
        (DEPLOYED, 'Deployed'),
        (FAILED, 'Failed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=DRAFT)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return self.name
    
    def get_compose_data(self):
        """Parse compose content as YAML"""
        try:
            import yaml
            return yaml.safe_load(self.compose_content)
        except Exception:
            return {}
    
    def update_metadata(self):
        """Update metadata from compose content"""
        try:
            compose_data = self.get_compose_data()
            services = compose_data.get('services', {})
            networks = compose_data.get('networks', {})
            volumes = compose_data.get('volumes', {})
            
            self.services_count = len(services)
            self.networks_list = list(networks.keys())
            self.volumes_list = list(volumes.keys())
            self.save()
        except Exception:
            pass


class ServiceLog(models.Model):
    """Store service log entries for better log management"""
    
    service_name = models.CharField(max_length=100, db_index=True)
    service_id = models.CharField(max_length=100, db_index=True)
    container_id = models.CharField(max_length=100, blank=True, db_index=True)
    timestamp = models.DateTimeField(db_index=True)
    level = models.CharField(max_length=20, default='info', db_index=True)
    message = models.TextField()
    source = models.CharField(max_length=10, choices=[('stdout', 'stdout'), ('stderr', 'stderr')], default='stdout')
    
    # Metadata
    node_id = models.CharField(max_length=100, blank=True)
    task_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['service_name', '-timestamp']),
            models.Index(fields=['service_id', '-timestamp']),
            models.Index(fields=['level', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.service_name} - {self.timestamp} - {self.level}"
    
    @classmethod
    def cleanup_old_logs(cls, days=7):
        """Remove logs older than specified days"""
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        return cls.objects.filter(created_at__lt=cutoff_date).delete()


class DeploymentHistory(models.Model):
    """Track deployment history for stacks"""
    
    stack = models.ForeignKey(ComposeStack, on_delete=models.CASCADE, related_name='deployments')
    deployed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    deployed_at = models.DateTimeField(auto_now_add=True)
    
    # Deployment details
    services_deployed = models.JSONField(default=list)
    services_failed = models.JSONField(default=list)
    deployment_log = models.TextField(blank=True)
    
    # Status
    SUCCESS = 'success'
    PARTIAL = 'partial'
    FAILED = 'failed'
    STATUS_CHOICES = [
        (SUCCESS, 'Success'),
        (PARTIAL, 'Partial'),
        (FAILED, 'Failed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=SUCCESS)
    
    class Meta:
        ordering = ['-deployed_at']
    
    def __str__(self):
        return f"{self.stack.name} - {self.deployed_at} - {self.status}"
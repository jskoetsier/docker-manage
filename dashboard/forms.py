from django import forms
from .models import ServiceGroup, ComposeStack


class ServiceGroupForm(forms.ModelForm):
    """Form for creating/editing service groups"""
    
    class Meta:
        model = ServiceGroup
        fields = ['name', 'description', 'color', 'icon']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Group name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional description'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'icon': forms.Select(choices=[
                ('bi-folder', 'Folder'),
                ('bi-collection', 'Collection'),
                ('bi-stack', 'Stack'),
                ('bi-layers', 'Layers'),
                ('bi-boxes', 'Boxes'),
                ('bi-grid-3x3', 'Grid'),
                ('bi-diagram-3', 'Diagram'),
                ('bi-server', 'Server'),
                ('bi-cloud', 'Cloud'),
                ('bi-database', 'Database'),
            ], attrs={'class': 'form-select'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].required = False
        self.fields['name'].help_text = 'Unique name for the service group'
        self.fields['color'].help_text = 'Color for the group badge'
        self.fields['icon'].help_text = 'Icon to display with the group'


class ComposeStackForm(forms.ModelForm):
    """Form for creating/editing Docker Compose stacks"""
    
    class Meta:
        model = ComposeStack
        fields = ['name', 'description', 'compose_content']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Stack name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional description'}),
            'compose_content': forms.Textarea(attrs={'class': 'form-control', 'rows': 20, 'style': 'font-family: monospace;'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].required = False
        self.fields['name'].help_text = 'Unique name for the Docker Compose stack'
        self.fields['compose_content'].help_text = 'Docker Compose YAML content'


class LogFilterForm(forms.Form):
    """Form for filtering service logs"""
    
    LEVEL_CHOICES = [
        ('', 'All Levels'),
        ('debug', 'Debug'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]
    
    lines = forms.IntegerField(
        initial=100,
        min_value=10,
        max_value=1000,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    since = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '2023-01-01T00:00:00Z or 1h or 30m'
        })
    )
    
    level = forms.ChoiceField(
        choices=LEVEL_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search in log messages'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['lines'].help_text = 'Number of recent log lines to display (10-1000)'
        self.fields['since'].help_text = 'Show logs since this time (ISO format, duration like "1h", or empty for all)'
        self.fields['level'].help_text = 'Filter by log level'
        self.fields['search'].help_text = 'Search for text in log messages'
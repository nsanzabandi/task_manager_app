from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import authenticate
from django.db.models import Q, Case, When, IntegerField
from django.contrib.auth import get_user_model
from .models import User, Task, Comment, Division, Project, ProjectFile
# REMOVED: from ckeditor.widgets import CKEditorWidget  # Remove this line
from tinymce.widgets import TinyMCE  # Add this for TinyMCE

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    division = forms.ModelChoiceField(queryset=Division.objects.all(), required=True)
    phone = forms.CharField(max_length=20, required=False)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'division', 'phone', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            if field_name in ['password1', 'password2']:
                field.widget.attrs['placeholder'] = field.label

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_active = False  # 🔒 Inactive until approved by admin
        if commit:
            user.save()
        return user


class CustomAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            field.widget.attrs['placeholder'] = field.label
            
class TaskForm(forms.ModelForm):
    due_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        required=False
    )
    
    assigned_to = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=True,
        help_text="Select one or more users to assign this task to"
    )

    class Meta:
        model = Task
        # REMOVED division from fields - it will be set automatically
        fields = ['title', 'description', 'status', 'due_date', 'priority', 'assigned_to', 'estimated_hours']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Task title'}),
            'description': TinyMCE(attrs={'cols': 80, 'rows': 30}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'estimated_hours': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)

        # Store for later use
        self._project = project
        self._user = user

        # Handle status field for new vs existing tasks
        if not self.instance.pk:  # Creating new task
            self.fields['status'].widget = forms.HiddenInput()
            self.fields['status'].initial = 'pending'
            self.fields['status'].required = False
        else:
            self.fields['status'].widget.attrs.update({'class': 'form-control'})
            self.fields['status'].required = True

        # Handle project field if task is within a project
        if project:
            self.fields['project'] = forms.ModelChoiceField(
                queryset=Project.objects.filter(id=project.id),
                initial=project,
                widget=forms.HiddenInput(),
                required=True
            )
        else:
            # For independent tasks, admins can optionally select a project
            if user and user.is_admin():
                self.fields['project'] = forms.ModelChoiceField(
                    queryset=Project.objects.none(),
                    required=False,
                    empty_label="No Project (Independent Task)",
                    widget=forms.Select(attrs={'class': 'form-control'})
                )
                
                # Set project queryset based on permissions
                if user.is_super_admin():
                    self.fields['project'].queryset = Project.objects.all()
                elif user.is_admin():
                    self.fields['project'].queryset = Project.objects.filter(
                        Q(assigned_to_admin=user) | Q(division=user.division)
                    )

        # Add form-control class to fields
        for field_name, field in self.fields.items():
            if field_name not in ['assigned_to', 'description']:
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-control'

        # Set up user filtering logic
        if user:
            try:
                available_users = User.objects.filter(is_active=True)
                
                if user.is_super_admin():
                    if project:
                        # Prioritize users from project's division
                        self.fields['assigned_to'].queryset = available_users.order_by(
                            Case(
                                When(division=project.division, then=0),
                                default=1,
                                output_field=IntegerField()
                            ),
                            'first_name', 'last_name'
                        )
                    else:
                        self.fields['assigned_to'].queryset = available_users.order_by('first_name', 'last_name')
                        
                elif user.is_admin():
                    if project and project.division:
                        # Tasks in projects: assign to project division users
                        self.fields['assigned_to'].queryset = available_users.filter(
                            division=project.division
                        ).order_by('first_name', 'last_name')
                    elif user.division:
                        # Independent tasks: assign to their division users
                        self.fields['assigned_to'].queryset = available_users.filter(
                            division=user.division
                        ).order_by('first_name', 'last_name')
                    else:
                        self.fields['assigned_to'].queryset = available_users.order_by('first_name', 'last_name')
                        
                else:
                    # Regular users
                    if project:
                        # In project context: can assign to project division users
                        if project.division:
                            self.fields['assigned_to'].queryset = available_users.filter(
                                division=project.division
                            ).order_by('first_name', 'last_name')
                        else:
                            # Project without division - fallback to user's division
                            if user.division:
                                self.fields['assigned_to'].queryset = available_users.filter(
                                    division=user.division
                                ).order_by('first_name', 'last_name')
                            else:
                                self.fields['assigned_to'].queryset = available_users.order_by('first_name', 'last_name')
                        
                        # Always include the current user
                        current_user_qs = User.objects.filter(id=user.id)
                        self.fields['assigned_to'].queryset = (
                            self.fields['assigned_to'].queryset | current_user_qs
                        ).distinct().order_by('first_name', 'last_name')
                    else:
                        # Independent tasks: can assign to division colleagues
                        if user.division:
                            self.fields['assigned_to'].queryset = available_users.filter(
                                division=user.division
                            ).order_by('first_name', 'last_name')
                        else:
                            # User without division can only assign to themselves
                            self.fields['assigned_to'].queryset = User.objects.filter(id=user.id)
                    
                    # Pre-select current user for convenience
                    self.fields['assigned_to'].initial = [user]
                    
            except Exception as e:
                # Fallback queryset
                self.fields['assigned_to'].queryset = User.objects.filter(
                    is_active=True
                ).order_by('first_name', 'last_name')
                print(f"TaskForm user filtering error: {e}")

        # Set help text based on context
        if project and project.division:
            self.fields['assigned_to'].help_text = f"Select users from {project.division.name} division to assign this task to"
        elif project:
            self.fields['assigned_to'].help_text = "Select users to assign this task to"
        else:
            self.fields['assigned_to'].help_text = "Select one or more users to assign this task to"
        
        # Set field labels
        self.fields['title'].label = "Task Title"
        self.fields['description'].label = "Task Description"
        self.fields['due_date'].label = "Due Date & Time"
        self.fields['estimated_hours'].label = "Estimated Hours"
        self.fields['status'].label = "Status"

    def clean(self):
        cleaned_data = super().clean()
        
        # Basic validation
        title = cleaned_data.get('title')
        assigned_to = cleaned_data.get('assigned_to')
        
        if title and len(title.strip()) < 3:
            raise forms.ValidationError("Task title must be at least 3 characters long.")
        
        if not assigned_to:
            raise forms.ValidationError("Please select at least one user to assign this task to.")
        
        # Set status for new tasks
        if not self.instance.pk:
            cleaned_data['status'] = 'pending'
            
        return cleaned_data

    def clean_assigned_to(self):
        assigned_to = self.cleaned_data.get('assigned_to')
        if not assigned_to:
            raise forms.ValidationError("At least one user must be assigned to this task.")
        
        if assigned_to.count() > 10:
            raise forms.ValidationError("Cannot assign more than 10 users to a single task.")
        
        return assigned_to

    def clean_title(self):
        title = self.cleaned_data.get('title')
        if title:
            title = title.strip()
            if len(title) < 3:
                raise forms.ValidationError("Task title must be at least 3 characters long.")
            if len(title) > 200:
                raise forms.ValidationError("Task title cannot exceed 200 characters.")
        return title

    def clean_estimated_hours(self):
        estimated_hours = self.cleaned_data.get('estimated_hours')
        if estimated_hours is not None:
            if estimated_hours < 0:
                raise forms.ValidationError("Estimated hours cannot be negative.")
            if estimated_hours > 999:
                raise forms.ValidationError("Estimated hours cannot exceed 999.")
        return estimated_hours

    def clean_due_date(self):
        due_date = self.cleaned_data.get('due_date')
        if due_date:
            from django.utils import timezone
            if not self.instance.pk and due_date < timezone.now():
                raise forms.ValidationError("Due date cannot be in the past for new tasks.")
        return due_date

    def save(self, commit=True):
        task = super().save(commit=False)
        
        # Ensure new tasks start with 'pending' status
        if not task.pk:
            task.status = 'pending'
        
        # SIMPLE DIVISION LOGIC - Following your business rules
        if not task.pk:  # New task
            if self._project and self._project.division:
                # Task in project → Use project's division
                task.division = self._project.division
            elif self._user and self._user.division:
                # Individual task → Use user's division
                task.division = self._user.division
            else:
                # Fallback error - this shouldn't happen in normal workflow
                raise forms.ValidationError(
                    "Cannot determine division: Project has no division and user has no division assigned. "
                    "Please contact administrator."
                )
        
        # Set project if provided
        if self._project and not task.project:
            task.project = self._project
            
        if commit:
            task.save()
            self.save_m2m()
        return task

    def set_project(self, project):
        """Helper method to set project after form initialization"""
        self._project = project
        
    def set_user(self, user):
        """Helper method to set user context"""
        self._user = user
               
class TaskUpdateForm(forms.ModelForm):
    actual_hours = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'})
    )
    
    class Meta:
        model = Task
        fields = ['status', 'actual_hours']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content', 'is_internal']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'Add your comment...'
            }),
            'is_internal': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Only admins can create internal comments
        if user and not user.is_admin():
            self.fields.pop('is_internal')


class TaskFilterForm(forms.Form):
    STATUS_CHOICES = [('', 'All Statuses')] + Task.STATUS_CHOICES
    PRIORITY_CHOICES = [('', 'All Priorities')] + Task.PRIORITY_CHOICES
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES, 
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    priority = forms.ChoiceField(
        choices=PRIORITY_CHOICES, 
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        empty_label="All Users",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user and user.division:
            # Filter users by division for non-super admins
            if not user.is_super_admin():
                self.fields['assigned_to'].queryset = User.objects.filter(division=user.division)


class UserManagementForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'division', 'role', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'division': forms.Select(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class DivisionForm(forms.ModelForm):
    class Meta:
        model = Division
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Division Name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description (optional)'}),
        }


User = get_user_model()

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['title', 'description', 'division', 'assigned_to_admin']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Project Title'}),
            # FIXED: Use TinyMCE widget for project description
            'description': TinyMCE(attrs={'cols': 80, 'rows': 30}),
            'division': forms.Select(attrs={'class': 'form-control', 'id': 'id_division'}),
            'assigned_to_admin': forms.Select(attrs={'class': 'form-control', 'id': 'id_assigned_to_admin'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Add form-control class to all fields except TinyMCE
        for field_name, field in self.fields.items():
            if field_name != 'description' and 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
        
        try:
            if user and user.is_super_admin():
                # Super admin can select any division and any admin
                self.fields['division'].queryset = Division.objects.all()
                # Initially show all admins, will be filtered by JavaScript
                self.fields['assigned_to_admin'].queryset = User.objects.filter(
                    role__in=['admin', 'super_admin'],
                    is_active=True
                ).select_related('division')
                
                # Add empty option
                self.fields['assigned_to_admin'].empty_label = "Select Admin (choose division first)"
                
            elif user and user.is_admin():
                # Regular admin can only assign to their division
                if user.division:
                    self.fields['division'].queryset = Division.objects.filter(id=user.division.id)
                    self.fields['division'].initial = user.division
                    self.fields['assigned_to_admin'].queryset = User.objects.filter(
                        division=user.division,
                        role__in=['admin', 'super_admin'],
                        is_active=True
                    )
                else:
                    # Admin without division - show all but warn
                    self.fields['division'].queryset = Division.objects.all()
                    self.fields['assigned_to_admin'].queryset = User.objects.filter(
                        role__in=['admin', 'super_admin'],
                        is_active=True
                    )
            else:
                # Non-admin users should not access this form
                self.fields['division'].queryset = Division.objects.none()
                self.fields['assigned_to_admin'].queryset = User.objects.none()
                
        except Exception as e:
            # Fallback querysets
            self.fields['division'].queryset = Division.objects.all()
            self.fields['assigned_to_admin'].queryset = User.objects.filter(
                role__in=['admin', 'super_admin'],
                is_active=True
            )

    def clean(self):
        cleaned_data = super().clean()
        division = cleaned_data.get('division')
        assigned_to_admin = cleaned_data.get('assigned_to_admin')
        
        # Validate that the selected admin belongs to the selected division
        if division and assigned_to_admin:
            if assigned_to_admin.division != division:
                raise forms.ValidationError(
                    f"Selected admin ({assigned_to_admin.get_display_name()}) "
                    f"does not belong to division '{division.name}'. "
                    f"Please select an admin from the chosen division."
                )
        
        return cleaned_data
         
class ProjectFileForm(forms.ModelForm):
    class Meta:
        model = ProjectFile
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control'})
        }
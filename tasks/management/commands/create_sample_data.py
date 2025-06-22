from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from tasks.models import Division, Task, Comment
from datetime import datetime, timedelta
from django.utils import timezone

User = get_user_model()


class Command(BaseCommand):
    help = 'Create sample data for testing the task management system'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating sample data...'))
        
        # Set password for admin user
        try:
            admin_user = User.objects.get(username='admin')
            admin_user.set_password('admin123')
            admin_user.first_name = 'Admin'
            admin_user.last_name = 'User'
            admin_user.role = 'super_admin'
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('Admin user password set to: admin123'))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('Admin user not found'))
            return
        
        # Create divisions
        divisions_data = [
            {'name': 'Engineering', 'description': 'Software development and technical operations'},
            {'name': 'Marketing', 'description': 'Marketing and promotional activities'},
            {'name': 'Sales', 'description': 'Sales and customer relations'},
            {'name': 'HR', 'description': 'Human resources and administration'},
            {'name': 'Finance', 'description': 'Financial planning and accounting'},
        ]
        
        divisions = []
        for div_data in divisions_data:
            division, created = Division.objects.get_or_create(
                name=div_data['name'],
                defaults={'description': div_data['description']}
            )
            divisions.append(division)
            if created:
                self.stdout.write(f'Created division: {division.name}')
        
        # Create sample users
        users_data = [
            {
                'username': 'john_doe',
                'email': 'john@example.com',
                'first_name': 'John',
                'last_name': 'Doe',
                'division': divisions[0],  # Engineering
                'role': 'admin',
                'password': 'password123'
            },
            {
                'username': 'jane_smith',
                'email': 'jane@example.com',
                'first_name': 'Jane',
                'last_name': 'Smith',
                'division': divisions[0],  # Engineering
                'role': 'user',
                'password': 'password123'
            },
            {
                'username': 'mike_wilson',
                'email': 'mike@example.com',
                'first_name': 'Mike',
                'last_name': 'Wilson',
                'division': divisions[1],  # Marketing
                'role': 'admin',
                'password': 'password123'
            },
            {
                'username': 'sarah_jones',
                'email': 'sarah@example.com',
                'first_name': 'Sarah',
                'last_name': 'Jones',
                'division': divisions[1],  # Marketing
                'role': 'user',
                'password': 'password123'
            },
            {
                'username': 'david_brown',
                'email': 'david@example.com',
                'first_name': 'David',
                'last_name': 'Brown',
                'division': divisions[2],  # Sales
                'role': 'user',
                'password': 'password123'
            },
        ]
        
        users = []
        for user_data in users_data:
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'email': user_data['email'],
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                    'division': user_data['division'],
                    'role': user_data['role'],
                }
            )
            if created:
                user.set_password(user_data['password'])
                user.save()
                users.append(user)
                self.stdout.write(f'Created user: {user.username}')
        
        # Add admin user to the list
        users.append(admin_user)
        
        # Create sample tasks
        tasks_data = [
            {
                'title': 'Implement user authentication system',
                'description': 'Design and implement a secure user authentication system with login, logout, and registration functionality.',
                'status': 'in_progress',
                'priority': 'high',
                'created_by': admin_user,
                'assigned_to': users[1] if len(users) > 1 else admin_user,
                'division': divisions[0],
                'estimated_hours': 40,
                'due_date': timezone.now() + timedelta(days=7)
            },
            {
                'title': 'Create marketing campaign for Q4',
                'description': 'Develop a comprehensive marketing campaign strategy for the fourth quarter including social media, email marketing, and advertising.',
                'status': 'pending',
                'priority': 'medium',
                'created_by': admin_user,
                'assigned_to': users[3] if len(users) > 3 else admin_user,
                'division': divisions[1],
                'estimated_hours': 60,
                'due_date': timezone.now() + timedelta(days=14)
            },
            {
                'title': 'Update database schema',
                'description': 'Update the database schema to support new features and optimize performance.',
                'status': 'completed',
                'priority': 'high',
                'created_by': admin_user,
                'assigned_to': users[0] if len(users) > 0 else admin_user,
                'division': divisions[0],
                'estimated_hours': 20,
                'actual_hours': 18,
                'due_date': timezone.now() - timedelta(days=2),
                'completed_at': timezone.now() - timedelta(days=1)
            },
            {
                'title': 'Prepare sales presentation',
                'description': 'Create a compelling sales presentation for potential clients showcasing our products and services.',
                'status': 'pending',
                'priority': 'medium',
                'created_by': admin_user,
                'assigned_to': users[4] if len(users) > 4 else admin_user,
                'division': divisions[2],
                'estimated_hours': 15,
                'due_date': timezone.now() + timedelta(days=5)
            },
            {
                'title': 'Fix critical bug in payment system',
                'description': 'Investigate and fix the critical bug that is preventing users from completing payments.',
                'status': 'in_progress',
                'priority': 'urgent',
                'created_by': admin_user,
                'assigned_to': users[1] if len(users) > 1 else admin_user,
                'division': divisions[0],
                'estimated_hours': 8,
                'due_date': timezone.now() + timedelta(days=1)
            },
            {
                'title': 'Conduct user research survey',
                'description': 'Design and conduct a user research survey to gather feedback on our current products.',
                'status': 'pending',
                'priority': 'low',
                'created_by': admin_user,
                'assigned_to': users[2] if len(users) > 2 else admin_user,
                'division': divisions[1],
                'estimated_hours': 25,
                'due_date': timezone.now() + timedelta(days=21)
            },
        ]
        
        tasks = []
        for task_data in tasks_data:
            task, created = Task.objects.get_or_create(
                title=task_data['title'],
                defaults=task_data
            )
            if created:
                tasks.append(task)
                self.stdout.write(f'Created task: {task.title}')
        
        # Create sample comments
        comments_data = [
            {
                'task': tasks[0] if tasks else None,
                'user': admin_user,
                'content': 'This is a high priority task. Please ensure all security best practices are followed.',
                'is_internal': True
            },
            {
                'task': tasks[0] if tasks else None,
                'user': users[1] if len(users) > 1 else admin_user,
                'content': 'I have started working on the authentication system. The basic structure is in place.',
                'is_internal': False
            },
            {
                'task': tasks[2] if len(tasks) > 2 else None,
                'user': users[0] if len(users) > 0 else admin_user,
                'content': 'Database schema update completed successfully. All tests are passing.',
                'is_internal': False
            },
            {
                'task': tasks[4] if len(tasks) > 4 else None,
                'user': admin_user,
                'content': 'This bug is affecting customer payments. Please prioritize this task.',
                'is_internal': True
            },
        ]
        
        for comment_data in comments_data:
            if comment_data['task']:
                comment, created = Comment.objects.get_or_create(
                    task=comment_data['task'],
                    user=comment_data['user'],
                    content=comment_data['content'],
                    defaults={'is_internal': comment_data['is_internal']}
                )
                if created:
                    self.stdout.write(f'Created comment for task: {comment.task.title}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Sample data created successfully!\n'
                f'- {len(divisions)} divisions\n'
                f'- {len(users)} users\n'
                f'- {len(tasks)} tasks\n'
                f'- {len(comments_data)} comments\n\n'
                f'Login credentials:\n'
                f'Admin: admin / admin123\n'
                f'Users: john_doe, jane_smith, mike_wilson, sarah_jones, david_brown / password123'
            )
        )


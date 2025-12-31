"""
Management command to fix criteria names with missing closing parentheses.

Usage:
    python manage.py fix_criterion_parentheses
    python manage.py fix_criterion_parentheses --dry-run
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from frameworks.models import Criterion


class Command(BaseCommand):
    help = 'Fix criteria names with missing closing parentheses'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be saved'))
        
        # Find all criteria with mismatched parentheses
        all_criteria = Criterion.objects.all()
        fixed_count = 0
        would_fix_count = 0
        
        for criterion in all_criteria:
            name = criterion.name
            open_count = name.count('(')
            close_count = name.count(')')
            
            if open_count > close_count:
                # Missing closing parentheses
                missing = open_count - close_count
                fixed_name = name + ')' * missing
                
                if dry_run:
                    would_fix_count += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f'Would fix: "{name}" -> "{fixed_name}"'
                        )
                    )
                else:
                    # Check if the fixed name already exists for this framework
                    existing = Criterion.objects.filter(
                        framework=criterion.framework,
                        name=fixed_name
                    ).exclude(id=criterion.id).first()
                    
                    if existing:
                        self.stdout.write(
                            self.style.WARNING(
                                f'Skipping "{name}" - fixed name "{fixed_name}" already exists for framework {criterion.framework.name}'
                            )
                        )
                    else:
                        criterion.name = fixed_name
                        criterion.save()
                        fixed_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Fixed: "{name}" -> "{fixed_name}"'
                            )
                        )
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSuccessfully fixed {fixed_count} criteria with missing closing parentheses'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nFound {would_fix_count} criteria that would be fixed'
                )
            )

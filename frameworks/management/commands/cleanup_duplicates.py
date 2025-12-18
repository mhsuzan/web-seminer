"""
Management command to clean up duplicate frameworks, criteria, and definitions.

Usage:
    python manage.py cleanup_duplicates
    python manage.py cleanup_duplicates --dry-run
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, Q
from frameworks.models import Framework, Criterion, Definition


class Command(BaseCommand):
    help = 'Clean up duplicate frameworks, criteria, and definitions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without actually deleting data',
        )

    def normalize_name(self, name):
        """Normalize a name for comparison"""
        if not name:
            return ''
        return ' '.join(name.lower().strip().split())

    def normalize_criterion_name(self, name):
        """Normalize criterion name for comparison"""
        if not name:
            return ''
        normalized = ' '.join(name.strip().split())
        if normalized:
            normalized = normalized[0].upper() + normalized[1:] if len(normalized) > 1 else normalized.upper()
        return normalized

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No data will be deleted'))
        
        with transaction.atomic():
            # Clean up duplicate frameworks
            frameworks_merged = self.cleanup_duplicate_frameworks(dry_run)
            
            # Clean up duplicate criteria
            criteria_merged = self.cleanup_duplicate_criteria(dry_run)
            
            # Clean up duplicate definitions
            definitions_removed = self.cleanup_duplicate_definitions(dry_run)
            
            if not dry_run:
                self.stdout.write(self.style.SUCCESS(
                    f'Cleanup complete: Merged {frameworks_merged} frameworks, '
                    f'{criteria_merged} criteria, removed {definitions_removed} duplicate definitions'
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f'Would merge {frameworks_merged} frameworks, '
                    f'{criteria_merged} criteria, remove {definitions_removed} duplicate definitions'
                ))

    def cleanup_duplicate_frameworks(self, dry_run):
        """Merge duplicate frameworks"""
        merged_count = 0
        
        # Find frameworks with duplicate names (normalized)
        all_frameworks = Framework.objects.all()
        framework_groups = {}
        
        for framework in all_frameworks:
            normalized_name = self.normalize_name(framework.name)
            if normalized_name not in framework_groups:
                framework_groups[normalized_name] = []
            framework_groups[normalized_name].append(framework)
        
        # Merge groups with multiple frameworks
        for normalized_name, frameworks in framework_groups.items():
            if len(frameworks) > 1:
                # Sort by creation date (keep oldest) and data completeness
                frameworks.sort(key=lambda f: (
                    f.created_at,
                    -sum([
                        1 if f.authors else 0,
                        1 if f.year else 0,
                        1 if f.title else 0,
                        1 if f.description else 0,
                    ])
                ))
                
                # Keep the first (oldest, most complete) framework
                primary = frameworks[0]
                duplicates = frameworks[1:]
                
                self.stdout.write(f'Merging {len(duplicates)} duplicate(s) into: {primary.name}')
                
                for duplicate in duplicates:
                    # Merge data from duplicate into primary
                    if not primary.authors and duplicate.authors:
                        primary.authors = duplicate.authors
                    if not primary.year and duplicate.year:
                        primary.year = duplicate.year
                    if not primary.title and duplicate.title:
                        primary.title = duplicate.title
                    if not primary.description and duplicate.description:
                        primary.description = duplicate.description
                    elif duplicate.description and len(duplicate.description) > len(primary.description):
                        primary.description = duplicate.description
                    if not primary.objectives and duplicate.objectives:
                        primary.objectives = duplicate.objectives
                    elif duplicate.objectives and len(duplicate.objectives) > len(primary.objectives):
                        primary.objectives = duplicate.objectives
                    if not primary.methodology and duplicate.methodology:
                        primary.methodology = duplicate.methodology
                    elif duplicate.methodology and len(duplicate.methodology) > len(primary.methodology):
                        primary.methodology = duplicate.methodology
                    if not primary.algorithm_used and duplicate.algorithm_used:
                        primary.algorithm_used = duplicate.algorithm_used
                    if not primary.top_model and duplicate.top_model:
                        primary.top_model = duplicate.top_model
                    if not primary.accuracy and duplicate.accuracy:
                        primary.accuracy = duplicate.accuracy
                    if not primary.advantages and duplicate.advantages:
                        primary.advantages = duplicate.advantages
                    elif duplicate.advantages and len(duplicate.advantages) > len(primary.advantages):
                        primary.advantages = duplicate.advantages
                    if not primary.drawbacks and duplicate.drawbacks:
                        primary.drawbacks = duplicate.drawbacks
                    elif duplicate.drawbacks and len(duplicate.drawbacks) > len(primary.drawbacks):
                        primary.drawbacks = duplicate.drawbacks
                    if not primary.source and duplicate.source:
                        primary.source = duplicate.source
                    
                    # Move criteria from duplicate to primary
                    for criterion in duplicate.criteria.all():
                        # Check if primary already has this criterion
                        existing = Criterion.objects.filter(
                            framework=primary,
                            name=criterion.name
                        ).first()
                        
                        if existing:
                            # Merge criterion data
                            if not existing.description and criterion.description:
                                existing.description = criterion.description
                            elif criterion.description and len(criterion.description) > len(existing.description):
                                existing.description = criterion.description
                            if not existing.category and criterion.category:
                                existing.category = criterion.category
                            existing.save()
                            
                            # Move definitions
                            for definition in criterion.definitions.all():
                                # Check for duplicate definition
                                if not Definition.objects.filter(
                                    criterion=existing,
                                    definition_text=definition.definition_text
                                ).exists():
                                    definition.criterion = existing
                                    definition.save()
                        else:
                            # Move criterion to primary
                            criterion.framework = primary
                            criterion.save()
                    
                    if not dry_run:
                        primary.save()
                        duplicate.delete()
                    merged_count += 1
        
        return merged_count

    def cleanup_duplicate_criteria(self, dry_run):
        """Merge duplicate criteria within the same framework"""
        merged_count = 0
        
        # Group criteria by framework
        frameworks = Framework.objects.prefetch_related('criteria').all()
        
        for framework in frameworks:
            criteria_groups = {}
            
            for criterion in framework.criteria.all():
                normalized_name = self.normalize_criterion_name(criterion.name)
                if normalized_name not in criteria_groups:
                    criteria_groups[normalized_name] = []
                criteria_groups[normalized_name].append(criterion)
            
            # Merge groups with multiple criteria
            for normalized_name, criteria in criteria_groups.items():
                if len(criteria) > 1:
                    # Sort by creation date and data completeness
                    criteria.sort(key=lambda c: (
                        c.created_at,
                        -sum([
                            1 if c.description else 0,
                            1 if c.category else 0,
                        ])
                    ))
                    
                    primary = criteria[0]
                    duplicates = criteria[1:]
                    
                    self.stdout.write(f'  Merging {len(duplicates)} duplicate criteria "{primary.name}" in {framework.name}')
                    
                    for duplicate in duplicates:
                        # Merge data
                        if not primary.description and duplicate.description:
                            primary.description = duplicate.description
                        elif duplicate.description and len(duplicate.description) > len(primary.description):
                            primary.description = duplicate.description
                        if not primary.category and duplicate.category:
                            primary.category = duplicate.category
                        
                        # Move definitions
                        for definition in duplicate.definitions.all():
                            if not Definition.objects.filter(
                                criterion=primary,
                                definition_text=definition.definition_text
                            ).exists():
                                definition.criterion = primary
                                definition.save()
                        
                        if not dry_run:
                            primary.save()
                            duplicate.delete()
                        merged_count += 1
        
        return merged_count

    def cleanup_duplicate_definitions(self, dry_run):
        """Remove duplicate definitions"""
        removed_count = 0
        
        criteria = Criterion.objects.prefetch_related('definitions').all()
        
        for criterion in criteria:
            definitions = list(criterion.definitions.all())
            seen_normalized = set()
            duplicates_to_remove = []
            
            for definition in definitions:
                normalized = self.normalize_name(definition.definition_text)
                
                if normalized in seen_normalized:
                    duplicates_to_remove.append(definition)
                else:
                    seen_normalized.add(normalized)
                    
                    # Also check for near-duplicates (one contains the other)
                    for other_def in definitions:
                        if other_def != definition:
                            other_normalized = self.normalize_name(other_def.definition_text)
                            if normalized in other_normalized or other_normalized in normalized:
                                if abs(len(normalized) - len(other_normalized)) < 20:
                                    # Keep the longer one
                                    if len(normalized) < len(other_normalized):
                                        duplicates_to_remove.append(definition)
                                        break
            
            if duplicates_to_remove:
                self.stdout.write(f'  Removing {len(duplicates_to_remove)} duplicate definitions for "{criterion.name}"')
                if not dry_run:
                    for dup in duplicates_to_remove:
                        dup.delete()
                removed_count += len(duplicates_to_remove)
        
        return removed_count

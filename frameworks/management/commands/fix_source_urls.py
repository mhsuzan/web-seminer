"""
Management command to fix source URLs that have "Read (URL)" format.

Usage:
    python manage.py fix_source_urls
    python manage.py fix_source_urls --dry-run
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from frameworks.models import Framework
import re


class Command(BaseCommand):
    help = 'Fix source URLs with "Read (URL)" format to use proper "Read|URL" format'

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
        
        # Find all frameworks with source containing "Read (URL)" pattern
        all_frameworks = Framework.objects.exclude(source='')
        fixed_count = 0
        would_fix_count = 0
        
        for framework in all_frameworks:
            source = framework.source
            if not source:
                continue
            
            # Check for "Read (URL)" or "Text (URL)" pattern
            read_url_pattern = re.search(r'(\w+)\s*\(((?:https?://|www\.)[^\)]+)\)', source, re.IGNORECASE)
            if read_url_pattern:
                link_text = read_url_pattern.group(1).strip()
                url = read_url_pattern.group(2).strip()
                
                # Remove closing parenthesis if it's part of the URL
                url = url.rstrip(')')
                
                # Normalize URL
                if url.startswith('www.'):
                    url = 'https://' + url
                
                # Get text before and after the pattern
                before_text = source[:read_url_pattern.start()].strip()
                after_text = source[read_url_pattern.end():].strip()
                
                # If link_text is "Read" or similar, and there's text before it, keep the before text
                # Otherwise, use the link_text
                if link_text.lower() in ['read', 'link', 'url', 'source', 'click here', 'here']:
                    if before_text:
                        # Use before_text as the link text, URL as the link
                        new_source = f"{before_text}|{url}"
                        if after_text:
                            new_source += f" {after_text}"
                    else:
                        # Just use the URL
                        new_source = url
                        if after_text:
                            new_source += f" {after_text}"
                else:
                    # Use link_text as the link text
                    if before_text:
                        new_source = f"{before_text} {link_text}|{url}"
                    else:
                        new_source = f"{link_text}|{url}"
                    if after_text:
                        new_source += f" {after_text}"
                
                # Truncate if too long (max 500 chars)
                if len(new_source) > 500:
                    new_source = new_source[:500]
                
                if dry_run:
                    would_fix_count += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f'Would fix framework "{framework.name}":\n'
                            f'  Old: {source[:100]}...\n'
                            f'  New: {new_source[:100]}...'
                        )
                    )
                else:
                    framework.source = new_source
                    framework.save()
                    fixed_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Fixed framework "{framework.name}": {new_source[:80]}...'
                        )
                    )
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSuccessfully fixed {fixed_count} frameworks with source URL issues'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nFound {would_fix_count} frameworks that would be fixed'
                )
            )

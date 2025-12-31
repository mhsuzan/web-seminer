import logging
from collections import Counter, defaultdict
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, Count, Prefetch
from django.http import JsonResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.http import urlencode
from .models import Framework, Criterion, Definition
from .llm_comparison import enhance_comparison_with_llm

# Set up logger for this module
logger = logging.getLogger(__name__)


def home(request):
    """Home page with search and comparison options"""
    frameworks = Framework.objects.all().order_by('-year', 'name')
    criteria_names = Criterion.objects.values_list('name', flat=True).distinct().order_by('name')
    
    context = {
        'frameworks': frameworks,
        'criteria_names': criteria_names,
    }
    return render(request, 'frameworks/home.html', context)


def framework_list(request):
    """List all frameworks"""
    frameworks = Framework.objects.prefetch_related('criteria').annotate(
        criteria_count=Count('criteria')
    ).order_by('-year', 'name')
    
    # Calculate data completeness for each framework and get criteria names
    for framework in frameworks:
        framework.data_completeness = calculate_completeness(framework)
        # Get criteria names as a comma-separated list
        criteria_names = framework.criteria.values_list('name', flat=True).order_by('order', 'name')
        framework.criteria_names_list = list(criteria_names)
        framework.criteria_names_display = ', '.join(criteria_names) if criteria_names else '—'
    
    context = {
        'frameworks': frameworks,
    }
    return render(request, 'frameworks/framework_list.html', context)


def calculate_completeness(framework):
    """Calculate data completeness percentage for a framework"""
    fields = [
        framework.authors,
        framework.year,
        framework.title,
        framework.description,
        framework.objectives,
        framework.methodology,
        framework.algorithm_used,
        framework.top_model,
        framework.accuracy,
        framework.advantages,
        framework.drawbacks,
        framework.source,
    ]
    filled = sum(1 for field in fields if field)
    return int((filled / len(fields)) * 100) if fields else 0


def framework_detail(request, framework_id):
    """Detail view of a single framework"""
    try:
        framework = Framework.objects.prefetch_related(
            Prefetch('criteria', queryset=Criterion.objects.select_related('framework').order_by('order', 'name'))
        ).get(id=framework_id)
        
        # Calculate data completeness
        framework.data_completeness = calculate_completeness(framework)
        
        # Deduplicate criteria by name (case-insensitive) - keep first occurrence
        seen_criteria = {}
        unique_criteria = []
        for criterion in framework.criteria.all():
            key = criterion.name.lower().strip()
            if key not in seen_criteria:
                seen_criteria[key] = True
                unique_criteria.append(criterion)
        
        # Replace criteria queryset with deduplicated list
        framework.criteria_list = unique_criteria
        
        context = {
            'framework': framework,
        }
        return render(request, 'frameworks/framework_detail.html', context)
    except Framework.DoesNotExist:
        from django.http import Http404
        raise Http404("Framework not found")


def compare_frameworks(request):
    """Compare two or more frameworks - shows similarities and differences"""
    framework_ids = request.GET.getlist('frameworks')
    
    if not framework_ids:
        frameworks = Framework.objects.all().order_by('-year', 'name')
        return render(request, 'frameworks/compare_frameworks.html', {
            'frameworks': frameworks,
            'selected_frameworks': None,
            'comparison_data': None,
            'framework_details': None,
        })
    
    # Validate framework IDs and filter out invalid ones
    try:
        framework_ids = [int(fid) for fid in framework_ids if fid.isdigit()]
    except (ValueError, TypeError):
        framework_ids = []
    
    if not framework_ids:
        frameworks = Framework.objects.all().order_by('-year', 'name')
        return render(request, 'frameworks/compare_frameworks.html', {
            'frameworks': frameworks,
            'selected_frameworks': None,
            'comparison_data': None,
            'framework_details': None,
        })
    
    selected_frameworks = Framework.objects.filter(id__in=framework_ids).order_by('-year', 'name')
    
    # If some IDs were invalid, only use valid ones
    if selected_frameworks.count() != len(framework_ids):
        framework_ids = [fw.id for fw in selected_frameworks]
        selected_frameworks = Framework.objects.filter(id__in=framework_ids).order_by('-year', 'name')
    
    # Get all unique criteria across selected frameworks
    # Use distinct() to ensure no duplicates, and normalize names for comparison
    all_criteria = Criterion.objects.filter(
        framework_id__in=framework_ids
    ).values_list('name', flat=True).distinct()
    
    # Normalize and deduplicate criterion names (case-insensitive, trim whitespace)
    criteria_names_set = set()
    criteria_names_list = []
    for name in all_criteria:
        normalized = name.strip() if name else ''
        if normalized:
            normalized_lower = normalized.lower()
            if normalized_lower not in criteria_names_set:
                criteria_names_set.add(normalized_lower)
                criteria_names_list.append(normalized)
    
    # Sort criteria names
    criteria_names = sorted(criteria_names_list, key=lambda x: x.lower())
    
    # Build comparison data for criteria - ensure we get actual criteria from database
    comparison_data = []
    seen_criteria = set()  # Track to prevent duplicates
    
    for criterion_name in criteria_names:
        # Skip if we've already processed this (case-insensitive check)
        criterion_key = criterion_name.lower().strip()
        if criterion_key in seen_criteria:
            continue
        seen_criteria.add(criterion_key)
        
        criterion_rows = []
        for framework in selected_frameworks:
            # Get the actual criterion from database - use exact match first, then case-insensitive
            criterion = Criterion.objects.filter(
                framework=framework,
                name__iexact=criterion_name
            ).select_related('framework').prefetch_related('definitions').first()
            
            if criterion:
                # Get unique definitions (filter duplicates)
                definitions_list = []
                seen_definitions = set()
                for definition in criterion.definitions.all():
                    def_text = definition.definition_text.strip() if definition.definition_text else ''
                    if def_text:
                        def_normalized = def_text.lower()
                        if def_normalized not in seen_definitions:
                            seen_definitions.add(def_normalized)
                            definitions_list.append(def_text)
                
                criterion_rows.append({
                    'has_criterion': True,
                    'description': criterion.description,
                    'author': criterion.author or framework.authors or '',
                    'category': criterion.category,
                    'definitions': definitions_list,
                })
            else:
                criterion_rows.append({
                    'has_criterion': False,
                })
        
        comparison_data.append({
            'name': criterion_name,
            'framework_data': criterion_rows,
        })
    
    # Build framework details comparison (all fields)
    framework_details = []
    for framework in selected_frameworks:
        framework_details.append({
            'id': framework.id,
            'name': framework.name,
            'authors': framework.authors,
            'year': framework.year,
            'title': framework.title,
            'description': framework.description,
            'objectives': framework.objectives,
            'methodology': framework.methodology,
            'algorithm_used': framework.algorithm_used,
            'top_model': framework.top_model,
            'accuracy': framework.accuracy,
            'advantages': framework.advantages,
            'drawbacks': framework.drawbacks,
            'source': framework.source,
            'criteria_count': framework.criteria.count(),
        })
    
    # Calculate similarities and differences using actual database queries
    similarities = []
    differences = []
    
    # Similarities: criteria that appear in ALL frameworks
    if len(selected_frameworks) > 1:
        for criterion_name in criteria_names:
            # Count frameworks that actually have this criterion (case-insensitive)
            frameworks_with_criterion = Criterion.objects.filter(
                framework__in=selected_frameworks,
                name__iexact=criterion_name
            ).values_list('framework_id', flat=True).distinct().count()
            
            if frameworks_with_criterion == len(selected_frameworks):
                similarities.append(criterion_name)
            elif frameworks_with_criterion > 0:
                differences.append({
                    'criterion': criterion_name,
                    'in_frameworks': frameworks_with_criterion,
                    'total': len(selected_frameworks)
                })
    
    # Enhance comparison with LLM if available - AUTO-ENABLE by default
    llm_enhancement = None
    try:
        use_llm = request.GET.get('llm', 'true').lower() != 'false'
        if use_llm:
            import time
            enhancement_start = time.time()
            try:
                llm_enhancement = enhance_comparison_with_llm(comparison_data, selected_frameworks)
                if llm_enhancement and llm_enhancement.get('enhanced'):
                    comparison_data = llm_enhancement.get('comparison_data', comparison_data)
                else:
                    error_msg = llm_enhancement.get('error', 'Unknown error') if llm_enhancement else 'No result'
                    if not llm_enhancement:
                        llm_enhancement = {'enhanced': False, 'error': 'LLM provider not available'}
                    elif not llm_enhancement.get('error'):
                        llm_enhancement['error'] = error_msg
            except Exception as e:
                logger.error(f"Error in LLM enhancement: {e}", exc_info=True)
                llm_enhancement = {'enhanced': False, 'error': str(e), 'provider': 'none'}
        else:
            llm_enhancement = {'enhanced': False, 'disabled': True}
    except Exception as e:
        logger.error(f"Error in LLM enhancement: {e}", exc_info=True)
        llm_enhancement = {'enhanced': False, 'error': str(e), 'provider': 'none'}
    
    context = {
        'frameworks': Framework.objects.all().order_by('-year', 'name'),
        'selected_frameworks': selected_frameworks,
        'comparison_data': comparison_data,
        'framework_details': framework_details,
        'similarities': similarities,
        'differences': differences,
        'llm_enhancement': llm_enhancement,
    }
    return render(request, 'frameworks/compare_frameworks.html', context)


def search_criteria(request):
    """Search for criteria across frameworks"""
    query = request.GET.get('q', '').strip()
    
    if not query:
        return render(request, 'frameworks/search_criteria.html', {
            'query': '',
            'results': None,
            'keywords': [],
        })
    
    # Split query by commas to support multiple keywords
    keywords = [k.strip() for k in query.split(',') if k.strip()]
    
    if not keywords:
        return render(request, 'frameworks/search_criteria.html', {
            'query': query,
            'results': None,
            'keywords': [],
        })
    
    # Build Q objects for each keyword - criteria must match ALL keywords (AND logic)
    # Each keyword should match either name or description
    q_objects = Q()
    for keyword in keywords:
        keyword_q = Q(name__icontains=keyword) | Q(description__icontains=keyword)
        q_objects &= keyword_q  # AND logic - all keywords must match
    
    # Search for criteria that match ALL keywords
    criteria = Criterion.objects.filter(q_objects).select_related('framework').prefetch_related('definitions').distinct()
    
    # Group by criterion name, but only include the specific criteria instances that matched
    results = {}
    for criterion in criteria:
        # Verify this specific criterion instance matches all keywords (double-check for precision)
        name_lower = criterion.name.lower()
        desc_lower = (criterion.description.lower() if criterion.description else '')
        
        # Check if all keywords match this criterion
        matches_all = True
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower not in name_lower and keyword_lower not in desc_lower:
                matches_all = False
                break
        
        if not matches_all:
            continue  # Skip if this specific instance doesn't match all keywords
        
        if criterion.name not in results:
            results[criterion.name] = {
                'name': criterion.name,
                'frameworks': []
            }
        
        # Get all criteria/dimensions for this framework to show in results
        all_framework_criteria = Criterion.objects.filter(
            framework=criterion.framework
        ).values_list('name', flat=True).order_by('order', 'name')
        criteria_keywords = ', '.join(all_framework_criteria) if all_framework_criteria else '—'
        
        # Filter out definitions that are identical or very similar to the description
        description_normalized = criterion.description.strip().lower() if criterion.description else ''
        unique_definitions = []
        for definition in criterion.definitions.all():
            definition_text = definition.definition_text.strip()
            definition_normalized = definition_text.lower()
            
            # Skip if definition is identical to description
            if description_normalized and definition_normalized == description_normalized:
                continue
            
            # Skip if definition is very similar (one is a substring of the other with small difference)
            if description_normalized and definition_normalized:
                if (definition_normalized in description_normalized or 
                    description_normalized in definition_normalized) and \
                    abs(len(definition_normalized) - len(description_normalized)) < 20:
                    continue
            
            unique_definitions.append(definition_text)
        
        results[criterion.name]['frameworks'].append({
            'framework': criterion.framework,
            'description': criterion.description,
            'category': criterion.category,
            'definitions': unique_definitions,
            'criteria_keywords': criteria_keywords,  # Add all dimensions/criteria for this framework
        })
    
    # Sort results by relevance (exact name matches first, then partial matches)
    # For multiple keywords, prioritize results that match the first keyword best
    first_keyword_lower = keywords[0].lower() if keywords else ''
    def sort_key(result):
        name_lower = result['name'].lower()
        if first_keyword_lower and name_lower == first_keyword_lower:
            return (0, name_lower)  # Exact match with first keyword
        elif first_keyword_lower and name_lower.startswith(first_keyword_lower):
            return (1, name_lower)  # Starts with first keyword
        else:
            return (2, name_lower)  # Contains first keyword
    
    sorted_results = sorted(results.values(), key=sort_key)
    
    context = {
        'query': query,
        'keywords': keywords,
        'results': sorted_results,
    }
    return render(request, 'frameworks/search_criteria.html', context)


def criterion_definitions(request):
    """Compare definitions of a specific criterion across frameworks"""
    criterion_name = request.GET.get('criterion', '').strip()
    
    all_criteria_names = list(Criterion.objects.values_list('name', flat=True).distinct())
    name_variants = defaultdict(list)
    
    for name in all_criteria_names:
        normalized = name.lower().strip()
        name_variants[normalized].append(name)
    
    all_variant_counts = Counter(
        Criterion.objects.values_list('name', flat=True)
    )
    
    criteria_names = []
    for normalized, variants in sorted(name_variants.items()):
        if len(variants) > 1:
            most_common = max(variants, key=lambda v: all_variant_counts.get(v, 0))
            criteria_names.append(most_common)
        else:
            criteria_names.append(variants[0])
    
    criteria_names = sorted(criteria_names, key=lambda x: x.lower())
    
    if not criterion_name:
        return render(request, 'frameworks/criterion_definitions.html', {
            'criterion_name': '',
            'criteria_names': criteria_names,
            'definitions': None,
        })
    
    criteria = Criterion.objects.filter(name__iexact=criterion_name).select_related(
        'framework'
    ).prefetch_related('definitions').order_by('framework')
    
    definitions_data = []
    seen_definitions = set()  # Track to prevent duplicates
    for criterion in criteria:
        for definition in criterion.definitions.all():
            # Normalize definition text for deduplication
            def_text = definition.definition_text.strip() if definition.definition_text else ''
            if def_text:
                def_key = def_text.lower()
                # Skip if we've seen this exact definition for this framework
                framework_def_key = (criterion.framework.id, def_key)
                if framework_def_key not in seen_definitions:
                    seen_definitions.add(framework_def_key)
                    definitions_data.append({
                        'framework': criterion.framework,
                        'criterion': criterion,
                        'definition': def_text,
                        'category': criterion.category,
                    })
    
    context = {
        'criterion_name': criterion_name,
        'criteria_names': criteria_names,
        'definitions': definitions_data,
    }
    return render(request, 'frameworks/criterion_definitions.html', context)


def api_frameworks(request):
    """API endpoint for frameworks list"""
    frameworks = Framework.objects.all().values('id', 'name', 'authors', 'year', 'title')
    return JsonResponse(list(frameworks), safe=False)


def api_criteria(request):
    """API endpoint for criteria search"""
    query = request.GET.get('q', '').strip()
    if query:
        criteria = Criterion.objects.filter(
            name__icontains=query
        ).values('id', 'name', 'framework__name', 'framework__id').distinct()
    else:
        criteria = Criterion.objects.values('id', 'name', 'framework__name', 'framework__id').distinct()
    
    return JsonResponse(list(criteria), safe=False)


# Source Management Views (for Framework.source field)
def source_list(request):
    """List all unique sources and frameworks grouped by source"""
    # Get all unique sources (non-empty)
    all_sources = Framework.objects.exclude(source='').values_list('source', flat=True).distinct().order_by('source')
    
    # Search filter
    search_query = request.GET.get('q', '').strip()
    if search_query:
        all_sources = [s for s in all_sources if search_query.lower() in s.lower()]
    
    # Group frameworks by source
    sources_data = []
    for source_name in all_sources:
        frameworks = Framework.objects.filter(source=source_name).order_by('-year', 'name')
        sources_data.append({
            'name': source_name,
            'frameworks': frameworks,
            'count': frameworks.count(),
        })
    
    # Sort by framework count (descending)
    sources_data.sort(key=lambda x: x['count'], reverse=True)
    
    # Statistics
    total_frameworks = Framework.objects.exclude(source='').count()
    total_sources = len(sources_data)
    frameworks_without_source = Framework.objects.filter(source='').count()
    
    context = {
        'sources_data': sources_data,
        'search_query': search_query,
        'stats': {
            'total_sources': total_sources,
            'total_frameworks': total_frameworks,
            'frameworks_without_source': frameworks_without_source,
        },
    }
    return render(request, 'frameworks/source_list.html', context)


def source_detail(request):
    """View and edit frameworks for a specific source"""
    source_name = request.GET.get('source', '').strip()
    
    if not source_name:
        messages.error(request, 'Source name is required')
        return redirect('frameworks:source_list')
    
    frameworks = Framework.objects.filter(source=source_name).order_by('-year', 'name')
    
    if request.method == 'POST':
        # Handle bulk source update
        framework_ids = request.POST.getlist('framework_ids')
        new_source = request.POST.get('new_source', '').strip()
        
        if framework_ids and new_source:
            updated = Framework.objects.filter(id__in=framework_ids).update(source=new_source)
            messages.success(request, f'Updated source for {updated} framework(s)')
            # Redirect to the new source if different, otherwise refresh current
            redirect_source = new_source if new_source != source_name else source_name
            return redirect(f"{reverse('frameworks:source_detail')}?{urlencode({'source': redirect_source})}")
    
    context = {
        'source_name': source_name,
        'frameworks': frameworks,
    }
    return render(request, 'frameworks/source_detail.html', context)


def source_edit_framework(request, framework_id):
    """Edit source for a specific framework"""
    framework = get_object_or_404(Framework, id=framework_id)
    
    if request.method == 'POST':
        new_source = request.POST.get('source', '').strip()
        framework.source = new_source
        framework.save()
        messages.success(request, f'Source updated for framework "{framework.name}"')
        return redirect('frameworks:framework_detail', framework_id=framework.id)
    
    context = {
        'framework': framework,
    }
    return render(request, 'frameworks/source_edit_framework.html', context)


def edit_framework(request, framework_id):
    """Edit all fields of a framework"""
    try:
        framework = get_object_or_404(Framework, id=framework_id)
    except Exception as e:
        logger.error(f"Error getting framework {framework_id}: {str(e)}", exc_info=True)
        raise
    
    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        try:
            name = request.POST.get('name', '').strip()
            if not name:
                error_msg = 'Framework name is required'
                if is_ajax:
                    return JsonResponse({'success': False, 'message': error_msg}, status=400)
                messages.error(request, error_msg)
                return redirect('frameworks:framework_list')
            
            framework.name = name
            framework.authors = request.POST.get('authors', '').strip()
            
            year_str = request.POST.get('year', '').strip()
            if year_str:
                try:
                    year_value = int(year_str)
                    if year_value < 1900 or year_value > 2100:
                        error_msg = 'Year must be between 1900 and 2100'
                        if is_ajax:
                            return JsonResponse({'success': False, 'message': error_msg}, status=400)
                        messages.error(request, error_msg)
                        return redirect('frameworks:framework_list')
                    framework.year = year_value
                except ValueError:
                    framework.year = None
            else:
                framework.year = None
            
            framework.title = request.POST.get('title', '').strip()
            framework.description = request.POST.get('description', '').strip()
            framework.objectives = request.POST.get('objectives', '').strip()
            framework.methodology = request.POST.get('methodology', '').strip()
            framework.algorithm_used = request.POST.get('algorithm_used', '').strip()
            framework.top_model = request.POST.get('top_model', '').strip()
            framework.accuracy = request.POST.get('accuracy', '').strip()
            framework.advantages = request.POST.get('advantages', '').strip()
            framework.drawbacks = request.POST.get('drawbacks', '').strip()
            framework.source = request.POST.get('source', '').strip()
            
            framework.full_clean()
            framework.save()
            messages.success(request, f'Framework "{framework.name}" updated successfully')
            
            if is_ajax:
                return JsonResponse({'success': True, 'message': 'Framework updated successfully'})
            
            return redirect('frameworks:framework_list')
        
        except ValidationError as e:
            if hasattr(e, 'message_dict'):
                error_msg = '; '.join([f"{k}: {', '.join(v)}" for k, v in e.message_dict.items()])
            elif hasattr(e, 'messages'):
                error_msg = '; '.join(e.messages)
            else:
                error_msg = str(e)
            
            logger.error(f"Validation error in edit_framework: {error_msg}", exc_info=True)
            
            if is_ajax:
                return JsonResponse({'success': False, 'message': f'Validation error: {error_msg}'}, status=400)
            
            messages.error(request, f'Validation error: {error_msg}')
            return redirect('frameworks:framework_list')
        except Exception as e:
            logger.error(f"Error updating framework: {str(e)}", exc_info=True)
            error_msg = str(e)
            
            if is_ajax:
                return JsonResponse({'success': False, 'message': f'Error updating framework: {error_msg}'}, status=500)
            
            messages.error(request, f'Error updating framework: {error_msg}')
            return redirect('frameworks:framework_list')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        framework_data = {
            'id': framework.id,
            'name': framework.name,
            'authors': framework.authors or '',
            'year': framework.year or '',
            'title': framework.title or '',
            'description': framework.description or '',
            'objectives': framework.objectives or '',
            'methodology': framework.methodology or '',
            'algorithm_used': framework.algorithm_used or '',
            'top_model': framework.top_model or '',
            'accuracy': framework.accuracy or '',
            'advantages': framework.advantages or '',
            'drawbacks': framework.drawbacks or '',
            'source': framework.source or '',
        }
        return JsonResponse(framework_data)
    
    context = {
        'framework': framework,
    }
    return render(request, 'frameworks/edit_framework.html', context)

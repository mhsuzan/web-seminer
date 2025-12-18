from django.shortcuts import render
from django.db.models import Q, Count, Prefetch
from django.http import JsonResponse
from .models import Framework, Criterion, Definition


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
    
    context = {
        'frameworks': frameworks,
    }
    return render(request, 'frameworks/framework_list.html', context)


def framework_detail(request, framework_id):
    """Detail view of a single framework"""
    framework = Framework.objects.prefetch_related(
        Prefetch('criteria', queryset=Criterion.objects.select_related('framework').order_by('order', 'name'))
    ).get(id=framework_id)
    
    context = {
        'framework': framework,
    }
    return render(request, 'frameworks/framework_detail.html', context)


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
    
    selected_frameworks = Framework.objects.filter(id__in=framework_ids).order_by('-year', 'name')
    
    # Get all unique criteria across selected frameworks
    all_criteria = Criterion.objects.filter(framework_id__in=framework_ids).values('name').distinct()
    criteria_names = sorted([c['name'] for c in all_criteria])
    
    # Build comparison data for criteria
    comparison_data = []
    for criterion_name in criteria_names:
        criterion_rows = []
        for framework in selected_frameworks:
            criteria = Criterion.objects.filter(
                framework=framework,
                name=criterion_name
            ).select_related('framework').prefetch_related('definitions')
            
            if criteria.exists():
                criterion = criteria.first()
                criterion_rows.append({
                    'has_criterion': True,
                    'description': criterion.description,
                    'category': criterion.category,
                    'definitions': [d.definition_text for d in criterion.definitions.all()],
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
    
    # Calculate similarities and differences
    similarities = []
    differences = []
    
    # Similarities: criteria that appear in ALL frameworks
    if len(selected_frameworks) > 1:
        for criterion_name in criteria_names:
            frameworks_with_criterion = sum(1 for fw in selected_frameworks 
                if Criterion.objects.filter(framework=fw, name=criterion_name).exists())
            if frameworks_with_criterion == len(selected_frameworks):
                similarities.append(criterion_name)
            elif frameworks_with_criterion > 0:
                differences.append({
                    'criterion': criterion_name,
                    'in_frameworks': frameworks_with_criterion,
                    'total': len(selected_frameworks)
                })
    
    context = {
        'frameworks': Framework.objects.all().order_by('-year', 'name'),
        'selected_frameworks': selected_frameworks,
        'comparison_data': comparison_data,
        'framework_details': framework_details,
        'similarities': similarities,
        'differences': differences,
    }
    return render(request, 'frameworks/compare_frameworks.html', context)


def search_criteria(request):
    """Search for criteria across frameworks"""
    query = request.GET.get('q', '').strip()
    
    if not query:
        return render(request, 'frameworks/search_criteria.html', {
            'query': '',
            'results': None,
        })
    
    # Search criteria by name
    criteria = Criterion.objects.filter(
        Q(name__icontains=query) | Q(description__icontains=query)
    ).select_related('framework').prefetch_related('definitions').order_by('name', 'framework')
    
    # Group by criterion name
    results = {}
    for criterion in criteria:
        if criterion.name not in results:
            results[criterion.name] = {
                'name': criterion.name,
                'frameworks': []
            }
        
        results[criterion.name]['frameworks'].append({
            'framework': criterion.framework,
            'description': criterion.description,
            'category': criterion.category,
            'definitions': [d.definition_text for d in criterion.definitions.all()],
        })
    
    context = {
        'query': query,
        'results': list(results.values()),
    }
    return render(request, 'frameworks/search_criteria.html', context)


def criterion_definitions(request):
    """Compare definitions of a specific criterion across frameworks"""
    criterion_name = request.GET.get('criterion', '').strip()
    
    if not criterion_name:
        criteria_names = Criterion.objects.values_list('name', flat=True).distinct().order_by('name')
        return render(request, 'frameworks/criterion_definitions.html', {
            'criterion_name': '',
            'criteria_names': criteria_names,
            'definitions': None,
        })
    
    criteria = Criterion.objects.filter(name__iexact=criterion_name).select_related(
        'framework'
    ).prefetch_related('definitions').order_by('framework')
    
    definitions_data = []
    for criterion in criteria:
        for definition in criterion.definitions.all():
            definitions_data.append({
                'framework': criterion.framework,
                'criterion': criterion,
                'definition': definition.definition_text,
                'notes': definition.notes,
                'category': criterion.category,
            })
    
    context = {
        'criterion_name': criterion_name,
        'criteria_names': Criterion.objects.values_list('name', flat=True).distinct().order_by('name'),
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

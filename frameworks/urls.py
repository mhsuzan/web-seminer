from django.urls import path
from . import views

app_name = 'frameworks'

urlpatterns = [
    path('', views.home, name='home'),
    path('frameworks/', views.framework_list, name='framework_list'),
    path('frameworks/<int:framework_id>/', views.framework_detail, name='framework_detail'),
    path('frameworks/<int:framework_id>/edit/', views.edit_framework, name='edit_framework'),
    path('compare/', views.compare_frameworks, name='compare_frameworks'),
    path('search/', views.search_criteria, name='search_criteria'),
    path('definitions/', views.criterion_definitions, name='criterion_definitions'),
    path('sources/', views.source_list, name='source_list'),
    path('sources/detail/', views.source_detail, name='source_detail'),
    path('sources/edit-framework/<int:framework_id>/', views.source_edit_framework, name='source_edit_framework'),
    path('api/frameworks/', views.api_frameworks, name='api_frameworks'),
    path('api/criteria/', views.api_criteria, name='api_criteria'),
]

# Data Source Management Features

This document describes the new data source management features added to the Knowledge Graph Quality Frameworks application.

## Overview

A comprehensive data source management system has been added that allows users to:
- View all data sources
- Create new data sources
- Edit existing data sources
- Delete data sources
- Track which frameworks were imported from which sources
- Filter and search data sources

## New Model: DataSource

The `DataSource` model tracks document sources used to import frameworks:

### Fields:
- **name**: Name or title of the data source (required)
- **source_type**: Type of source (docx, pdf, csv, json, manual, other)
- **file_path**: Path to the source file (optional)
- **url**: URL to the source if available online (optional)
- **author**: Author or organization (optional)
- **publication_date**: Publication or creation date (optional)
- **description**: Description of the data source (optional)
- **notes**: Additional notes (optional)
- **imported_at**: When data was imported from this source (optional)
- **frameworks_count**: Number of frameworks imported from this source
- **is_active**: Whether this source is currently active
- **created_at**: Creation timestamp
- **updated_at**: Last update timestamp

### Relationship:
- Frameworks can be linked to a data source via `Framework.data_source` (ForeignKey)

## New Views

### 1. Data Source List (`data_source_list`)
- Displays all data sources in a beautiful grid layout
- Shows statistics (total sources, active sources, total frameworks)
- Filtering by:
  - Source type
  - Active status
  - Search by name, description, or author
- Pagination support

### 2. Data Source Detail (`data_source_detail`)
- Shows complete information about a data source
- Displays all frameworks imported from this source
- Quick actions: Edit, Delete
- Statistics display

### 3. Create Data Source (`data_source_create`)
- Form to create a new data source
- All fields with proper validation
- Beautiful, responsive form design

### 4. Edit Data Source (`data_source_edit`)
- Form to edit an existing data source
- Pre-populated with current values
- Same beautiful form design

### 5. Delete Data Source (`data_source_delete`)
- Confirmation page before deletion
- Shows source details and framework count
- Warning about impact on linked frameworks

## New Templates

All templates use modern, beautiful styling with:
- Gradient buttons and cards
- Responsive grid layouts
- Color-coded badges for source types
- Smooth hover effects
- Mobile-friendly design

### Templates Created:
1. `data_source_list.html` - Grid view with filters
2. `data_source_detail.html` - Detailed view with framework list
3. `data_source_form.html` - Create/Edit form
4. `data_source_delete.html` - Confirmation page

## Updated Features

### Base Template
- Modern, gradient-based design
- Improved navigation with hover effects
- Better color scheme and typography
- Responsive design for mobile devices
- Added "Data Sources" link to navigation

### Framework Detail
- Now shows linked data source (if any)
- Clickable link to data source detail page
- Badge showing source type

## URL Routes

New routes added:
- `/data-sources/` - List all data sources
- `/data-sources/create/` - Create new data source
- `/data-sources/<id>/` - View data source detail
- `/data-sources/<id>/edit/` - Edit data source
- `/data-sources/<id>/delete/` - Delete data source

## Forms

### DataSourceForm
- Model form for DataSource
- All fields with proper widgets and styling
- Optional fields clearly marked
- Validation included

## Admin Integration

DataSource is registered in Django admin with:
- List display showing key fields
- Filters for source type, active status, dates
- Search functionality
- Organized fieldsets
- Read-only timestamp fields

## Usage

### Creating a Data Source

1. Navigate to "Data Sources" in the navigation
2. Click "+ Add New Source"
3. Fill in the form:
   - Name (required)
   - Source Type (required)
   - Other fields as needed
4. Click "Create Source"

### Linking Frameworks to Sources

Currently, frameworks can be linked to data sources through:
1. Django admin interface
2. Programmatically when importing (future enhancement)

### Viewing Source Information

1. Go to Data Sources page
2. Click on any source card to view details
3. See all frameworks imported from that source
4. Edit or delete as needed

## Future Enhancements

Potential improvements:
1. **Auto-linking during import**: Update import script to automatically create/link data sources
2. **Bulk operations**: Import multiple sources at once
3. **Source validation**: Validate file paths and URLs
4. **Import history**: Track import attempts and results
5. **Source comparison**: Compare frameworks from different sources
6. **Export functionality**: Export source information

## Migration

Run the migration to add the DataSource model:
```bash
python manage.py migrate
```

This will:
- Create the DataSource table
- Add data_source field to Framework model
- Create necessary indexes

## Styling

The new features use a modern design system with:
- CSS variables for consistent colors
- Gradient backgrounds
- Smooth transitions and hover effects
- Responsive grid layouts
- Card-based UI components
- Badge system for status indicators

All styling is consistent with the updated base template design.

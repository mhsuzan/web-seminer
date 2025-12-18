# Knowledge Graph Quality Frameworks - Usage Guide

## Overview

This system allows you to compare, analyze, and manage Knowledge Graph quality frameworks from literature. It provides a comprehensive interface for understanding similarities and differences between frameworks, searching for specific criteria, and managing framework data.

## Getting Started

### 1. Access the Application

- **Local Development**: `http://localhost:8000`
- **Production**: `http://seminer.codinzy.com` (or your configured domain)

### 2. Homepage Features

The homepage provides:
- **Quick Search**: Search for criteria across all frameworks
- **Browse Frameworks**: View all available frameworks in a grid
- **Popular Criteria**: Quick links to commonly used criteria

## Main Features

### Framework Comparison

**Purpose**: Compare multiple frameworks side-by-side to identify similarities and differences.

**How to Use**:
1. Navigate to "Compare Frameworks"
2. Select 2 or more frameworks using checkboxes
3. Click "Compare Frameworks"
4. Review the comparison table showing:
   - Framework details (year, title, description, objectives, methodology, etc.)
   - Criteria comparison with framework-specific descriptions
   - Similarities (criteria in ALL frameworks)
   - Differences (criteria in some but not all frameworks)

**AI Enhancement**:
- Click "🤖 Enable AI Enhancement" to activate:
  - **Semantic Similarity Detection**: Finds criteria that are conceptually similar even if named differently
  - **AI Comparison Summaries**: Intelligent summaries comparing how frameworks define criteria
  - **Framework-Specific Descriptions**: Enhanced descriptions tailored to each framework
  - **Related Criteria Grouping**: Groups criteria by conceptual similarity

**Tips**:
- Use AI enhancement for deeper insights
- Compare 2-4 frameworks at a time for best readability
- Look for "In All" badges to find common criteria
- Check semantic similarities to find related concepts

### Criteria Search

**Purpose**: Find which frameworks include a specific criterion and how they define it.

**How to Use**:
1. Navigate to "Search Criteria"
2. Enter a criterion name (e.g., "Completeness", "Accuracy")
3. View results showing:
   - All frameworks that include this criterion
   - Framework-specific descriptions
   - Definitions for each framework
   - Links to view full framework details

**Tips**:
- Search is case-insensitive
- Partial matches work (e.g., "complete" finds "Completeness")
- Results show framework context and related criteria

### Criterion Definitions Comparison

**Purpose**: Compare how different frameworks define the same criterion.

**How to Use**:
1. Navigate to "Criterion Definitions"
2. Select a criterion from the dropdown menu
3. View a table showing:
   - Framework name and year
   - Definitions from each framework
   - Additional notes or context

**Tips**:
- Use this to understand definitional differences
- Compare definitions across multiple frameworks
- Look for common themes and unique perspectives

### Framework Browsing

**Purpose**: View detailed information about individual frameworks.

**How to Use**:
1. Navigate to "Frameworks"
2. Browse the list of all frameworks
3. Click "View Details" on any framework to see:
   - Complete framework information
   - All criteria with descriptions
   - Definitions for each criterion
   - Link to compare with other frameworks

**Editing Frameworks**:
- Click "Edit" button to update framework information
- All fields can be edited through the modal interface
- Changes are saved immediately

### Source Management

**Purpose**: Organize and manage frameworks by publication source.

**How to Use**:
1. Navigate to "Sources"
2. View frameworks grouped by publication source
3. Click on a source to see all frameworks from that publication
4. Use bulk update to change source names for multiple frameworks
5. Edit individual framework sources from the framework detail page

**Tips**:
- Sources help organize frameworks by publication venue
- Use bulk update for efficiency when reorganizing
- Sources are displayed in framework comparisons

## Data Management

### Importing Data

Import frameworks from Word documents (.docx) or PDF files:

```bash
# Import from DOCX
python manage.py import_document path/to/document.docx

# Import from PDF
python manage.py import_document path/to/document.pdf

# Preview without saving (dry run)
python manage.py import_document path/to/document.pdf --dry-run
```

### Updating Criteria Descriptions

Use AI to intelligently update criteria descriptions:

```bash
# Update all criteria descriptions (framework-specific)
python manage.py update_criteria_intelligently

# Update specific criterion
python manage.py update_criteria_intelligently --criterion "Accuracy"

# Update for specific framework
python manage.py update_criteria_intelligently --framework "Framework Name"

# Preview changes first
python manage.py update_criteria_intelligently --dry-run

# Force update duplicate/generic descriptions
python manage.py force_update_duplicate_descriptions
```

### Cleaning Up Duplicates

Remove duplicate frameworks, criteria, or definitions:

```bash
# Preview what would be cleaned
python manage.py cleanup_duplicates --dry-run

# Actually clean up
python manage.py cleanup_duplicates
```

### Testing LLM Enhancement

Verify that AI enhancement is working:

```bash
python manage.py test_llm_enhancement
```

This will:
- Check LLM provider availability
- Test enhanced description generation
- Verify full enhancement pipeline
- Show any errors or issues

## Best Practices

### For Researchers

1. **Start with Comparison**: Use framework comparison to understand the landscape
2. **Use AI Enhancement**: Enable AI for deeper semantic insights
3. **Search Specific Criteria**: Use criteria search to find framework coverage
4. **Compare Definitions**: Use definition comparison to understand nuances

### For Data Managers

1. **Import in Batches**: Import related frameworks together
2. **Review Before Saving**: Use `--dry-run` to preview imports
3. **Update Descriptions**: Regularly update criteria descriptions for accuracy
4. **Clean Duplicates**: Periodically clean up duplicates
5. **Organize Sources**: Use source management to keep data organized

### For Administrators

1. **Monitor Logs**: Check logs for errors or issues
2. **Test LLM**: Regularly test LLM enhancement functionality
3. **Backup Database**: Regular backups of `db.sqlite3`
4. **Update Dependencies**: Keep requirements.txt up to date

## Troubleshooting

### AI Enhancement Not Working

1. Check LLM provider setup (see [LLM_SETUP.md](LLM_SETUP.md))
2. Run test command: `python manage.py test_llm_enhancement`
3. Check logs: `tail -f logs/error.log`
4. Verify API keys are set correctly

### Data Not Showing

1. Clear browser cache (Ctrl+F5 or Cmd+Shift+R)
2. Restart server: `pkill -f gunicorn` then restart
3. Check database: `python manage.py shell` to inspect data
4. Verify migrations: `python manage.py migrate`

### Import Issues

1. Check file format (DOCX or PDF)
2. Review document structure matches expected format
3. Use `--dry-run` to preview before importing
4. Check logs for parsing errors

## Keyboard Shortcuts

- **Ctrl+F** (Cmd+F on Mac): Search in page
- **Ctrl+R** (Cmd+R): Refresh page
- **Ctrl+Shift+R** (Cmd+Shift+R): Hard refresh (clear cache)

## Support

For issues or questions:
1. Check logs: `/root/seminer/logs/error.log`
2. Review documentation: README.md, LLM_SETUP.md
3. Test functionality: Use test commands
4. Check server status: See STATUS.md

## Advanced Usage

### API Endpoints

- `/api/frameworks/` - JSON list of all frameworks
- `/api/criteria/?q=<query>` - JSON search results for criteria

### Customization

- Modify templates in `frameworks/templates/frameworks/`
- Adjust import parsing in `frameworks/management/commands/import_document.py`
- Configure LLM in `frameworks/llm_comparison.py`

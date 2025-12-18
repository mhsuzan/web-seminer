# Data Import and Integrity Improvements

This document describes the improvements made to handle duplicate and missing data in the Knowledge Graph Quality Frameworks application.

## Problems Fixed

### 1. Duplicate Frameworks
**Issue**: Same frameworks were being imported multiple times with slightly different names (e.g., "Chen et al. 2019" vs "Chen et al. (2019)")

**Solution**: 
- Implemented intelligent framework matching using normalized names
- Added matching by year and title as fallback
- Automatic merging of duplicate frameworks during import

### 2. Duplicate Criteria
**Issue**: Same criteria appearing multiple times within a framework with slight name variations

**Solution**:
- Normalized criterion names for comparison
- Automatic detection and merging of duplicate criteria
- Preserves the most complete data when merging

### 3. Duplicate Definitions
**Issue**: Near-duplicate definitions being stored multiple times

**Solution**:
- Normalized definition text for comparison
- Detection of substring matches (one definition containing another)
- Automatic removal of near-duplicates

### 4. Missing Data
**Issue**: Incomplete data extraction from documents

**Solution**:
- Improved parsing logic to extract more fields
- Better handling of edge cases in table parsing
- Intelligent data merging that preserves existing data when new data is empty

## New Features

### 1. Enhanced Import Script (`import_document.py`)

**New Capabilities**:
- **Normalized Matching**: Uses normalized (lowercase, trimmed) names for duplicate detection
- **Intelligent Merging**: When updating existing frameworks, merges data intelligently:
  - Keeps existing data if new data is empty
  - Uses longer/more complete data when both exist
  - Updates only changed fields
- **Better Criteria Handling**: 
  - Normalizes criterion names (capitalizes first letter, removes extra spaces)
  - Detects duplicates by normalized name
  - Updates existing criteria with better data
- **Definition Deduplication**: 
  - Detects similar definitions
  - Removes near-duplicates (one containing another with similar length)

**Usage**:
```bash
# Import with automatic duplicate handling
python manage.py import_document document.docx

# Preview import (dry run)
python manage.py import_document document.docx --dry-run
```

### 2. Cleanup Command (`cleanup_duplicates.py`)

**Purpose**: Clean up existing duplicate data in the database

**Features**:
- Merges duplicate frameworks (keeps oldest, most complete)
- Merges duplicate criteria within frameworks
- Removes duplicate definitions
- Moves all related data (criteria, definitions) when merging frameworks

**Usage**:
```bash
# Preview what would be cleaned
python manage.py cleanup_duplicates --dry-run

# Actually clean up duplicates
python manage.py cleanup_duplicates
```

### 3. Improved Views

**Enhancements**:
- Better error handling for missing frameworks
- Data completeness calculation
- Graceful handling of missing data in templates
- Validation of framework IDs in comparison view

## Data Integrity Improvements

### Framework Matching Logic

1. **Exact Name Match**: First tries exact name match
2. **Normalized Name Match**: Compares normalized (lowercase, trimmed) names
3. **Year + Title Match**: If both year and title exist, matches on both
4. **Year + Normalized Title**: Fallback to year + normalized title match

### Criteria Matching Logic

1. **Exact Name Match**: Within the same framework
2. **Normalized Name Match**: Compares normalized criterion names

### Definition Deduplication

1. **Exact Match**: Normalized text comparison
2. **Substring Detection**: Detects if one definition contains another
3. **Length Check**: Only considers near-duplicates if lengths are similar (< 20 char difference)

## Best Practices

### When Importing New Data

1. **Always use dry-run first**: Check what will be imported
   ```bash
   python manage.py import_document document.pdf --dry-run
   ```

2. **Run cleanup after import**: Clean up any duplicates
   ```bash
   python manage.py cleanup_duplicates
   ```

3. **Review the output**: Check the import logs for any warnings

### Data Quality Tips

- **Framework Names**: Use consistent naming (e.g., "Author et al. Year")
- **Criteria Names**: Use consistent capitalization and spelling
- **Definitions**: Avoid storing very similar definitions multiple times

## Technical Details

### Normalization Functions

- `normalize_name()`: Converts to lowercase, trims, removes extra spaces
- `normalize_criterion_name()`: Normalizes and capitalizes first letter
- `find_matching_framework()`: Multi-step matching process
- `find_matching_criterion()`: Normalized criterion matching
- `merge_framework_data()`: Intelligent data merging

### Database Constraints

- Framework: No unique constraint (allows flexibility, handled in code)
- Criterion: `unique_together = [['framework', 'name']]` (enforced at DB level)
- Definition: No unique constraint (allows multiple definitions, deduplication in code)

## Migration Path

If you have existing data with duplicates:

1. **Backup your database** (important!)
2. **Run cleanup command with dry-run**:
   ```bash
   python manage.py cleanup_duplicates --dry-run
   ```
3. **Review the output** to see what will be merged
4. **Run cleanup for real**:
   ```bash
   python manage.py cleanup_duplicates
   ```
5. **Re-import documents** if needed (will now use improved deduplication)

## Future Improvements

Potential enhancements:
- Add unique constraint on Framework(name) with case-insensitive comparison
- Add admin interface for manual duplicate merging
- Add data quality metrics dashboard
- Export/import functionality with deduplication

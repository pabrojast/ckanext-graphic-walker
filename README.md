# ckanext-graphic-walker

Interactive CSV data visualization plugin for CKAN using [Graphic Walker](https://github.com/Kanaries/graphic-walker).

## Features

- 📊 Interactive drag-and-drop data visualization (Tableau-like)
- 📁 Automatic CSV resource detection and view creation
- 🎨 Modern, elegant UI with dark/light mode support
- 📈 Multiple chart types: bar, line, scatter, area, heatmap, and more
- 🔍 Data exploration with aggregations, filters, and sorting
- 🗺️ Spatial visualization support (GeoJSON)

## Requirements

- CKAN >= 2.10
- Python >= 3.8

## Installation

1. Activate your CKAN virtual environment
2. Install the extension:
   ```bash
   pip install -e /path/to/ckanext-graphic-walker
   ```
3. Add `graphic_walker` to `ckan.plugins` in your CKAN config file

## Configuration

```ini
# Supported resource formats (default: csv)
ckanext.graphic_walker.formats = csv

# Default view title
ckanext.graphic_walker.default_title = Data Explorer

# Maximum rows to load client-side (default: 50000)
ckanext.graphic_walker.max_rows = 50000
```

## Development

### Frontend (graphic-walker-app/)

```bash
cd graphic-walker-app
npm install
npm run dev     # Development server
npm run build   # Build for production
```

## License

AGPL-3.0

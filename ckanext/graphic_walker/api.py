# encoding: utf-8
"""
Flask blueprint for Graphic Walker API endpoints.
Serves CSV resource data as JSON for the frontend.
"""
import csv
import io
import os
import json

from flask import Blueprint, jsonify, request
import ckan.plugins.toolkit as toolkit

graphic_walker_api = Blueprint(
    'graphic_walker',
    __name__,
)


def _get_max_rows():
    """Get configured max rows limit."""
    try:
        return int(toolkit.config.get('ckanext.graphic_walker.max_rows', '50000'))
    except (ValueError, TypeError):
        return 50000


def _debug(msg):
    if os.getenv("GW_DEBUG", "false").lower() == "true":
        print(f"[graphic_walker] {msg}")


def _current_user():
    """Return the username of the requesting user, or empty string."""
    try:
        return toolkit.c.user or ''
    except Exception:
        pass
    try:
        from flask import g
        return getattr(g, 'user', '') or ''
    except Exception:
        return ''


def _authorize_resource(resource_id):
    """
    Verify that the requesting user is allowed to view this resource.
    Returns (resource_dict, error_response_tuple).
    On success: (dict, None). On failure: (None, (json_response, status_code)).
    """
    user = _current_user()
    context = {'user': user, 'ignore_auth': False}
    try:
        resource = toolkit.get_action('resource_show')(context, {'id': resource_id})
        return resource, None
    except toolkit.ObjectNotFound:
        return None, (jsonify({
            'success': False,
            'error': 'Resource not found.',
        }), 404)
    except toolkit.NotAuthorized:
        if not user:
            return None, (jsonify({
                'success': False,
                'error': 'Authentication required to view this resource.',
            }), 401)
        return None, (jsonify({
            'success': False,
            'error': 'Not authorized to view this resource.',
        }), 403)


def _try_datastore(resource_id, max_rows):
    """Try to fetch data from CKAN DataStore API."""
    try:
        context = {'ignore_auth': True}
        result = toolkit.get_action('datastore_search')(context, {
            'resource_id': resource_id,
            'limit': max_rows,
        })

        records = result.get('records', [])
        fields_info = result.get('fields', [])

        # Filter out internal _id field
        fields = []
        for f in fields_info:
            if f['id'].startswith('_'):
                continue
            fields.append({
                'fid': f['id'],
                'name': f['id'],
                'semanticType': _infer_semantic_type_from_datastore(f.get('type', 'text')),
                'analyticType': _infer_analytic_type_from_datastore(f.get('type', 'text')),
            })

        # Clean records (remove _id)
        clean_records = []
        for rec in records:
            clean_rec = {k: v for k, v in rec.items() if not k.startswith('_')}
            clean_records.append(clean_rec)

        return clean_records, fields, result.get('total', len(records))

    except Exception:
        return None, None, None


def _infer_semantic_type_from_datastore(ds_type):
    """Map DataStore types to Graphic Walker semantic types."""
    ds_type = ds_type.lower()
    if ds_type in ('int', 'int4', 'int8', 'float', 'float4', 'float8',
                    'numeric', 'number', 'integer', 'bigint', 'smallint',
                    'double precision', 'real'):
        return 'quantitative'
    if ds_type in ('date', 'timestamp', 'timestamptz', 'time', 'timetz'):
        return 'temporal'
    return 'nominal'


def _infer_analytic_type_from_datastore(ds_type):
    """Map DataStore types to Graphic Walker analytic types."""
    ds_type = ds_type.lower()
    if ds_type in ('int', 'int4', 'int8', 'float', 'float4', 'float8',
                    'numeric', 'number', 'integer', 'bigint', 'smallint',
                    'double precision', 'real'):
        return 'measure'
    return 'dimension'


def _read_local_upload(uploader, resource_id):
    """Read content from a local-disk uploader. Returns str or None."""
    try:
        if not hasattr(uploader, 'get_path'):
            return None
        upload_path = uploader.get_path(resource_id)
        if not upload_path or not os.path.exists(upload_path):
            return None
        with open(upload_path, 'rb') as f:
            raw = f.read()
        return raw.decode('utf-8', errors='replace')
    except Exception as e:
        _debug(f"local upload read failed: {e}")
        return None


def _read_cloud_upload(uploader, resource_dict):
    """
    Read content from a non-local uploader (e.g. ckanext-cloudstorage,
    ckanext-s3filestore). Tries several strategies in order of robustness:
      1. Direct libcloud container/object stream — works for private blobs
         regardless of whether signed URLs are enabled.
      2. Uploader's `download` method (returns a Flask response).
      3. Uploader's `get_url_from_filename` (signed URL we then fetch).
    Returns str or None.
    """
    rid = resource_dict.get('id')
    filename = resource_dict.get('url') or ''
    if filename:
        # CKAN sometimes stores the full URL in `url` for uploads; keep just
        # the basename which is what cloud uploaders expect.
        filename = filename.rsplit('/', 1)[-1]

    # 1. libcloud direct read (ckanext-cloudstorage)
    container = getattr(uploader, 'container', None)
    if container is not None and rid and filename:
        try:
            path_method = getattr(uploader, 'path_from_filename', None)
            object_name = path_method(rid, filename) if path_method else f'resources/{rid}/{filename}'
            obj = container.get_object(object_name=object_name)
            chunks = []
            for chunk in container.download_object_as_stream(obj):
                if isinstance(chunk, str):
                    chunk = chunk.encode('utf-8', errors='replace')
                chunks.append(chunk)
            raw = b''.join(chunks)
            return raw.decode('utf-8', errors='replace')
        except Exception as e:
            _debug(f"libcloud direct read failed: {e}")

    # 2. Uploader's download method
    if hasattr(uploader, 'download'):
        try:
            resp = uploader.download(rid, filename) if filename else uploader.download(rid)
            data = getattr(resp, 'data', None)
            if data is None and hasattr(resp, 'get_data'):
                data = resp.get_data()
            if isinstance(data, bytes):
                return data.decode('utf-8', errors='replace')
            if isinstance(data, str):
                return data
        except Exception as e:
            _debug(f"uploader.download failed: {e}")

    # 3. Signed/public URL
    if hasattr(uploader, 'get_url_from_filename') and rid and filename:
        try:
            signed_url = uploader.get_url_from_filename(rid, filename)
            if signed_url:
                return _http_get_text(signed_url)
        except Exception as e:
            _debug(f"get_url_from_filename failed: {e}")

    return None


def _http_get_text(url, headers=None, timeout=60):
    """GET a URL and return the body as text, or None on failure."""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        _debug(f"http get failed for {url}: {e}")
        return None


def _try_direct_csv(resource_dict, max_rows):
    """Fall back to downloading the CSV file directly.

    `resource_dict` is the dict returned by resource_show — the caller is
    expected to have already authorized the user.
    """
    try:
        resource_id = resource_dict.get('id')
        resource_url = resource_dict.get('url') or ''
        url_type = resource_dict.get('url_type') or ''

        if not resource_id:
            return None, None, None

        content = None

        # For uploaded files, use the configured uploader rather than HTTP
        # so we don't have to worry about authentication for private files.
        if url_type == 'upload':
            try:
                from ckan.lib.uploader import get_resource_uploader
                uploader = get_resource_uploader(resource_dict)
            except Exception as e:
                _debug(f"get_resource_uploader failed: {e}")
                uploader = None

            if uploader is not None:
                content = _read_local_upload(uploader, resource_id)
                if content is None:
                    content = _read_cloud_upload(uploader, resource_dict)

        # External URL: fetch directly. This won't help if the URL itself
        # requires auth, but at least public external CSVs work.
        if content is None and resource_url.startswith(('http://', 'https://')):
            content = _http_get_text(resource_url, timeout=30)

        if content is None:
            return None, None, None

        return _parse_csv_content(content, max_rows)

    except Exception as e:
        _debug(f"CSV download error: {e}")
        return None, None, None


def _parse_csv_content(content, max_rows):
    """Parse CSV content string into records and field metadata."""
    reader = csv.DictReader(io.StringIO(content))

    if not reader.fieldnames:
        return [], [], 0

    records = []
    for i, row in enumerate(reader):
        if i >= max_rows:
            break
        clean_row = {}
        for k, v in row.items():
            if v is None:
                clean_row[k] = ''
            else:
                # Try to convert numeric values
                try:
                    if '.' in v:
                        clean_row[k] = float(v)
                    else:
                        clean_row[k] = int(v)
                except (ValueError, TypeError):
                    clean_row[k] = v
        records.append(clean_row)

    total = len(records)

    # Infer field types from first N rows
    sample_size = min(100, total)
    fields = []
    for col_name in reader.fieldnames:
        if not col_name or not col_name.strip():
            continue
        col_name = col_name.strip()
        semantic_type = _infer_semantic_type_from_sample(
            [r.get(col_name) for r in records[:sample_size]]
        )
        analytic_type = 'measure' if semantic_type == 'quantitative' else 'dimension'
        fields.append({
            'fid': col_name,
            'name': col_name,
            'semanticType': semantic_type,
            'analyticType': analytic_type,
        })

    return records, fields, total


def _infer_semantic_type_from_sample(values):
    """Infer semantic type from a sample of values."""
    import re
    date_patterns = [
        re.compile(r'^\d{4}[-/]\d{1,2}[-/]\d{1,2}'),
        re.compile(r'^\d{1,2}[-/]\d{1,2}[-/]\d{4}'),
    ]

    numeric_count = 0
    date_count = 0
    total = 0

    for v in values:
        if v is None or v == '':
            continue
        total += 1
        if isinstance(v, (int, float)):
            numeric_count += 1
            continue
        s = str(v).strip()
        if s == '':
            continue
        try:
            float(s)
            numeric_count += 1
            continue
        except (ValueError, TypeError):
            pass
        for pat in date_patterns:
            if pat.match(s):
                date_count += 1
                break

    if total == 0:
        return 'nominal'

    if numeric_count / total > 0.8:
        return 'quantitative'
    if date_count / total > 0.8:
        return 'temporal'
    return 'nominal'


@graphic_walker_api.route('/api/graphic_walker/data/<resource_id>', methods=['GET'])
def get_resource_data(resource_id):
    """
    Serve resource data as JSON for Graphic Walker frontend.
    Tries DataStore API first, falls back to direct CSV download.

    Authorization: the requesting user must be allowed to view the resource
    (resource_show). Once they are, we use ignore_auth=True internally so
    that data backends (datastore, file uploader) work consistently for
    both public and private resources.
    """
    max_rows = _get_max_rows()

    # Enforce auth: a user that cannot resource_show this resource should
    # not be able to read its data via this endpoint either.
    resource, err = _authorize_resource(resource_id)
    if err is not None:
        body, status = err
        return body, status

    # Try DataStore first
    records, fields, total = _try_datastore(resource_id, max_rows)

    if records is not None:
        return jsonify({
            'success': True,
            'source': 'datastore',
            'data': records,
            'fields': fields,
            'total': total,
            'max_rows': max_rows,
        })

    # Fall back to direct CSV (uploader-based, works for private files too)
    records, fields, total = _try_direct_csv(resource, max_rows)

    if records is not None:
        return jsonify({
            'success': True,
            'source': 'csv',
            'data': records,
            'fields': fields,
            'total': total,
            'max_rows': max_rows,
        })

    return jsonify({
        'success': False,
        'error': 'Could not load data from this resource. Ensure it is a valid CSV file.',
    }), 404


@graphic_walker_api.route('/api/graphic_walker/view/<view_id>/save-spec', methods=['POST'])
def save_view_specs(view_id):
    """
    Save chart specifications to a resource view's config.
    Expects JSON body: {"specs": "...json string..."}
    """
    try:
        from flask import g
        user = None
        try:
            user = toolkit.c.user or None
        except Exception:
            user = getattr(g, 'user', None) if hasattr(g, 'user') else None

        if not user:
            return jsonify({'success': False, 'error': 'Authentication required. Please log in.'}), 401

        data = request.get_json(silent=True)
        if not data or 'specs' not in data:
            return jsonify({'success': False, 'error': 'Missing "specs" field in request body.'}), 400

        specs = data['specs']
        if not isinstance(specs, str):
            try:
                specs = json.dumps(specs)
            except (TypeError, ValueError):
                return jsonify({'success': False, 'error': 'Invalid specs format.'}), 400

        # Validate it's valid JSON
        try:
            json.loads(specs)
        except (json.JSONDecodeError, TypeError):
            return jsonify({'success': False, 'error': 'Specs must be valid JSON.'}), 400

        context = {'user': user, 'ignore_auth': False}

        try:
            current_view = toolkit.get_action('resource_view_show')(context, {'id': view_id})
        except toolkit.ObjectNotFound:
            return jsonify({'success': False, 'error': f'View not found: {view_id}'}), 404
        except toolkit.NotAuthorized:
            return jsonify({'success': False, 'error': 'Not authorized to access this view.'}), 403

        update_data = {
            'id': view_id,
            'resource_id': current_view.get('resource_id'),
            'view_type': current_view.get('view_type'),
            'title': current_view.get('title'),
            'description': current_view.get('description', ''),
            'chart_specs': specs,
        }

        try:
            toolkit.get_action('resource_view_update')(context, update_data)
        except toolkit.NotAuthorized:
            return jsonify({'success': False, 'error': 'Not authorized to update this view.'}), 403
        except Exception as e:
            return jsonify({'success': False, 'error': f'Failed to save: {str(e)}'}), 500

        return jsonify({
            'success': True,
            'message': 'Chart configuration saved successfully.',
            'view_id': view_id,
        })

    except Exception as e:
        if os.getenv("GW_DEBUG", "false").lower() == "true":
            print(f"[graphic_walker] Save error: {e}")
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

from flask import Blueprint, request, jsonify, send_file
import logging
from pathlib import Path

from src.utils.chordpro_parser import ChordPosition, ChordProLine, parse_chordpro
from src.utils.compiler import CompilationError, compile_slides_html
from src.utils.html_renderer import RenderError
from src.utils.preview import SongValidationError, generate_preview, generate_regeneration
from src.utils.search import search_song as search_worship_together
from src.utils.song_validator import (
    OverflowWarning,
    ValidationResult,
    check_licensing,
    estimate_slide_overflow,
    validate_song,
)
from src.utils.slide_storage import (
    clear_temp_files,
    delete_slide,
    get_slide,
    get_slide_file,
    list_slides,
    save_slide,
    update_slide,
)
from src.utils.yaml_api import generate_yaml_response
from src.utils.yaml_converter import infer_section_type
from src.utils.yaml_models import SongSection, SongYAML

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
api_bp = Blueprint('api', __name__)

@api_bp.route('/search', methods=['GET'])
def search_song():
    """
    Search for song lyrics and chords
    Required param: song (song name)
    Optional param: artist (artist name)
    Optional param: key (desired key)
    """
    song_name = request.args.get('song', '')
    artist_name = request.args.get('artist', '')
    target_key = request.args.get('key', '')
    
    if not song_name:
        return jsonify({'error': 'Song name is required'}), 400
    
    logger.info(f"Searching for song: '{song_name}' by '{artist_name}' in key '{target_key}'")

    # Search Worship Together
    result = search_worship_together(song_name, artist_name, target_key=target_key if target_key else None)

    if not result:
        return jsonify({'error': 'Song not found'}), 404

    if target_key:
        result['key'] = target_key
    return jsonify(result)


# NOTE: ``/api/download`` (the legacy PowerPoint stream-from-search endpoint)
# has been removed. The recommended workflow is HTML/Marp via the dedicated
# per-format endpoints (``/api/download/{format}``) and ``/api/preview``.
# See docs/MIGRATION.md for the rollout plan and replacement paths.


@api_bp.route('/health', methods=['GET'])
def api_health():
    """Operational health probe (Requirement 9.4).

    Reports whether the dependencies needed to render HTML decks are
    available, plus storage directory size so an operator can spot
    runaway disk usage without leaving the API surface.
    """
    from src.utils.html_renderer import verify_marp_cli
    import src.utils.slide_storage as storage_module

    marp_ok = verify_marp_cli()

    slides_dir = Path(storage_module.SLIDES_DIR)
    storage_bytes = 0
    storage_files = 0
    if slides_dir.exists():
        for entry in slides_dir.glob('**/*'):
            if entry.is_file():
                storage_files += 1
                try:
                    storage_bytes += entry.stat().st_size
                except OSError:
                    continue

    return jsonify({
        'status': 'ok' if marp_ok else 'degraded',
        'marp_cli': {
            'available': marp_ok,
            'note': (
                'Marp CLI not detected; HTML rendering will fail until it '
                'is installed (see docs/DEPLOYMENT.md).'
                if not marp_ok
                else 'Marp CLI is available.'
            ),
        },
        'storage': {
            'path': str(slides_dir),
            'files': storage_files,
            'bytes': storage_bytes,
        },
    })

@api_bp.route('/generate_yaml', methods=['POST'])
def api_generate_yaml():
    """Generate structured song YAML data from metadata and chart data."""
    song_data = request.get_json(silent=True)
    if not song_data:
        return jsonify({'error': 'No song data provided'}), 400

    try:
        return jsonify(generate_yaml_response(song_data))
    except Exception as e:
        logger.error(f"Error generating YAML: {str(e)}")
        return jsonify({'error': 'Failed to generate YAML'}), 500

@api_bp.route('/preview', methods=['POST'])
def api_generate_preview():
    """Generate rendered HTML preview content from structured song YAML data."""
    try:
        return jsonify(generate_preview(request.get_json(silent=True) or {}))
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except RenderError as e:
        logger.error(f"Error rendering HTML preview: {str(e)}")
        return jsonify({'error': 'Failed to render preview'}), 500
    except Exception as e:
        logger.error(f"Error generating HTML preview: {str(e)}")
        return jsonify({'error': 'Failed to generate preview'}), 500

@api_bp.route('/validate', methods=['POST'])
def api_validate_song():
    """Validate a song YAML payload (Requirements 7.1, 7.7).

    Body:
        song (dict)               - The song YAML payload (title, authors,
                                    target_key, sections, arrangement, ...).
        style (str, optional)     - Slide style variant used to estimate
                                    slide overflow (``"practice"``,
                                    ``"performance"``, ``"simple"``).
                                    Defaults to ``"practice"``.
        check_placeholders (bool) - When true, also flag TODO/TBD/XXX/{}/
                                    [placeholder] markers in the lyrics and
                                    metadata. Defaults to false (Requirement
                                    7.8: the placeholder check must be
                                    opt-in).

    Returns:
        ``200 OK`` with the validation status, errors, warnings, overflow,
        and licensing warnings.
        ``400 Bad Request`` if the body is empty or not a JSON object.

    The endpoint never raises for invalid songs — it returns the structural
    issues so the editor UI can let the user decide whether to continue.
    """
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({'error': 'JSON object body is required'}), 400

    style = str(payload.get('style') or 'practice')
    check_placeholders = bool(payload.get('check_placeholders', False))

    raw_song = payload.get('song')
    if isinstance(raw_song, dict) and raw_song:
        song_payload = raw_song
    elif any(key in payload for key in ('title', 'sections', 'arrangement')):
        song_payload = payload
    else:
        return jsonify({'error': 'song payload is required ({"song": {...}} or raw song fields)'}), 400

    song = _song_from_api_payload(song_payload)

    validation: ValidationResult = validate_song(song, check_placeholders=check_placeholders)
    overflow_warnings: list[OverflowWarning] = estimate_slide_overflow(song, style)
    licensing_warnings: list[str] = check_licensing(song)

    return jsonify({
        'is_valid': validation.is_valid,
        'errors': validation.errors,
        'warnings': validation.warnings,
        'overflow': [
            {
                'section_name': warning.section_name,
                'estimated_lines': warning.estimated_lines,
                'max_lines': warning.max_lines,
                'suggestion': warning.suggestion,
            }
            for warning in overflow_warnings
        ],
        'licensing_warnings': licensing_warnings,
        'style': style,
    })


def _song_from_api_payload(song_payload: dict) -> SongYAML:
    """Reconstruct a ``SongYAML`` from a request dict without re-using the
    preview pipeline's stricter namespace, so the validate endpoint can
    accept raw YAML payloads as well as already-built dataclasses."""
    sections_data = song_payload.get('sections') or {}
    if not isinstance(sections_data, dict):
        raise ValueError('sections must be an object')

    sections = {}
    for section_name, section_payload in sections_data.items():
        if not isinstance(section_payload, dict):
            continue
        lines_payload = section_payload.get('lines') or []
        parsed_lines = []
        for line_payload in lines_payload:
            if isinstance(line_payload, str):
                parsed_lines.append(parse_chordpro(line_payload))
            elif isinstance(line_payload, dict):
                chordpro = line_payload.get('chordpro') or line_payload.get('raw')
                if chordpro is not None:
                    parsed_lines.append(parse_chordpro(str(chordpro)))
                else:
                    text = str(line_payload.get('text') or '')
                    chords = [
                        ChordPosition(
                            chord=str(chord.get('chord') or ''),
                            position=int(chord.get('position') or 0),
                        )
                        for chord in (line_payload.get('chords') or [])
                        if isinstance(chord, dict)
                    ]
                    parsed_lines.append(ChordProLine(text=text, chords=chords))

        section_name_str = str(section_payload.get('name') or section_name)
        section_type_str = str(section_payload.get('type') or infer_section_type(section_name_str))
        sections[section_name_str] = {
            'name': section_name_str,
            'type': section_type_str,
            'lines': parsed_lines,
            'notes': section_payload.get('notes'),
        }

    section_models = {
        key: SongSection(
            name=value['name'],
            type=value['type'],
            lines=value['lines'],
            notes=value['notes'] if isinstance(value['notes'], list) else None,
        )
        for key, value in sections.items()
    }

    arrangement_payload = song_payload.get('arrangement')
    if isinstance(arrangement_payload, list) and arrangement_payload:
        arrangement = [str(name) for name in arrangement_payload if name]
    else:
        arrangement = list(section_models.keys())

    authors_payload = song_payload.get('authors') or []
    if isinstance(authors_payload, list):
        authors = [str(author) for author in authors_payload if author]
    else:
        authors = [str(authors_payload)] if authors_payload else []

    practice_notes_payload = song_payload.get('practice_notes')
    practice_notes = None
    if isinstance(practice_notes_payload, dict):
        practice_notes = {
            str(key): [str(note) for note in (notes or []) if note]
            for key, notes in practice_notes_payload.items()
            if notes
        }

    return SongYAML(
        title=str(song_payload.get('title') or ''),
        authors=authors or ['Unknown'],
        ccli_number=song_payload.get('ccli_number'),
        copyright=song_payload.get('copyright'),
        original_key=song_payload.get('original_key'),
        target_key=str(song_payload.get('target_key') or 'C'),
        bpm=song_payload.get('bpm'),
        time_signature=song_payload.get('time_signature'),
        capo=song_payload.get('capo'),
        sections=section_models,
        arrangement=arrangement,
        practice_notes=practice_notes,
        source_urls=song_payload.get('source_urls') or [],
    )


@api_bp.route('/regenerate', methods=['POST'])
def api_regenerate_preview():
    """Regenerate rendered HTML preview content from edited song YAML data."""
    try:
        return jsonify(generate_regeneration(request.get_json(silent=True) or {}))
    except SongValidationError as e:
        return jsonify({'error': str(e), 'validation': e.validation}), 400
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except RenderError as e:
        logger.error(f"Error rendering regenerated HTML preview: {str(e)}")
        return jsonify({'error': 'Failed to render preview'}), 500
    except Exception as e:
        import traceback
        logger.error(f"Error regenerating HTML preview: {str(e)}")
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        return jsonify({'error': 'Failed to regenerate preview'}), 500

@api_bp.route('/save_slide', methods=['POST'])
def api_save_slide():
    """
    Save a slide in one or more formats.

    Request body:
        song_data: dict - Song data containing metadata and content
        formats: list[str] - Optional list of formats to generate
                           ('yaml', 'marp', 'html', 'pdf')
                           Defaults to ['yaml', 'marp', 'html']

    Returns:
        Metadata dict with 'id', 'title', 'artist', 'key', 'filenames',
        'created_at', 'updated_at', and optional fields

    Requirements: 14.1, 14.2, 14.3
    """
    request_data = request.json
    if not request_data:
        return jsonify({'error': 'No data provided'}), 400

    if 'song_data' in request_data:
        song_data = request_data['song_data']
        formats = request_data.get('formats')
    else:
        song_data = request_data
        formats = request_data.get('formats')

    if formats is None:
        formats = ['yaml', 'marp', 'html']

    valid_formats = {'yaml', 'marp', 'html', 'pdf'}
    if not isinstance(formats, list):
        return jsonify({'error': 'formats must be a list'}), 400

    invalid_formats = [f for f in formats if f not in valid_formats]
    if invalid_formats:
        return jsonify({
            'error': f'Invalid formats: {invalid_formats}',
            'valid_formats': list(valid_formats)
        }), 400

    try:
        meta = save_slide(song_data, formats=formats)
        return jsonify(meta)
    except Exception as e:
        logger.error(f"Error saving slide: {str(e)}")
        return jsonify({'error': 'Failed to save slide'}), 500

@api_bp.route('/saved_slides', methods=['GET'])
def api_list_slides():
    """
    List all saved slides with format availability.
    
    Returns:
        List of metadata dicts, each including 'filenames' dict
        showing which formats are available.
    
    Requirements: 14.5
    """
    return jsonify(list_slides())

@api_bp.route('/saved_slide/<slide_id>', methods=['GET'])
def api_legacy_unversioned_download(slide_id):
    """Stub for the legacy unversioned ``/api/saved_slide/<id>`` download endpoint.

    The endpoint used to default to PowerPoint; PowerPoint export is now
    retired, so the stub returns 404 with an explanatory message pointing
    callers to the per-format download route.
    """
    return jsonify({
        'error': 'unversioned download endpoint removed; '
                 'use /api/saved_slide/<id>/download/<format>',
        'available_formats': ['html', 'marp', 'yaml', 'pdf'],
    }), 404


@api_bp.route('/saved_slide/<slide_id>/download/<format>', methods=['GET'])
def api_download_slide_format(slide_id, format):
    """
    Download a saved slide in a specific format.

    Supported formats: html, marp, yaml, pdf

    Requirements: 14.5
    """
    valid_formats = {'html', 'marp', 'yaml', 'pdf'}
    if format not in valid_formats:
        return jsonify({
            'error': f'Invalid format: {format}',
            'valid_formats': list(valid_formats)
        }), 400

    meta = get_slide(slide_id)
    if not meta:
        return jsonify({'error': 'Slide not found'}), 404

    file_path = get_slide_file(slide_id, format)
    if not file_path:
        available_formats = list(meta.get('filenames', {}).keys())
        return jsonify({
            'error': f'Format {format} not available for this slide',
            'available_formats': available_formats
        }), 404

    mime_types = {
        'html': 'text/html',
        'marp': 'text/markdown',
        'yaml': 'text/yaml',
        'pdf': 'application/pdf',
    }

    extensions = {
        'html': 'html',
        'marp': 'marp.md',
        'yaml': 'yaml',
        'pdf': 'pdf',
    }

    mime_type = mime_types.get(format, 'application/octet-stream')
    extension = extensions.get(format, format)

    title = meta.get('title', 'Untitled')
    artist = meta.get('artist', '')
    if artist:
        download_name = f"{title} - {artist}.{extension}"
    else:
        download_name = f"{title}.{extension}"

    return send_file(
        file_path,
        as_attachment=True,
        download_name=download_name,
        mimetype=mime_type
    )

@api_bp.route('/saved_slide/<slide_id>', methods=['DELETE'])
def api_delete_slide(slide_id):
    if delete_slide(slide_id):
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Slide not found'}), 404


@api_bp.route('/saved_slide/<slide_id>', methods=['PUT'])
def api_update_saved_slide(slide_id):
    """
    Update a saved slide with modified YAML song data.
    
    Request body:
        song: dict - Modified song YAML data
        formats: list[str] - Optional list of formats to regenerate
                           ('yaml', 'marp', 'html', 'pdf', 'pptx')
                           Defaults to all existing formats
    
    Returns:
        Updated metadata dict with 'id', 'title', 'artist', 'key', 'filenames',
        'created_at', 'updated_at'
    
    Requirements: 14.7
    """
    request_data = request.json
    if not request_data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        meta = update_slide(slide_id, request_data)
        return jsonify(meta)
    except FileNotFoundError:
        return jsonify({'error': 'Slide not found'}), 404
    except ValueError as e:
        logger.error(f"Error updating slide {slide_id}: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error updating slide {slide_id}: {str(e)}")
        return jsonify({'error': 'Failed to update slide'}), 500


# NOTE: ``/api/compile_slides`` (legacy PPTX bundle with index slide) has
# been removed. Multi-song decks are now built through the HTML pipeline
# at ``POST /api/compile`` (see docs/MIGRATION.md).

@api_bp.route('/compile', methods=['POST'])
def api_compile_html():
    """Combine saved slides into a single HTML deck with a clickable index.

    Request body:
        slide_ids (list[str], required): Ordered list of saved slide IDs. The
            array position determines both playback order and the anchor id
            used in the index, so callers can encode order without needing a
            separate ``order`` field. An optional ``order`` field is accepted
            for compatibility with the spec wording; if supplied, it must list
            exactly the same set of IDs as ``slide_ids``.

    Returns:
        A downloadable HTML file (``text/html``) named after the deck.

    Requirements: 15.1, 15.2, 15.3, 15.4, 15.5
    """
    request_data = request.get_json(silent=True) or {}

    slide_ids = request_data.get("slide_ids")
    if not isinstance(slide_ids, list) or not slide_ids:
        return jsonify({'error': 'slide_ids must be a non-empty list'}), 400
    if not all(isinstance(item, str) and item for item in slide_ids):
        return jsonify({'error': 'slide_ids must contain only non-empty strings'}), 400

    order = request_data.get("order")
    if order is not None:
        if not isinstance(order, list) or set(order) != set(slide_ids):
            return jsonify({
                'error': 'order must list the same slide ids as slide_ids',
            }), 400

    try:
        compiled_path = compile_slides_html(slide_ids)
    except CompilationError as exc:
        return jsonify({'error': str(exc)}), 400
    except RenderError as exc:
        logger.error("Error rendering compiled HTML deck: %s", exc)
        return jsonify({'error': 'Failed to render compiled deck'}), 500
    except Exception as exc:
        logger.error("Error compiling slides: %s", exc)
        return jsonify({'error': 'Failed to compile slides'}), 500

    return send_file(
        compiled_path,
        as_attachment=True,
        download_name='Compiled_Slide_Deck.html',
        mimetype='text/html',
    )

@api_bp.route('/clear_temp_files', methods=['POST'])
def api_clear_temp_files():
    try:
        clear_temp_files()
        return jsonify({'success': True, 'message': 'Temporary files cleared.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

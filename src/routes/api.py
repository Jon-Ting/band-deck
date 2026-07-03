from flask import Blueprint, request, jsonify, send_file
import logging
from src.utils.search import search_song as search_worship_together
from src.utils.html_renderer import RenderError
from src.utils.preview import SongValidationError, generate_preview, generate_regeneration
from src.utils.slide_storage import save_slide, list_slides, get_slide, delete_slide, get_slide_file, compile_slides_with_index, clear_temp_files
from src.utils.yaml_api import generate_yaml_response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
api_bp = Blueprint('api', __name__)

# Rate limiting dictionary
request_timestamps = {}
RATE_LIMIT_SECONDS = 5  # Time between requests to same source

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
    
    if result:
        # Generate PowerPoint preview
        try:
            from src.utils.pptx_generator import PowerPointGenerator
            ppt_gen = PowerPointGenerator()
            ppt_gen.create_slide(result)
            
            # Add PowerPoint preview info to the result
            result['pptx_preview'] = {
                'title': result.get('title', 'Unknown Title'),
                'artist': result.get('artist', 'Unknown Artist'),
                'key': target_key,
                'sections': []
            }
            
            # Parse sections for preview
            if 'content' in result:
                sections = [s for s in result['content'].split('\n\n') if s.strip()]
                for section in sections:
                    lines = section.split('\n')
                    if lines:
                        section_header = lines[0].strip()
                        section_content = '\n'.join(lines[1:]).strip()
                        result['pptx_preview']['sections'].append({
                            'header': section_header,
                            'content': section_content
                        })
            result['key'] = target_key
            return jsonify(result)
        except Exception as e:
            logger.error(f"Error generating PowerPoint preview: {str(e)}")
            # Return result without preview if generation fails
            return jsonify(result)
    else:
        return jsonify({'error': 'Song not found'}), 404

@api_bp.route('/download', methods=['GET'])
def download_file():
    """
    Generate and download PowerPoint file
    Required param: song (song name)
    Optional param: artist (artist name)
    Optional param: key (desired key)
    """
    song_name = request.args.get('song', '')
    artist_name = request.args.get('artist', '')
    target_key = request.args.get('key', '')
    
    if not song_name:
        return jsonify({'error': 'Song name is required'}), 400
    
    # Get song data
    song_data = search_worship_together(song_name, artist_name, target_key=target_key if target_key else None)
    
    if song_data is not None:
        song_data['key'] = target_key
    
    if not song_data:
        return jsonify({'error': 'Song not found'}), 404
    
    # Generate PowerPoint file
    try:
        from src.utils.pptx_generator import generate_pptx_from_song_data
        print("\n" + "="*50)
        print(f"Generating PowerPoint for: {song_name}")
        print(f"Artist: {artist_name}")
        print(f"Key: {target_key}")
        print("="*50 + "\n")
        
        pptx_path = generate_pptx_from_song_data(song_data)
        
        print("\n" + "="*50)
        print(f"PowerPoint generated successfully: {pptx_path}")
        print("="*50 + "\n")
        
        return send_file(
            pptx_path,
            as_attachment=True,
            download_name=f"{song_data['title']} - Lyrics and Chords.pptx",
            mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation'
        )
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        logger.error(f"Error generating PowerPoint: {str(e)}")
        return jsonify({'error': 'Failed to generate file'}), 500

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
        logger.error(f"Error regenerating HTML preview: {str(e)}")
        return jsonify({'error': 'Failed to regenerate preview'}), 500

@api_bp.route('/save_slide', methods=['POST'])
def api_save_slide():
    song_data = request.json
    if not song_data:
        return jsonify({'error': 'No song data provided'}), 400
    meta = save_slide(song_data)
    return jsonify(meta)

@api_bp.route('/saved_slides', methods=['GET'])
def api_list_slides():
    return jsonify(list_slides())

@api_bp.route('/saved_slide/<slide_id>', methods=['GET'])
def api_download_slide(slide_id):
    path = get_slide_file(slide_id)
    meta = get_slide(slide_id)
    if not path or not meta:
        return jsonify({'error': 'Slide not found'}), 404
    return send_file(path, as_attachment=True, download_name=f"{meta['title']} - {meta['artist']}.pptx", mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation')

@api_bp.route('/saved_slide/<slide_id>', methods=['DELETE'])
def api_delete_slide(slide_id):
    if delete_slide(slide_id):
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Slide not found'}), 404

@api_bp.route('/compile_slides', methods=['GET'])
def api_compile_slides():
    try:
        path = compile_slides_with_index()
        return send_file(path, as_attachment=True, download_name='All_Slides_Compiled.pptx', mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/clear_temp_files', methods=['POST'])
def api_clear_temp_files():
    try:
        clear_temp_files()
        return jsonify({'success': True, 'message': 'Temporary files cleared.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

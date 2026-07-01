import os
import json
import uuid
from typing import List, Dict, Optional
from src.utils.pptx_generator import generate_pptx_from_song_data
from pptx.util import Inches, Pt
from pptx import Presentation
from pptx.oxml import parse_xml
from pptx.oxml.ns import qn
import logging

SLIDES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'saved_slides')

if not os.path.exists(SLIDES_DIR):
    os.makedirs(SLIDES_DIR)

def _slide_path(slide_id):
    return os.path.join(SLIDES_DIR, f"{slide_id}.pptx")

def _meta_path(slide_id):
    return os.path.join(SLIDES_DIR, f"{slide_id}.json")

def save_slide(song_data: dict) -> dict:
    slide_id = str(uuid.uuid4())
    pptx_path = _slide_path(slide_id)
    meta_path = _meta_path(slide_id)
    # Generate pptx file
    generate_pptx_from_song_data(song_data, filename=pptx_path)
    # Use the user-inputted song name (search_name) as the title if present
    meta = {
        'id': slide_id,
        'title': song_data.get('search_name') or song_data.get('title'),
        'artist': song_data.get('artist'),
        'key': song_data.get('key'),
        'filename': os.path.basename(pptx_path)
    }
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f)
    return meta

def list_slides() -> List[dict]:
    slides = []
    for fname in os.listdir(SLIDES_DIR):
        if fname.endswith('.json'):
            with open(os.path.join(SLIDES_DIR, fname), 'r', encoding='utf-8') as f:
                slides.append(json.load(f))
    return slides

def get_slide(slide_id: str) -> Optional[dict]:
    meta_path = _meta_path(slide_id)
    if not os.path.exists(meta_path):
        return None
    with open(meta_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def delete_slide(slide_id: str) -> bool:
    pptx_path = _slide_path(slide_id)
    meta_path = _meta_path(slide_id)
    removed = False
    if os.path.exists(pptx_path):
        os.remove(pptx_path)
        removed = True
    if os.path.exists(meta_path):
        os.remove(meta_path)
        removed = True
    return removed

def get_slide_file(slide_id: str) -> Optional[str]:
    pptx_path = _slide_path(slide_id)
    if os.path.exists(pptx_path):
        return pptx_path
    return None

def compile_slides_with_index() -> str:
    """
    Compile all saved slides into a single pptx file with an index slide at the front.
    Returns the path to the compiled pptx file.
    """
    logger = logging.getLogger(__name__)
    compiled_path = os.path.join(SLIDES_DIR, 'all_songs.pptx')
    slides = list_slides()
    logger.info(f"Found {len(slides)} slides to compile.")
    if not slides:
        logger.error("No slides to compile.")
        raise Exception("No slides to compile.")
    # Order slides alphabetically by title (case-insensitive)
    slides = sorted(slides, key=lambda x: (x.get('title') or '').lower())
    logger.info(f"Slides after sorting: {[s.get('title') for s in slides]}")
    # Start with a new presentation
    prs = Presentation()
    # Set slide size to match individual song slides (10 x 5.625 inches)
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(5.625)
    # Add index slide
    slide_layout = prs.slide_layouts[5]  # Title Only
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    title.text = "Song Index"
    # Add song titles as bullet points
    tf = slide.shapes.add_textbox(left=Inches(1), top=Inches(1.5), width=Inches(8), height=Inches(4)).text_frame
    song_slide_indices = []
    for meta in slides:
        p = tf.add_paragraph()
        p.text = f"{meta.get('title', 'Untitled')} - {meta.get('artist', '')}"
        song_slide_indices.append(len(prs.slides))  # The next slide to be added will be this song's first slide
    # Remove any leading empty paragraph from the text frame
    while tf.paragraphs and not tf.paragraphs[0].text.strip():
        p = tf.paragraphs[0]
        tf._element.remove(p._p)

    # Append all slides from each pptx, keeping track of the first slide index for each song
    song_first_slide_indices = []
    for idx, meta in enumerate(slides):
        pptx_path = _slide_path(meta['id'])
        logger.info(f"Adding slides from: {pptx_path}")
        src_prs = Presentation(pptx_path)
        first_song_slide_idx = len(prs.slides)
        song_first_slide_indices.append(first_song_slide_idx)
        for src_slide in src_prs.slides:
            blank_slide_layout = prs.slide_layouts[6]
            new_slide = prs.slides.add_slide(blank_slide_layout)
            for shape in src_slide.shapes:
                el = shape.element
                new_slide.shapes._spTree.insert_element_before(el, 'p:extLst')
    # Add transparent shapes as hyperlinks over each index entry
    index_slide = prs.slides[0]
    textbox_top = 1.5
    textbox_height = 4
    left = Inches(1)
    width = Inches(8)
    tf_paragraphs = tf.paragraphs
    num_paragraphs = len(tf_paragraphs)
    # Calculate the height of each paragraph box
    para_height = textbox_height / num_paragraphs if num_paragraphs else 0.33
    box_height = para_height * 0.75  # 75% of the calculated height
    vertical_offset = (para_height - box_height) / 2  # Center the box on the text line

    for idx, first_song_slide_idx in enumerate(song_first_slide_indices):
        top = Inches(textbox_top + idx * para_height + vertical_offset)
        height = Inches(box_height)
        shape = index_slide.shapes.add_shape(
            1,  # Rectangle
            left, top, width, height
        )
        shape.fill.solid()
        shape.fill.transparency = 1.0
        shape.line.fill.solid()
        shape.line.fill.transparency = 1.0
        shape.line.width = Pt(0)
        shape.click_action.target_slide = prs.slides[first_song_slide_idx]
        logger.info(f"Added clickable area for '{slides[idx].get('title')}' to slide {first_song_slide_idx+1}")
    prs.save(compiled_path)
    logger.info(f"Compiled PPTX saved to: {compiled_path}")
    return compiled_path

def clear_temp_files():
    """Delete all files in saved_slides except for .pptx and .json files (keeps all saved slides and compiled PPTX)."""
    for fname in os.listdir(SLIDES_DIR):
        if fname.endswith('.pptx') or fname.endswith('.json'):
            continue
        file_path = os.path.join(SLIDES_DIR, fname)
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Could not remove {file_path}: {e}") 
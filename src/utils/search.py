import logging
import re
import requests
from bs4 import BeautifulSoup



def format_worship_together_url(song_name, artist):
    """
    Format a song name and artist into a URL slug for the default
    pluggable chord/lyric source.

    Example: 'Amazing Grace' by 'Traditional' becomes 'amazing-grace-traditional'.
    If artist is not specified, do not append the artist part.

    Note: The function name is preserved for historical reasons. When a
    second scraper is wired in, the helper can be renamed (and moved
    behind a per-source adapter) alongside the other source-specific
    symbols called out in ADR-001 (Trade-offs). For now it lives here so
    the default scraper can build the URL it fetches.
    """
    def clean_text(text):
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s-]', '', text)
        text = re.sub(r'\s+', '-', text)
        return text.strip('-')

    song_slug = clean_text(song_name)
    artist_slug = clean_text(artist) if artist else ''
    if artist_slug:
        return f"https://www.worshiptogether.com/songs/{song_slug}-{artist_slug}/"
    return f"https://www.worshiptogether.com/songs/{song_slug}/"



# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SECTION_HEADERS = ['Intro', 'Verse', 'Pre-Chorus', 'Chorus', 'Interlude', 'Instrumental.', 'Bridge', 'Tag', 'Outro']
NUMBERED_SECTIONS = ['Verse', 'Chorus', 'Bridge']

CHROMATIC_SCALE_SHARPS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
CHROMATIC_SCALE_FLATS = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']



def is_chord_line(line):
    # Heuristic: line contains only chords, bars, slashes, spaces
    return bool(re.match(r'^[A-G][#b]?m?7?sus?2?4?|[|/\s]+$', line.strip())) or bool(re.match(r'^[|/\sA-G0-9#bm7susdimaug\-]+$', line.strip()))



def is_repeat_instruction(line):
    # Check if line contains repeat instructions
    return bool(re.match(r'^REPEAT\s+(VERSE|CHORUS|BRIDGE)', line.strip(), re.IGNORECASE))



def extract_wt_chordpro_sections(html, target_key=None, original_key=None):
    """
    Extract and group content from ``<div class='chord-pro-line'>``,
    combining segments into aligned chord and lyric lines, grouped into
    sections. If ``target_key`` and ``original_key`` are provided,
    transpose the chords accordingly.

    Returns a list of dicts: ``{name, lines: [chord_line, lyric_line, ...]}``.

    Note: the function name is preserved until additional scrapers land
    (see ADR-001, Trade-offs). New scrapers should ship with their own
    per-source parse helper rather than reusing this one.
    """
    soup = BeautifulSoup(html, 'html.parser')
    lines = []
    
    # Calculate semitones for transposition if needed
    semitones = 0
    use_flats = False
    if target_key and original_key and target_key != original_key:
        semitones = get_semitone_shift(original_key, target_key)
        use_flats = 'b' in target_key
    
    for line_div in soup.find_all('div', class_='chord-pro-line'):
        chord_segments = []
        lyric_segments = []
        for seg in line_div.find_all('div', class_='chord-pro-segment'):
            chord = ''
            lyric = ''
            note = seg.find('div', class_='chord-pro-note')
            lyric_div = seg.find('div', class_='chord-pro-lyric')
            if note:
                chord = note.get_text(strip=True).replace('\xa0', ' ')
                # Transpose chord if needed
                if semitones != 0:
                    logger.debug(f"Transposing chord '{chord}' from {original_key} to {target_key} by {semitones} semitones")
                    chord = transpose_chord(chord, semitones, use_flats)
            if lyric_div:
                lyric = lyric_div.get_text(strip=True)
            # Alignment logic: pad chord or lyric to match the longer one
            max_len = max(len(chord), len(lyric), 1)
            chord_segments.append(chord.ljust(max_len))
            lyric_segments.append(lyric.ljust(max_len))
        # Now align chords above lyrics
        chord_line = ''
        lyric_line = ''
        for idx in range(len(chord_segments)):
            if idx > 0:
                chord_line += ' '
                lyric_line += ' '
            chord_line += chord_segments[idx]
            lyric_line += lyric_segments[idx]
        # Remove lines with 'REPEAT *'
        repeat_pattern = re.compile(r'^\s*REPEAT\s+.*$', re.IGNORECASE)
        if repeat_pattern.match(lyric_line.strip()):
            continue
        lines.append((chord_line.rstrip(), lyric_line.rstrip()))
    
    # Group into sections
    sections = []
    current_lines = []
    current_section_name = None
    section_header_regex = re.compile(r'^(' + '|'.join(SECTION_HEADERS) + r')(\s*\d*)$', re.IGNORECASE)
    
    # Instrumental-like section names (case-insensitive)
    INSTRUMENTAL_SECTIONS = {s.lower().rstrip('.') for s in ['Intro', 'Instrumental', 'Interlude', 'Tag', 'Outro']}
    
    for chord_line, lyric_line in lines:
        # Remove lines with 'REPEAT *' in grouping as well
        repeat_pattern = re.compile(r'^\s*REPEAT\s+.*$', re.IGNORECASE)
        if repeat_pattern.match(lyric_line.strip()):
            continue
            
        # Check if this is a section header (lyric line only)
        match = section_header_regex.match(lyric_line.strip())
        if match:
            # Save previous section if it exists
            if current_section_name or current_lines:
                sections.append({'name': current_section_name or 'Intro', 'lines': current_lines})
            current_section_name = lyric_line.strip()
            current_lines = []
        else:
            # For instrumental-like sections, ensure chord lines are properly transposed
            if current_section_name and current_section_name.lower().rstrip('.') in INSTRUMENTAL_SECTIONS:
                if chord_line.strip():
                    # Transpose the entire chord line if needed
                    if semitones != 0:
                        chord_line = transpose_chord_line(chord_line, semitones, use_flats)
                    current_lines.append(chord_line)
                if lyric_line.strip() and chord_line.strip() != lyric_line.strip():
                    current_lines.append(lyric_line)
            else:
                # Add both chord and lyric lines if they are not empty
                if chord_line.strip():
                    current_lines.append(chord_line)
                if lyric_line.strip() and chord_line.strip() != lyric_line.strip():
                    current_lines.append(lyric_line)
    
    # Save the last section
    if current_section_name or current_lines:
        sections.append({'name': current_section_name or 'Intro', 'lines': current_lines})
    return sections



def get_note_index(note, use_flats=False):
    scale = CHROMATIC_SCALE_FLATS if use_flats else CHROMATIC_SCALE_SHARPS
    try:
        return scale.index(note)
    except ValueError:
        # Try enharmonic
        enharmonic_map = {
            'Db': 'C#', 'Eb': 'D#', 'Gb': 'F#', 'Ab': 'G#', 'Bb': 'A#',
            'C#': 'Db', 'D#': 'Eb', 'F#': 'Gb', 'G#': 'Ab', 'A#': 'Bb',
        }
        alternate = enharmonic_map.get(note)
        if alternate is not None:
            return scale.index(alternate)
        return -1
def get_note_name(index, use_flats=False):
    scale = CHROMATIC_SCALE_FLATS if use_flats else CHROMATIC_SCALE_SHARPS
    return scale[index % 12]

def transpose_chord(chord, semitones, use_flats=False):
    # Handle chords with bass notes (e.g., C/G, Eb/G)
    if '/' in chord:
        # Split only on the last '/' to handle cases like 'C/G/B'
        parts = chord.rsplit('/', 1)
        if len(parts) == 2:
            root, bass = parts
            # Transpose both root and bass
            root = transpose_chord(root, semitones, use_flats)
            bass = transpose_chord(bass, semitones, use_flats)
            return f"{root}/{bass}"
    
    # Handle regular chords
    match = re.match(r'^([A-G][b#]?)(.*)$', chord)
    if not match:
        return chord
    root, suffix = match.groups()
    idx = get_note_index(root, use_flats)
    if idx == -1:
        return chord
    new_root = get_note_name(idx + semitones, use_flats)
    return new_root + suffix

def transpose_chord_line(line, semitones, use_flats=False):
    def repl(match):
        return transpose_chord(match.group(0), semitones, use_flats)
    return re.sub(r'([A-G][b#]?(?:/([A-G][b#]?))?)', repl, line)

def get_semitone_shift(original_key, target_key):
    # Use sharps for calculation
    try:
        idx_orig = get_note_index(original_key, use_flats=False)
        idx_target = get_note_index(target_key, use_flats=False)
        return (idx_target - idx_orig) % 12
    except Exception:
        return 0

def clean_song_name_for_url(song_name):
    text = song_name.lower()
    # Replace any space or comma between numbers with a dash
    text = re.sub(r'(?<=\d)[\s,]+(?=\d)', '-', text)
    # Remove all characters except alphanumerics, spaces, and dashes
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    # Replace spaces with dashes
    text = re.sub(r'[\s]+', '-', text)
    # Collapse multiple dashes
    text = re.sub(r'-+', '-', text)
    return text.strip('-')

def search_song(song_name, artist='', target_key=None, log_mode='preview'):
    """
    Search for a song on any registered public chord/lyric source and
    extract chords/lyrics from its chord-pro HTML. If ``target_key`` is
    specified, transpose all chords to that key. Returns the song data
    if found, ``None`` otherwise.

    ``log_mode``: controls which parts of the terminal logs are displayed.
        - ``all``: all parts (HTML extraction, chord transposition, preview).
        - ``html``: only the extracted HTML info.
        - ``chords``: only the original and transposed chords by section.
        - ``preview``: only the rendered-deck preview info.
    """
    try:
        # Back-compat: the part-3 branch was historically labelled 'pptx'
        # before PPTX export was retired. Map the legacy label to its
        # replacement so any stale caller keeps logging Part 3 output.
        if log_mode == 'pptx':
            log_mode = 'preview'
        logger.info(f"Log mode is: {log_mode}")
        cleaned_song_name = clean_song_name_for_url(song_name)
        url = format_worship_together_url(cleaned_song_name, artist)
        logger.info(f"Searching for song: {song_name} by {artist} at {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        logger.info(f"Response status: {response.status_code}")
        title_elem = soup.find('h1')
        if not title_elem:
            logger.error("Could not find song title")
            return None
        title = title_elem.text.strip()
        # Extract original key from meta tag
        meta_key = soup.find('meta', attrs={'property': 'cludo:originalKey'})
        original_key = meta_key['content'] if meta_key and meta_key.has_attr('content') else None
        logger.info(f"Original key: {original_key}")
        logger.info(f"Target key: {target_key}")
        # Extract chord-pro-line HTML
        chordpro_html = str(soup)
        # Extract original (untransposed) sections
        original_sections = extract_wt_chordpro_sections(chordpro_html, original_key, original_key)
        # Extract transposed sections (if needed)
        transposed_sections = extract_wt_chordpro_sections(chordpro_html, target_key, original_key) if target_key and original_key and target_key != original_key else original_sections
        
        # Use all transposed sections in order, do not filter out repeated section names
        lyrics_content = '\n\n'.join([
            f"{sec['name']}\n" + '\n'.join(sec['lines']) for sec in transposed_sections
        ])
        artist_name = artist
        logger.info(f"Found song: {title}")
        
        # Part 3: Display rendered-deck preview info
        if log_mode in ['all', 'preview']:
            logger.info("Preview info:")
            logger.info(f"Title: {title}")
            logger.info(f"Artist: {artist_name}")
            logger.info(f"Original Key: {original_key}")
            logger.info(f"Target Key: {target_key}")
            logger.info(f"Content:\n{lyrics_content}")
        
        return {
            'title': title,
            'search_name': song_name,
            'artist': artist_name,
            'content': lyrics_content,
            'source_url': url,
            'original_key': original_key
        }
    except requests.RequestException as e:
        logger.error(f"Error searching for song: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error parsing song data: {str(e)}")
        return None 

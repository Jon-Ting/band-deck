# Band-Deck - User Guide

## Application Overview

Band-Deck is a web application that allows you to quickly create musician-friendly slides displaying song lyrics with chord notations. The application searches reliable public sources for songs across many genres — including hymns, contemporary worship, folk, pop, and more — formats the content appropriately, and generates downloadable PowerPoint files optimized for musicians.

## Features

- **Simple Search Interface**: Enter a song name and optionally an artist to find your desired song
- **Preview Functionality**: View how the lyrics and chords will appear before downloading
- **PowerPoint Generation**: Download a professionally formatted PowerPoint file with lyrics and chords, ready to project during services, concerts, rehearsals, or lessons
- **Optimized Layout**: All content is auto-distributed across 2–4 columns with font sizing that fits the slide
- **Error Handling**: Clear feedback when songs cannot be found or other issues occur

## How to Use

1. **Access the Application**: Visit [https://4y0h0i3c5kmy.manus.space](https://4y0h0i3c5kmy.manus.space)

2. **Search for a Song**:
   - Enter the song name in the "Song Name" field
   - Optionally enter the artist name for more accurate results
   - Click "Generate Slide"

3. **Preview the Result**:
   - Once found, the song will appear in the preview section
   - Review the lyrics and chord formatting

4. **Download the PowerPoint File**:
   - Click the "Download PowerPoint" button
   - Save the `.pptx` file to your computer
   - Open it in PowerPoint, Keynote, or LibreOffice Impress to project or print

5. **Start a New Search**:
   - Click "New Search" to clear the form and search for another song

## Data Sources

The application searches the following sources for lyrics and chords:

1. **HymnChords.net**: Public-domain traditional hymns and similar songs
2. **Reawaken Hymns**: Modern arrangements of traditional hymns and contemporary songs

Additional sources (covering more genres, e.g. pop, rock, folk, country) may be added in future updates.

## Legal Considerations

- This tool is intended for personal, educational, and live-performance use (including worship services, concerts, rehearsals, and lessons)
- Users are responsible for ensuring they have appropriate licenses — e.g. **CCLI** for worship use, or **ASCAP / BMI / SESAC** or other rights organisations for general public performance — for any copyrighted material used in public settings
- The application respects rate limits of source websites to prevent overloading their servers

## Printing Instructions

The downloaded `.pptx` files can be opened in PowerPoint, Keynote, or LibreOffice Impress. From there, you can:

1. Print directly to paper (use **landscape orientation** for best results)
2. Export to PDF using your viewer of choice
3. Project directly from the application during services, concerts, rehearsals, or lessons

## Troubleshooting

- **Song Not Found**: Try checking the spelling or searching with just the song name without the artist
- **Download Issues**: Ensure your browser allows downloads from the application
- **Display Problems**: If the preview appears incorrect, try a different song or contact support

## Technical Information

- The application is built using Flask (Python) and modern web technologies
- PowerPoint files are generated with adaptive layout and font sizing for projection on different displays
- The application includes rate limiting to respect source websites

---

Thank you for using Band-Deck!

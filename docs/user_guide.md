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

1. **Access the Application**: Run the Flask app locally per the docs (see [README → Installation](../README.md)) and open **http://localhost:5000** in your browser.

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
   - Type a new song name into the **Song Name** field and click **Generate Slide** to search for another song

## Data Sources

The application currently scrapes one public source for lyrics and chords:

1. **[Worship Together](https://www.worshiptogether.com/)** — Christian-worship songs with chord charts.

Additional sources across more genres (pop, rock, folk, country) are planned; the scraper list lives in `src/utils/search.py`.

## Legal Considerations

This tool is intended for **personal study, educational, and live-performance use only**. All content is retrieved from public sources and should be consumed in compliance with applicable copyright laws.

By using this application you acknowledge that:

- Generated slides may be subject to copyright. You are responsible for ensuring appropriate licensing (e.g. **CCLI** for worship use, or **ASCAP / BMI / SESAC** for general public performance) before projection or distribution.
- Acceptable use includes (but is not limited to) worship services, concerts, rehearsals, and lessons.
- The application respects rate limits of source websites to prevent overloading their servers.
- This project ships with template/sample songs only — please verify each song's licensing status for your jurisdiction and use case.
- The maintainers do not endorse redistribution of copyrighted lyrics or chord charts outside the bounds of fair use.

## Printing Instructions

The downloaded `.pptx` files can be opened in PowerPoint, Keynote, or LibreOffice Impress. From there, you can:

1. Print directly to paper (use **landscape orientation** for best results)
2. Export to PDF using your viewer of choice
3. Project directly from the application during services, concerts, rehearsals, or lessons

## Troubleshooting

- **Song Not Found**: Try checking the spelling or searching with just the song name without the artist
- **Download Issues**: Ensure your browser allows downloads from the application
- **Display Problems**: If the preview appears incorrect, try a different song or open an issue on the project repository

## Technical Information

- The application is built using Flask (Python) and modern web technologies
- PowerPoint files are generated with adaptive layout and font sizing for projection on different displays
- The application includes rate limiting to respect source websites

---

Thank you for using Band-Deck!

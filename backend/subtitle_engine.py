def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds * 100) % 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def generate_karaoke_ass(words):
    """Generates V2.0 ASS Subtitles with Karaoke effect."""
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Montserrat ExtraBold,85,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,20,20,380,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = ""
    # Group words into small execution blocks (3-4 words)
    chunk_size = 4
    for i in range(0, len(words), chunk_size):
        chunk = words[i:i+chunk_size]
        start_t = format_time(chunk[0]['start'])
        end_t = format_time(chunk[-1]['end'])

        line_text = ""
        for w in chunk:
            # V2.0: Simple Karaoke
            dur_cs = int((w['end'] - w['start']) * 100)
            line_text += f"{{\\k{dur_cs}}}{w['word']} "

        events += f"Dialogue: 0,{start_t},{end_t},Default,,0,0,0,,{line_text.strip()}\n"

    return header + events

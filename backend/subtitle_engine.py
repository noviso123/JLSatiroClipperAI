def format_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds * 100) % 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def get_vertical_margin(t_middle, zones):
    """
    Determines margin based on layout at time t.
    Split -> True Center (900) - Straddles the 960px line.
    Normal -> Lower Third (350)
    """
    if not zones: return 350 # Default Normal

    current_layout = "Normal"
    for z in zones:
        # z: (start, end, layout)
        if z[0] <= t_middle <= z[1]:
            current_layout = z[2]
            break

    if current_layout == "Split": return 900 # 1920/2 - 60(half font) = 900
    return 350

def generate_karaoke_ass(words, zones=[]):
    """
    Titan V24.17: Anti-Overlap & True Center.
    - Chunk Size: 2 words
    - Alignment: 2
    - Margin: 900 (Center) / 350 (Bottom)
    """
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Viral,Arial Black,120,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,8,4,2,50,50,350,2

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = ""
    chunk_size = 2
    last_end_time = 0.0 # Track strict timing

    for i in range(0, len(words), chunk_size):
        chunk = words[i:i+chunk_size]
        if not chunk: continue

        # 1. Clamp Start Time to prevent overlap
        chk_start = chunk[0]['start']
        if chk_start < last_end_time: chk_start = last_end_time

        # 2. Clamp End Time
        chk_end = chunk[-1]['end']
        if chk_end <= chk_start: chk_end = chk_start + 0.1

        # Update tracker
        last_end_time = chk_end

        start_t = format_time(chk_start)
        end_t = format_time(chk_end)

        # Dynamic Positioning
        mid_t = (chk_start + chk_end) / 2
        margin_v = get_vertical_margin(mid_t, zones)

        line_text = ""
        for w in chunk:
            # Strip punctuation for cleaner look
            clean_word = w['word'].strip(".,?!")

            dur_cs = int((w['end'] - w['start']) * 100)
            line_text += f"{{\\k{dur_cs}}}{clean_word} "

        events += f"Dialogue: 0,{start_t},{end_t},Viral,,0,0,{margin_v},,{line_text.strip()}\n"

    return header + events.replace("&H00FFFFFF,&H00FFFFFF", "&H0000FFFF,&H00FFFFFF")

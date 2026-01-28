def segment_transcript(words, target_duration=60.0):
    """
    Groups words into segments of approx 'target_duration' seconds.
    Tries to break at sentence endings (.?!) or pauses.
    """
    segments = []
    if not words: return []

    current_words = []
    current_start = words[0]['start']

    for i, w in enumerate(words):
        current_words.append(w)
        current_end = w['end']
        duration = current_end - current_start

        # Check if we should split
        if duration >= target_duration:
            # Look ahead a bit for a better break?
            # Simplified: Just break here.
            # Or better: Check if last word ends with punctuation (if available) - Whisper sometimes gives punctuation.

            # Simple Logic: Break.
            segments.append({
                "start": current_start,
                "end": current_end,
                "text": " ".join([x['word'] for x in current_words])
            })

            # Reset
            if i + 1 < len(words):
                current_start = words[i+1]['start']
                current_words = []
            else:
                current_words = [] # Done

    # Floating stragglers (if > 10s)
    if current_words:
        dur = current_words[-1]['end'] - current_start
        if dur > 10:
             segments.append({
                "start": current_start,
                "end": current_words[-1]['end'],
                "text": " ".join([x['word'] for x in current_words])
            })

    print(f"✂️ Segmentação: {len(segments)} cortes criados.")
    return segments

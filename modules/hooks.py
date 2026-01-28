import os
import subprocess
import numpy as np

def find_impact_hook(audio_path, segment_start, segment_end, hook_duration=3.0):
    """
    Finds the 3-second window with the highest audio energy within a segment.
    Uses ffmpeg to extract a small chunk of audio and numpy for analysis.
    """
    duration = segment_end - segment_start
    if duration <= hook_duration:
        return segment_start

    # Extract raw audio for energy analysis
    # We sample every 0.5s to find the best window
    temp_raw = "temp_hook_scan.raw"
    try:
        subprocess.run([
            'ffmpeg', '-y',
            '-ss', str(segment_start),
            '-t', str(duration),
            '-i', audio_path,
            '-f', 's16le', '-ac', '1', '-ar', '16000',
            temp_raw
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        with open(temp_raw, 'rb') as f:
            audio_data = np.frombuffer(f.read(), dtype=np.int16)

        # Calculate RMS energy in windows
        samples_per_sec = 16000
        window_size = int(hook_duration * samples_per_sec)
        stride = int(0.5 * samples_per_sec) # Check every 0.5s

        best_energy = -1
        best_start_idx = 0

        for i in range(0, len(audio_data) - window_size, stride):
            window = audio_data[i:i+window_size]
            energy = np.sqrt(np.mean(window.astype(np.float32)**2))
            if energy > best_energy:
                best_energy = energy
                best_start_idx = i

        hook_start_offset = best_start_idx / samples_per_sec
        return segment_start + hook_start_offset
    except Exception as e:
        print(f"⚠️ Erro ao buscar Hook: {e}")
        return segment_start # Fallback to start
    finally:
        if os.path.exists(temp_raw):
            os.remove(temp_raw)

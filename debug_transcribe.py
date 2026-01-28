from modules import transcriber
import os

audio_path = r"c:\Users\12001036\Documents\JLSatiroClipperAI\production_temp\source.wav"
if os.path.exists(audio_path):
    print(f"Testing transcription on: {audio_path}")
    try:
        words = transcriber.transcribe_audio(audio_path)
        print(f"Transcription successful: {len(words)} words found.")
        for w in words[:10]:
            print(w)
    except Exception as e:
        print(f"Transcription FAILED: {e}")
else:
    print("Audio file NOT FOUND.")

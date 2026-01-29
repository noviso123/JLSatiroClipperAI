import subprocess
import os

video_path = 'temp_work\\input_video.mp4'
# COMMAND FROM LOG (FAILED FOR 1769697569_7)
cmd = ['ffmpeg', '-y', '-threads', '1', '-ss', '375.28', '-t', '60.12', '-i', video_path, '-filter_complex', '[0:v]split=2[v1][v2];[v1]scale=720:640:force_original_aspect_ratio=increase,crop=720:640[top];[v2]scale=720:640:force_original_aspect_ratio=increase,crop=720:640[bottom];[top][bottom]vstack=inputs=2[v_out];[v_out]scale=720:1280:flags=lanczos', '-r', '30', '-c:v', 'libx264', '-preset', 'ultrafast', '-c:a', 'aac', '-ar', '44100', '-max_muxing_queue_size', '9999', '-movflags', '+faststart', 'temp_work\\debug_fail_7.mp4']

print(f"Running command...")
res = subprocess.run(cmd, capture_output=True, text=True)
print("STDOUT:", res.stdout)
print("STDERR:", res.stderr)
print("RETURN CODE:", res.returncode)

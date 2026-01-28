import os
import shutil
from pytubefix import YouTube

def download_video(url, output_path):
    """
    Downloads the best MP4 video from YouTube using pytubefix.
    Returns: file_path (str) or None
    """
    try:
        print(f"⬇️ Baixando: {url}")
        yt = YouTube(url)

        # Priority: Progressive MP4 (Audio+Video) to save processing time
        stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()

        # Fallback: Best Video (might require manual merge later, but let's try direct first)
        if not stream:
            stream = yt.streams.filter(file_extension='mp4').order_by('resolution').desc().first()

        if not stream:
            print("❌ Nenhum stream MP4 encontrado.")
            return None

        # Download to a temporary filename first to avoid path issues
        filename = stream.default_filename
        download_dir = os.path.dirname(output_path)

        stream.download(output_path=download_dir, filename=os.path.basename(output_path))
        print("✅ Download concluído!")
        return output_path

    except Exception as e:
        print(f"❌ Erro Download: {e}")
        return None

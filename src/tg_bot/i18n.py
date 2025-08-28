from __future__ import annotations

from typing import Any, Dict


LANGS: Dict[str, str] = {
    "id": "Bahasa Indonesia",
    "en": "English",
}


TEXTS: Dict[str, Dict[str, str]] = {
    "id": {
    "welcome": "👋 Selamat datang! Pilih bahasa lalu pilih sumber platform atau unggah file.",
    "choose_platform": "🧭 Pilih sumber platform untuk dikonversi ke sticker Telegram, atau unggah file.",
    "send_url": "🔗 Kirim link dari platform yang dipilih.",
    "send_file": "📤 Unggah file gambar/video untuk dikonversi (webp/png/gif/webm/mp4/tgs/svg dll).",
    "processing": "⏳ Memproses...",
    "analyzing": "🤖 Analisa AI {done}/{total}...",
    "done": "✅ Selesai.",
    "partial_success": "⚠️ Sebagian berhasil. Gagal: {fails}. Anda bisa coba ulang untuk file yang gagal.",
    "retry_prompt": "🔁 Ingin konversi ulang file yang gagal? /retry",
    "ai_disabled": "🤖❌ AI tidak aktif; gunakan emoji default.",
    "error": "❌ Terjadi kesalahan: {msg}",
    "no_failed": "✅ Tidak ada file gagal untuk diulang.",
    "queued": "⏳ Bot sedang sibuk. Kamu di antrian nomor {pos} dari {total}. Estimasi ~{eta}s.",
    "queue_full": "🚫 Maaf, antrian penuh. Coba lagi nanti.",
    "cooldown": "🕒 Terlalu cepat. Tunggu {sec}s sebelum mencoba lagi.",
    "status": "📊 Status bot: sistem={sys}, AI={ai}, load={load}/{cap}, antrian={qsize}",
    "detected_files": "🧮 Terdeteksi {n} file. ⏱️ Estimasi ~{eta}s.",
    "link_received_estimating": "🔗 Link diterima. Estimasi akan muncul setelah paket terdeteksi.",
    },
    "en": {
    "welcome": "👋 Welcome! Choose language, then pick a source platform or upload files.",
    "choose_platform": "🧭 Choose a source platform to convert to Telegram stickers, or upload files.",
    "send_url": "🔗 Send the URL from the chosen platform.",
    "send_file": "📤 Upload image/video files to convert (webp/png/gif/webm/mp4/tgs/svg etc).",
    "processing": "⏳ Processing...",
    "analyzing": "🤖 Analyzing with AI {done}/{total}...",
    "done": "✅ Done.",
    "partial_success": "⚠️ Partially succeeded. Failed: {fails}. You can retry failed items.",
    "retry_prompt": "🔁 Retry failed files? /retry",
    "ai_disabled": "🤖❌ AI disabled; using default emoji.",
    "error": "❌ Error: {msg}",
    "no_failed": "✅ No failed files to retry.",
    "queued": "⏳ Bot is busy. You are in queue position {pos} of {total}. ETA ~{eta}s.",
    "queue_full": "🚫 Sorry, queue is full. Please try again later.",
    "cooldown": "🕒 Too fast. Wait {sec}s before trying again.",
    "status": "📊 Bot status: system={sys}, AI={ai}, load={load}/{cap}, queue={qsize}",
    "detected_files": "🧮 Detected {n} files. ⏱️ ETA ~{eta}s.",
    "link_received_estimating": "🔗 Link received. ETA will appear after the pack is detected.",
    },
}


def t(lang: str, key: str, **kwargs: Any) -> str:
    table = TEXTS.get(lang, TEXTS["en"])  # default EN
    v = table.get(key, key)
    try:
        return v.format(**kwargs)
    except Exception:
        return v

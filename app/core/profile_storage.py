"""Stockage sécurisé des photos de profil dans Supabase Storage."""
from uuid import uuid4

import httpx
from fastapi import HTTPException, UploadFile

from app.core.config import settings

MAX_PROFILE_PHOTO_SIZE = 5 * 1024 * 1024
ALLOWED_IMAGES = {
    "image/jpeg": (".jpg", lambda data: data.startswith(b"\xff\xd8\xff")),
    "image/png": (".png", lambda data: data.startswith(b"\x89PNG\r\n\x1a\n")),
    "image/webp": (".webp", lambda data: len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"),
}


async def upload_profile_photo(file: UploadFile, folder: str) -> str:
    """Valide puis envoie une image au bucket public avec une clé serveur."""
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise HTTPException(status_code=503, detail="Le stockage des photos n'est pas configuré")

    content = await file.read(MAX_PROFILE_PHOTO_SIZE + 1)
    if not content:
        raise HTTPException(status_code=400, detail="Le fichier est vide")
    if len(content) > MAX_PROFILE_PHOTO_SIZE:
        raise HTTPException(status_code=413, detail="La photo ne doit pas dépasser 5 Mo")

    detected = next(
        ((mime, extension) for mime, (extension, check) in ALLOWED_IMAGES.items() if check(content)),
        None,
    )
    if detected is None:
        raise HTTPException(status_code=415, detail="Format accepté : JPG, PNG ou WebP")
    mime_type, extension = detected

    bucket = settings.SUPABASE_AVATAR_BUCKET
    object_path = f"{folder}/{uuid4().hex}{extension}"
    base_url = settings.SUPABASE_URL.rstrip("/")
    headers = {
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": mime_type,
        "x-upsert": "false",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base_url}/storage/v1/object/{bucket}/{object_path}",
                content=content,
                headers=headers,
            )
            response.raise_for_status()
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Impossible d'enregistrer la photo pour le moment")

    return f"{base_url}/storage/v1/object/public/{bucket}/{object_path}"

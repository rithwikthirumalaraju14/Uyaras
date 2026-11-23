"""R2 signed upload adapter. Never stores image bytes in PostgreSQL."""

import os
import secrets
from urllib.parse import quote
from fastapi import Request
from sqlalchemy.orm import Session
from .models import Product, Media
from .schemas import MediaInput, MediaConfirm, MediaEdit
from .security import staff, require
from .catalog import row_dict
from .checkout import audit


def client():
    import boto3

    account = os.getenv("R2_ACCOUNT_ID")
    require(
        account
        and os.getenv("R2_ACCESS_KEY_ID")
        and os.getenv("R2_SECRET_ACCESS_KEY")
        and os.getenv("R2_BUCKET")
        and os.getenv("R2_PUBLIC_URL"),
        "R2 is not configured. Sample images remain available.",
        503,
    )
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def attach_routes(api, DB):
    @api.patch("/api/v1/admin/media/{media_id}")
    def edit_media(media_id: str, data: MediaEdit, request: Request, db: Session = DB):
        u = staff(db, request, "catalog", True)
        m = db.get(Media, media_id)
        require(m, "Image not found.", 404)
        m.alt = data.alt
        m.position = data.position
        audit(db, u.id, "media_edited", m.id, alt=m.alt, position=m.position)
        return row_dict(m)

    @api.delete("/api/v1/admin/media/{media_id}")
    def detach_media(media_id: str, request: Request, db: Session = DB):
        u = staff(db, request, "catalog", True)
        m = db.get(Media, media_id)
        require(m, "Image not found.", 404)
        audit(db, u.id, "media_detached", m.id, object_key=m.object_key)
        db.delete(m)
        return {"ok": True}

    @api.post("/api/v1/admin/media/upload")
    def upload(data: MediaInput, request: Request, db: Session = DB):
        u = staff(db, request, "catalog", True)
        require(db.get(Product, data.product_id), "Product not found.", 404)
        ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[
            data.content_type
        ]
        key = f"products/{data.product_id}/{u.id}/{secrets.token_hex(16)}.{ext}"
        url = client().generate_presigned_url(
            "put_object",
            Params={
                "Bucket": os.environ["R2_BUCKET"],
                "Key": key,
                "ContentType": data.content_type,
                "ContentLength": data.size,
            },
            ExpiresIn=300,
        )
        return {"url": url, "object_key": key, "content_type": data.content_type}

    @api.post("/api/v1/admin/media/confirm")
    def confirm(data: MediaConfirm, request: Request, db: Session = DB):
        u = staff(db, request, "catalog", True)
        require(db.get(Product, data.product_id), "Product not found.", 404)
        require(
            data.object_key.startswith(f"products/{data.product_id}/{u.id}/")
            and ".." not in data.object_key,
            "Invalid object key.",
            422,
        )
        r2 = client()
        bucket = os.environ["R2_BUCKET"]
        head = r2.head_object(Bucket=bucket, Key=data.object_key)
        require(
            0 < head["ContentLength"] <= 10000000
            and head.get("ContentType") in ("image/jpeg", "image/png", "image/webp"),
            "Invalid uploaded file.",
            422,
        )
        # Decode actual bytes: a forged Content-Type must not publish arbitrary content.
        from PIL import Image
        from io import BytesIO

        raw = r2.get_object(Bucket=bucket, Key=data.object_key)["Body"].read(10000001)
        try:
            im = Image.open(BytesIO(raw))
            require(
                im.format in ("JPEG", "PNG", "WEBP")
                and im.width * im.height <= 24000000,
                "Invalid image.",
                422,
            )
            im.verify()
        except (ValueError, OSError):
            require(False, "Image could not be decoded.", 422)
        media = Media(
            product_id=data.product_id,
            object_key=data.object_key,
            url=os.environ["R2_PUBLIC_URL"].rstrip("/") + "/" + quote(data.object_key),
            alt=data.alt,
        )
        db.add(media)
        audit(db, u.id, "media_uploaded", data.product_id)
        db.flush()
        return row_dict(media)

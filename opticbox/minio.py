from minio import Minio
from django.conf import settings

client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_SECURE,
)

def upload_file_to_minio(file, object_name):
    """Загрузка файла в MinIO и возврат URL"""
    if not client.bucket_exists(settings.MINIO_BUCKET_NAME):
        client.make_bucket(settings.MINIO_BUCKET_NAME)
    client.put_object(
        settings.MINIO_BUCKET_NAME,
        object_name,
        file,
        length=file.size,
        content_type=file.content_type,
    )
    url = f"http://{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET_NAME}/{object_name}"
    return url

def delete_file_from_minio(object_name):
    """Удаление файла из MinIO"""
    try:
        client.remove_object(settings.MINIO_BUCKET_NAME, object_name)
    except Exception:
        pass  # Если файла нет — молча игнорируем

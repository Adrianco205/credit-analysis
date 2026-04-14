import logging
from datetime import timedelta
from google.cloud import storage
from app.core.config import settings

logger = logging.getLogger(__name__)

class GCSService:
    def __init__(self):
        # Al correr dentro de Google Cloud (VM/Cloud Run), esto se
        # autentica automáticamente sin necesidad de API Keys en el .env
        self.client = storage.Client()
        self.bucket_name = settings.GCS_BUCKET_NAME
        self.bucket = self.client.bucket(self.bucket_name)

    def upload_file(self, file_obj, destination_blob_name: str, content_type: str = "application/pdf") -> str:
        """Sube un archivo al bucket y retorna la ruta en el bucket."""
        try:
            blob = self.bucket.blob(destination_blob_name)
            
            # Subir desde un objeto de archivo (ej. de UploadFile de FastAPI)
            file_obj.seek(0)
            blob.upload_from_file(file_obj, content_type=content_type)
            
            logger.info(f"File uploaded to {self.bucket_name}/{destination_blob_name}")
            return destination_blob_name
        except Exception as e:
            logger.error(f"Error uploading to GCS: {e}")
            raise

    def generate_presigned_url(self, blob_name: str, expiration_minutes: int = 15) -> str:
        """
        Genera una URL temporal para que el cliente pueda descargar/ver el PDF
        sin hacer el bucket público.
        """
        try:
            blob = self.bucket.blob(blob_name)
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=expiration_minutes),
                method="GET",
            )
            return url
        except Exception as e:
            logger.error(f"Error generating presigned URL for {blob_name}: {e}")
            raise
# app/azure_client.py (dla klasyfikacji Ras)

import os
import httpx
import logging
from PIL import Image
from io import BytesIO

# Ustawienie logowania (na górze pliku, raz)
logging.basicConfig(level=logging.INFO)

# --- KLUCZOWA ZMIANA ZMIENNYCH ŚRODOWISKOWYCH DLA RAS! ---
CUSTOM_VISION_BREED_ENDPOINT = os.getenv("CUSTOM_VISION_BREED_ENDPOINT")
CUSTOM_VISION_BREED_PREDICTION_KEY = os.getenv("CUSTOM_VISION_BREED_PREDICTION_KEY")

# Maksymalny rozmiar obrazu dla Custom Vision API (4 MB)
MAX_IMAGE_SIZE_BYTES = 4 * 1024 * 1024

# --- KLUCZOWA ZMIANA NAZWY FUNKCJI! ---
async def get_breed_prediction(image_bytes: bytes):
    if not CUSTOM_VISION_BREED_ENDPOINT or not CUSTOM_VISION_BREED_PREDICTION_KEY:
        logging.error("CUSTOM_VISION_BREED_ENDPOINT lub CUSTOM_VISION_BREED_PREDICTION_KEY nie są ustawione.")
        return {"error": "Klucze API Custom Vision (Rasy) nie są skonfigurowane."}

    # --- NOWA LOGIKA: Kompresja obrazu, jeśli jest za duży ---
    if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
        logging.warning(f"Obraz jest za duży ({len(image_bytes)} bajtów). Próba kompresji do {MAX_IMAGE_SIZE_BYTES} bajtów.")
        try:
            img = Image.open(BytesIO(image_bytes))
            
            output_buffer = BytesIO()
            img.save(output_buffer, format="JPEG", quality=80) 
            
            compressed_image_bytes = output_buffer.getvalue()

            if len(compressed_image_bytes) > MAX_IMAGE_SIZE_BYTES:
                logging.warning("Obraz nadal za duży po kompresji JPEG. Zmniejszam wymiary.")
                max_dim = 1024 
                if img.width > max_dim or img.height > max_dim:
                    if img.width > img.height:
                        new_width = max_dim
                        new_height = int(img.height * (max_dim / img.width))
                    else:
                        new_height = max_dim
                        new_width = int(img.width * (max_dim / img.height))
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                output_buffer = BytesIO()
                img.save(output_buffer, format="JPEG", quality=80) 
                compressed_image_bytes = output_buffer.getvalue()

            image_bytes = compressed_image_bytes
            logging.info(f"Rozmiar obrazu po kompresji: {len(image_bytes)} bajtów.")

            if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
                logging.error(f"Obraz nadal za duży po wszystkich próbach kompresji. {len(image_bytes)} bajtów.")
                return {"error": "Obraz jest zbyt duży, nawet po próbie kompresji. Maksymalny rozmiar to 4MB."}

        except Exception as e:
            logging.error(f"Błąd podczas kompresji obrazu: {e}")
            return {"error": f"Wystąpił błąd podczas próby kompresji obrazu: {str(e)}"}
    # --- KONIEC NOWEJ LOGIKI ---

    headers = {
        "Prediction-Key": CUSTOM_VISION_BREED_PREDICTION_KEY, 
        "Content-Type": "application/octet-stream"
    }
    
    logging.info(f"Wysyłam zapytanie do Custom Vision (Rasy). Endpoint: {CUSTOM_VISION_BREED_ENDPOINT}") 

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                CUSTOM_VISION_BREED_ENDPOINT, 
                headers=headers,
                content=image_bytes,
                timeout=30
            )
            response.raise_for_status()
            
            cv_response = response.json()
            logging.info(f"Otrzymano odpowiedź z Custom Vision (Rasy): {cv_response}")

            breeds = []
            if "predictions" in cv_response:
                for prediction in cv_response["predictions"]:
                    breeds.append({
                        "name": prediction.get("tagName", "Nieznana rasa"),
                        "confidence": prediction.get("probability", 0.0)
                    })
                breeds.sort(key=lambda x: x['confidence'], reverse=True)
            
            return {"breeds": breeds}

    except httpx.HTTPStatusError as e:
        error_message = f"Błąd HTTP z Custom Vision (Rasy): {e.response.status_code} - {e.response.text}"
        logging.error(error_message)
        return {"error": error_message}
    except httpx.RequestError as e:
        error_message = f"Błąd połączenia z Custom Vision (Rasy): {e}"
        logging.error(error_message)
        return {"error": error_message}
    except Exception as e:
        error_message = f"Ogólny błąd w kliencie Custom Vision (Rasy): {e}"
        logging.error(error_message)
        return {"error": error_message}
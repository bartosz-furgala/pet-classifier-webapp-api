# app/custom_vision_client.py (dla klasyfikacji Pies/Kot)

import os
import httpx
import base64
import json
import logging

logging.basicConfig(level=logging.INFO)

# Zmienne dla Custom Vision (Pies/Kot)
CUSTOM_VISION_DOG_CAT_ENDPOINT = os.getenv("CUSTOM_VISION_DOG_CAT_ENDPOINT")
CUSTOM_VISION_DOG_CAT_PREDICTION_KEY = os.getenv("CUSTOM_VISION_DOG_CAT_PREDICTION_KEY")

async def get_dog_cat_prediction(image_bytes: bytes):
    if not CUSTOM_VISION_DOG_CAT_ENDPOINT or not CUSTOM_VISION_DOG_CAT_PREDICTION_KEY:
        logging.error("CUSTOM_VISION_DOG_CAT_ENDPOINT lub CUSTOM_VISION_DOG_CAT_PREDICTION_KEY nie są ustawione.")
        return {"error": "Klucze API Custom Vision (Pies/Kot) nie są skonfigurowane."}

    headers = {
        "Prediction-Key": CUSTOM_VISION_DOG_CAT_PREDICTION_KEY,
        "Content-Type": "application/octet-stream" 
    }

    data = image_bytes
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                CUSTOM_VISION_DOG_CAT_ENDPOINT,
                headers=headers,
                content=data,
                timeout=30
            )
            response.raise_for_status()

            cv_response = response.json()
            logging.info(f"Otrzymano odpowiedź z Custom Vision (Pies/Kot): {cv_response}")

            if "predictions" in cv_response and cv_response["predictions"]:
                best_prediction = max(cv_response["predictions"], key=lambda p: p["probability"])
                tag_name = best_prediction.get("tagName", "Nieokreślony")
                probability = best_prediction.get("probability", 0.0)

                return {
                    "animal_type": tag_name, 
                    "animal_confidence": probability
                }
            else:
                logging.warning(f"Nieoczekiwany format odpowiedzi z Custom Vision (Pies/Kot): {cv_response}")
                return {"error": "Nieoczekiwany format odpowiedzi z Custom Vision (Pies/Kot)."}

    except httpx.HTTPStatusError as e:
        error_message = f"Błąd HTTP z Custom Vision (Pies/Kot): {e.response.status_code} - {e.response.text}"
        logging.error(error_message)
        return {"error": error_message}
    except httpx.RequestError as e:
        error_message = f"Błąd połączenia z Custom Vision (Pies/Kot): {e}"
        logging.error(error_message)
        return {"error": error_message}
    except Exception as e:
        error_message = f"Ogólny błąd w kliencie Custom Vision (Pies/Kot): {e}"
        logging.error(error_message)
        return {"error": error_message}
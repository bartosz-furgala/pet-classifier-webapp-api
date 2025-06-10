# app/main.py

from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import os
import shutil
from io import BytesIO
import logging

# Ustawienie logowania (na górze pliku, raz)
logging.basicConfig(level=logging.INFO)

# Importujemy KLIENTÓW dla obu usług Custom Vision
# get_breeds_prediction - model do klasyfikacji RAS (używa azure_client.py)
from .azure_client import get_breed_prediction as get_breeds_prediction 
# get_dog_cat_prediction - model do klasyfikacji Pies/Kot (używa custom_vision_client.py)
from .custom_vision_client import get_dog_cat_prediction 

# Wczytanie zmiennych środowiskowych (potrzebne tylko lokalnie, na Azure nie)
load_dotenv()

app = FastAPI(title="Pet Classifier AI 🐕🐈")

# Montowanie statycznych plików (CSS, JS)
# Upewnij się, że ten katalog istnieje i zawiera Twoje pliki CSS i JS
# Ścieżka katalogu powinna być względem miejsca uruchomienia aplikacji (czyli katalogu głównego projektu)
# Aplikacja jest uruchamiana z katalogu głównego, więc app/static
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Konfiguracja szablonów Jinja2
# Ścieżka katalogu powinna być względem miejsca uruchomienia aplikacji (czyli katalogu głównego projektu)
# Aplikacja jest uruchamiana z katalogu głównego, więc app/templates
templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, error_message: str = None):
    """Serwuje główną stronę HTML."""
    context = {"request": request}
    if error_message:
        context["error_message"] = error_message # Przekazujemy błąd do szablonu, jeśli istnieje
    return templates.TemplateResponse("index.html", context=context)

@app.post("/predict_breeds/", response_class=JSONResponse)
async def predict_breeds_endpoint(file: UploadFile = File(...)):
    """
    Endpoint do przyjmowania obrazu i zwracania predykcji RAS (za pomocą Custom Vision).
    """
    if not file.content_type.startswith("image/"):
        logging.warning(f"Otrzymano plik, który nie jest obrazem: {file.content_type}")
        return JSONResponse(
            status_code=400,
            content={"error": "Przesłany plik nie jest obrazem."}
        )

    try:
        image_bytes = await file.read()
        
        # Wywołujemy klienta Custom Vision dla ras
        # Zgodnie z naszą refaktoryzacją, get_breeds_prediction pochodzi z azure_client.py
        prediction_results = await get_breeds_prediction(image_bytes=image_bytes)

        if prediction_results and prediction_results.get("error"): # Sprawdzamy czy prediction_results nie jest None i ma klucz "error"
            logging.error(f"Błąd z Custom Vision (Rasy): {prediction_results.get('error')}")
            return JSONResponse(
                status_code=500,
                content={"error": f"Błąd predykcji ras: {prediction_results.get('error')}"}
            )

        return prediction_results # Zwracamy całe wyniki predykcji ras

    except Exception as e:
        logging.error(f"Błąd podczas przetwarzania pliku dla ras: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": f"Wystąpił wewnętrzny błąd serwera dla ras: {str(e)}"}
        )

@app.post("/predict_animal_type/", response_class=JSONResponse)
async def predict_animal_type_endpoint(file: UploadFile = File(...)):
    """
    Endpoint do przyjmowania obrazu i zwracania predykcji typu zwierzęcia (Pies/Kot)
    (za pomocą Custom Vision).
    """
    if not file.content_type.startswith("image/"):
        logging.warning(f"Otrzymano plik, który nie jest obrazem: {file.content_type}")
        return JSONResponse(
            status_code=400,
            content={"error": "Przesłany plik nie jest obrazem."}
        )

    try:
        image_bytes = await file.read()
        
        # Wywołujemy klienta Custom Vision dla typu zwierzęcia (Pies/Kot)
        # Zgodnie z naszą refaktoryzacją, get_dog_cat_prediction pochodzi z custom_vision_client.py
        prediction_result = await get_dog_cat_prediction(image_bytes) 

        if prediction_result and prediction_result.get("error"): 
            logging.error(f"Błąd z Custom Vision (Pies/Kot): {prediction_result.get('error')}")
            return JSONResponse(
                status_code=500,
                content={"error": f"Błąd predykcji typu zwierzęcia: {prediction_result.get('error')}"} 
            )

        return prediction_result 

    except Exception as e:
        logging.error(f"Błąd podczas przetwarzania pliku dla typu zwierzęcia: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": f"Wystąpił wewnętrzny błąd serwera dla typu zwierzęcia: {str(e)}"}
        )

# To uruchamiasz tylko lokalnie
if __name__ == "__main__":
    import uvicorn
    # Upewnij się, że uruchamiasz to z katalogu głównego projektu (`pet-classifier-webapp`)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
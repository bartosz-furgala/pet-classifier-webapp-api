document.addEventListener('DOMContentLoaded', () => {
    const imageUpload = document.getElementById('imageUpload');
    const selectImageButton = document.getElementById('selectImageButton');
    const imageFileName = document.getElementById('imageFileName');
    const imagePreview = document.getElementById('imagePreview');
    const analyzeButton = document.getElementById('analyzeButton');

    const loadingIndicator = document.getElementById('loadingIndicator');
    const animalTypeResults = document.getElementById('animalTypeResults');
    const animalTypeSpan = document.getElementById('animalType');
    const animalConfidenceSpan = document.getElementById('animalConfidence');
    const animalTypeErrorP = document.getElementById('animalTypeError');

    const breedResults = document.getElementById('breedResults');
    const breedListUl = document.getElementById('breedList');
    const breedErrorP = document.getElementById('breedError');

    let selectedFile = null;
    let translationData = { animal_types: {}, breeds: {} }; // Domyślne puste dane

    async function loadTranslations() {
        try {
            const response = await fetch('/static/data/translations.json');
            if (!response.ok) {
                console.error('Nie udało się załadować pliku tłumaczeń:', response.statusText);
                return;
            }
            translationData = await response.json();
            console.log('Tłumaczenia załadowane:', translationData);
        } catch (error) {
            console.error('Błąd podczas ładowania pliku tłumaczeń:', error);
        }
    }

    // --- POPRAWIONA FUNKCJA DO CZYSZCZENIA I TŁUMACZENIA NAZW, Bartek! ---
    function cleanAndTranslateName(name, type = 'breeds') {
        // 1. Najpierw zamień podkreślenia na spacje, aby klucz pasował do JSON-a.
        // Myślniki '-' zostają nienaruszone.
        const normalizedName = name.replace(/_/g, ' '); 
        
        // 2. Przekształć nazwę na małe litery do wyszukiwania w słowniku
        const nameToLookup = normalizedName.toLowerCase(); 

        let translatedName = normalizedName; // Domyślnie użyj znormalizowanej nazwy, jeśli nie ma tłumaczenia

        if (type === 'animal_types' && translationData.animal_types[nameToLookup]) {
            translatedName = translationData.animal_types[nameToLookup];
        } else if (type === 'breeds') {
            // Sprawdź, czy istnieje klucz z dokładnie taką nazwą jak model zwrócił (po normalizacji, ale przed toLowerCase)
            if (translationData.breeds[normalizedName]) { // Próbujemy znaleźć exact match z normalizowaną nazwą
                translatedName = translationData.breeds[normalizedName];
            } 
            // Jeśli nie ma dokładnego dopasowania, próbujemy znaleźć po nazwieToLookup (małe litery)
            else if (translationData.breeds[nameToLookup]) { 
                translatedName = translationData.breeds[nameToLookup];
            } else {
                // Jeśli w ogóle nie ma tłumaczenia, użyj znormalizowanej nazwy
                translatedName = normalizedName;
            }
        }

        // 3. Spraw, by pierwsza litera wyniku była duża (tylko jeśli jest to sensowne)
        if (translatedName && translatedName.length > 0) {
            return translatedName.charAt(0).toUpperCase() + translatedName.slice(1);
        }
        return translatedName; // Zwróć niezmienioną nazwę, jeśli jest pusta lub null
    }
    // --- KONIEC POPRAWIONEJ FUNKCJI ---


    function resetResults(keepLoaderVisible = false) {
        animalTypeSpan.textContent = '--';
        animalConfidenceSpan.textContent = '--';
        breedListUl.innerHTML = '';

        animalTypeErrorP.style.display = 'none';
        animalTypeErrorP.textContent = '';
        breedErrorP.style.display = 'none';
        breedErrorP.textContent = '';

        if (!keepLoaderVisible) {
            loadingIndicator.style.display = 'none';
        }
        animalTypeResults.style.display = 'none';
        breedResults.style.display = 'none';
    }

    selectImageButton.addEventListener('click', () => {
        imageUpload.click();
    });

    imageUpload.addEventListener('change', (event) => {
        selectedFile = event.target.files[0];
        resetResults(false);
        if (selectedFile) {
            imageFileName.textContent = selectedFile.name;
            imagePreview.src = URL.createObjectURL(selectedFile);
            imagePreview.style.display = 'block';
            analyzeButton.disabled = false;
        } else {
            imageFileName.textContent = 'Brak pliku';
            imagePreview.src = '#';
            imagePreview.style.display = 'none';
            analyzeButton.disabled = true;
        }
    });

    analyzeButton.addEventListener('click', async () => {
        if (!selectedFile) {
            alert('Proszę najpierw wybrać zdjęcie!');
            return;
        }

        resetResults(true);
        loadingIndicator.style.display = 'block';

        analyzeButton.disabled = true;

        const formData = new FormData();
        formData.append('file', selectedFile);

        // Predykcja typu zwierzęcia (Pies/Kot)
        try {
            const response = await fetch('/predict_animal_type/', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();

            if (response.ok) {
                const displayedAnimalType = cleanAndTranslateName(result.animal_type || 'Nieokreślony', 'animal_types');
                animalTypeSpan.textContent = displayedAnimalType;
                animalConfidenceSpan.textContent = `${(result.animal_confidence * 100).toFixed(2)}%` || '--';
                animalTypeResults.style.display = 'block';
            } else {
                animalTypeErrorP.textContent = `Błąd typu zwierzęcia: ${result.error || 'Nieznany błąd.'}`;
                animalTypeErrorP.style.display = 'block';
                animalTypeResults.style.display = 'block';
            }
        } catch (error) {
            console.error('Błąd podczas predykcji typu zwierzęcia:', error);
            animalTypeErrorP.textContent = `Wystąpił błąd komunikacji z serwerem dla typu zwierzęcia: ${error.message || error}`;
            animalTypeErrorP.style.display = 'block';
            animalTypeResults.style.display = 'block';
        }

        const breedsFormData = new FormData();
        breedsFormData.append('file', selectedFile);

        try {
            const response = await fetch('/predict_breeds/', {
                method: 'POST',
                body: breedsFormData
            });
            const result = await response.json();

            if (response.ok) {
                if (result.breeds && result.breeds.length > 0) {
                    const minConfidence = 0.10;
                    const filteredBreeds = result.breeds.filter(breed => breed.confidence >= minConfidence);

                    filteredBreeds.sort((a, b) => b.confidence - a.confidence);
                    const top3Breeds = filteredBreeds.slice(0, 3);

                    if (top3Breeds.length > 0) {
                        top3Breeds.forEach(breed => {
                            const li = document.createElement('li');
                            const displayedBreedName = cleanAndTranslateName(breed.name, 'breeds');
                            li.textContent = `${displayedBreedName} (${(breed.confidence * 100).toFixed(2)}%)`;
                            breedListUl.appendChild(li);
                        });
                    } else {
                        const li = document.createElement('li');
                        li.textContent = 'Brak sugerowanych ras (żadne nie spełniają progu pewności lub jest ich za mało).';
                        breedListUl.appendChild(li);
                    }
                } else {
                    const li = document.createElement('li');
                    li.textContent = 'Brak sugerowanych ras.';
                    breedListUl.appendChild(li);
                }
                breedResults.style.display = 'block';
            } else {
                breedErrorP.textContent = `Błąd ras: ${result.error || 'Nieznany błąd.'}`;
                breedErrorP.style.display = 'block';
                breedResults.style.display = 'block';
            }
        } catch (error) {
            console.error('Błąd podczas predykcji ras:', error);
            breedErrorP.textContent = `Wystąpił błąd komunikacji z serwerem dla ras: ${error.message || error}`;
            breedErrorP.style.display = 'block';
            breedResults.style.display = 'block';
        } finally {
            loadingIndicator.style.display = 'none';
            analyzeButton.disabled = false;
        }
    });

    resetResults(false);
    loadTranslations();
});
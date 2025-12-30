// Variables globales
let availableFiles = [];
let selectedFiles = new Set();

// Initialisation au chargement de la page
document.addEventListener('DOMContentLoaded', () => {
    loadAvailableFiles();
    setupEventListeners();
});

// Configuration des écouteurs d'événements
function setupEventListeners() {
    document.getElementById('select-all').addEventListener('click', selectAllFiles);
    document.getElementById('deselect-all').addEventListener('click', deselectAllFiles);
    document.getElementById('analyze-btn').addEventListener('click', performAnalysis);
}

// Charger la liste des fichiers disponibles
async function loadAvailableFiles() {
    try {
        const response = await fetch('/api/files');
        const data = await response.json();
        
        if (data.success) {
            availableFiles = data.files;
            renderFileSelection();
        } else {
            showError('Erreur lors du chargement des fichiers: ' + data.error);
        }
    } catch (error) {
        showError('Erreur de connexion: ' + error.message);
    }
}

// Afficher les fichiers disponibles
function renderFileSelection() {
    const container = document.getElementById('file-selection');
    container.innerHTML = '';
    
    if (availableFiles.length === 0) {
        container.innerHTML = '<p class="loading">Aucun fichier CSV trouvé</p>';
        return;
    }
    
    availableFiles.forEach(filename => {
        const div = document.createElement('div');
        div.className = 'file-checkbox';
        div.innerHTML = `
            <input type="checkbox" id="file-${filename}" value="${filename}">
            <label for="file-${filename}">${filename}</label>
        `;
        
        const checkbox = div.querySelector('input');
        checkbox.addEventListener('change', (e) => {
            if (e.target.checked) {
                selectedFiles.add(filename);
                div.classList.add('selected');
            } else {
                selectedFiles.delete(filename);
                div.classList.remove('selected');
            }
        });
        
        container.appendChild(div);
    });
}

// Sélectionner tous les fichiers
function selectAllFiles() {
    document.querySelectorAll('#file-selection input[type="checkbox"]').forEach(checkbox => {
        checkbox.checked = true;
        selectedFiles.add(checkbox.value);
        checkbox.parentElement.classList.add('selected');
    });
}

// Désélectionner tous les fichiers
function deselectAllFiles() {
    document.querySelectorAll('#file-selection input[type="checkbox"]').forEach(checkbox => {
        checkbox.checked = false;
        checkbox.parentElement.classList.remove('selected');
    });
    selectedFiles.clear();
}

// Effectuer l'analyse
async function performAnalysis() {
    // Validation
    if (selectedFiles.size === 0) {
        showError('Veuillez sélectionner au moins un fichier');
        return;
    }
    
    const graphType = document.querySelector('input[name="graph-type"]:checked').value;
    
    // Afficher le loading
    showLoading(true);
    hideError();
    
    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                files: Array.from(selectedFiles),
                graph_type: graphType
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayResults(data.plot, data.summaries);
        } else {
            showError('Erreur lors de l\'analyse: ' + data.error);
        }
    } catch (error) {
        showError('Erreur de connexion: ' + error.message);
    } finally {
        showLoading(false);
    }
}

// Afficher les résultats
function displayResults(plotData, summaries) {
    // Afficher la section résultats
    const resultsSection = document.getElementById('results-section');
    resultsSection.classList.remove('hidden');
    
    // Afficher les statistiques
    displayStatistics(summaries);
    
    // Afficher le graphique
    Plotly.newPlot('plot-container', plotData.data, plotData.layout, {
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ['lasso2d', 'select2d'],
        displaylogo: false
    });
    
    // Scroll vers les résultats
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Afficher les statistiques
function displayStatistics(summaries) {
    const container = document.getElementById('statistics');
    container.innerHTML = '';
    
    summaries.forEach(summary => {
        const card = document.createElement('div');
        card.className = 'stat-card';
        card.innerHTML = `
            <h3>${summary.filename}</h3>
            <div class="stat-value">${summary.rssi_moyen.toFixed(1)} dBm</div>
            <div class="stat-details">
                RSSI moyen<br>
                LQ: ${summary.lq_moyen.toFixed(1)}% | 
                Dist max: ${summary.distance_max.toFixed(0)}m<br>
                ${summary.nombre_points} points
            </div>
        `;
        container.appendChild(card);
    });
}

// Afficher/masquer le loading
function showLoading(show) {
    const loading = document.getElementById('loading');
    if (show) {
        loading.classList.remove('hidden');
    } else {
        loading.classList.add('hidden');
    }
}

// Afficher un message d'erreur
function showError(message) {
    const errorDiv = document.getElementById('error-message');
    errorDiv.textContent = '❌ ' + message;
    errorDiv.classList.remove('hidden');
    
    // Auto-masquer après 5 secondes
    setTimeout(() => {
        errorDiv.classList.add('hidden');
    }, 5000);
}

// Masquer le message d'erreur
function hideError() {
    document.getElementById('error-message').classList.add('hidden');
}

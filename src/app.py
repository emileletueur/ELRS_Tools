from flask import Flask, render_template, request, jsonify
from pathlib import Path
import json

from src.analyzer import RssiAnalyzer

app = Flask(__name__, 
            template_folder='../templates',
            static_folder='../static')

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
CSV_FOLDER = PROJECT_ROOT / "resources" / "csv"

@app.route('/')
def index():
    """Page principale"""
    return render_template('index.html')

@app.route('/api/files')
def get_files():
    """API pour récupérer la liste des fichiers CSV disponibles"""
    try:
        csv_files = sorted([f.name for f in CSV_FOLDER.glob("*.csv")])
        return jsonify({
            'success': True,
            'files': csv_files
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """API pour analyser les fichiers sélectionnés"""
    try:
        data = request.get_json()
        selected_files = data.get('files', [])
        graph_type = data.get('graph_type', 'rssi')
        
        if not selected_files:
            return jsonify({
                'success': False,
                'error': 'Aucun fichier sélectionné'
            }), 400
        
        # Créer l'analyseur
        analyzer = RssiAnalyzer(CSV_FOLDER, selected_files)
        
        if not analyzer.datasets:
            return jsonify({
                'success': False,
                'error': 'Impossible de charger les fichiers'
            }), 500
        
        # Générer le graphique demandé
        if graph_type == 'rssi':
            plot_json = analyzer.create_rssi_vs_distance_plot()
        elif graph_type == 'lq':
            plot_json = analyzer.create_link_quality_plot()
        elif graph_type == 'grid':
            plot_json = analyzer.create_comparison_grid()
        else:
            return jsonify({
                'success': False,
                'error': 'Type de graphique inconnu'
            }), 400
        
        # Récupérer les statistiques
        summaries = analyzer.get_summary_data()
        
        return jsonify({
            'success': True,
            'plot': json.loads(plot_json),
            'summaries': summaries
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

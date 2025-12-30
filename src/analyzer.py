import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.rssi_distance import RssiDistance

class RssiAnalyzer:
    def __init__(self, csv_folder: Path, csv_files: List[str]):
        """
        Initialise l'analyseur avec plusieurs fichiers CSV
        """
        self.csv_folder = csv_folder
        self.datasets = []
        self.load_files(csv_files)
    
    def load_files(self, csv_files: List[str]):
        """Charge tous les fichiers CSV"""
        for filename in csv_files:
            filepath = self.csv_folder / filename
            try:
                rssi_dist = RssiDistance(str(filepath))
                self.datasets.append(rssi_dist)
            except Exception as e:
                print(f"Erreur lors du chargement de {filename}: {e}")
    
    def get_summary_data(self) -> List[Dict]:
        """Retourne les données de résumé pour tous les datasets"""
        summaries = []
        for dataset in self.datasets:
            summary = dataset.get_summary()
            summary['filename'] = dataset.filename
            summaries.append(summary)
        return summaries
    
    def create_rssi_vs_distance_plot(self) -> str:
        """Génère un graphique interactif RSSI vs Distance"""
        fig = go.Figure()
        
        colors = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
            '#9467bd', '#8c564b', '#e377c2', '#7f7f7f'
        ]
        
        
        all_distances = []  # Pour déterminer l'étendue du graphique
        limit_added = False
        
        for i, dataset in enumerate(self.datasets):
            distances = [point.distance for point in dataset.data]
            rssi_values = [-abs(point.rssi_dbm) for point in dataset.data]
            
            valid_data = [(d, r) for d, r in zip(distances, rssi_values) 
                         if not (np.isnan(d) or np.isnan(r))]
            
            if valid_data:
                distances, rssi_values = zip(*valid_data)
                label = f"{dataset.RxPower} - {dataset.RxModule} (Mode {dataset.RxMode})"
                color = colors[i % len(colors)]                
                
                all_distances.extend(distances)
                
                # Points de données
                fig.add_trace(go.Scatter(
                    x=distances,
                    y=rssi_values,
                    mode='markers',
                    name=label,
                    marker=dict(size=3, color=color, opacity=0.6),
                    hovertemplate='<b>Distance:</b> %{x:.1f}m<br>' +
                                '<b>RSSI:</b> %{y:.1f}dBm<br>' +
                                '<extra></extra>'
                ))
                
                # Ligne de tendance
                if len(distances) > 1:
                    z = np.polyfit(distances, rssi_values, 2)
                    p = np.poly1d(z)
                    x_line = np.linspace(min(distances), max(distances), 100)
                    y_line = p(x_line)
                    
                    fig.add_trace(go.Scatter(
                        x=x_line.tolist(),
                        y=y_line.tolist(),
                        mode='lines',
                        name=f'{label} (tendance)',
                        line=dict(color=color),
                        hoverinfo='skip',
                        showlegend=False
                    ))
                    
            # AJOUTER LA LIGNE DE LIMITE À -98 dBm
            if all_distances and not limit_added:
                min_dist = min(all_distances)
                max_dist = max(all_distances)
                
                fig.add_trace(go.Scatter(
                    x=[min_dist, max_dist],
                    y=[-98, -98],
                    mode='lines',
                    name='Limite de sensibilité (-98 dBm)',
                    line=dict(
                        color='red',
                        width=2,
                        dash='dash'  # Ligne pointillée
                    ),
                    showlegend=False
                ))
                limit_added = True
        
        fig.update_layout(
            title='RSSI en fonction de la Distance',
            xaxis_title='Distance (m)',
            yaxis_title='RSSI (dBm)',
            hovermode='closest',
            template='plotly_white',
            height=600,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            )
        )
        
        return fig.to_json()
    
    def create_link_quality_plot(self) -> str:
        """Génère un graphique interactif Link Quality vs Distance"""
        fig = go.Figure()
        
        colors = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
            '#9467bd', '#8c564b', '#e377c2', '#7f7f7f'
        ]
        
        for i, dataset in enumerate(self.datasets):
            distances = [point.distance for point in dataset.data]
            lq_values = [point.link_quality for point in dataset.data]
            
            valid_data = [(d, lq) for d, lq in zip(distances, lq_values) 
                         if not (np.isnan(d) or np.isnan(lq))]
            
            if valid_data:
                distances, lq_values = zip(*valid_data)
                label = f"{dataset.RxPower} - {dataset.RxModule} (Mode {dataset.RxMode})"
                color = colors[i % len(colors)]
                
                fig.add_trace(go.Scatter(
                    x=distances,
                    y=lq_values,
                    mode='markers',
                    name=label,
                    marker=dict(size=3, color=color, opacity=0.6),
                    hovertemplate='<b>Distance:</b> %{x:.1f}m<br>' +
                                '<b>Link Quality:</b> %{y:.0f}%<br>' +
                                '<extra></extra>'
                ))
                
                # Ligne de tendance
                if len(distances) > 1:
                    z = np.polyfit(distances, lq_values, 2)
                    p = np.poly1d(z)
                    x_line = np.linspace(min(distances), max(distances), 100)
                    y_line = p(x_line)
                    
                    fig.add_trace(go.Scatter(
                        x=x_line,
                        y=y_line,
                        mode='lines',
                        name=f'{label} (tendance)',
                        line=dict(color=color, dash='dash', width=2),
                        showlegend=False,
                        hoverinfo='skip'
                    ))
        
        fig.update_layout(
            title='Link Quality en fonction de la Distance',
            xaxis_title='Distance (m)',
            yaxis_title='Link Quality (%)',
            hovermode='closest',
            template='plotly_white',
            height=600,
            yaxis=dict(range=[0, 105]),
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            )
        )
        
        return fig.to_json()
    
    def create_comparison_grid(self) -> str:
        """Génère une grille de comparaison avec 4 sous-graphiques"""
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('RSSI vs Distance', 'Link Quality vs Distance',
                          'Distribution RSSI', 'Statistiques'),
            specs=[[{"type": "scatter"}, {"type": "scatter"}],
                   [{"type": "box"}, {"type": "table"}]]
        )
        
        colors = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
            '#9467bd', '#8c564b', '#e377c2', '#7f7f7f'
        ]
        
        # 1. RSSI vs Distance
        for i, dataset in enumerate(self.datasets):
            distances = [p.distance for p in dataset.data]
            rssi_values = [p.rssi_dbm for p in dataset.data]
            valid_data = [(d, r) for d, r in zip(distances, rssi_values) 
                         if not (np.isnan(d) or np.isnan(r))]
            if valid_data:
                distances, rssi_values = zip(*valid_data)
                label = f"{dataset.RxPower}-{dataset.RxModule}"
                
                fig.add_trace(go.Scatter(
                    x=distances, y=rssi_values,
                    mode='markers',
                    name=label,
                    marker=dict(size=6, color=colors[i % len(colors)], opacity=0.5),
                    showlegend=True
                ), row=1, col=1)
        
        # 2. Link Quality vs Distance
        for i, dataset in enumerate(self.datasets):
            distances = [p.distance for p in dataset.data]
            lq_values = [p.link_quality for p in dataset.data]
            valid_data = [(d, lq) for d, lq in zip(distances, lq_values) 
                         if not (np.isnan(d) or np.isnan(lq))]
            if valid_data:
                distances, lq_values = zip(*valid_data)
                
                fig.add_trace(go.Scatter(
                    x=distances, y=lq_values,
                    mode='markers',
                    marker=dict(size=6, color=colors[i % len(colors)], opacity=0.5),
                    showlegend=False
                ), row=1, col=2)
        
        # 3. Distribution RSSI (Box plot)
        for i, dataset in enumerate(self.datasets):
            rssi_values = [p.rssi_dbm for p in dataset.data if not np.isnan(p.rssi_dbm)]
            if rssi_values:
                label = f"{dataset.RxPower}<br>{dataset.RxModule}"
                
                fig.add_trace(go.Box(
                    y=rssi_values,
                    name=label,
                    marker=dict(color=colors[i % len(colors)]),
                    showlegend=False
                ), row=2, col=1)
        
        # 4. Tableau de statistiques
        headers = ['Config', 'RSSI moy', 'LQ moy', 'Dist max']
        table_data = []
        
        for dataset in self.datasets:
            summary = dataset.get_summary()
            row = [
                f"{dataset.RxPower}-{dataset.RxModule}",
                f"{summary['rssi_moyen']:.1f} dBm",
                f"{summary['lq_moyen']:.1f}%",
                f"{summary['distance_max']:.0f} m"
            ]
            table_data.append(row)
        
        # Transposer les données pour Plotly
        table_values = [headers] + [[row[i] for row in table_data] for i in range(len(headers))]
        
        fig.add_trace(go.Table(
            header=dict(values=headers,
                       fill_color='#40466e',
                       font=dict(color='white', size=12),
                       align='center'),
            cells=dict(values=[table_data[i] for i in range(len(table_data[0]))],
                      fill_color='lavender',
                      align='center')
        ), row=2, col=2)
        
        # Mise à jour de la mise en page
        fig.update_xaxes(title_text="Distance (m)", row=1, col=1)
        fig.update_yaxes(title_text="RSSI (dBm)", row=1, col=1)
        fig.update_xaxes(title_text="Distance (m)", row=1, col=2)
        fig.update_yaxes(title_text="Link Quality (%)", row=1, col=2)
        fig.update_yaxes(title_text="RSSI (dBm)", row=2, col=1)
        
        fig.update_layout(
            height=900,
            showlegend=True,
            template='plotly_white',
            title_text="Analyse Complète RSSI - Comparaison des Configurations"
        )
        
        return fig.to_json()

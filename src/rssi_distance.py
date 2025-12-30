import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Dict
from pathlib import Path

@dataclass
class RssiDataPoint:
    """Représente un point de données RSSI"""
    rssi_dbm: float
    link_quality: int
    gps_lat: float
    gps_lon: float
    distance: float

class RssiDistance:
    def __init__(self, filepath: str):
        """
        Initialise l'objet RssiDistance à partir d'un fichier CSV
        
        Args:
            filepath: Chemin complet vers le fichier CSV
        """
        self.filepath = Path(filepath)
        self.filename = self.filepath.name
        
        # Extraction des informations du nom de fichier
        parts = self.filename.replace('.csv', '').split('_')
        
        self.RxPower = parts[0] if len(parts) > 0 else None
        self.RxModule = parts[1] if len(parts) > 1 else None
        
        # Chargement des métadonnées et données CSV
        self.metadata, self.df = self._load_csv_with_metadata()
        
        # Extraction du RxMode (première valeur de debug[3]) avec vérification
        self.RxMode = self._extract_rx_mode()
        
        # Création des objets RssiDataPoint
        self.data = self._create_data_points()
    
    def _load_csv_with_metadata(self) -> tuple[Dict[str, any], pd.DataFrame]:
        """
        Charge le fichier CSV en séparant les métadonnées et les données
        
        Returns:
            Tuple (métadonnées, DataFrame)
        """
        metadata = {}
        data_start_line = 0
        
        # Lire le fichier pour trouver où commencent les vraies données
        with open(self.filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
            for i, line in enumerate(lines):
                line = line.strip()
                
                # Ligne de métadonnée (contient une virgule mais pas de guillemets pour les headers)
                if ',' in line and not line.startswith('"loopIteration"'):
                    parts = line.split(',')
                    if len(parts) == 2:
                        # C'est une métadonnée
                        key = parts[0].strip('"')
                        try:
                            value = int(parts[1])
                        except ValueError:
                            try:
                                value = float(parts[1])
                            except ValueError:
                                value = parts[1].strip('"')
                        metadata[key] = value
                
                # Ligne d'en-tête des données (commence par "loopIteration")
                elif line.startswith('"loopIteration"'):
                    data_start_line = i
                    print(f"✓ En-tête des données trouvé à la ligne {i+1}")
                    break
        
        # Charger les données à partir de la ligne d'en-tête
        try:
            df = pd.read_csv(self.filepath, skiprows=data_start_line)
            print(f"✓ Fichier {self.filename} chargé: {len(df)} lignes de données")
            print(f"✓ Métadonnées trouvées: {metadata}")
            return metadata, df
        except Exception as e:
            print(f"❌ Erreur lors du chargement des données: {e}")
            raise
    
    def _extract_rx_mode(self) -> Optional[int]:
        """
        Extrait le RxMode de façon sécurisée depuis debug[3]
        
        Returns:
            Valeur de RxMode ou None
        """
        if self.df.empty:
            return None
        
        # Vérifier si la colonne existe
        if 'debug[3]' in self.df.columns:
            try:
                # Trouver la première valeur non-NaN
                non_nan_values = self.df['debug[3]'].dropna()
                if len(non_nan_values) > 0:
                    value = non_nan_values.iloc[0]
                    return int(value)
                else:
                    return None
            except (ValueError, IndexError) as e:
                print(f"⚠ Erreur lors de l'extraction de RxMode: {e}")
                return None
        else:
            print(f"⚠ Colonne 'debug[3]' absente dans {self.filename}")
            return None
    
    def _create_data_points(self) -> List[RssiDataPoint]:
        """
        Crée une liste d'objets RssiDataPoint à partir du DataFrame
        
        Returns:
            Liste d'objets RssiDataPoint
        """
        data_points = []
        
        # Vérifier que les colonnes requises existent
        required_columns = {
            'debug[0]': 'RSSI (dBm)',
            'debug[2]': 'Link Quality (%)',
            'GPS_coord[0]': 'GPS Latitude',
            'GPS_coord[1]': 'GPS Longitude',
            'gpsDistance': 'Distance (m)'
        }
        
        missing_columns = [f"{col} ({desc})" for col, desc in required_columns.items() if col not in self.df.columns]
        
        if missing_columns:
            print(f"⚠ Colonnes manquantes dans {self.filename}: {missing_columns}")
            print(f"   Colonnes disponibles: {list(self.df.columns)}")
            return data_points
        
        skipped_rows = 0
        for idx, row in self.df.iterrows():
            try:
                # Vérifier que la ligne contient des données valides (pas juste des NaN)
                if pd.isna(row['debug[0]']) or pd.isna(row['GPS_coord[0]']) or pd.isna(row['GPS_coord[1]']):
                    skipped_rows += 1
                    continue
                
                point = RssiDataPoint(
                    rssi_dbm=float(row['debug[0]']),
                    link_quality=int(row['debug[2]']) if pd.notna(row['debug[2]']) else 0,
                    gps_lat=float(row['GPS_coord[0]']),
                    gps_lon=float(row['GPS_coord[1]']),
                    distance=float(row['gpsDistance']) if pd.notna(row['gpsDistance']) else 0.0
                )
                data_points.append(point)
            except (ValueError, KeyError, TypeError) as e:
                skipped_rows += 1
                continue
        
        print(f"✓ {len(data_points)} points de données créés pour {self.filename}")
        if skipped_rows > 0:
            print(f"  ({skipped_rows} lignes ignorées car invalides)")
        
        return data_points
    
    def get_summary(self) -> dict:
        """
        Retourne un résumé statistique des données
        
        Returns:
            Dictionnaire contenant les statistiques principales
        """
        if not self.data:
            return {
                'filename': self.filename,
                'RxPower': self.RxPower,
                'RxModule': self.RxModule,
                'RxMode': self.RxMode,
                'nombre_points': 0,
                'error': 'Aucune donnée valide'
            }
        
        rssi_values = [p.rssi_dbm for p in self.data if not np.isnan(p.rssi_dbm)]
        lq_values = [p.link_quality for p in self.data if not np.isnan(p.link_quality)]
        distance_values = [p.distance for p in self.data if not np.isnan(p.distance) and p.distance > 0]
        
        return {
            'filename': self.filename,
            'RxPower': self.RxPower,
            'RxModule': self.RxModule,
            'RxMode': self.RxMode,
            'metadata': self.metadata,
            'nombre_points': len(self.data),
            'rssi_moyen': float(np.mean(rssi_values)) if rssi_values else 0,
            'rssi_min': float(np.min(rssi_values)) if rssi_values else 0,
            'rssi_max': float(np.max(rssi_values)) if rssi_values else 0,
            'rssi_std': float(np.std(rssi_values)) if rssi_values else 0,
            'lq_moyen': float(np.mean(lq_values)) if lq_values else 0,
            'lq_min': float(np.min(lq_values)) if lq_values else 0,
            'lq_max': float(np.max(lq_values)) if lq_values else 0,
            'distance_max': float(np.max(distance_values)) if distance_values else 0,
            'distance_moyen': float(np.mean(distance_values)) if distance_values else 0,
        }
    
    def __str__(self) -> str:
        """Représentation en chaîne de l'objet"""
        return (f"RssiDistance(fichier='{self.filename}', "
                f"RxPower={self.RxPower}, "
                f"RxModule={self.RxModule}, "
                f"RxMode={self.RxMode}, "
                f"points={len(self.data)})")
    
    def __repr__(self) -> str:
        """Représentation technique de l'objet"""
        return self.__str__()


# Test de la classe
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        try:
            print(f"\n{'='*70}")
            print(f"Test de chargement: {Path(filepath).name}")
            print(f"{'='*70}\n")
            
            rssi_dist = RssiDistance(filepath)
            print(f"\n{rssi_dist}")
            
            print("\n" + "="*70)
            print("Résumé des données:")
            print("="*70)
            summary = rssi_dist.get_summary()
            for key, value in summary.items():
                if key == 'metadata':
                    print(f"  {key:20s}:")
                    for mk, mv in value.items():
                        print(f"    {mk:25s}: {mv}")
                else:
                    print(f"  {key:20s}: {value}")
            
            # Afficher quelques exemples de points
            if rssi_dist.data:
                print(f"\n{'='*70}")
                print("Échantillon de points de données:")
                print("="*70)
                print(f"{'#':>3} | {'RSSI (dBm)':>10} | {'LQ (%)':>6} | {'Latitude':>12} | {'Longitude':>12} | {'Dist (m)':>8}")
                print("-" * 70)
                for i, point in enumerate(rssi_dist.data[:10]):
                    print(f"{i+1:3d} | {point.rssi_dbm:10.1f} | {point.link_quality:6d} | "
                          f"{point.gps_lat:12.6f} | {point.gps_lon:12.6f} | {point.distance:8.1f}")
            else:
                print("\n⚠ Aucun point de données valide trouvé")
                
        except Exception as e:
            print(f"\n❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("Usage: python rssi_distance.py <chemin_fichier_csv>")
        print("\nExemple:")
        print("  python rssi_distance.py ../resources/csv/25mW_internal_elrs.csv")

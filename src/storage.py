"""
Module de gestion du stockage des données
"""

import json
import os
from datetime import datetime
import logging
from pathlib import Path

class JobStorage:
    """Gestionnaire de stockage des données d'emploi"""

    def __init__(self, output_file="data/jobs_data.json"):
        self.output_file = Path(output_file)
        self.logger = logging.getLogger(__name__)

        # Création du répertoire de sortie si nécessaire
        self.output_file.parent.mkdir(parents=True, exist_ok=True)

        # Chargement des données existantes
        self.jobs_data = self.load_existing_data()
        self.job_urls = {job.get('url') for job in self.jobs_data if job.get('url')}

    def load_existing_data(self):
        """Charge les données existantes depuis le fichier JSON"""
        if self.output_file.exists():
            try:
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict) and 'jobs' in data:
                        return data['jobs']
                    elif isinstance(data, list):
                        return data
                    else:
                        return []
            except (json.JSONDecodeError, IOError) as e:
                self.logger.warning(f"Impossible de charger les données existantes: {e}")
                return []
        return []

    def job_exists(self, job_url):
        """Vérifie si une offre d'emploi existe déjà"""
        return job_url in self.job_urls

    def save_job(self, job_data):
        """Sauvegarde une offre d'emploi"""
        if not job_data or not job_data.get('url'):
            self.logger.warning("Données d'emploi invalides ou URL manquante")
            return False

        # Éviter les doublons
        if job_data['url'] not in self.job_urls:
            # Ajout d'un ID unique
            job_data['id'] = len(self.jobs_data) + 1
            job_data['added_at'] = datetime.now().isoformat()

            self.jobs_data.append(job_data)
            self.job_urls.add(job_data['url'])

            self.logger.debug(f"Offre ajoutée: {job_data.get('title', 'Sans titre')}")
            return True
        else:
            self.logger.debug(f"Offre déjà existante: {job_data['url']}")
            return False

    def finalize(self):
        """Sauvegarde finale des données"""
        output_data = {
            'metadata': {
                'total_jobs': len(self.jobs_data),
                'last_updated': datetime.now().isoformat(),
                'source': 'emploitogo.info',
                'scraper_version': '1.0.0'
            },
            'jobs': self.jobs_data
        }

        try:
            # Sauvegarde avec backup
            if self.output_file.exists():
                backup_file = self.output_file.with_suffix(f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
                os.rename(self.output_file, backup_file)
                self.logger.info(f"Backup créé: {backup_file}")

            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"Données sauvegardées: {len(self.jobs_data)} offres dans {self.output_file}")

        except IOError as e:
            self.logger.error(f"Erreur lors de la sauvegarde: {e}")
            raise

    def get_stats(self):
        """Retourne des statistiques sur les données"""
        return {
            'total_jobs': len(self.jobs_data),
            'unique_companies': len({job.get('company') for job in self.jobs_data if job.get('company')}),
            'unique_locations': len({job.get('location') for job in self.jobs_data if job.get('location')}),
            'latest_job': max((job.get('scraped_at') for job in self.jobs_data if job.get('scraped_at')), default=None)
        }
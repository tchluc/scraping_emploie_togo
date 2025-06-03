"""
Utilitaires pour le scraper
"""

import logging
import os
from pathlib import Path

def setup_logging(verbose=False):
    """Configure le système de logging"""

    # Création du dossier logs
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)

    # Configuration du niveau de log
    level = logging.DEBUG if verbose else logging.INFO

    # Configuration du format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Handler pour fichier
    file_handler = logging.FileHandler(
        log_dir / 'scraping.log',
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Handler pour console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # Configuration du logger racine
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Réduction du niveau pour les librairies externes
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

def create_directories():
    """Crée les répertoires nécessaires"""
    directories = ['data', 'logs', 'config']

    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
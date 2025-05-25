#!/usr/bin/env python3
"""
Point d'entrée principal du scraper emploitogo.info
Auteur: tchluc
Date: 2025-05-25
"""

import sys
import argparse
from src.scraper import EmploiTogoScraper
from src.utils import setup_logging
import logging

def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description='Scraper pour emploitogo.info')
    parser.add_argument('--pages', type=int, default=5, help='Nombre de pages à scraper')
    parser.add_argument('--output', type=str, default='data/jobs_data.json', help='Fichier de sortie')
    parser.add_argument('--verbose', '-v', action='store_true', help='Mode verbose')
    parser.add_argument('--incremental', action='store_true', help='Mode incrémental (nouvelles offres uniquement)')

    args = parser.parse_args()

    # Configuration du logging
    setup_logging(verbose=args.verbose)
    logger = logging.getLogger(__name__)

    logger.info("Démarrage du scraping emploitogo.info")
    logger.info(f"Pages à scraper: {args.pages}")
    logger.info(f"Fichier de sortie: {args.output}")

    try:
        # Initialisation du scraper
        scraper = EmploiTogoScraper(
            output_file=args.output,
            incremental=args.incremental
        )

        # Lancement du scraping
        results = scraper.scrape_jobs(max_pages=args.pages)

        logger.info(f"Scraping terminé avec succès: {results['total_jobs']} offres collectées")
        print(f"✅ Scraping terminé: {results['total_jobs']} offres sauvegardées dans {args.output}")

    except Exception as e:
        logger.error(f"Erreur lors du scraping: {str(e)}")
        print(f"❌ Erreur: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
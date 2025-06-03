#!/usr/bin/env python3
"""
Point d'entrée principal du scraper emploitogo.info
Version mise à jour avec la vraie structure HTML
"""

import sys
import argparse
import json
from pathlib import Path
from src.scraper import EmploiTogoScraper
from src.utils import setup_logging, create_directories
from src.extract_structured_info import extract_all_structured
import logging

def process_structured(input_file, output_file):
    """Traitement des offres extraites pour structuration avancée"""
    if not Path(input_file).exists():
        print(f"Fichier d'entrée {input_file} introuvable.")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        jobs_json = json.load(f)
        jobs = jobs_json["jobs"] if "jobs" in jobs_json else jobs_json

    structured_list = []
    for job in jobs:
        title = job.get("title", "")
        content = job.get("content", "")
        struct = extract_all_structured(content,title=title)
        struct["url"] = job.get("url")
        struct["title"] = job.get("title")
        structured_list.append(struct)

    output = {
        "total": len(structured_list),
        "jobs": structured_list
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Structuration terminée : {len(structured_list)} offres traitées et sauvegardées dans {output_file}")

def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(
        description='Scraper pour emploitogo.info - Extraction complète des offres d\'emploi',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:
  python main.py                           # Scraping de 5 pages par défaut
  python main.py --pages 10 --verbose      # 10 pages avec logs détaillés
  python main.py --all                     # Toutes les pages du site
  python main.py --incremental             # Nouvelles offres uniquement
  python main.py --output data/jobs.json   # Fichier de sortie personnalisé
  python main.py --struct                  # Structurer data/jobs_data.json en data/jobs_data_structured.json
        """
    )

    parser.add_argument('--pages', type=int, default=5,
                        help='Nombre de pages à scraper (défaut: 5)')
    parser.add_argument('--all', action='store_true',
                        help='Scraper toutes les pages disponibles')
    parser.add_argument('--output', type=str, default='data/jobs_data.json',
                        help='Fichier de sortie (défaut: data/jobs_data.json)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Mode verbose avec logs détaillés')
    parser.add_argument('--incremental', action='store_true',
                        help='Mode incrémental (nouvelles offres uniquement)')
    parser.add_argument('--test', action='store_true',
                        help='Mode test (1 seule page)')
    parser.add_argument('--struct', action='store_true',
                        help='Post-traitement : structurer les offres du scraping dans data/jobs_data_structured.json')

    args = parser.parse_args()

    # Créer les répertoires nécessaires
    create_directories()

    # Si l'utilisateur veut structurer uniquement
    if args.struct:
        process_structured("data/jobs_data.json", "data/jobs_data_structured.json")
        return

    # Configuration du logging
    setup_logging(verbose=args.verbose)
    logger = logging.getLogger(__name__)

    # Déterminer le nombre de pages
    if args.test:
        max_pages = 1
        logger.info("=== MODE TEST - 1 PAGE SEULEMENT ===")
    elif args.all:
        max_pages = None
        logger.info("=== MODE COMPLET - TOUTES LES PAGES ===")
    else:
        max_pages = args.pages
        logger.info(f"=== SCRAPING DE {max_pages} PAGES ===")

    logger.info("Démarrage du scraper emploitogo.info")
    logger.info(f"Fichier de sortie: {args.output}")
    logger.info(f"Mode incrémental: {'Oui' if args.incremental else 'Non'}")

    try:
        # Initialisation du scraper
        scraper = EmploiTogoScraper(
            output_file=args.output,
            incremental=args.incremental
        )

        # Information sur le site cible
        logger.info(f"Site cible: {scraper.jobs_url}")
        logger.info(f"Délai entre requêtes: {scraper.delay_between_requests}s")

        # Lancement du scraping
        logger.info("\n🚀 Début du scraping...")
        results = scraper.scrape_jobs(max_pages=max_pages)

        # Affichage des résultats
        print("\n" + "="*60)
        print("📊 RÉSULTATS DU SCRAPING")
        print("="*60)
        print(f"✅ Emplois collectés: {results['total_jobs']}")
        print(f"📄 Pages traitées: {results['pages_scraped']}")
        if results.get('total_pages_found', 0) > 0:
            print(f"📄 Pages totales disponibles: {results['total_pages_found']}")
        if args.incremental:
            print(f"🆕 Nouveaux emplois: {results['new_jobs']}")
        if results['errors'] > 0:
            print(f"❌ Erreurs: {results['errors']}")
        print(f"💾 Données sauvegardées dans: {args.output}")
        print(f"📈 Statistiques dans: data/scraping_stats.json")

        # Durée du scraping
        from datetime import datetime
        start_time = datetime.fromisoformat(results['start_time'])
        end_time = datetime.fromisoformat(results['end_time'])
        duration = end_time - start_time
        print(f"⏱️  Durée: {duration}")

        print("="*60)

        # Recommandations
        if results['total_jobs'] == 0:
            print("\n⚠️  Aucun emploi collecté. Vérifiez:")
            print("   - Votre connexion Internet")
            print("   - La structure du site (peut avoir changé)")
            print("   - Les logs pour plus de détails")
        elif results['total_jobs'] < 10 and not args.test:
            print(f"\n💡 Peu d'emplois collectés ({results['total_jobs']}). Considérez:")
            print("   - Augmenter le nombre de pages avec --pages N")
            print("   - Vérifier les logs avec --verbose")
        else:
            print(f"\n🎉 Scraping réussi! {results['total_jobs']} emplois collectés.")
            if not args.all and results.get('total_pages_found', 0) > args.pages:
                print(f"💡 Il reste {results['total_pages_found'] - args.pages} pages. Utilisez --all pour tout scraper.")

        logger.info("Scraping terminé avec succès")

    except KeyboardInterrupt:
        print("\n⏹️  Scraping interrompu par l'utilisateur")
        logger.info("Scraping interrompu par l'utilisateur")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Erreur fatale: {str(e)}", exc_info=True)
        print(f"\n❌ Erreur fatale: {str(e)}")
        print("Consultez les logs pour plus de détails: logs/scraping.log")
        sys.exit(1)

if __name__ == "__main__":
    main()
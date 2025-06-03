"""
Module principal de scraping pour emploitogo.info
Version mise à jour avec les vrais sélecteurs CSS
"""
import concurrent.futures

import requests
from bs4 import BeautifulSoup
import time
import logging
from urllib.parse import urljoin, urlparse
from datetime import datetime
import re
from .storage import JobStorage
from .data_processor import JobDataProcessor

class EmploiTogoScraper:
    """Scraper principal pour emploitogo.info"""

    def __init__(self, output_file="data/jobs_data.json", incremental=False):
        self.base_url = "https://www.emploitogo.info"
        self.jobs_url = "https://www.emploitogo.info/emploitogo/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        self.logger = logging.getLogger(__name__)
        self.storage = JobStorage(output_file)
        self.processor = JobDataProcessor()
        self.incremental = incremental

        # Configuration du rate limiting
        self.delay_between_requests = 3  # secondes entre chaque requête

    def get_page(self, url, retries=3):
        """Récupère une page web avec gestion d'erreurs"""
        for attempt in range(retries):
            try:
                self.logger.debug(f"Récupération de: {url}")
                response = self.session.get(url, timeout=30)
                response.raise_for_status()

                # Rate limiting pour respecter le serveur
                time.sleep(self.delay_between_requests)
                return response

            except requests.RequestException as e:
                self.logger.warning(f"Tentative {attempt + 1} échouée pour {url}: {str(e)}")
                if attempt == retries - 1:
                    raise
                time.sleep(5)  # Attendre avant de réessayer
                return None
        return None

    def extract_job_urls_from_listing(self, soup):
        """Extrait les URLs des offres d'emploi de la page de liste"""
        job_urls = []

        # Sélecteur pour les articles d'emploi
        job_articles = soup.select('.post-item')

        self.logger.info(f"Trouvé {len(job_articles)} articles sur cette page")

        for article in job_articles:
            # Chercher le lien dans le titre
            title_link = article.select_one('.entry-title a')
            if title_link:
                href = title_link.get('href')
                if href:
                    full_url = urljoin(self.base_url, href)
                    job_urls.append(full_url)
                    self.logger.debug(f"URL trouvée: {full_url}")

        return job_urls

    def extract_job_details(self, job_url):
        """Extrait les détails d'une offre d'emploi depuis sa page détaillée"""
        try:
            response = self.get_page(job_url)
            soup = BeautifulSoup(response.content, 'html.parser')

            job_data = {
                'url': job_url,
                'scraped_at': datetime.now().isoformat(),
                'title': self._extract_title(soup),
                'description': self._extract_description(soup),
                'content': self._extract_full_content(soup),
                'publication_date': self._extract_publication_date(soup),
                'meta_info': self._extract_meta_info(soup),
                'images': self._extract_images(soup)
            }

            # Traitement et nettoyage des données
            job_data = self.processor.process_job_data(job_data)

            return job_data

        except Exception as e:
            self.logger.error(f"Erreur lors de l'extraction de {job_url}: {str(e)}")
            return None

    def _extract_title(self, soup):
        """Extrait le titre du poste"""
        selectors = [
            'h1.entry-title',
            'h1',
            '.post-title h1',
            '.entry-header h1',
            'h1[class*="title"]'
        ]

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        return None

    def _extract_company(self, soup):
        """Extrait le nom de l'entreprise depuis le contenu"""
        content_text = soup.get_text()

        # Patterns courants pour identifier l'entreprise
        company_patterns = [
            r'(.*?)\s+recrute',
            r'La société\s+(.*?)\s+recherche',
            r'L[\']entreprise\s+(.*?)\s+recrute',
            r'Le groupe\s+(.*?)\s+recrute',
            r'La compagnie\s+(.*?)\s+recrute',
            r'(.*?)\s+cherche',
            r'RECRUTEMENT.*?(\w+(?:\s+\w+)*)',
        ]

        for pattern in company_patterns:
            match = re.search(pattern, content_text, re.IGNORECASE)
            if match:
                company = match.group(1).strip()
            # Nettoyer le nom de l'entreprise
            company = re.sub(r'^(la|le|l\'|une|un)\s+', '', company, flags=re.IGNORECASE)
            if len(company) > 2 and len(company) < 100:  # Validation basique
                return company

        return None

    def _extract_location(self, soup):
        """Extrait la localisation"""
        content_text = soup.get_text()

        # Villes du Togo et d'Afrique courantes
        african_cities = [
            'Lomé', 'Kara', 'Sokodé', 'Kpalimé', 'Atakpamé', 'Tsévié', 'Aného',
            'Abidjan', 'Douala', 'Yaoundé', 'Dakar', 'Cotonou', 'Ouagadougou',
            'Bamako', 'Accra', 'Lagos', 'Kinshasa', 'Libreville', 'Niamey'
        ]

        # Recherche des villes dans le texte
        found_cities = []
        for city in african_cities:
            if city.lower() in content_text.lower():
                found_cities.append(city)

        # Patterns de localisation
        location_patterns = [
            r'(?:à|au|en)\s+([A-Z][a-zé]+(?:\s+[A-Z][a-zé]+)*)',
            r'Lieu\s*:?\s*([A-Z][a-zé]+(?:\s+[A-Z][a-zé]+)*)',
            r'Poste basé\s+(?:à|au|en)\s+([A-Z][a-zé]+)',
            r'Siège\s*:?\s*([A-Z][a-zé]+)'
        ]

        for pattern in location_patterns:
            matches = re.findall(pattern, content_text)
            for match in matches:
                if match in african_cities:
                    return match

        return found_cities[0] if found_cities else None

    def _extract_description(self, soup):
        """Extrait la description courte du poste"""
        # D'abord chercher dans l'excerpt de la page de liste
        excerpt = soup.select_one('.entry-excerpt')
        if excerpt:
            return excerpt.get_text(strip=True)

        # Sinon prendre le début du contenu principal
        content = soup.select_one('.entry-content, .post-content, .content, main')
        if content:
            text = content.get_text(strip=True)
            # Prendre les premiers 300 caractères comme description
            return text[:300] + "..." if len(text) > 300 else text

        return None

    def _extract_full_content(self, soup):
        """Extrait le contenu complet de l'offre"""
        content_selectors = [
            '.entry-content',
            '.post-content',
            '.content',
            'main .container',
            'article'
        ]

        for selector in content_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)

        return None

    def _extract_contract_type(self, soup):
        """Extrait le type de contrat"""
        text = soup.get_text().lower()

        contract_types = [
            ('cdi', 'CDI'),
            ('cdd', 'CDD'),
            ('stage', 'Stage'),
            ('freelance', 'Freelance'),
            ('consultant', 'Consultant'),
            ('temps partiel', 'Temps partiel'),
            ('temps plein', 'Temps plein'),
            ('bénévolat', 'Bénévolat'),
            ('interim', 'Interim'),
            ('apprentissage', 'Apprentissage')
        ]

        for pattern, contract_type in contract_types:
            if pattern in text:
                return contract_type

        return None

    def _extract_sector(self, soup):
        """Extrait le secteur d'activité"""
        text = soup.get_text()

        # Secteurs d'activité courants
        sectors = [
            'Informatique', 'IT', 'Technologies', 'Finance', 'Banque',
            'Assurance', 'Santé', 'Médical', 'Education', 'Formation',
            'Commerce', 'Marketing', 'Communication', 'Logistique',
            'Transport', 'Agriculture', 'Industrie', 'Construction',
            'BTP', 'Humanitaire', 'ONG', 'Consulting', 'Juridique',
            'Analyste ',
            'Ressources Humaines', 'RH', 'Comptabilité', 'Audit','Génie Civil'
        ]

        for sector in sectors:
            if sector.lower() in text.lower():
                return sector

        return None

    def _extract_publication_date(self, soup):
        """Extrait la date de publication"""
        # Chercher dans les métadonnées
        date_selectors = [
            '.meta-date',
            '.entry-meta .meta-date',
            'time',
            '.published',
            '.post-date'
        ]

        for selector in date_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)

        return None

    def _extract_deadline(self, soup):
        """Extrait la date limite de candidature"""
        text = soup.get_text()

        # Patterns pour les dates limites
        deadline_patterns = [
            r'[Dd]ate limite[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})',
            r'[Aa]vant le[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})',
            r'[Jj]usqu[\']au[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})',
            r'[Dd]eadline[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})',
            r'[Ll]imite[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})',
            r'(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})\s*(?:au plus tard|maximum)'
        ]

        for pattern in deadline_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        return None

    def _extract_application_deadline(self, soup):
        """Extrait des informations sur la procédure de candidature"""
        text = soup.get_text()

        # Chercher des informations sur comment postuler
        application_patterns = [
            r'[Ee]nvoyer.*?(?:CV|candidature).*?(?:à|au|sur)[:\s]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            r'[Cc]andidature.*?(?:à|au|sur)[:\s]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            r'[Cc]ontact[:\s]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        ]

        for pattern in application_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)

        return None

    def _extract_salary(self, soup):
        """Extrait le salaire si mentionné"""
        text = soup.get_text()

        # Patterns de salaire pour l'Afrique
        salary_patterns = [
            r'(\d+[\s,]*\d*)\s*(?:FCFA|CFA|F\s*CFA)',
            r'salaire[:\s]*(\d+[\s,]*\d*)\s*(?:FCFA|CFA|F\s*CFA|euros?|€|\$)',
            r'rémunération[:\s]*(\d+[\s,]*\d*)\s*(?:FCFA|CFA|F\s*CFA|euros?|€|\$)',
            r'(\d+[\s,]*\d*)\s*(?:euros?|€|\$)',
            r'traitement[:\s]*(\d+[\s,]*\d*)',
            r'indemnité[:\s]*(\d+[\s,]*\d*)'
        ]

        for pattern in salary_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)

        return None

    def _extract_experience_level(self, soup):
        """Extrait le niveau d'expérience requis"""
        text = soup.get_text().lower()

        experience_patterns = [
        r'(\d+)\s*(?:ans?|années?)\s*d[\']expérience',
        r'expérience[:\s]*(\d+)\s*(?:ans?|années?)',
        r'minimum\s*(\d+)\s*(?:ans?|années?)',
        r'au moins\s*(\d+)\s*(?:ans?|années?)'
        ]

        # Mots-clés d'expérience
        experience_keywords = [
        'débutant', 'junior', 'senior', 'expérimenté',
        'sans expérience', 'première expérience',
        'confirmé', 'expert'
        ]

        # Chercher les patterns numériques d'abord
        for pattern in experience_patterns:
            match = re.search(pattern, text)
            if match:
                years = match.group(1)
                return f"{years} ans d'expérience"

        # Puis chercher les mots-clés
        for keyword in experience_keywords:
            if keyword in text:
                return keyword

        return None

    def _extract_qualifications(self, soup):
        """Extrait les qualifications requises"""
        text = soup.get_text()

        # Patterns pour les qualifications
        qualification_patterns = [
            r'[Dd]iplôme[:\s]*([^.]+)',
            r'[Ff]ormation[:\s]*([^.]+)',
            r'[Bb]ac\s*\+\s*(\d+)',
            r'[Nn]iveau[:\s]*([^.]+)',
            r'[Qq]ualifications?[:\s]*([^.]+)',
            r'[Cc]ompétences requises[:\s]*([^.]+)'
        ]

        qualifications = []
        for pattern in qualification_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            qualifications.extend(matches)

        # Nettoyer et retourner
        if qualifications:
            return ' | '.join([q.strip() for q in qualifications[:3]])  # Max 3 qualifications

        return None

    def _extract_requirements(self, soup):
        """Extrait les exigences détaillées du poste"""
        text = soup.get_text()

        # Sections contenant les exigences
        requirement_sections = [
            r'[Pp]rofil recherché[:\s]*([^.]+)',
            r'[Ee]xigences[:\s]*([^.]+)',
            r'[Rr]equirements[:\s]*([^.]+)',
            r'[Cc]ritères[:\s]*([^.]+)',
            r'[Cc]onditions[:\s]*([^.]+)'
        ]

        requirements = []
        for pattern in requirement_sections:
            matches = re.findall(pattern, text, re.IGNORECASE)
            requirements.extend(matches)

        if requirements:
            return ' | '.join([req.strip() for req in requirements[:2]])

        return None

    def _extract_contact_info(self, soup):
        """Extrait les informations de contact"""
        text = soup.get_text()

        contact_info = {}

        # Emails
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, text)
        if emails:
            contact_info['emails'] = list(set(emails))  # Supprimer les doublons

        # Téléphones (format africain et international)
        phone_patterns = [
            r'\+228\s*\d{2}\s*\d{2}\s*\d{2}\s*\d{2}',  # Togo
            r'\+225\s*\d{2}\s*\d{2}\s*\d{2}\s*\d{2}',  # Côte d'Ivoire
            r'\+229\s*\d{2}\s*\d{2}\s*\d{2}\s*\d{2}',  # Bénin
            r'\+[\d\s\-\(\)]{8,15}',  # Format international général
            r'\d{2}\s*\d{2}\s*\d{2}\s*\d{2}',  # Format local
        ]

        phones = []
        for pattern in phone_patterns:
            matches = re.findall(pattern, text)
            phones.extend(matches)

        if phones:
            contact_info['phones'] = list(set(phones))

        return contact_info if contact_info else None

    def _extract_application_process(self, soup):
        """Extrait le processus de candidature"""
        text = soup.get_text()

        # Patterns pour le processus de candidature
        application_patterns = [
            r'[Cc]omment postuler[:\s]*([^.]+)',
            r'[Pp]rocédure[:\s]*([^.]+)',
            r'[Dd]ossier de candidature[:\s]*([^.]+)',
            r'[Ee]nvoyer[:\s]*([^.]+)',
            r'[Cc]andidatures?[:\s]*([^.]+)'
        ]

        for pattern in application_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _extract_benefits(self, soup):
        """Extrait les avantages du poste"""
        text = soup.get_text()

        # Patterns pour les avantages
        benefits_patterns = [
            r'[Aa]vantages[:\s]*([^.]+)',
            r'[Bb]énéfices[:\s]*([^.]+)',
            r'[Cc]onditions de travail[:\s]*([^.]+)',
            r'[Oo]ffert[:\s]*([^.]+)'
        ]

        for pattern in benefits_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _extract_category(self, soup):
        """Extrait la catégorie de l'emploi"""
        # Chercher dans les métadonnées
        category_element = soup.select_one('.meta-firstcat, .category, .post-category')
        if category_element:
            return category_element.get_text(strip=True)

        return "Emploi Afrique"  # Catégorie par défaut

    def _extract_meta_info(self, soup):
        """Extrait les métadonnées additionnelles"""
        meta_info = {}

        # Nombre de commentaires
        comments_element = soup.select_one('.meta-comments a')
        if comments_element:
            meta_info['comments_count'] = comments_element.get_text(strip=True)

        # Auteur/Publié par
        author_element = soup.select_one('.meta-author, .author')
        if author_element:
            meta_info['author'] = author_element.get_text(strip=True)

        return meta_info if meta_info else None

    def _extract_images(self, soup):
        """Extrait les URLs des images"""
        images = []

        # Images dans le contenu
        img_elements = soup.select('.entry-content img, .post-content img, img')

        for img in img_elements:
            src = img.get('src')
            if src:
                full_url = urljoin(self.base_url, src)
                images.append({
                    'url': full_url,
                    'alt': img.get('alt', ''),
                    'title': img.get('title', '')
                })

        return images[:5] if images else None  # Max 5 images

    def get_pagination_urls(self, soup):
        """Récupère les URLs de pagination"""
        pagination_urls = []

        # Sélecteur pour la pagination
        pagination_links = soup.select('.pages-numbers .pagi-item[href]')

        for link in pagination_links:
            href = link.get('href')
            if href:
                full_url = urljoin(self.base_url, href)
                pagination_urls.append(full_url)

        return pagination_urls

    def get_next_page_url(self, soup):
        """Récupère l'URL de la page suivante"""
        # Chercher le lien "suivant"
        next_link = soup.select_one('.pages-numbers .pagi-item-next[href]')
        if next_link:
            href = next_link.get('href')
            if href:
                return urljoin(self.base_url, href)

        return None

    def scrape_jobs(self, max_pages=5, max_workers=8):
        self.logger.info(f"Début du scraping emploitogo.info - Mode incrémental: {self.incremental}")

        results = {
            'total_jobs': 0,
            'new_jobs': 0,
            'errors': 0,
            'pages_scraped': 0,
            'start_time': datetime.now().isoformat()
        }

        current_url = self.jobs_url
        pages_scraped = 0

        while current_url and pages_scraped < max_pages:
            try:
                self.logger.info(f"Scraping page {pages_scraped + 1}: {current_url}")
                response = self.get_page(current_url)
                soup = BeautifulSoup(response.content, 'html.parser')

                # Extraction des URLs des offres
                job_urls = self.extract_job_urls_from_listing(soup)
                self.logger.info(f"Trouvé {len(job_urls)} offres sur cette page")

                page_jobs_count = 0

                # Utilisation de ThreadPoolExecutor pour paralléliser les requêtes
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {executor.submit(self.extract_job_details, job_url): job_url for job_url in job_urls}

                    for future in concurrent.futures.as_completed(futures):
                        job_url = futures[future]
                        try:
                            job_data = future.result()
                            if job_data:
                                self.storage.save_job(job_data)
                                results['total_jobs'] += 1
                                page_jobs_count += 1
                                if self.incremental:
                                    results['new_jobs'] += 1
                                self.logger.info(f"✅ Offre sauvegardée: {job_data.get('title', 'Titre non trouvé')}")
                            else:
                                results['errors'] += 1
                                self.logger.error(f"❌ Échec extraction: {job_url}")
                        except Exception as e:
                            results['errors'] += 1
                            self.logger.error(f"❌ Exception sur {job_url}: {str(e)}")

                self.logger.info(f"Page {pages_scraped + 1} terminée: {page_jobs_count} offres extraites")

                # Recherche de la page suivante
                next_url = self.get_next_page_url(soup)
                if next_url and next_url != current_url:
                    current_url = next_url
                    self.logger.info(f"Page suivante trouvée: {next_url}")
                else:
                    self.logger.info("Aucune page suivante trouvée ou fin de pagination")
                    break

                pages_scraped += 1

            except Exception as e:
                self.logger.error(f"Erreur lors du scraping de la page {current_url}: {str(e)}")
                results['errors'] += 1
                break

        results['end_time'] = datetime.now().isoformat()
        results['pages_scraped'] = pages_scraped

        # Sauvegarde finale
        self.storage.finalize()
        stats = self.storage.get_stats()
        results.update(stats)
        return results
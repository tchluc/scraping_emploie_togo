"""
Module de traitement et nettoyage des données
"""

import re
from datetime import datetime
import logging

class JobDataProcessor:
    """Processeur pour nettoyer et normaliser les données d'emploi"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def process_job_data(self, job_data):
        """Traite et nettoie les données d'une offre d'emploi"""
        if not job_data:
            return job_data

        # Nettoyage des champs texte
        text_fields = ['title', 'company', 'location', 'description', 'sector']
        for field in text_fields:
            if job_data.get(field):
                job_data[field] = self.clean_text(job_data[field])

        # Normalisation de la localisation
        if job_data.get('location'):
            job_data['location'] = self.normalize_location(job_data['location'])

        # Normalisation du type de contrat
        if job_data.get('contract_type'):
            job_data['contract_type'] = self.normalize_contract_type(job_data['contract_type'])

        # Traitement du salaire
        if job_data.get('salary'):
            job_data['salary_normalized'] = self.normalize_salary(job_data['salary'])

        # Traitement des dates
        for date_field in ['publication_date', 'deadline']:
            if job_data.get(date_field):
                job_data[f'{date_field}_normalized'] = self.normalize_date(job_data[date_field])

        # Extraction de mots-clés
        if job_data.get('description'):
            job_data['keywords'] = self.extract_keywords(job_data['description'])

        return job_data

    def clean_text(self, text):
        """Nettoie un texte"""
        if not text:
            return text

        # Suppression des espaces multiples
        text = re.sub(r'\s+', ' ', text)

        # Suppression des caractères de contrôle
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)

        return text.strip()

    def normalize_location(self, location):
        """Normalise la localisation"""
        if not location:
            return location

        # Normalisation des noms de villes
        location_mapping = {
            'lome': 'Lomé',
            'lomé': 'Lomé',
            'kara': 'Kara',
            'sokode': 'Sokodé',
            'sokodé': 'Sokodé',
            'kpalime': 'Kpalimé',
            'kpalimé': 'Kpalimé',
            'atakpame': 'Atakpamé',
            'atakpamé': 'Atakpamé'
        }

        location_lower = location.lower()
        return location_mapping.get(location_lower, location)

    def normalize_contract_type(self, contract_type):
        """Normalise le type de contrat"""
        if not contract_type:
            return contract_type

        contract_mapping = {
            'cdi': 'CDI',
            'cdd': 'CDD',
            'stage': 'Stage',
            'freelance': 'Freelance',
            'temps partiel': 'Temps partiel',
            'temps plein': 'Temps plein',
            'consultant': 'Consultant',
            'bénévolat': 'Bénévolat'
        }

        contract_lower = contract_type.lower()
        return contract_mapping.get(contract_lower, contract_type)

    def normalize_salary(self, salary):
        """Normalise le salaire"""
        if not salary:
            return None

        # Extraction du montant numérique
        numbers = re.findall(r'\d+(?:[,\s]\d+)*', salary)
        if not numbers:
            return None

        # Conversion en nombre
        amount_str = numbers[0].replace(',', '').replace(' ', '')
        try:
            amount = int(amount_str)
        except ValueError:
            return None

        # Détection de la devise
        currency = 'FCFA'  # Par défaut
        if '€' in salary or 'euro' in salary.lower():
            currency = 'EUR'
        elif '$' in salary or 'dollar' in salary.lower():
            currency = 'USD'

        # Détection de la période
        period = 'mensuel'  # Par défaut
        if 'annuel' in salary.lower() or 'an' in salary.lower():
            period = 'annuel'
        elif 'journalier' in salary.lower() or 'jour' in salary.lower():
            period = 'journalier'

        return {
            'amount': amount,
            'currency': currency,
            'period': period,
            'raw': salary
        }

    def normalize_date(self, date_str):
        """Normalise une date"""
        if not date_str:
            return None

        # Patterns de dates courantes
        date_patterns = [
            (r'(\d{1,2})/(\d{1,2})/(\d{4})', '%d/%m/%Y'),
            (r'(\d{1,2})-(\d{1,2})-(\d{4})', '%d-%m-%Y'),
            (r'(\d{4})-(\d{1,2})-(\d{1,2})', '%Y-%m-%d'),
        ]

        for pattern, format_str in date_patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    if format_str == '%d/%m/%Y':
                        day, month, year = match.groups()
                    elif format_str == '%d-%m-%Y':
                        day, month, year = match.groups()
                    elif format_str == '%Y-%m-%d':
                        year, month, day = match.groups()

                    date_obj = datetime(int(year), int(month), int(day))
                    return date_obj.isoformat().split('T')[0]
                except ValueError:
                    continue

        return None

    def extract_keywords(self, description):
        """Extrait les mots-clés d'une description"""
        if not description:
            return []

        # Mots-clés techniques courrants
        tech_keywords = [
            'python', 'java', 'javascript', 'php', 'sql', 'mysql', 'postgresql',
            'html', 'css', 'react', 'angular', 'vue', 'node.js', 'django',
            'flask', 'spring', 'laravel', 'wordpress', 'git', 'docker',
            'kubernetes', 'aws', 'azure', 'gcp', 'linux', 'windows',
            'photoshop', 'illustrator', 'figma', 'sketch'
        ]

        # Compétences générales
        soft_skills = [
            'communication', 'leadership', 'teamwork', 'management',
            'analytique', 'créatif', 'autonome', 'rigoureux'
        ]

        description_lower = description.lower()
        found_keywords = []

        for keyword in tech_keywords + soft_skills:
            if keyword in description_lower:
                found_keywords.append(keyword)

        return found_keywords
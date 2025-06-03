import re
import unicodedata

def fix_encoding(text):
    """Corrige les erreurs d'encodage courantes."""
    if not text:
        return text
    fixes = {
        'Ã©': 'é', 'Ã¨': 'è', 'Ãª': 'ê', 'Ã ': 'à', 'Ã¢': 'â',
        'Ã»': 'û', 'Ã¼': 'ü', 'Ã§': 'ç', 'Ã«': 'ë', 'Ã¯': 'ï', 'Ã´': 'ô',
        'â€™': "'", 'â€“': '-', 'â€œ': '"', 'â€': '"', 'â€˜': "'", 'â€¢': '-', 'â€': '"',
        'â‚¬': '€', 'â€¦': '...', 'Â': '', 'Ã': 'à', 'â': 'à'
    }
    for wrong, right in fixes.items():
        text = text.replace(wrong, right)
    text = unicodedata.normalize('NFKC', text)
    return text

def extract_job_details(text):
    text = fix_encoding(text)
    m = re.search(r'(le|la|l’|l\'|société|centre|groupe|compagnie)\s+([A-Z][A-Za-z0-9&\-\s]+)', text, re.I)
    entreprise = m.group(2).strip() if m else None

    villes = ['Lomé', 'Kara', 'Sokodé', 'Kpalimé', 'Atakpamé','Dapaong', 'Abidjan', 'Cotonou', 'Ouagadougou', 'Bamako']
    ville = None
    for v in villes:
        if re.search(r'\b' + re.escape(v) + r'\b', text, re.I):
            ville = v
            break

    m = re.search(r'\brecrutement (?:d[eu]|pour)\s+(stagiaires?|postulant|agent|collaborateur|technicien|employé|ingénieur|commercial|assistant|manager|consultant|superviseur|chef|responsable|directeur|secrétaire|chargé[ée]?)', text, re.I)
    type_de_poste = m.group(1).capitalize() if m else None
    if not type_de_poste and re.search(r'stage|stagiaire', text, re.I):
        type_de_poste = 'Stagiaire'

    m = re.search(r'(cdi|cdd|stage|bénévolat|intérim|freelance|contrat à durée déterminée|contrat à durée indéterminée)', text, re.I)
    type_de_contrat = m.group(1).upper() if m else ('STAGE' if 'stage' in text.lower() else None)

    m = re.search(r'(?:d[ée]marrage|d[ée]but|prise de poste|à partir du)\s*[:\-]?\s*(\d{1,2}\s*[a-zéû]+\s*\d{4})', text, re.I)
    date_de_demarrage = m.group(1) if m else None

    return {
        "entreprise": entreprise,
        "ville": ville,
        "type_de_poste": type_de_poste,
        "type_de_contrat": type_de_contrat,
        "date_de_demarrage": date_de_demarrage
    }

def extract_required_skills(text):
    text = fix_encoding(text)
    diplome = re.findall(r'(bac ?\+ ?[1-9]|licence|master|doctorat|bts|dut|dipl[ôo]me|certificat)', text, re.I)
    qualities = re.findall(r'(rigoureux|autonome|motivé|dynamique|créatif|organisé|ponctuel|esprit d’équipe|polyvalent|proactif|communication)', text, re.I)
    found = list(dict.fromkeys([d.title() for d in diplome + qualities]))
    return found if found else None

def extract_internship_tasks(text):
    text = fix_encoding(text)
    # 1. Chercher la section missions/tâches/responsabilités :
    section = None
    section_titles = [
        r'(missions principales|missions|tâches principales|tâches|responsabilités)([:\s]+)',
    ]
    for pattern in section_titles:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            start = m.end()
            # Coupe à la fin du paragraphe ou au prochain titre courant
            end = len(text)
            next_titles = [
                r'profil', r'expérience', r'aptitude', r'qualité', r'compétence', r'date limite', r'document(s)? à fournir', r'pour postuler', r'candidature'
            ]
            for nt in next_titles:
                n = re.search(r'\n\s*' + nt, text[start:], re.IGNORECASE)
                if n:
                    end = start + n.start()
                    break
            section = text[start:end].strip()
            break

    # 2. Extraire les lignes à puce ou les phrases commençant par un verbe :
    tasks = []
    if section:
        # Essaye d'abord les puces
        bullets = re.findall(r'[-*•]\s*(.+?)(?:\n|$)', section)
        if bullets:
            tasks = [b.strip() for b in bullets if len(b.strip()) > 5]
        else:
            # Sinon, coupe en phrases et prend les phrases d’action (commençant par un verbe à l’infinitif ou à la 3e pers)
            phrases = re.split(r'[\n\.]', section)
            for p in phrases:
                p = p.strip()
                if len(p) < 10:
                    continue
                if re.match(r'^(Participer|Réaliser|Assurer|Animer|Contribuer|Préparer|Gérer|Encadrer|Aider|Soutenir|Accompagner|Élaborer|Analyser|Soutenir|Développer|Effectuer|Organiser|Coordonner|Superviser|Appuyer|Créer|Mettre en place|Participate|Support|Lead|Develop|Manage|Assist|Prepare|Write|Design|Test|Deliver)', p, re.IGNORECASE):
                    tasks.append(p)
                elif re.match(r'^(?:Être chargé de|Il s\'agira de|Vous serez amené à|La mission consiste à|La mission principale est de|Sous la direction de)', p, re.IGNORECASE):
                    tasks.append(p)
    else:
        # Fallback : puces sur tout le texte
        bullets = re.findall(r'[-*•]\s*(.+?)(?:\n|$)', text)
        tasks = [b.strip() for b in bullets if len(b.strip()) > 5]

    return tasks if tasks else None

def extract_application_deadline(text):
    text = fix_encoding(text)
    m = re.search(r'(?:date limite|avant le|jusqu[’\']?au|deadline|Dossiers de Candidatures|Date limite de dépôt des candidatures|Date limite de candidature|)[:\s]*(\d{1,2}[ /\-][a-zéû0-9]+[ /\-]\d{4})', text, re.I)
    return m.group(1) if m else None

def extract_application_documents(text):
    text = fix_encoding(text)
    docs = re.findall(r'(curriculum vitae|cv|lettre de motivation|copie diplôme|photo|pièce d’identité|relevé de notes|attestation)', text, re.I)
    docs = list(set([d.title() for d in docs]))
    return docs if docs else None

def extract_company_from_title(title):
    if not title:
        return None
    # Cherche "Le/La/L'/L’/Société/Entreprise/Group/Compagnie" suivi du nom, puis "recrute" ou "recherche"
    m = re.search(r"(?i)(le|la|l’|l'|société|entreprise|groupe|compagnie)?\s*([A-Z0-9][A-Za-z0-9&\-\séÉèêàâçôûüï]+?)\s+(recrute|recherche|embauche|offre|propose)", title)
    if m:
        # Le groupe 2 contient le nom
        return m.group(2).strip()
    # Cas fallback : avant "recrute" ou "recherche", prendre tout ce qui précède
    m = re.search(r"^(.*?)(recrute|recherche|embauche|offre|propose)", title, re.IGNORECASE)
    if m:
        company = m.group(1).strip(' -')
        # Nettoie les articles initiaux
        company = re.sub(r"^(Le|La|L’|L'|Société|Entreprise|Groupe|Compagnie)\s+", "", company, flags=re.I)
        return company.strip() if company else None
    return None

def extract_date_from_title(title):
    if not title:
        return None
    # Cherche une date au format JJ/MM/AAAA ou JJ-MM-AAAA
    m = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', title)
    if m:
        return m.group(1)
    # Cas fallback : date au format "10 juin 2025" ou "05 juin 2025"
    m = re.search(r'(\d{1,2}\s+[a-zéû]+\s+\d{4})', title, re.IGNORECASE)
    if m:
        return m.group(1)
    return None

def extract_all_structured(content, title=None):
    struct = {
        "job_details": extract_job_details(content),
        "required_skills": extract_required_skills(content),
        "internship_tasks": extract_internship_tasks(content),
        "application_deadline": extract_application_deadline(content),
        "application_documents": extract_application_documents(content)
    }
    if title:
        struct["job_details"]["entreprise"] = extract_company_from_title(title)
        struct["job_details"]["publication_date"] = extract_date_from_title(title)
    return struct
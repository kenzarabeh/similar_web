"""
Script de gestion des sites web à analyser
Compatible avec l'architecture 3 tables SimilarWeb
Permet d'ajouter, supprimer et lister les sites web
"""
import json
import os
import sys
from typing import List, Dict
import argparse
from datetime import datetime

# Ajouter le chemin parent pour importer les modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import TARGET_DOMAINS

# Fichier de configuration des sites web
WEBSITES_CONFIG_FILE = 'config/websites.json'


def load_websites() -> List[str]:
    """
    Charge la liste des sites web depuis le fichier de configuration
    Compatible avec l'architecture 3 tables
    
    Returns:
        Liste des domaines
    """
    if os.path.exists(WEBSITES_CONFIG_FILE):
        try:
            with open(WEBSITES_CONFIG_FILE, 'r') as f:
                data = json.load(f)
                websites = data.get('domains', TARGET_DOMAINS)
                print(f"[INFO] {len(websites)} sites web chargés depuis la configuration")
                return websites
        except Exception as e:
            print(f"[ERREUR] Impossible de lire {WEBSITES_CONFIG_FILE}: {e}")
            print(f"[INFO] Utilisation de la liste par défaut: {len(TARGET_DOMAINS)} sites")
            return TARGET_DOMAINS
    else:
        # Créer le fichier avec les domaines par défaut
        print(f"[INFO] Fichier {WEBSITES_CONFIG_FILE} non trouvé, création avec domaines par défaut")
        save_websites(TARGET_DOMAINS)
        return TARGET_DOMAINS


def save_websites(domains: List[str]):
    """
    Sauvegarde la liste des sites web
    Compatible avec l'architecture 3 tables
    
    Args:
        domains: Liste des domaines
    """
    os.makedirs(os.path.dirname(WEBSITES_CONFIG_FILE), exist_ok=True)
    
    # Nettoyer et valider les domaines
    cleaned_domains = []
    for domain in domains:
        domain = domain.strip().lower()
        if validate_domain(domain):
            cleaned_domains.append(domain)
        else:
            print(f"[WARNING] Domaine invalide ignoré: {domain}")
    
    data = {
        'domains': sorted(list(set(cleaned_domains))),  # Éliminer les doublons et trier
        'last_updated': datetime.now().isoformat(),
        'architecture': '3_tables',
        'note': 'Sites web pour extraction websites_daily (avec unique_visitors)',
        'count': len(cleaned_domains)
    }
    
    with open(WEBSITES_CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"[SUCCESS] {len(data['domains'])} sites web sauvegardés dans {WEBSITES_CONFIG_FILE}")
    print(f"[INFO] Architecture: 3 tables (websites_daily)")


def add_websites(new_domains: List[str]):
    """
    Ajoute de nouveaux sites web à la liste
    
    Args:
        new_domains: Liste des nouveaux domaines
    """
    current_domains = load_websites()
    before_count = len(current_domains)
    
    # Valider les nouveaux domaines
    valid_new_domains = []
    for domain in new_domains:
        domain = domain.strip().lower()
        if validate_domain(domain):
            valid_new_domains.append(domain)
        else:
            print(f"[WARNING] Domaine invalide ignoré: {domain}")
    
    # Ajouter les nouveaux domaines
    updated_domains = current_domains + valid_new_domains
    save_websites(updated_domains)
    
    after_count = len(load_websites())
    added_count = after_count - before_count
    
    print(f"[SUCCESS] {added_count} nouveaux sites ajoutés (total: {after_count})")
    
    # Afficher les domaines ajoutés
    if added_count > 0:
        print("\nSites ajoutés:")
        actually_added = sorted(set(valid_new_domains) - set(current_domains))
        for domain in actually_added:
            print(f"  ✓ {domain}")
        
        print(f"\n[INFO] Ces sites seront inclus dans websites_daily (avec unique_visitors)")


def remove_websites(domains_to_remove: List[str]):
    """
    Supprime des sites web de la liste
    
    Args:
        domains_to_remove: Liste des domaines à supprimer
    """
    current_domains = load_websites()
    before_count = len(current_domains)
    
    # Normaliser les domaines à supprimer
    domains_to_remove = [d.strip().lower() for d in domains_to_remove]
    
    # Supprimer les domaines
    updated_domains = [d for d in current_domains if d not in domains_to_remove]
    save_websites(updated_domains)
    
    removed_count = before_count - len(updated_domains)
    
    print(f"[SUCCESS] {removed_count} sites supprimés (reste: {len(updated_domains)})")
    
    if removed_count > 0:
        print("\nSites supprimés:")
        actually_removed = sorted(set(current_domains) - set(updated_domains))
        for domain in actually_removed:
            print(f"  ✗ {domain}")


def list_websites():
    """
    Affiche la liste des sites web actuels avec informations sur l'architecture 3 tables
    """
    domains = load_websites()
    
    print(f"\n{'='*60}")
    print(f"SITES WEB CONFIGURÉS - ARCHITECTURE 3 TABLES")
    print(f"{'='*60}")
    print(f"Table destination: websites_daily")
    print(f"Granularité: daily")
    print(f"Métriques incluses: visits, bounce_rate, pages_per_visit,")
    print(f"                   avg_visit_duration, page_views, unique_visitors,")
    print(f"                   desktop_share, mobile_share")
    print(f"{'='*60}")
    
    for i, domain in enumerate(sorted(domains), 1):
        print(f"{i:3d}. {domain}")
    
    print(f"{'='*60}")
    print(f"Total: {len(domains)} sites web")
    
    # Vérifier la configuration
    try:
        with open(WEBSITES_CONFIG_FILE, 'r') as f:
            data = json.load(f)
            last_updated = data.get('last_updated', 'Inconnu')
            architecture = data.get('architecture', 'legacy')
            
        print(f"Dernière mise à jour: {last_updated[:19] if last_updated != 'Inconnu' else last_updated}")
        print(f"Architecture: {architecture}")
        
        if architecture != '3_tables':
            print(f"[WARNING] Configuration non optimisée pour architecture 3 tables")
            
    except Exception as e:
        print(f"[WARNING] Impossible de lire les métadonnées: {e}")


def validate_domain(domain: str) -> bool:
    """
    Valide le format d'un nom de domaine
    
    Args:
        domain: Nom de domaine à valider
        
    Returns:
        True si valide
    """
    # Validation basique
    if not domain or '.' not in domain:
        return False
    
    # Ne doit pas contenir de protocole
    if domain.startswith(('http://', 'https://')):
        return False
    
    # Ne doit pas contenir de chemin
    if '/' in domain:
        return False
        
    # Ne doit pas contenir d'espaces
    if ' ' in domain:
        return False
    
    # Doit avoir au moins un point
    parts = domain.split('.')
    if len(parts) < 2:
        return False
    
    # Chaque partie ne doit pas être vide
    if any(not part for part in parts):
        return False
    
    return True


# Liste suggérée de sites e-commerce français - ÉTENDUE pour 3 tables
SUGGESTED_WEBSITES = [
    # E-commerce généralistes principaux
    'amazon.fr',
    'cdiscount.com',
    'fnac.com',
    'darty.com',
    'boulanger.com',
    'rueducommerce.fr',
    'ldlc.com',
    'materiel.net',
    
    # Grande distribution
    'carrefour.fr',
    'auchan.fr',
    'leclerc.com',
    'intermarche.com',
    'monoprix.fr',
    'franprix.fr',
    
    # Mode et beauté
    'zalando.fr',
    'asos.fr',
    'shein.com',
    'kiabi.com',
    'celio.com',
    'camaieu.fr',
    'sephora.fr',
    'marionnaud.fr',
    'parfumsmoinscher.com',
    
    # Bricolage et maison
    'leroymerlin.fr',
    'castorama.fr',
    'bricodepot.fr',
    'but.fr',
    'ikea.com',
    'conforama.fr',
    'maisons-du-monde.com',
    'alinea.fr',
    'laredoute.fr',
    
    # Auto et moto
    'norauto.fr',
    'feuvert.fr',
    'midas.fr',
    'speedy.fr',
    'oscaro.com',
    'yakarouler.com',
    
    # Sport et loisirs
    'decathlon.fr',
    'intersport.fr',
    'go-sport.com',
    'alltricks.fr',
    'snowleader.com',
    
    # High-tech et électronique
    'rue-montgallet.com',
    'grosbill.com',
    'topachat.com',
    'son-video.com',
    
    # Livres, culture, jeux
    'cultura.com',
    'micromania.fr',
    'nature-et-decouvertes.com',
    'decitre.fr',
    'chapitre.com',
    
    # Autres secteurs
    'vertbaudet.fr',
    'oxybul.com',
    'manomano.fr',
    'cdav.fr',
    'ubaldi.com'
]


def suggest_websites():
    """
    Suggère des sites web populaires à ajouter avec info architecture 3 tables
    """
    current_domains = load_websites()
    suggestions = [d for d in SUGGESTED_WEBSITES if d not in current_domains]
    
    if not suggestions:
        print("[INFO] Tous les sites suggérés sont déjà dans votre liste!")
        return
    
    print(f"\n{'='*60}")
    print(f"SITES SUGGÉRÉS - ARCHITECTURE 3 TABLES")
    print(f"{'='*60}")
    print(f"Sites non présents dans votre liste ({len(suggestions)}):")
    print(f"Seront ajoutés à la table: websites_daily")
    print(f"Métriques disponibles: unique_visitors inclus")
    print(f"{'='*60}")
    
    # Grouper par catégories pour un affichage plus clair
    categories = {
        'E-commerce généralistes': ['amazon.fr', 'cdiscount.com', 'fnac.com', 'darty.com', 'boulanger.com'],
        'Grande distribution': ['carrefour.fr', 'auchan.fr', 'leclerc.com', 'intermarche.com'],
        'Mode et beauté': ['zalando.fr', 'asos.fr', 'shein.com', 'kiabi.com', 'sephora.fr'],
        'Bricolage et maison': ['leroymerlin.fr', 'castorama.fr', 'ikea.com', 'maisons-du-monde.com'],
        'Auto et sport': ['norauto.fr', 'decathlon.fr', 'intersport.fr', 'oscaro.com'],
        'Autres': []
    }
    
    # Classer les suggestions
    categorized_suggestions = {cat: [] for cat in categories}
    for domain in suggestions:
        categorized = False
        for cat, examples in categories.items():
            if cat != 'Autres' and domain in examples:
                categorized_suggestions[cat].append(domain)
                categorized = True
                break
        if not categorized:
            categorized_suggestions['Autres'].append(domain)
    
    # Affichage par catégories
    for category, domains in categorized_suggestions.items():
        if domains:
            print(f"\n{category}:")
            for domain in sorted(domains):
                print(f"  • {domain}")
    
    print(f"\n{'='*60}")
    print("COMMANDES DISPONIBLES:")
    print("• Ajouter tous les sites suggérés:")
    print("  python scripts/manage_websites.py add --all-suggestions")
    print("• Ajouter des sites spécifiques:")
    print("  python scripts/manage_websites.py add site1.com site2.com")
    print(f"{'='*60}")


def get_statistics():
    """
    Affiche des statistiques sur la configuration actuelle
    """
    try:
        domains = load_websites()
        
        # Analyser les TLD
        tld_stats = {}
        for domain in domains:
            tld = domain.split('.')[-1]
            tld_stats[tld] = tld_stats.get(tld, 0) + 1
        
        print(f"\n{'='*40}")
        print(f"STATISTIQUES DES SITES WEB")
        print(f"{'='*40}")
        print(f"Total des sites: {len(domains)}")
        print(f"\nRépartition par TLD:")
        for tld, count in sorted(tld_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"  .{tld}: {count} sites")
        
        # Estimation des appels API pour websites_daily (6 appels par site par période)
        daily_calls_per_period = len(domains) * 6
        print(f"\nEstimation appels API (par période daily):")
        print(f"  Websites_daily: {daily_calls_per_period} appels")
        print(f"  (6 métriques × {len(domains)} sites)")
        
        print(f"{'='*40}")
        
    except Exception as e:
        print(f"[ERREUR] Impossible de calculer les statistiques: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Gestion sites web - Architecture 3 tables')
    subparsers = parser.add_subparsers(dest='command', help='Commandes disponibles')
    
    # Commande list
    parser_list = subparsers.add_parser('list', help='Lister les sites web')
    
    # Commande add
    parser_add = subparsers.add_parser('add', help='Ajouter des sites web')
    parser_add.add_argument('domains', nargs='*', help='Domaines à ajouter')
    parser_add.add_argument('--all-suggestions', action='store_true', 
                           help='Ajouter tous les sites suggérés')
    
    # Commande remove
    parser_remove = subparsers.add_parser('remove', help='Supprimer des sites web')
    parser_remove.add_argument('domains', nargs='+', help='Domaines à supprimer')
    
    # Commande suggest
    parser_suggest = subparsers.add_parser('suggest', help='Voir les sites suggérés')
    
    # Commande stats
    parser_stats = subparsers.add_parser('stats', help='Voir les statistiques')
    
    args = parser.parse_args()
    
    if args.command == 'list':
        list_websites()
    
    elif args.command == 'add':
        if args.all_suggestions:
            current = load_websites()
            to_add = [d for d in SUGGESTED_WEBSITES if d not in current]
            if to_add:
                print(f"[INFO] Ajout de {len(to_add)} sites suggérés...")
                add_websites(to_add)
            else:
                print("[INFO] Tous les sites suggérés sont déjà dans la liste!")
        elif args.domains:
            add_websites(args.domains)
        else:
            print("[ERROR] Veuillez spécifier des domaines ou utiliser --all-suggestions")
    
    elif args.command == 'remove':
        remove_websites(args.domains)
    
    elif args.command == 'suggest':
        suggest_websites()
        
    elif args.command == 'stats':
        get_statistics()
    
    else:
        print("GESTION DES SITES WEB - ARCHITECTURE 3 TABLES")
        print("=" * 50)
        print("Sites web utilisés pour la table: websites_daily")
        print("Métriques incluses: unique_visitors disponible")
        print("=" * 50)
        parser.print_help()
        print("\nExemples:")
        print("  python scripts/manage_websites.py list")
        print("  python scripts/manage_websites.py suggest")
        print("  python scripts/manage_websites.py add amazon.fr ebay.fr")
        print("  python scripts/manage_websites.py add --all-suggestions")
"""
Script de gestion des sites web à analyser
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
    
    Returns:
        Liste des domaines
    """
    if os.path.exists(WEBSITES_CONFIG_FILE):
        with open(WEBSITES_CONFIG_FILE, 'r') as f:
            data = json.load(f)
            return data.get('domains', TARGET_DOMAINS)
    else:
        # Créer le fichier avec les domaines par défaut
        save_websites(TARGET_DOMAINS)
        return TARGET_DOMAINS


def save_websites(domains: List[str]):
    """
    Sauvegarde la liste des sites web
    
    Args:
        domains: Liste des domaines
    """
    os.makedirs(os.path.dirname(WEBSITES_CONFIG_FILE), exist_ok=True)
    
    data = {
        'domains': sorted(list(set(domains))),  # Éliminer les doublons et trier
        'last_updated': datetime.now().isoformat()
    }
    
    with open(WEBSITES_CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ {len(data['domains'])} sites web sauvegardés dans {WEBSITES_CONFIG_FILE}")


def add_websites(new_domains: List[str]):
    """
    Ajoute de nouveaux sites web à la liste
    
    Args:
        new_domains: Liste des nouveaux domaines
    """
    current_domains = load_websites()
    before_count = len(current_domains)
    
    # Ajouter les nouveaux domaines
    updated_domains = current_domains + new_domains
    save_websites(updated_domains)
    
    after_count = len(load_websites())
    added_count = after_count - before_count
    
    print(f"✅ {added_count} nouveaux sites ajoutés (total: {after_count})")
    
    # Afficher les domaines ajoutés
    if added_count > 0:
        print("\nSites ajoutés:")
        for domain in sorted(set(new_domains) - set(current_domains)):
            print(f"  - {domain}")


def remove_websites(domains_to_remove: List[str]):
    """
    Supprime des sites web de la liste
    
    Args:
        domains_to_remove: Liste des domaines à supprimer
    """
    current_domains = load_websites()
    before_count = len(current_domains)
    
    # Supprimer les domaines
    updated_domains = [d for d in current_domains if d not in domains_to_remove]
    save_websites(updated_domains)
    
    removed_count = before_count - len(updated_domains)
    
    print(f"✅ {removed_count} sites supprimés (reste: {len(updated_domains)})")


def list_websites():
    """
    Affiche la liste des sites web actuels
    """
    domains = load_websites()
    
    print(f"\n📋 Sites web configurés ({len(domains)}):")
    print("-" * 40)
    
    for i, domain in enumerate(sorted(domains), 1):
        print(f"{i:2d}. {domain}")
    
    print("-" * 40)
    print(f"Total: {len(domains)} sites")


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
    
    return True


# Liste suggérée de sites e-commerce français
SUGGESTED_WEBSITES = [
    # E-commerce généralistes
    'cdiscount.com',
    'fnac.com',
    'darty.com',
    'boulanger.com',
    'rueducommerce.fr',
    'carrefour.fr',
    'auchan.fr',
    'leclerc.com',
    'intermarche.com',
    
    # Mode et beauté
    'zalando.fr',
    'asos.fr',
    'shein.com',
    'kiabi.com',
    'sephora.fr',
    'marionnaud.fr',
    
    # Bricolage et maison
    'leroymerlin.fr',
    'castorama.fr',
    'bricodepot.fr',
    'but.fr',
    'ikea.com',
    'conforama.fr',
    'maisons-du-monde.com',
    
    # Auto et moto
    'norauto.fr',
    'feuvert.fr',
    'midas.fr',
    'speedy.fr',
    'oscaro.com',
    
    # Sport
    'decathlon.fr',
    'intersport.fr',
    'go-sport.com',
    
    # Autres
    'cultura.com',
    'micromania.fr',
    'nature-et-decouvertes.com'
]


def suggest_websites():
    """
    Suggère des sites web populaires à ajouter
    """
    current_domains = load_websites()
    suggestions = [d for d in SUGGESTED_WEBSITES if d not in current_domains]
    
    if not suggestions:
        print("✅ Tous les sites suggérés sont déjà dans votre liste!")
        return
    
    print(f"\n💡 Sites suggérés non présents dans votre liste ({len(suggestions)}):")
    print("-" * 50)
    
    for i, domain in enumerate(suggestions, 1):
        print(f"{i:2d}. {domain}")
    
    print("-" * 50)
    print("\nPour ajouter tous les sites suggérés:")
    print("python scripts/manage_websites.py add --all-suggestions")
    print("\nPour ajouter des sites spécifiques:")
    print("python scripts/manage_websites.py add site1.com site2.com")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Gestion des sites web à analyser')
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
    
    args = parser.parse_args()
    
    if args.command == 'list':
        list_websites()
    
    elif args.command == 'add':
        if args.all_suggestions:
            current = load_websites()
            to_add = [d for d in SUGGESTED_WEBSITES if d not in current]
            if to_add:
                add_websites(to_add)
            else:
                print("✅ Tous les sites suggérés sont déjà dans la liste!")
        elif args.domains:
            # Valider les domaines
            valid_domains = []
            for domain in args.domains:
                if validate_domain(domain):
                    valid_domains.append(domain)
                else:
                    print(f"⚠️  Domaine invalide ignoré: {domain}")
            
            if valid_domains:
                add_websites(valid_domains)
        else:
            print("❌ Veuillez spécifier des domaines ou utiliser --all-suggestions")
    
    elif args.command == 'remove':
        remove_websites(args.domains)
    
    elif args.command == 'suggest':
        suggest_websites()
    
    else:
        parser.print_help() 
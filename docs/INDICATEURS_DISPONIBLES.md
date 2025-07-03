# 📊 INDICATEURS DISPONIBLES - SimilarWeb Intelligence Platform

## 📈 INDICATEURS SEGMENTS (88 segments personnels)

### ✅ Indicateurs stockés dans BigQuery

| Indicateur | Description | Taux de remplissage | Valeurs |
|------------|-------------|-------------------|----------|
| **segment_id** | Identifiant unique du segment | 100% | UUID |
| **segment_name** | Nom du segment | 100% | Ex: "Carrefour - Électroménager" |
| **date** | Date des données | 100% | Format: YYYY-MM-DD |
| **visits** | Nombre de visites | 100% | Min: 954, Max: 67M, Moy: 3.4M |
| **share** | Part de marché | 100% | Min: 0.00007, Max: 1.0 |
| **extraction_date** | Date d'extraction | 100% | Timestamp de l'extraction |

### ⚠️ Indicateurs disponibles dans l'API mais NON stockés

| Indicateur | Description | Disponibilité API |
|------------|-------------|-------------------|
| **confidence** | Niveau de confiance des données | ✅ Disponible |
| **bounce_rate** | Taux de rebond | ✅ Disponible |
| **pages_per_visit** | Pages par visite | ✅ Disponible |
| **visit_duration** | Durée de visite (secondes) | ✅ Disponible |
| **page_views** | Nombre de pages vues | ✅ Disponible |
| **unique_visitors** | Visiteurs uniques | ✅ Disponible |

### 📊 Couverture temporelle des segments
- **4,899 lignes** au total dans BigQuery
- **Période couverte** : Janvier 2024 → Mai 2025
- **Mois complets** : Jan-Juin 2024, Jan-Mai 2025 (88 segments/mois)
- **Moyenne** : 55 points de données par segment

---

## 🌐 INDICATEURS WEBSITES (21 domaines)

### ✅ Indicateurs stockés dans BigQuery

| Indicateur | Description | Taux de remplissage | Valeurs |
|------------|-------------|-------------------|----------|
| **domain** | Nom de domaine | 100% | Ex: "amazon.fr" |
| **date** | Date des données | 100% | Format: YYYY-MM-DD |
| **visits** | Nombre de visites | 100% | Variable selon domaine |
| **pages_per_visit** | Pages par visite | 100% | Min: 1.03, Max: 11.8, Moy: 5.6 |
| **avg_visit_duration** | Durée moyenne (secondes) | 100% | Min: 0.002s, Max: 386s |
| **bounce_rate** | Taux de rebond | 100% | Min: 21%, Max: 94% |
| **extraction_date** | Date d'extraction | 100% | Timestamp |

### ❌ Indicateurs NON remplis (colonnes vides)

| Indicateur | Description | Statut |
|------------|-------------|---------|
| **page_views** | Nombre total de pages vues | 0% - Colonne existe mais vide |
| **desktop_share** | Part du trafic desktop | 0% - Colonne existe mais vide |
| **mobile_share** | Part du trafic mobile | 0% - Colonne existe mais vide |

### ⚠️ Indicateurs disponibles dans l'API mais partiellement exploités

| Indicateur | Description | Statut |
|------------|-------------|---------|
| **desktop_mobile_split** | Répartition desktop/mobile | ✅ Dans l'API, ❌ Non extrait dans BigQuery |

### 📊 Couverture temporelle des websites
- **359 lignes** au total dans BigQuery
- **Période couverte** : Données éparses (9 mois sur 17)
- **Mois avec données** : Jan, Fév, Mai, Juin, Sept, Oct 2024 + Jan, Fév, Mai 2025
- **Moyenne** : 17 points de données par domaine

---

## 🏆 TOP SEGMENTS & DOMAINES

### Top 5 Segments (par nombre de données)
1. **Feuvert - Auto_Pièces_détachées** : 114 points
2. **Carrefour - Électroménager** : 114 points
3. **E.leclerc - Bricolage** : 111 points
4. **Auchan - High-Tech** : 111 points
5. **Fnac - Jeux vidéo** : 111 points

### Top 5 Domaines (par trafic total)
1. **amazon.fr** : 3.07 milliards de visites
2. **leroymerlin.fr** : 489M visites
3. **fnac.com** : 367M visites
4. **decathlon.fr** : 331M visites
5. **shein.com** : 263M visites

---

## 💡 RECOMMANDATIONS

### Pour les Segments
- ✅ **Données principales bien remplies** (visits, share)
- 🔄 **Enrichissement possible** : Ajouter bounce_rate, pages_per_visit, unique_visitors
- 📈 **Excellente couverture temporelle** : 10 mois complets

### Pour les Websites
- ✅ **Métriques comportementales complètes** (pages/visite, durée, bounce)
- ❌ **Données manquantes** : page_views, desktop/mobile split
- ⚠️ **Couverture temporelle incomplète** : Manque Mars, Avril, Juillet-Décembre

### Actions suggérées
1. **Enrichir la table segments** avec les 6 indicateurs manquants
2. **Implémenter l'extraction** desktop/mobile split pour websites
3. **Compléter les mois manquants** pour websites (Mars, Avril prioritaires)
4. **Créer des vues agrégées** pour faciliter l'analyse 
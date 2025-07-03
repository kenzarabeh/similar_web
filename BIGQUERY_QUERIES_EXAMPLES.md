# 🔍 Exemples de Requêtes BigQuery pour Analyse SimilarWeb

## 📊 Requêtes de Base

### 1. Vue d'ensemble des segments
```sql
-- Top 10 segments par trafic du mois dernier
SELECT 
  segment_name,
  SUM(visits) as total_visits,
  AVG(share) as avg_market_share,
  AVG(bounce_rate) as avg_bounce_rate
FROM `votre-projet.similarweb_data.segments_data`
WHERE DATE(date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH)
GROUP BY segment_name
ORDER BY total_visits DESC
LIMIT 10;
```

### 2. Évolution temporelle d'un segment
```sql
-- Évolution mensuelle d'un segment spécifique
SELECT 
  segment_name,
  date,
  visits,
  share,
  bounce_rate,
  pages_per_visit,
  visit_duration
FROM `votre-projet.similarweb_data.segments_data`
WHERE segment_name LIKE '%Leclerc%'
  AND DATE(date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
ORDER BY date DESC;
```

## 📈 Analyses de Croissance

### 3. Croissance YoY par segment
```sql
-- Comparaison année sur année
WITH current_year AS (
  SELECT 
    segment_name,
    SUM(visits) as visits_current,
    AVG(share) as share_current
  FROM `votre-projet.similarweb_data.segments_data`
  WHERE EXTRACT(YEAR FROM date) = 2025
  GROUP BY segment_name
),
previous_year AS (
  SELECT 
    segment_name,
    SUM(visits) as visits_previous,
    AVG(share) as share_previous
  FROM `votre-projet.similarweb_data.segments_data`
  WHERE EXTRACT(YEAR FROM date) = 2024
  GROUP BY segment_name
)
SELECT 
  c.segment_name,
  c.visits_current,
  p.visits_previous,
  ROUND((c.visits_current - p.visits_previous) / p.visits_previous * 100, 2) as growth_rate,
  c.share_current,
  p.share_previous,
  ROUND((c.share_current - p.share_previous) * 100, 2) as share_point_change
FROM current_year c
JOIN previous_year p ON c.segment_name = p.segment_name
ORDER BY growth_rate DESC;
```

### 4. Tendances mensuelles par catégorie
```sql
-- Grouper les segments par catégorie
SELECT 
  CASE 
    WHEN segment_name LIKE '%Parapharmacie%' THEN 'Parapharmacie'
    WHEN segment_name LIKE '%Fnac%' OR segment_name LIKE '%Darty%' THEN 'High-Tech'
    WHEN segment_name LIKE '%Ikea%' OR segment_name LIKE '%Conforama%' THEN 'Mobilier'
    WHEN segment_name LIKE '%Carrefour%' OR segment_name LIKE '%Leclerc%' THEN 'Grande Distribution'
    ELSE 'Autres'
  END as category,
  FORMAT_DATE('%Y-%m', date) as month,
  SUM(visits) as total_visits,
  AVG(bounce_rate) as avg_bounce_rate
FROM `votre-projet.similarweb_data.segments_data`
WHERE DATE(date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)
GROUP BY category, month
ORDER BY month DESC, category;
```

## 🏆 Analyses Compétitives

### 5. Parts de marché par secteur
```sql
-- Parts de marché dans le secteur parapharmacie
WITH sector_data AS (
  SELECT 
    segment_name,
    date,
    visits,
    SUM(visits) OVER (PARTITION BY date) as total_sector_visits
  FROM `votre-projet.similarweb_data.segments_data`
  WHERE segment_name LIKE '%Parapharmacie%'
)
SELECT 
  segment_name,
  date,
  visits,
  ROUND(visits / total_sector_visits * 100, 2) as market_share_pct
FROM sector_data
WHERE DATE(date) = DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH)
ORDER BY market_share_pct DESC;
```

### 6. Benchmark de performance
```sql
-- Comparer les métriques d'engagement
SELECT 
  segment_name,
  AVG(pages_per_visit) as avg_pages_per_visit,
  AVG(visit_duration) as avg_visit_duration_seconds,
  AVG(bounce_rate) as avg_bounce_rate,
  COUNT(DISTINCT date) as months_of_data
FROM `votre-projet.similarweb_data.segments_data`
WHERE DATE(date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 MONTH)
GROUP BY segment_name
HAVING COUNT(DISTINCT date) >= 3
ORDER BY avg_pages_per_visit DESC;
```

## 📅 Analyses Saisonnières

### 7. Saisonnalité par mois
```sql
-- Identifier les patterns saisonniers
SELECT 
  EXTRACT(MONTH FROM date) as month_number,
  FORMAT_DATE('%B', date) as month_name,
  segment_name,
  AVG(visits) as avg_monthly_visits,
  STDDEV(visits) as visits_stddev
FROM `votre-projet.similarweb_data.segments_data`
GROUP BY month_number, month_name, segment_name
ORDER BY segment_name, month_number;
```

### 8. Périodes de pointe
```sql
-- Top 5 mois par segment
SELECT 
  segment_name,
  FORMAT_DATE('%Y-%m', date) as month,
  visits,
  RANK() OVER (PARTITION BY segment_name ORDER BY visits DESC) as rank
FROM `votre-projet.similarweb_data.segments_data`
QUALIFY rank <= 5
ORDER BY segment_name, rank;
```

## 🚨 Alertes et Anomalies

### 9. Détection de chutes de trafic
```sql
-- Alertes sur baisses significatives (> 20%)
WITH monthly_changes AS (
  SELECT 
    segment_name,
    date,
    visits,
    LAG(visits) OVER (PARTITION BY segment_name ORDER BY date) as previous_month_visits
  FROM `votre-projet.similarweb_data.segments_data`
)
SELECT 
  segment_name,
  date,
  visits,
  previous_month_visits,
  ROUND((visits - previous_month_visits) / previous_month_visits * 100, 2) as change_pct
FROM monthly_changes
WHERE previous_month_visits > 0
  AND (visits - previous_month_visits) / previous_month_visits < -0.20
ORDER BY date DESC, change_pct;
```

### 10. Données manquantes
```sql
-- Vérifier la complétude des données
WITH expected_data AS (
  SELECT 
    segment_name,
    COUNT(DISTINCT date) as months_count,
    MIN(date) as first_date,
    MAX(date) as last_date,
    DATE_DIFF(MAX(date), MIN(date), MONTH) + 1 as expected_months
  FROM `votre-projet.similarweb_data.segments_data`
  GROUP BY segment_name
)
SELECT 
  segment_name,
  months_count,
  expected_months,
  expected_months - months_count as missing_months,
  first_date,
  last_date
FROM expected_data
WHERE months_count < expected_months
ORDER BY missing_months DESC;
```

## 🌐 Analyses Sites Web

### 11. Performance des sites web
```sql
-- Top sites par engagement
SELECT 
  domain,
  AVG(visits) as avg_visits,
  AVG(pages_per_visit) as avg_pages_per_visit,
  AVG(visit_duration) as avg_duration_seconds,
  AVG(bounce_rate) as avg_bounce_rate
FROM `votre-projet.similarweb_data.websites_data`
WHERE DATE(date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 MONTH)
GROUP BY domain
ORDER BY avg_visits DESC;
```

### 12. Corrélations segments/sites
```sql
-- Analyser la relation entre segments et sites principaux
WITH segment_totals AS (
  SELECT 
    FORMAT_DATE('%Y-%m', date) as month,
    'Segments' as type,
    SUM(visits) as total_visits
  FROM `votre-projet.similarweb_data.segments_data`
  GROUP BY month
),
website_totals AS (
  SELECT 
    FORMAT_DATE('%Y-%m', date) as month,
    'Websites' as type,
    SUM(visits) as total_visits
  FROM `votre-projet.similarweb_data.websites_data`
  WHERE domain IN ('amazon.fr', 'fnac.com', 'cdiscount.com')
  GROUP BY month
)
SELECT * FROM segment_totals
UNION ALL
SELECT * FROM website_totals
ORDER BY month DESC, type;
```

## 📊 Export pour Visualisation

### 13. Export pour dashboard
```sql
-- Format optimisé pour Tableau/Looker
SELECT 
  segment_name,
  date,
  visits,
  share * 100 as market_share_pct,
  bounce_rate * 100 as bounce_rate_pct,
  pages_per_visit,
  visit_duration / 60 as visit_duration_minutes,
  EXTRACT(YEAR FROM date) as year,
  EXTRACT(MONTH FROM date) as month,
  EXTRACT(QUARTER FROM date) as quarter
FROM `votre-projet.similarweb_data.segments_data`
WHERE DATE(date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 24 MONTH)
ORDER BY date DESC, segment_name;
```

## 💡 Tips d'utilisation

1. **Remplacez `votre-projet`** par votre ID de projet GCP
2. **Utilisez WITH** pour des requêtes complexes (CTE)
3. **QUALIFY** est très utile pour filtrer sur des window functions
4. **FORMAT_DATE** pour des formats de date personnalisés
5. **Sauvegardez vos requêtes** fréquentes comme vues

## 🔗 Ressources utiles

- [Documentation BigQuery SQL](https://cloud.google.com/bigquery/docs/reference/standard-sql/query-syntax)
- [Fonctions BigQuery](https://cloud.google.com/bigquery/docs/reference/standard-sql/functions-and-operators)
- [Best Practices BigQuery](https://cloud.google.com/bigquery/docs/best-practices-performance-overview) 
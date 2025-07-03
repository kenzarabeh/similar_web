# 🚀 Comment pousser ce projet vers GitHub

## 1️⃣ Après avoir créé le repo sur GitHub

Une fois votre repo créé sur GitHub (vide, sans README), copiez l'URL qui ressemble à :
- HTTPS : `https://github.com/VOTRE_USERNAME/similarweb-data-pipeline.git`
- SSH : `git@github.com:VOTRE_USERNAME/similarweb-data-pipeline.git`

## 2️⃣ Connecter votre repo local au repo GitHub

Exécutez ces commandes dans ce dossier :

```bash
# Ajouter l'origine distante (remplacez URL_DU_REPO par votre URL)
git remote add origin URL_DU_REPO

# Vérifier que c'est bien configuré
git remote -v

# Pousser le code vers GitHub
git push -u origin main
```

## 3️⃣ Inviter la Data Scientist

Dans les paramètres du repo GitHub :
1. Allez dans Settings → Manage access
2. Cliquez sur "Add people"
3. Invitez la data scientist avec son username GitHub ou email

## 4️⃣ Instructions pour la Data Scientist

Elle pourra cloner le projet avec :
```bash
git clone URL_DU_REPO
cd similarweb-data-pipeline
```

Puis suivre le `QUICKSTART_DATA_SCIENTIST.md` !

## ✅ C'est fait !

Votre code est maintenant partagé de manière professionnelle et sécurisée. 
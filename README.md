# 🛡️ Himaya (حماية)

**Application desktop 100% hors ligne pour les vendeurs e-commerce algériens.**
تطبيق مكتبي يعمل بدون إنترنت لحماية البائعين الجزائريين من النصب والطلبيات الوهمية.

> **Zéro internet. Zéro serveur. Zéro abonnement.** Toutes les données, toute
> l'analyse et toutes les impressions se passent sur votre PC. — **بدون إنترنت، بدون سيرفر، بدون اشتراك.**

---

## 🇫🇷 Fonctionnalités

| Module | Description |
|---|---|
| 📊 **Tableau de bord** | Résumé du jour (commandes, expéditions, fantômes), alertes arnaque, graphique revenus/pertes sur 6 mois, taux de complétion, argent économisé |
| 👥 **Clients** | Base complète avec **score de confiance auto (0-100)**, étiquettes automatiques (Fiable / Fantôme / Escroc / Perditeur de temps / Nouveau), historique, argent perdu par client |
| 📦 **Commandes** | Cycle complet (En attente → Confirmée → Expédiée → Livrée → Payée) + statuts d'arnaque (Fantôme, Refusée, Téléphone éteint, Faux paiement, Annulée, **Bloquée**), filtres statut/wilaya/date |
| 🔍 **Détecteur de faux reçus** | Analyse locale des captures BaridiMob : OCR (Tesseract), empreinte d'image (dHash) contre les faux déjà connus, métadonnées (traces de PicsArt/Snapseed…), cohérence de police (OpenCV), analyse ELA, format date/référence/montant. Verdict **RÉEL / SUSPECT / FAUX** avec raisons |
| ⏳ **Perditeur de temps** | Journal de chaque contact, taux de conversion, suggestion automatique de demander un **acompte**, réponses intelligentes AR/FR prêtes à coller dans Messenger/WhatsApp |
| 💰 **Rapports financiers** | Revenus, frais, profit net, détail des pertes (fantômes / refus / faux paiements), argent économisé par les blocages. Export CSV / Excel |
| 🔌 **Import / Export USB** | **Fichier `.hma`** : la liste noire officielle Himaya à partager sur clé USB entre vendeurs. Export/import des commandes CSV / Excel |
| 🖨️ **Étiquettes** | PDF A6 (105×148) ou 100×100 avec niveau de risque coloré, code-barres, avertissements (« Appeler avant la livraison ») |
| ⚙️ **Paramètres** | Langue FR/AR, infos CCP/BaridiMob (pour les acomptes), société de livraison par défaut, sauvegarde/restauration, 58 wilayas intégrées |

## 🇩🇿 الميزات (باختصار)

- حماية تعمل محليا 100% — معطياتك تبقى في جهازك (ملف واحد `himaya.db`)
- كشف وصولات BaridiMob المزيفة بالذكاء الاصطناعي المحلي (OCR + تحليل البكسل)
- قائمة سوداء للأرقام المشبوهة تُشارك بين البائعين عبر فلاشة USB (ملف `.hma`)
- نقطة ثقة تلقائية لكل زبون + تصنيفات (نصاب، شبح، مضيع وقت، موثوق)
- تقارير مالية: الأرباح، الخسائر، والمال الذي وفّرته الحماية
- بطاقات توصيل PDF مع مستوى الخطر — تطبع على أي طابعة

---

## 📥 Installation (développeur)

**Prérequis :** Python 3.11+ (https://python.org — cochez *Add to PATH*)

```bat
git clone <ce dépôt> himaya
cd himaya
pip install -r requirements.txt
python main.py
```

### OCR complet (optionnel mais recommandé)

Le détecteur fonctionne sans Tesseract (empreinte + métadonnées + pixels),
mais l'extraction du montant/date/référence nécessite le moteur OCR local :

1. Téléchargez **Tesseract-OCR for Windows** (UB Mannheim) : https://github.com/UB-Mannheim/tesseract/wiki
2. Installez avec les langues **French** (+ Arabic si possible)
3. Si installé hors du PATH, mettez le chemin dans *Paramètres → Chemin de Tesseract*
   (ex. `C:\Program Files\Tesseract-OCR\tesseract.exe`)

> Le paquet `tesseract-ocr-fra` doit être sélectionné pendant l'installation.

## 📦 Créer le .exe (PyInstaller)

```bat
build_windows.bat
```

Résultat : `dist\Himaya\Himaya.exe` — dossier portable, copiable sur n'importe
quel PC Windows 10/11 (même 4 Go de RAM). Pour un fichier unique :

```bat
pyinstaller --noconfirm --onefile --windowed --name Himaya --icon assets/icon.ico --add-data "assets;assets" main.py
```

**Taille** : ~70-95 Mo avec OpenCV. Si besoin, remplacez
`opencv-python-headless` par une build réduite et gardez les `excludes` de
`himaya.spec` pour rester sous 100 Mo.

## 🧱 Créer l'installateur (setup.exe)

Deux méthodes — dans les deux cas le résultat est un **installateur Windows
classique** : `installer\output\Himaya-Setup-1.0.0.exe`.

### Méthode A — sur votre PC Windows (recommandé)

1. Installez **Inno Setup 6** (gratuit) : https://jrsoftware.org/isdl.php
2. Double-cliquez sur :

```bat
build_installer.bat
```

Le script fait tout : environnement virtuel → dépendances → PyInstaller →
`setup.exe`. Si Inno Setup n'est pas détecté, passez son chemin en argument :

```bat
build_installer.bat "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
```

L'installateur offre : assistant en **français** (+ anglais), licence MIT,
icône bureau/menu Démarrer (optionnelles), désinstalleur propre, et à la
désinstallation il **demande** avant de toucher à vos données
(`%APPDATA%\Himaya`) — aucune perte accidentelle de base clients.

Installation silencieuse (déploiement en masse / magasin) :

```bat
Himaya-Setup-1.0.0.exe /VERYSILENT /SUPPRESSMSGBOXES
```

### Méthode B — compilation automatique sur GitHub (aucun PC requis)

Le dépôt contient un workflow `.github/workflows/build-windows.yml` :

- Onglet **Actions** → *Build Windows installer* → **Run workflow** :
  le `setup.exe` apparaît en *artifact* téléchargeable ;
- ou poussez un tag : `git tag v1.0.0 && git push origin v1.0.0` —
  une **Release** est créée automatiquement avec l'installateur attaché.

### Contenu de `installer/`

| Fichier | Rôle |
|---|---|
| `himaya.iss` | Script Inno Setup (version, raccourcis, désinstalleur, prompt données) |
| `file_version_info.txt` | Métadonnées de version de `Himaya.exe` (Propriétés → Détails) |

> ⚠️ Ne changez jamais le `AppId` du script après la première distribution
> (c'est lui qui lie les mises à jour/désinstallations). Pour publier une
> nouvelle version : incrémentez `__version__` dans `himaya/__init__.py`,
> mettez à jour `MyAppVersion` et `filevers` — `tests/test_packaging.py`
> vérifie que tout reste synchronisé.


---

## 🗄️ Où sont mes données ?

Un seul dossier, facile à sauvegarder ou copier sur USB :

| OS | Emplacement |
|---|---|
| Windows | `%APPDATA%\Himaya\himaya.db` |
| Linux/Mac | `~/.himaya/himaya.db` |

- `himaya.db` : **toute** l'application (clients, commandes, liste noire…)
- `evidence/` : copies horodatées des faux reçus analysés
- `backups/` : sauvegardes (bouton *Sauvegarder maintenant* dans Paramètres)

Variable d'environnement `HIMAYA_DATA_DIR` ou `python main.py --db CHEMIN`
pour placer la base ailleurs (ex. directement sur une clé USB).

## 🔐 Le format .hma (partage hors ligne)

Un fichier `.hma` est un document JSON signé par l'en-tête `HIMAYA-BLACKLIST`,
lisible par n'importe quelle instance de Himaya et vérifiable dans un éditeur
de texte :

```json
{
  "magic": "HIMAYA-BLACKLIST",
  "version": 1,
  "exported_at": "2026-09-04T15:30:00",
  "count": 2,
  "entries": [
    {"phone": "0770999888", "reason": "faux reçu BaridiMob", "severity": 3,
     "reported_date": "2026-09-01"}
  ]
}
```

L'import **fusionne** (le niveau de sévérité le plus élevé gagne) — vos
données ne sont jamais écrasées.

## 🧠 Score de confiance — comment il est calculé

Départ à **50/100** (nouveau). Chaque commande bouge le score :

| Événement | Effet |
|---|---|
| Livrée | +10 |
| Payée | +15 |
| Fantôme | −25 |
| Refusée | −12 |
| Téléphone éteint | −10 |
| Faux paiement | **−45 + plafonné à 10** |
| Annulée | −6 |
| Bloquée (liste noire) | −35 + plafonné |

Fiable ≥ 80 (avec 3+ livraisons) · ⚠️ prudence 40-79 · 🚨 dangereux < 40.

**Conventions financières** : revenu = commandes *payées* · perte fantôme/refus/téléphone éteint = frais de livraison · perte faux paiement = frais + prix complet (COD perdu) · **argent économisé** = frais de livraison évités sur les commandes *bloquées* avant expédition.

## ✅ Tests

```bash
python tests/test_core.py       # 79 tests : DB, trust, détection, .hma, PDF, rapports
python tests/test_ui_smoke.py   # interface complète (sans écran, via stubs)
python tests/test_packaging.py  # cohérence versions exe / installateur / spec
```

## 📁 Structure du projet

```
himaya/
├── main.py                  # point d'entrée (--db, --init-only)
├── requirements.txt
├── himaya.spec              # config PyInstaller
├── build_windows.bat        # build portable en 1 clic
├── build_installer.bat      # setup.exe complet en 1 clic (PyInstaller + Inno Setup)
├── installer/               # himaya.iss (Inno Setup) + version info de l'exe
├── .github/workflows/       # build automatique du setup.exe sur GitHub
├── assets/                  # icône, polices, modèles TFLite optionnels
├── tools/make_icon.py       # régénère l'icône
├── tests/                   # tests headless (core + UI)
└── himaya/
    ├── config.py            # chemins, couleurs, constantes métier
    ├── wilayas.py           # les 58 wilayas (FR + AR)
    ├── i18n.py              # traductions FR/AR complètes
    ├── database/            # moteur SQLite + schéma + seed
    ├── models/              # clients, commandes, liste noire, contacts, reçus, modèles, réglages
    ├── services/            # trust, phone, detector (OCR/IA), reports, hma, labels, backup
    └── ui/                  # app + 9 pages CustomTkinter
```

## 🤝 Licence & aide

Projet pour la communauté des vendeurs algériens. Aucune donnée ne quitte
jamais votre ordinateur — c'est la promesse Himaya. وعد حماية: معطياتك لا تغادر جهازك أبدا.

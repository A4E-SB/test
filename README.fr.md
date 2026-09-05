<p align="center"><img src="assets/brand.png" width="240" alt="Logo Himaya"></p>

# 🛡️ Himaya (حماية)

[English](README.md) | **Français** | [العربية](README.ar.md)

**Application desktop 100% hors ligne pour les vendeurs e-commerce algériens.**
تطبيق مكتبي يعمل بدون إنترنت لحماية البائعين الجزائريين من النصب والطلبيات الوهمية.

> **Zéro internet. Zéro serveur. Zéro abonnement.** Toutes les données, toute
> l'analyse et toutes les impressions se passent sur votre PC.

---

## ✨ Fonctionnalités

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
| ⚙️ **Paramètres** | Langue FR/EN/AR, infos CCP/BaridiMob (pour les acomptes), société de livraison par défaut, sauvegarde/restauration, 58 wilayas intégrées |
| 🛒 **Catalogue produits & stock** *(nouveau v1.1)* | Produits avec prix d'achat/vente et marge, stock automatique (bloqué par commande active, rendu si annulée), alertes stock bas, **profit réel** après coûts |
| 💰 **Acomptes** *(nouveau v1.1)* | Suivi des avances avec le statut « attente acompte » ; l'étiquette imprime le **reste à payer** exact |
| ⇩ **Import statuts livreur** *(nouveau v1.1)* | Chargez les exports CSV/Excel Yalidine / ZR / Maystro (ou collez « numéro ; statut ») — les commandes se mettent à jour en masse |
| 👥 **Fusion de doublons** *(nouveau v1.1)* | Détecte la même personne derrière plusieurs SIM (nom + wilaya/adresse similaires) et fusionne l'historique en un clic |
| 📊 **Stats par wilaya** *(nouveau v1.1)* | Taux de fantômes par wilaya avec conseil automatique « demandez un acompte ici », entonnoir des commandes, meilleurs clients avec messages de fidélité |
| 🔔 **Centre de relance** *(nouveau v1.1)* | Commandes coincées en confirmée/expédiée + rappels AR/FR prêts à coller |
| ⚡ **Ajout rapide** *(nouveau v1.1)* | Collez « Karim 0555123456 Sétif cite 200 » — nom/téléphone/wilaya/adresse se remplissent seuls |
| 🧠 **Détecteur qui apprend** *(nouveau v1.1)* | Vos verdicts RÉEL/FAUX ajustent localement les poids de détection à votre marché |
| 🔐 **Sécurité** *(nouveau v1.1)* | Mot de passe applicatif optionnel (PBKDF2), sauvegarde automatique tournante (5 copies) à la fermeture |
| 🔎 **Recherche globale** *(nouveau v1.1)* | Ctrl+K cherche clients, commandes, liste noire et produits en même temps |

L'interface est entièrement trilingue **Français ⇄ Anglais ⇄ Arabe (RTL)** en un clic.

---

## ⬇️ Télécharger l'installateur (déjà compilé)

➡️ **[Himaya-Setup-1.4.0.exe — dernière version](https://github.com/belmezouarsouhil95-byte/test/releases/latest)**
Un seul fichier (≈83 Mo) : double-cliquez, Suivant → Suivant → Terminé.
Application + moteur Python + moteur OCR inclus, aucune connexion requise.

## 🧱 L'installateur tout-en-un

**Un seul fichier. Installez-le et vous avez l'application complète.** Tout est
inclus : l'application, le moteur Python complet, **et le moteur OCR**
(détection de faux reçus opérationnelle dès l'installation). Aucun prérequis,
aucune connexion internet — fonctionne sur n'importe quel Windows 10/11
(4 Go de RAM suffisent).

L'installateur ajoute : raccourcis bureau + menu Démarrer, assistant en
**français**, désinstalleur propre qui **demande** avant de toucher aux
données (`%APPDATA%\Himaya`). Installation silencieuse en masse :
`Himaya-Setup-1.4.0.exe /VERYSILENT /SUPPRESSMSGBOXES`

### Méthode A — sur votre PC Windows

1. Installez **Inno Setup 6** (gratuit, une seule fois) : https://jrsoftware.org/isdl.php
2. Double-cliquez :

```bat
build_installer.bat
```

Le script fait tout : venv → dépendances → PyInstaller → récupération du moteur
OCR (Tesseract, copié depuis votre PC ou téléchargé une fois au moment du
build — jamais chez l'utilisateur final) → `installer\output\Himaya-Setup-1.4.0.exe`.

### Méthode B — compilé automatiquement sur GitHub (zéro PC requis)

- Onglet **Actions** → *Build Windows installer* → **Run workflow** →
  téléchargez le `setup.exe` dans les *artifacts* ;
- ou poussez un tag (`git tag v1.4.0 && git push origin v1.4.0`) : une
  **Release** est créée automatiquement avec l'installateur attaché.

---

## 📥 Installation (développeur)

**Prérequis :** Python 3.11+ (https://python.org — cochez *Add to PATH*)

```bash
git clone https://github.com/belmezouarsouhil95-byte/test himaya
cd himaya
pip install -r requirements.txt
python main.py
```

### OCR complet (optionnel en mode développeur)

Le détecteur fonctionne sans Tesseract (empreinte + métadonnées + pixels),
mais l'extraction du montant/date/référence nécessite le moteur OCR local :

1. Téléchargez **Tesseract-OCR for Windows** (UB Mannheim) : https://github.com/UB-Mannheim/tesseract/wiki
2. Installez avec les langues **French** (+ Arabic si possible)
3. Si installé hors du PATH, mettez le chemin dans *Paramètres → Chemin de Tesseract*
   (ex. `C:\Program Files\Tesseract-OCR\tesseract.exe`)

### .exe portable (PyInstaller)

```bat
build_windows.bat
```

Résultat : `dist\Himaya\Himaya.exe` — dossier portable pour n'importe quel PC
Windows 10/11 (même 4 Go de RAM). Pour un fichier unique :

```bat
pyinstaller --noconfirm --onefile --windowed --name Himaya --icon assets/icon.ico --add-data "assets;assets" --add-data "himaya/database/schema.sql;himaya/database" main.py
```

**Taille** : ~70-95 Mo avec OpenCV.

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
python tests/test_core.py       # 86 tests : DB, trust, détection, .hma, PDF, rapports
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
├── assets/                  # logo, icône, polices, modèles TFLite optionnels
├── tools/                   # générateurs logo/icône
├── tests/                   # tests headless (core + UI + packaging)
└── himaya/
    ├── config.py            # chemins, couleurs, constantes métier
    ├── wilayas.py           # les 58 wilayas (FR + AR)
    ├── i18n.py              # traductions FR/AR complètes
    ├── database/            # moteur SQLite + schéma + seed
    ├── models/              # clients, commandes, liste noire, contacts, reçus…
    ├── services/            # trust, phone, detector (OCR/IA), reports, hma, labels…
    └── ui/                  # app + 9 pages CustomTkinter
```

## 🤝 Licence & promesse

Projet pour la communauté des vendeurs algériens (licence MIT — voir `LICENSE`).
Aucune donnée ne quitte jamais votre ordinateur — c'est la promesse Himaya.
وعد حماية: معطياتك لا تغادر جهازك أبداً.

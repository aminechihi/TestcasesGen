# TestCasesGen - Générateur de Cas de Tests

TestCasesGen, développé par Chihi Amine, est une application Python avec une interface graphique Tkinter. Elle analyse des pages web pour identifier des fonctionnalités communes et générer des ébauches de cas de tests manuels. L'application intègre également des fonctionnalités d'automatisation partielle via Selenium et permet le suivi de l'exécution des tests.

##Fonctionnalités Principales : 

Analyse de Pages Web 🕵️‍♀️: Utilise Selenium et BeautifulSoup pour récupérer et décortiquer le contenu HTML des sites web.
Identification de Fonctionnalités 🔎: Détecte automatiquement les éléments courants d'une page tels que :
Formulaires de connexion (traditionnels et via réseaux sociaux).
Barres de recherche.
Éléments de panier d'achat.
Menus de navigation.
Génération de Cas de Tests 📝: Crée des ébauches de cas de tests manuels pour chaque fonctionnalité identifiée, incluant :
Un ID unique.
Un titre descriptif.
Les préconditions.
Les étapes de test.
Des suggestions de données de test.
Les résultats attendus.
Une priorité (Élevée, Moyenne).
Un "indicateur de localisation" (locator_hint) pour aider à identifier l'élément sur la page.
Interface Graphique (GUI) 💻: Offre une interface utilisateur développée avec Tkinter permettant de :
Saisir l'URL du site à analyser.
Configurer des options de génération (nombre max de tests, etc.).
Visualiser les cas de tests dans un tableau détaillé.
Mettre à jour le statut des tests ("Passé", "Échoué", "Non Testé") et saisir les résultats obtenus.
Appliquer un codage couleur aux tests selon leur priorité et statut.
Automatisation Partielle des Clics🖱️⚡: Permet d'exécuter automatiquement l'étape de clic pour certains cas de tests.
L'utilisateur peut sélectionner un cas de test dans l'interface.
Une option "Exécuter Clic (Automatisé)" lance Selenium.
Selenium ouvre la page, localise l'élément grâce à son ActionableElementLocator et effectue un clic.
Le statut du test est automatiquement mis à jour en "Passé" ou "Échoué" avec un message indiquant le résultat de l'action Selenium.
Gestion des Tests 🗂️:
Sauvegarde et chargement des sessions de test (URL, cas de tests, statuts) au format JSON.
Exportation des cas de tests (avec leur statut) au format CSV.
Support Utilisateur ℹ️:
Informations sur le développeur.
Fonctionnalité pour signaler des bugs par email.

## Prérequis

* Python 3.8 ou plus récent.
* Un navigateur web Google Chrome (l'application utilise ChromeDriver).
* Git (pour cloner le dépôt).

## Cloner le dépôt :**
    Ouvrez votre terminal ou invite de commandes et exécutez :
    ```bash
    git clone https://github.com/aminechihi/TestcasesGen.git
    cd [NOM_DU_DOSSIER_DU_PROJET]
    ```
## Installer les dépendances :**
    Installez toutes les bibliothèques nécessaires à partir du fichier `requirements.txt` :
    ```bash
    pip install -r requirements.txt
    ```
    Cela installera `BeautifulSoup`, `Selenium`, `webdriver-manager`, et leurs dépendances associées.

## Lancement de l'application

Après avoir installé les dépendances, vous pouvez lancer l'application en exécutant le script principal :

```bash
python analyseur_site.py

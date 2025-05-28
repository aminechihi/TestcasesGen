import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import csv
import webbrowser

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

# --- FONCTIONS BACKEND ---

def get_locator_hint(element):
    # ... (Code complet de la fonction get_locator_hint - Identique à la version précédente)
    if not element: return "Élément non trouvé"
    tag_name = element.name; el_id = element.get('id')
    if el_id: return f"XPath: //{tag_name}[@id='{el_id}']"
    el_name = element.get('name')
    if el_name: return f"Name: {el_name}"
    if tag_name in ['input', 'textarea']:
        el_placeholder = element.get('placeholder')
        if el_placeholder: return f"Placeholder: '{el_placeholder[:30]}...'"
        el_aria_label = element.get('aria-label')
        if el_aria_label: return f"XPath: //{tag_name}[@aria-label='{el_aria_label}']"
        el_title = element.get('title')
        if el_title: return f"Title: '{el_title[:30]}...'"
    if tag_name in ['button', 'a', 'input']:
        el_text = element.get_text(strip=True)
        if el_text and len(el_text) < 50:
            clean_text = el_text.replace("'", "\\'")
            if "'" not in clean_text: return f"XPath: //{tag_name}[contains(text(),'{clean_text}')]"
            else: return f"Texte: '{el_text[:30]}...'"
        el_value = element.get('value')
        if el_value: return f"Value: '{el_value[:30]}...'"
        el_aria_label = element.get('aria-label')
        if el_aria_label: return f"Aria-label: '{el_aria_label[:30]}...'"
    el_class = element.get('class')
    if el_class:
        first_class = el_class[0]
        if first_class and not any(c in first_class for c in [' ',':',';']):
            return f"XPath: //{tag_name}[contains(@class,'{first_class}')]"
    return f"Tag: {tag_name}"

def recuperer_contenu_page_avec_selenium(url):
    # ... (Code complet de la fonction recuperer_contenu_page_avec_selenium - Identique)
    print(f"Tentative de récupération de l'URL avec Selenium : {url}")
    driver = None
    try:
        options_chrome = webdriver.ChromeOptions(); options_chrome.add_argument('--headless'); options_chrome.add_argument('--disable-gpu'); options_chrome.add_argument('--log-level=3'); options_chrome.add_argument("--start-maximized"); options_chrome.add_argument('--window-size=1920,1080'); options_chrome.add_argument('--ignore-certificate-errors'); options_chrome.add_argument('--allow-running-insecure-content'); options_chrome.add_argument('--no-sandbox'); options_chrome.add_argument('--disable-dev-shm-usage'); options_chrome.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        service_chrome = ChromeService(ChromeDriverManager().install()); driver = webdriver.Chrome(service=service_chrome, options=options_chrome)
        driver.get(url); print(f"Page {url} en cours de chargement... Attente de 4 secondes."); time.sleep(4)
        page_source = driver.page_source; print(f"Contenu de la page récupéré (longueur: {len(page_source)} caractères).")
        return page_source
    except Exception as e: print(f"Erreur lors de la récupération de la page {url} avec Selenium : {e}"); return None
    finally:
        if driver: print("Fermeture du navigateur Selenium."); driver.quit()

def analyser_page_pour_fonctionnalites(html_content, url_page):
    # ... (Code complet de la fonction analyser_page_pour_fonctionnalites - Identique,
    #      s'assurant que get_locator_hint est appelé partout où c'est nécessaire)
    print(f"\nDébut de l'analyse de la page : {url_page}.")
    fonctionnalites_retournees = { "url_page": url_page, "titre_page": "Pas de titre", "formulaires_connexion": [], "barres_recherche": [], "elements_panier": [], "menus_navigation": [] }
    if not html_content: return fonctionnalites_retournees
    try: soup = BeautifulSoup(html_content, 'lxml')
    except Exception:
        try: soup = BeautifulSoup(html_content, 'html.parser')
        except Exception as e_parser: print(f"Erreur avec tous les parseurs: {e_parser}."); return fonctionnalites_retournees
    if soup.title and soup.title.string: fonctionnalites_retournees["titre_page"] = soup.title.string.strip()
    else: print("Aucun titre de page trouvé.")
    all_inputs_and_textareas = soup.find_all(['input', 'textarea']); all_buttons_and_inputs_on_page = soup.find_all(['button', 'input'])
    # Connexion
    champs_identifiants_trouves_login = []; possible_username_texts = ['user', 'login', 'email', 'identifier', 'account', 'pseudo', 'username', 'userid', 'e-mail', 'identifiant']
    for el in all_inputs_and_textareas:
        el_type = el.get('type', '').lower() if el.name == 'input' else 'textarea'; el_name = el.get('name', '').lower(); el_placeholder = el.get('placeholder', '').lower(); el_id = el.get('id', '').lower()
        if el_type in ['text', 'email', 'tel', 'search', 'textarea']: 
            is_username_field = False
            if any(term in el_name for term in possible_username_texts): is_username_field = True
            if not is_username_field and any(term in el_placeholder for term in possible_username_texts): is_username_field = True
            if not is_username_field and any(term in el_id for term in possible_username_texts): is_username_field = True
            if is_username_field and 'search' in el_type and not any(term in (el_name + el_placeholder + el_id) for term in ['user', 'login', 'email', 'account']): is_username_field = False 
            if is_username_field: champs_identifiants_trouves_login.append(el)
    champs_mdp_trouves = soup.find_all('input', {'type': 'password'})
    boutons_soumission_login_trouves = []; possible_button_login_texts = ['log in', 'login', 'sign in', 'signin', 'connect', 'connexion', 'entrer', 'valider', 'ok', 'se connecter']
    for btn in all_buttons_and_inputs_on_page:
        btn_tag = btn.name.lower(); btn_type = btn.get('type', '').lower(); is_potential_submit = False
        if btn_tag == 'button' and btn_type in ['submit', 'button', '']: is_potential_submit = True
        elif btn_tag == 'input' and btn_type in ['submit', 'button', 'image']: is_potential_submit = True
        if is_potential_submit:
            btn_text = (btn.get_text(strip=True) or btn.get('value','') or btn.get('aria-label','')).lower(); btn_name = btn.get('name', '').lower(); btn_id = btn.get('id', '').lower()
            if any(term in btn_text for term in possible_button_login_texts) or any(term in btn_name for term in possible_button_login_texts) or any(term in btn_id for term in possible_button_login_texts) or (is_potential_submit and not btn_text and any(key in (btn_id+btn_name) for key in ['login','submit'])):
                boutons_soumission_login_trouves.append(btn)
    print(f"[Analyse Connexion] Éléments bruts: {len(champs_identifiants_trouves_login)} ID, {len(champs_mdp_trouves)} MDP, {len(boutons_soumission_login_trouves)} Boutons Login.")
    if champs_identifiants_trouves_login and champs_mdp_trouves and boutons_soumission_login_trouves:
        for idx, champ_mdp in enumerate(champs_mdp_trouves):
            champ_id_associe = champs_identifiants_trouves_login[0]; bouton_associe = boutons_soumission_login_trouves[0]
            form_simule_details = {"id_formulaire_page": f"sim_login_mechanism_{idx+1}", "champ_identifiant": {"tag": champ_id_associe.name, "type": champ_id_associe.get('type', 'text') if champ_id_associe.name == 'input' else 'textarea', "name": champ_id_associe.get('name'), "id": champ_id_associe.get('id'), "placeholder": champ_id_associe.get('placeholder'), "locator_hint": get_locator_hint(champ_id_associe)}, "champ_mot_de_passe": {"tag": champ_mdp.name, "type": champ_mdp.get('type'), "name": champ_mdp.get('name'), "id": champ_mdp.get('id'), "placeholder": champ_mdp.get('placeholder'), "locator_hint": get_locator_hint(champ_mdp)}, "bouton_soumission": {"tag": bouton_associe.name, "type": bouton_associe.get('type'), "text": bouton_associe.get_text(strip=True) or bouton_associe.get('value') or bouton_associe.get('aria-label',''), "id": bouton_associe.get('id'), "name": bouton_associe.get('name'), "locator_hint": get_locator_hint(bouton_associe)}}
            fonctionnalites_retournees["formulaires_connexion"].append(form_simule_details); print(f"[INFO] Mécanisme de connexion simulé #{idx+1} construit.")
    if not fonctionnalites_retournees["formulaires_connexion"]: print("[INFO] Aucun mécanisme de connexion simulé n'a pu être assemblé.")
    # Recherche
    barres_recherche_trouvees = []; possible_search_input_texts = ['search', 'query', 'q', 'recherche', 'keyword', 'motcle', 'keywords', 'requête', 'rechercher sur']; possible_search_button_texts = ['search', 'rechercher', 'go', 'find', 'trouver', 'ok', 'submit', 'loupe']
    champs_recherche_potentiels = []
    for el in all_inputs_and_textareas:
        el_type = el.get('type', '').lower() if el.name == 'input' else 'textarea'; el_name = el.get('name', '').lower(); el_placeholder = el.get('placeholder', '').lower(); el_id = el.get('id', '').lower(); el_title = el.get('title','').lower(); el_aria_label = el.get('aria-label','').lower()
        is_search_field = False
        if any(term in el_name for term in possible_search_input_texts): is_search_field = True
        if not is_search_field and any(term in el_placeholder for term in possible_search_input_texts): is_search_field = True
        if not is_search_field and any(term in el_id for term in possible_search_input_texts): is_search_field = True
        if not is_search_field and any(term in el_title for term in possible_search_input_texts): is_search_field = True
        if not is_search_field and any(term in el_aria_label for term in possible_search_input_texts): is_search_field = True
        if is_search_field and el_type not in ['text', 'search', 'textarea', 'url', 'tel', 'email']: is_search_field = False
        if is_search_field: champs_recherche_potentiels.append(el)
    boutons_recherche_potentiels = []
    for btn in all_buttons_and_inputs_on_page:
        btn_tag = btn.name.lower(); btn_type = btn.get('type', '').lower(); is_potential_search_submit = False
        if btn_tag == 'button' and btn_type in ['submit', 'button', '']: is_potential_search_submit = True
        elif btn_tag == 'input' and btn_type in ['submit', 'button', 'image']: is_potential_search_submit = True
        if is_potential_search_submit:
            btn_text = (btn.get_text(strip=True) or btn.get('value','') or btn.get('aria-label','')).lower()
            if any(term in btn_text for term in possible_search_button_texts) or (not btn_text and btn_type == 'submit'):
                boutons_recherche_potentiels.append(btn)
    print(f"[Analyse Recherche] Éléments bruts: {len(champs_recherche_potentiels)} champ(s) recherche, {len(boutons_recherche_potentiels)} bouton(s) recherche.")
    if champs_recherche_potentiels and boutons_recherche_potentiels:
        champ_recherche_principal = champs_recherche_potentiels[0]; bouton_recherche_principal = boutons_recherche_potentiels[0]
        if bouton_recherche_principal in boutons_soumission_login_trouves and len(boutons_recherche_potentiels) > 1:
            non_login_search_buttons = [b for b in boutons_recherche_potentiels if b not in boutons_soumission_login_trouves]
            if non_login_search_buttons: bouton_recherche_principal = non_login_search_buttons[0]
        details_barre_recherche = {"id_barre_recherche": f"sim_searchbar_{len(barres_recherche_trouvees)+1}", "champ_recherche": {"tag": champ_recherche_principal.name, "type": champ_recherche_principal.get('type') if champ_recherche_principal.name == 'input' else 'textarea', "name": champ_recherche_principal.get('name'), "id": champ_recherche_principal.get('id'), "placeholder": champ_recherche_principal.get('placeholder'), "aria-label": champ_recherche_principal.get('aria-label'), "title": champ_recherche_principal.get('title'), "locator_hint": get_locator_hint(champ_recherche_principal)}, "bouton_recherche": {"tag": bouton_recherche_principal.name, "type": bouton_recherche_principal.get('type'), "text": bouton_recherche_principal.get_text(strip=True) or bouton_recherche_principal.get('value') or bouton_recherche_principal.get('aria-label'), "id": bouton_recherche_principal.get('id'), "name": bouton_recherche_principal.get('name'), "locator_hint": get_locator_hint(bouton_recherche_principal)}}
        barres_recherche_trouvees.append(details_barre_recherche); print(f"[INFO] Barre de recherche simulée #{len(barres_recherche_trouvees)} construite.")
    fonctionnalites_retournees["barres_recherche"] = barres_recherche_trouvees
    if not barres_recherche_trouvees: print("[INFO] Aucune barre de recherche simulée n'a pu être assemblée.")
    # Panier
    elements_panier_trouves = []; possible_cart_texts_attributes = ['cart', 'panier', 'basket', 'caddie', 'sac', 'checkout', 'mon panier', 'votre panier']; possible_cart_icon_classes = ['fa-shopping-cart', 'fa-shopping-basket', 'fa-shopping-bag', 'cart-icon', 'icon-cart', 'shopping-cart']
    potential_cart_elements = soup.find_all(['a', 'button', 'span', 'div', 'i'])
    for el in potential_cart_elements:
        el_text = el.get_text(strip=True).lower(); el_href = el.get('href', '').lower(); el_id = el.get('id', '').lower(); el_class = " ".join(el.get('class', [])).lower(); el_aria_label = el.get('aria-label', '').lower(); el_title = el.get('title', '').lower()
        is_cart_element = False
        if any(term in el_text for term in possible_cart_texts_attributes): is_cart_element = True
        if not is_cart_element and any(term in el_href for term in possible_cart_texts_attributes): is_cart_element = True;
        if not is_cart_element and any(term in el_id for term in possible_cart_texts_attributes): is_cart_element = True;
        if not is_cart_element and any(term in el_aria_label for term in possible_cart_texts_attributes): is_cart_element = True;
        if not is_cart_element and any(term in el_title for term in possible_cart_texts_attributes): is_cart_element = True;
        if not is_cart_element and any(icon_class in el_class for icon_class in possible_cart_icon_classes): is_cart_element = True;
        if not is_cart_element and '(' in el_text and ')' in el_text:
            if any(term in el_text for term in possible_cart_texts_attributes):
                try: count_str = el_text[el_text.find('(')+1 : el_text.find(')')]; int(count_str); is_cart_element = True
                except ValueError: pass
        if is_cart_element:
            already_added = False;
            for added_el_detail in elements_panier_trouves:
                if added_el_detail["element_text"] == el.get_text(strip=True): already_added = True; break
            if not already_added:
                cart_el_details = {"id_panier_element": f"sim_cart_el_{len(elements_panier_trouves)+1}", "tag_name": el.name, "element_text": el.get_text(strip=True), "href": el.get('href') if el.name == 'a' else None, "attributes": { "id": el.get('id'), "class": el.get('class'), "aria-label": el.get('aria-label'), "title": el.get('title')}, "locator_hint": get_locator_hint(el)}
                elements_panier_trouves.append(cart_el_details); print(f"[INFO] Élément de panier simulé #{len(elements_panier_trouves)} ('{cart_el_details['element_text']}') construit.")
    fonctionnalites_retournees["elements_panier"] = elements_panier_trouves
    if not elements_panier_trouves: print("[INFO] Aucun élément de panier simulé n'a pu être assemblé.")
    # Navigation
    menus_navigation_trouves = []; nav_tags = soup.find_all('nav'); potential_menu_uls = soup.find_all('ul', {'role': ['menu', 'menubar', 'navigation', 'listbox', 'tree']}); common_menu_classes_ids = ['menu', 'nav', 'navbar', 'navigation', 'main-menu', 'nav-menu', 'top-menu', 'primary-menu']
    for ul_candidate in soup.find_all('ul'):
        current_id = ul_candidate.get('id', '').lower(); current_classes = " ".join(ul_candidate.get('class', [])).lower()
        if any(term in current_id for term in common_menu_classes_ids) or any(term in current_classes for term in common_menu_classes_ids):
            if ul_candidate not in potential_menu_uls: potential_menu_uls.append(ul_candidate)
    all_menu_containers = nav_tags + potential_menu_uls; print(f"[Analyse Navigation] Conteneurs de menu potentiels trouvés: {len(all_menu_containers)}")
    menu_item_id_counter = 0; processed_hrefs_in_menu = set()
    for container_idx, menu_container in enumerate(all_menu_containers):
        menu_links_in_container = []; list_items = menu_container.find_all('li', recursive=True)
        if list_items:
            for li in list_items:
                link = li.find('a', href=True)
                if link: menu_links_in_container.append(link)
        else: menu_links_in_container = menu_container.find_all('a', href=True, recursive=True)
        if menu_links_in_container:
            print(f"[INFO] Menu/Navigation #{container_idx+1} détecté avec {len(menu_links_in_container)} lien(s).")
            current_menu_links = []
            for link in menu_links_in_container:
                link_text = link.get_text(strip=True); link_href = link.get('href')
                if link_text and link_href and not link_href.startswith(('#', 'javascript:')) and link_href not in processed_hrefs_in_menu:
                    menu_item_id_counter += 1
                    menu_item_details = {"id_menu_item": f"menu_item_{menu_item_id_counter}", "texte_lien": link_text, "href": link_href, "tag_name": link.name, "parent_container_info": f"Menu Container #{container_idx+1} ({menu_container.name})", "locator_hint": get_locator_hint(link)}
                    current_menu_links.append(menu_item_details); processed_hrefs_in_menu.add(link_href)
            if current_menu_links: menus_navigation_trouves.extend(current_menu_links)
    fonctionnalites_retournees["menus_navigation"] = menus_navigation_trouves
    if not menus_navigation_trouves: print("[INFO] Aucun lien de menu significatif n'a été assemblé.")
    else: print(f"[INFO] Total de {len(menus_navigation_trouves)} liens de menu significatifs trouvés.")
    return fonctionnalites_retournees

def generer_cas_tests_connexion(form_details, url_page, base_id="CT_LOGIN"):
    # ... (Code complet, avec les descriptions mises à jour utilisant locator_hint)
    cas_tests = []
    champ_id_details = form_details.get("champ_identifiant", {}); champ_mdp_details = form_details.get("champ_mot_de_passe", {}); bouton_soumission_details = form_details.get("bouton_soumission", {})
    desc_identifiant = f"'{champ_id_details.get('name') or champ_id_details.get('id') or champ_id_details.get('placeholder', 'identifiant')}' (Indicateur: {champ_id_details.get('locator_hint', 'N/A')})"
    desc_mdp = f"'{champ_mdp_details.get('name') or champ_mdp_details.get('id') or champ_mdp_details.get('placeholder', 'mot de passe')}' (Indicateur: {champ_mdp_details.get('locator_hint', 'N/A')})"
    desc_bouton = f"'{bouton_soumission_details.get('text') or 'soumission'}' (Indicateur: {bouton_soumission_details.get('locator_hint', 'N/A')})"
    precondition = f"L'utilisateur est sur la page {url_page} où un mécanisme de connexion ({form_details.get('id_formulaire_page', 'N/A')}) est identifié."
    cas_tests.append({"ID du cas de test": f"{base_id}_VALID_001", "Titre du cas de test": "Vérifier la connexion avec des identifiants valides", "Préconditions": precondition, "Étapes de test": (f"1. Entrer un nom d'utilisateur valide dans le champ {desc_identifiant}.\n2. Entrer un mot de passe valide dans le champ {desc_mdp}.\n3. Cliquer sur le bouton {desc_bouton}."), "Données de test": "Nom d'utilisateur: [identifiant_valide]\nMot de passe: [mdp_valide]", "Résultat attendu": "L'utilisateur est connecté avec succès et redirigé.", "Priorité": "Élevée"})
    cas_tests.append({"ID du cas de test": f"{base_id}_INVALID_PWD_002", "Titre du cas de test": "Vérifier la connexion avec un mot de passe incorrect", "Préconditions": precondition, "Étapes de test": (f"1. Entrer un nom d'utilisateur valide dans le champ {desc_identifiant}.\n2. Entrer un mot de passe INVALIDE dans le champ {desc_mdp}.\n3. Cliquer sur le bouton {desc_bouton}."), "Données de test": "Nom d'utilisateur: [identifiant_valide]\nMot de passe: [mdp_invalide]", "Résultat attendu": "Message d'erreur affiché. Non connecté.", "Priorité": "Élevée"})
    cas_tests.append({"ID du cas de test": f"{base_id}_EMPTY_FIELDS_003", "Titre du cas de test": "Vérifier la connexion avec des champs vides", "Préconditions": precondition, "Étapes de test": (f"1. Laisser le champ {desc_identifiant} vide.\n2. Laisser le champ {desc_mdp} vide.\n3. Cliquer sur le bouton {desc_bouton}."), "Données de test": "Nom d'utilisateur: \nMot de passe: ", "Résultat attendu": "Messages d'erreur pour champs obligatoires ou connexion échouée.", "Priorité": "Moyenne"})
    return cas_tests

def generer_cas_tests_recherche(search_bar_details, url_page, base_id="CT_SEARCH"):
    # ... (Code complet, avec les descriptions mises à jour utilisant locator_hint)
    cas_tests = []
    champ_recherche_details = search_bar_details.get("champ_recherche", {}); bouton_recherche_details = search_bar_details.get("bouton_recherche", {})
    desc_champ_recherche = f"'{champ_recherche_details.get('name') or champ_recherche_details.get('id') or champ_recherche_details.get('placeholder', 'recherche')}' (Indicateur: {champ_recherche_details.get('locator_hint', 'N/A')})"
    desc_bouton_recherche = f"'{bouton_recherche_details.get('text') or 'recherche'}' (Indicateur: {bouton_recherche_details.get('locator_hint', 'N/A')})"
    precondition = f"L'utilisateur est sur la page {url_page} où une barre de recherche ({search_bar_details.get('id_barre_recherche', 'N/A')}) est identifiée."
    cas_tests.append({"ID du cas de test": f"{base_id}_VALID_RESULTS_001", "Titre du cas de test": "Vérifier la recherche avec un terme valide (résultats attendus)", "Préconditions": precondition, "Étapes de test": (f"1. Entrer un terme de recherche pertinent dans {desc_champ_recherche}.\n2. Cliquer sur le bouton {desc_bouton_recherche}."), "Données de test": "Terme de recherche: [terme_valide_avec_resultats]", "Résultat attendu": "Les résultats de recherche pertinents sont affichés.", "Priorité": "Élevée"})
    cas_tests.append({"ID du cas de test": f"{base_id}_VALID_NO_RESULTS_002", "Titre du cas de test": "Vérifier la recherche avec un terme valide (aucun résultat attendu)", "Préconditions": precondition, "Étapes de test": (f"1. Entrer un terme de recherche peu commun dans {desc_champ_recherche}.\n2. Cliquer sur le bouton {desc_bouton_recherche}."), "Données de test": "Terme de recherche: [terme_valide_sans_resultats]", "Résultat attendu": "Un message indique qu'aucun résultat n'a été trouvé.", "Priorité": "Moyenne"})
    cas_tests.append({"ID du cas de test": f"{base_id}_EMPTY_003", "Titre du cas de test": "Vérifier la recherche avec un champ vide", "Préconditions": precondition, "Étapes de test": (f"1. Laisser le champ {desc_champ_recherche} vide.\n2. Cliquer sur le bouton {desc_bouton_recherche}."), "Données de test": "Terme de recherche: ", "Résultat attendu": "Aucune action de recherche ou message d'erreur.", "Priorité": "Moyenne"})
    return cas_tests

def generer_cas_tests_panier(cart_element_details, url_page, base_id="CT_CART"):
    # ... (Code complet, avec les descriptions mises à jour utilisant locator_hint)
    cas_tests = []
    element_texte = cart_element_details.get("element_text", "l'élément du panier"); locator_hint_panier = cart_element_details.get("locator_hint", "N/A")
    desc_element_panier = f"'{element_texte}' (Indicateur: {locator_hint_panier})"
    precondition = f"L'utilisateur est sur la page {url_page} où un élément de panier ({desc_element_panier}) est visible."
    cas_tests.append({"ID du cas de test": f"{base_id}_ACCESS_VIEW_001", "Titre du cas de test": f"Vérifier l'accès et l'affichage du panier via {desc_element_panier}", "Préconditions": precondition, "Étapes de test": f"1. Cliquer sur l'élément du panier {desc_element_panier}.", "Données de test": "N/A - Panier supposé vide.", "Résultat attendu": "La page du panier s'affiche. Si vide, un message l'indique.", "Priorité": "Élevée"})
    cas_tests.append({"ID du cas de test": f"{base_id}_PRESENCE_CLICKABLE_002", "Titre du cas de test": f"Vérifier la présence et la cliquabilité de {desc_element_panier}", "Préconditions": f"L'utilisateur est sur une page où {desc_element_panier} devrait être visible (ex: {url_page}).", "Étapes de test": (f"1. Repérer {desc_element_panier}.\n2. Vérifier qu'il est cliquable."), "Données de test": "N/A", "Résultat attendu": "L'élément du panier est présent, visible et interactif.", "Priorité": "Moyenne"})
    return cas_tests

def generer_cas_tests_navigation(nav_link_details, url_page, base_id="CT_NAV"):
    # ... (Code complet, avec les descriptions mises à jour utilisant locator_hint)
    cas_tests = []
    link_text = nav_link_details.get("texte_lien", "Lien inconnu"); link_href = nav_link_details.get("href", "#"); locator_hint_nav = nav_link_details.get("locator_hint", "N/A")
    desc_lien_nav = f"'{link_text}' (Cible: {link_href}, Indicateur: {locator_hint_nav})"
    precondition_base = f"L'utilisateur est sur la page {url_page}."
    cas_tests.append({"ID du cas de test": f"{base_id}_{nav_link_details.get('id_menu_item', 'item').replace('menu_item_', '')}_PRESENCE_001", "Titre du cas de test": f"Navigation: Vérifier présence/visibilité du lien {desc_lien_nav}", "Préconditions": precondition_base, "Étapes de test": f"1. Rechercher visuellement le lien de menu {desc_lien_nav}.", "Données de test": "N/A", "Résultat attendu": f"Le lien de menu {desc_lien_nav} est présent, visible et correctement libellé.", "Priorité": "Élevée"})
    cas_tests.append({"ID du cas de test": f"{base_id}_{nav_link_details.get('id_menu_item', 'item').replace('menu_item_', '')}_CLICK_002", "Titre du cas de test": f"Navigation: Vérifier clic et redirection du lien {desc_lien_nav}", "Préconditions": f"{precondition_base} Le lien {desc_lien_nav} est visible.", "Étapes de test": f"1. Cliquer sur le lien de menu {desc_lien_nav}.", "Données de test": "N/A", "Résultat attendu": (f"Redirection vers une page valide ({link_href}). Page chargée sans erreur."), "Priorité": "Élevée"})
    return cas_tests

# --- Classe de l'Application GUI ---
class TestGenApp:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Générateur Intelligent de Cas de Test Manuels v1.2")
        self.root.geometry("1100x800")
        
        style = ttk.Style()
        try: style.theme_use('clam')
        except tk.TclError: print("Thème ttk 'clam' non trouvé.")

        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Aide", menu=help_menu)
        help_menu.add_command(label="À propos du développeur", command=self.show_developer_info)
        help_menu.add_separator()
        help_menu.add_command(label="Signaler un bug", command=self.report_bug)

        url_frame = ttk.LabelFrame(self.root, text="URL du Site Web")
        url_frame.pack(padx=10, pady=5, fill="x")
        ttk.Label(url_frame, text="URL:").pack(side=tk.LEFT, padx=5)
        self.url_entry = ttk.Entry(url_frame, width=60)
        self.url_entry.pack(side=tk.LEFT, padx=5, expand=True, fill="x")
        self.url_entry.insert(0, "https://www.wikipedia.org/")
        self.analyze_button = ttk.Button(url_frame, text="Analyser et Générer", command=self.start_analysis_thread)
        self.analyze_button.pack(side=tk.LEFT, padx=(5,0), pady=5)
        
        main_content_frame = ttk.Frame(self.root)
        main_content_frame.pack(padx=10, pady=5, expand=True, fill="both")
        
        results_frame = ttk.LabelFrame(main_content_frame, text="Cas de Test Générés")
        results_frame.pack(pady=(0,5), expand=True, fill="both")
        
        columns = ("id_test", "titre", "preconditions", "etapes", "donnees", "attendu", "priorite")
        self.tree = ttk.Treeview(results_frame, columns=columns, show="headings") # Création de self.tree
        
        # --- DÉPLACÉ ICI : Configuration des tags APRÈS la création de self.tree ---
        self.tree.tag_configure("Priority.Élevée", foreground="black", background="#FFDDDD") # Rouge clair
        self.tree.tag_configure("Priority.Moyenne", foreground="black", background="#FFFFCC") # Jaune clair
        self.tree.tag_configure("Priority.Faible", foreground="black", background="#DDFFDD")  # Vert clair (si vous l'utilisez)
        # --- Fin configuration des tags ---

        col_config = { "id_test": ("ID Cas Test", 120), "titre": ("Titre Cas Test", 220), 
                       "preconditions": ("Préconditions", 180), "etapes": ("Étapes de Test", 350), 
                       "donnees": ("Données Test", 150), "attendu": ("Résultat Attendu", 200), 
                       "priorite": ("Priorité", 80) }
        for col_id, (col_text, col_width) in col_config.items():
            self.tree.heading(col_id, text=col_text)
            self.tree.column(col_id, width=col_width, anchor=tk.W, stretch=(col_id not in ["id_test", "priorite"]))
        
        vsb = ttk.Scrollbar(results_frame, orient="vertical", command=self.tree.yview); hsb = ttk.Scrollbar(results_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set); vsb.pack(side='right', fill='y'); hsb.pack(side='bottom', fill='x')
        self.tree.pack(expand=True, fill='both')
        
        action_buttons_frame = ttk.Frame(main_content_frame); action_buttons_frame.pack(fill=tk.X, pady=(5,0))
        self.export_csv_button = ttk.Button(action_buttons_frame, text="Exporter en CSV", command=self.export_to_csv, state=tk.DISABLED)
        self.export_csv_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.status_bar = ttk.Label(self.root, text="Prêt. Développé par Chihi Amine.", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(5,0))
        self.generated_test_cases_data = []

    def show_developer_info(self): # ... (Identique)
        info_window = tk.Toplevel(self.root); info_window.title("À Propos du Développeur"); info_window.geometry("400x200"); info_window.resizable(False, False); info_window.grab_set(); info_window.transient(self.root)
        main_frame = ttk.Frame(info_window, padding="20"); main_frame.pack(expand=True, fill="both")
        ttk.Label(main_frame, text="Application Développée par :", font=('TkDefaultFont', 12, 'bold')).pack(pady=(0,5)); ttk.Label(main_frame, text="Chihi Amine", font=('TkDefaultFont', 11)).pack()
        linkedin_label = ttk.Label(main_frame, text="Profil LinkedIn", foreground="blue", cursor="hand2", font=('TkDefaultFont', 10, 'underline')); linkedin_label.pack(pady=5); linkedin_label.bind("<Button-1>", lambda e: webbrowser.open_new_tab("https://www.linkedin.com/in/chihiamine/"))
        github_label = ttk.Label(main_frame, text="Profil GitHub", foreground="blue", cursor="hand2", font=('TkDefaultFont', 10, 'underline')); github_label.pack(pady=5); github_label.bind("<Button-1>", lambda e: webbrowser.open_new_tab("https://github.com/aminechihi"))
        ttk.Button(main_frame, text="Fermer", command=info_window.destroy).pack(pady=10); info_window.wait_window()

    def report_bug(self): # ... (Identique)
        subject = "Signalement de Bug - Générateur de Cas de Test"; body = ("Bonjour Amine,\n\nJe souhaite signaler un bug concernant l'application 'Générateur Intelligent de Cas de Test Manuels'.\n\nURL testée (si applicable) :\n[Entrez l'URL ici]\n\nDescription du bug :\n[Décrivez le problème rencontré]\n\nÉtapes pour reproduire le bug :\n1. \n2. \n3. \n\nRésultat attendu :\n[Ce que vous attendiez]\n\nRésultat obtenu :\n[Ce qui s'est réellement passé]\n\nMerci!")
        mailto_url = f"mailto:amine.chihi@hotmail.fr?subject={subject.replace(' ', '%20')}&body={body.replace(' ', '%20').replace('\n', '%0D%0A')}"
        try: webbrowser.open(mailto_url); messagebox.showinfo("Signaler un bug", "Votre client de messagerie devrait s'ouvrir.")
        except Exception as e: messagebox.showerror("Erreur", f"Impossible d'ouvrir le client de messagerie.\nErreur: {e}\nEmail: amine.chihi@hotmail.fr")

    def start_analysis_thread(self): # ... (Identique)
        url = self.url_entry.get();
        if not url or not (url.startswith("http://") or url.startswith("https://")):
            messagebox.showerror("URL Invalide", "Veuillez entrer une URL valide."); return
        self.analyze_button.config(state=tk.DISABLED); self.export_csv_button.config(state=tk.DISABLED)
        self.status_bar.config(text=f"Analyse de {url} en cours...")
        self.tree.delete(*self.tree.get_children()); self.generated_test_cases_data = []
        thread = threading.Thread(target=self.run_analysis, args=(url,)); thread.daemon = True; thread.start()

    def run_analysis(self, url): # ... (Identique)
        try:
            print(f"Lancement de l'analyse pour l'URL : {url}")
            contenu_html = recuperer_contenu_page_avec_selenium(url)
            all_test_cases_for_url = []
            if contenu_html:
                fonctionnalites = analyser_page_pour_fonctionnalites(contenu_html, url)
                if fonctionnalites.get("formulaires_connexion"):
                    for i, form_data in enumerate(fonctionnalites["formulaires_connexion"]):
                        all_test_cases_for_url.extend(generer_cas_tests_connexion(form_data, fonctionnalites["url_page"], base_id=f"CT_LOGIN_MEC_{i+1}"))
                if fonctionnalites.get("barres_recherche"):
                    for i, search_data in enumerate(fonctionnalites["barres_recherche"]):
                        all_test_cases_for_url.extend(generer_cas_tests_recherche(search_data, fonctionnalites["url_page"], base_id=f"CT_SEARCH_BAR_{i+1}"))
                if fonctionnalites.get("elements_panier"):
                    for i, cart_data in enumerate(fonctionnalites["elements_panier"]):
                        all_test_cases_for_url.extend(generer_cas_tests_panier(cart_data, fonctionnalites["url_page"], base_id=f"CT_CART_EL_{i+1}"))
                if fonctionnalites.get("menus_navigation"): 
                    for i, nav_link_data in enumerate(fonctionnalites["menus_navigation"]):
                        all_test_cases_for_url.extend(generer_cas_tests_navigation(nav_link_data, fonctionnalites["url_page"], base_id=f"CT_NAV_LINK_{nav_link_data.get('id_menu_item','').replace('menu_item_','')}"))
                self.root.after(0, self.update_gui_with_results, all_test_cases_for_url, fonctionnalites.get('titre_page', 'Titre inconnu'))
            else:
                self.root.after(0, self.update_gui_with_error, f"Impossible de récupérer le contenu de {url}.")
        except Exception as e:
            print(f"Erreur majeure pendant l'analyse : {e}"); import traceback; traceback.print_exc()
            self.root.after(0, self.update_gui_with_error, f"Erreur d'analyse : {e}")
        finally:
            self.root.after(0, self.finalize_analysis_ui)
            
    def update_gui_with_results(self, test_cases, page_title):
        self.status_bar.config(text=f"Analyse terminée: {page_title}. {len(test_cases)} cas de test générés.")
        if not test_cases: 
            messagebox.showinfo("Résultats", "Aucun cas de test pertinent n'a pu être généré.")
            self.export_csv_button.config(state=tk.DISABLED); return
        
        self.generated_test_cases_data = test_cases
        print(f"[DEBUG GUI] Dans update_gui_with_results. Nombre de cas à afficher: {len(test_cases)}")

        item_inserted_count = 0
        # La configuration des tags est maintenant dans __init__
        for i, tc in enumerate(test_cases):
            values = (
                tc.get("ID du cas de test", ""), tc.get("Titre du cas de test", ""), 
                tc.get("Préconditions", ""), tc.get("Étapes de test", ""), 
                tc.get("Données de test", ""), tc.get("Résultat attendu", ""),
                tc.get("Priorité", "")
            )
            priority_value = tc.get("Priorité", "")
            current_tags = [] 
            if priority_value == "Élevée": current_tags.append("Priority.Élevée")
            elif priority_value == "Moyenne": current_tags.append("Priority.Moyenne")
            elif priority_value == "Faible": current_tags.append("Priority.Faible")
            
            try:
                # Utiliser un iid basé sur l'ID du cas de test pour unicité si possible, sinon un fallback
                item_id = tc.get("ID du cas de test") 
                if not item_id or self.tree.exists(item_id): # Si l'ID est vide ou déjà utilisé
                    item_id = f"item_{i}_{int(time.time()*1000)}" # Fallback plus unique
                
                self.tree.insert("", tk.END, iid=item_id, values=values, tags=tuple(current_tags))
                item_inserted_count += 1
            except Exception as e_insert:
                print(f"[ERREUR GUI] Erreur lors de l'insertion du cas de test ID '{item_id}': {values}")
                print(f"[ERREUR GUI] Exception: {e_insert}")
        
        print(f"[DEBUG GUI] Nombre d'items réellement tentés pour insertion: {len(test_cases)}")
        print(f"[DEBUG GUI] Nombre d'items insérés avec succès (selon compteur): {item_inserted_count}")
        
        self.tree.update_idletasks()
        self.root.update_idletasks()

        if item_inserted_count > 0: self.export_csv_button.config(state=tk.NORMAL)
        else:
            self.export_csv_button.config(state=tk.DISABLED)
            if len(test_cases) > 0:
                 messagebox.showwarning("Affichage", "Des données ont été générées mais n'ont pas pu être affichées dans le tableau.")

    def update_gui_with_error(self, error_message): # ... (Identique)
        self.status_bar.config(text=f"Erreur : {error_message}"); messagebox.showerror("Erreur d'Analyse", error_message); self.export_csv_button.config(state=tk.DISABLED)

    def finalize_analysis_ui(self): # ... (Identique)
        self.analyze_button.config(state=tk.NORMAL); current_status = self.status_bar.cget("text")
        if self.generated_test_cases_data and "Erreur" not in current_status : self.export_csv_button.config(state=tk.NORMAL)
        else: self.export_csv_button.config(state=tk.DISABLED)
        if "Analyse de" in current_status: self.status_bar.config(text="Prêt. Analyse terminée (vérifiez les résultats).")
        elif not self.generated_test_cases_data and "Erreur" not in current_status: self.status_bar.config(text="Prêt. Aucune donnée pertinente trouvée ou générée.")
    
    def export_to_csv(self): # ... (Identique, avec delimiter=';')
        if not self.generated_test_cases_data: messagebox.showwarning("Exportation CSV", "Aucun cas de test à exporter."); return
        fieldnames = ["ID du cas de test", "Titre du cas de test", "Préconditions", "Étapes de test", "Données de test", "Résultat attendu", "Résultat obtenu", "Statut", "Priorité", "Commentaires"]
        filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")], title="Enregistrer les cas de test sous...")
        if not filepath: return
        try:
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';', extrasaction='ignore', quoting=csv.QUOTE_ALL)
                writer.writeheader()
                for test_case_data in self.generated_test_cases_data:
                    row_to_write = {key: test_case_data.get(key, "") for key in fieldnames}; writer.writerow(row_to_write)
            messagebox.showinfo("Exportation Réussie", f"Les cas de test ont été exportés avec succès dans :\n{filepath}"); self.status_bar.config(text=f"Exportation réussie vers {filepath}")
        except Exception as e:
            print(f"Erreur lors de l'exportation CSV : {e}"); messagebox.showerror("Erreur d'Exportation", f"Une erreur est survenue lors de l'exportation:\n{e}"); self.status_bar.config(text="Erreur lors de l'exportation CSV.")

# ----- Point d'entrée principal de l'application -----
if __name__ == "__main__":
    main_window = tk.Tk()
    app = TestGenApp(main_window)
    main_window.mainloop()
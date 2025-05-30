import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog # simpledialog pour saisir le résultat
import threading
import csv
import webbrowser
import sys
import json # Pour sauvegarder et charger les sessions de test
from datetime import datetime # Pour dater les résultats
import os # Pour créer un dossier de sauvegarde
# Imports cruciaux pour Selenium et BeautifulSoup
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By # AJOUTÉ POUR LA NOUVELLE FONCTIONNALITÉ

# --- FONCTION UTILITAIRE POUR AFFICHAGE CONSOLE SÛR ---
def safe_str_for_console(text_data):
    if not isinstance(text_data, str): text_data = str(text_data)
    console_encoding = sys.stdout.encoding if sys.stdout.encoding else 'utf-8'
    try: return text_data.encode(console_encoding, errors='replace').decode(console_encoding)
    except Exception: return text_data.encode('ascii', errors='replace').decode('ascii')

# --- FONCTIONS BACKEND ---
def get_locator_hint(element):
    # ... (Identique à la version précédente)
    if not element: return "Élément non trouvé"
    tag_name = element.name; el_id = element.get('id')
    if el_id: return f"XPath: //{tag_name}[@id='{el_id}']" # More specific XPath for ID
    el_name = element.get('name')
    if el_name: return f"Name: {el_name}"
    if tag_name in ['input', 'textarea']:
        el_placeholder = element.get('placeholder')
        if el_placeholder: return f"Placeholder: '{el_placeholder[:30]}...'"
        el_aria_label = element.get('aria-label')
        # Prefer XPath for aria-label if it's unique enough
        if el_aria_label: return f"XPath: //{tag_name}[@aria-label='{el_aria_label}']"
        el_title = element.get('title')
        if el_title: return f"Title: '{el_title[:30]}...'"
    if tag_name in ['button', 'a', 'input']: # Input can be a button
        el_text = element.get_text(strip=True)
        if el_text and len(el_text) < 50: # Text should be reasonably short for a locator
            clean_text = el_text.replace("'", "\\'") # Basic attempt to handle single quotes
            if "'" not in clean_text : return f"XPath: //{tag_name}[contains(text(),'{clean_text}')]" # More robust
            else: return f"Texte: '{el_text[:30]}...'" # Fallback if text is complex
        el_value = element.get('value')
        if el_value: return f"Value: '{el_value[:30]}...'"
        el_aria_label = element.get('aria-label')
        if el_aria_label: return f"Aria-label: '{el_aria_label[:30]}...'" # Fallback if not used in XPath above
    el_class = element.get('class')
    if el_class:
        first_class = el_class[0]
        # Ensure class name is simple enough for a basic XPath
        if first_class and not any(c in first_class for c in [' ',':',';']):
            return f"XPath: //{tag_name}[contains(@class,'{first_class}')]"
    return f"Tag: {tag_name}" # Least preferred

def recuperer_contenu_page_avec_selenium(url):
    # ... (Identique à la version précédente)
    print(f"Tentative de récupération de l'URL avec Selenium : {safe_str_for_console(url)}")
    driver = None
    try:
        options_chrome = webdriver.ChromeOptions(); options_chrome.add_argument('--headless'); options_chrome.add_argument('--disable-gpu'); options_chrome.add_argument('--log-level=3'); options_chrome.add_argument("--start-maximized"); options_chrome.add_argument('--window-size=1920,1080'); options_chrome.add_argument('--ignore-certificate-errors'); options_chrome.add_argument('--allow-running-insecure-content'); options_chrome.add_argument('--no-sandbox'); options_chrome.add_argument('--disable-dev-shm-usage'); options_chrome.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        service_chrome = ChromeService(ChromeDriverManager().install()); driver = webdriver.Chrome(service=service_chrome, options=options_chrome)
        driver.get(url); print(f"Page {safe_str_for_console(url)} en cours de chargement... Attente de 4 secondes."); time.sleep(4)
        page_source = driver.page_source; print(f"Contenu de la page récupéré (longueur: {len(page_source)} caractères).")
        return page_source
    except Exception as e: print(f"Erreur lors de la récupération de la page {safe_str_for_console(url)} avec Selenium : {safe_str_for_console(e)}"); return None
    finally:
        if driver: print("Fermeture du navigateur Selenium."); driver.quit()

def analyser_page_pour_fonctionnalites(html_content, url_page):
    # ... (Identique à la version précédente - assurez-vous que les appels à get_locator_hint sont corrects)
    print(f"\nDébut de l'analyse de la page : {safe_str_for_console(url_page)}.")
    fonctionnalites_retournees = { "url_page": url_page, "titre_page": "Pas de titre", "formulaires_connexion": [], "barres_recherche": [], "elements_panier": [], "menus_navigation": [], "connexions_sociales": [] }
    if not html_content: return fonctionnalites_retournees
    try: soup = BeautifulSoup(html_content, 'lxml')
    except Exception:
        try: soup = BeautifulSoup(html_content, 'html.parser')
        except Exception as e_parser: print(f"Erreur avec tous les parseurs: {safe_str_for_console(e_parser)}."); return fonctionnalites_retournees
    if soup.title and soup.title.string: fonctionnalites_retournees["titre_page"] = soup.title.string.strip()
    all_inputs_and_textareas = soup.find_all(['input', 'textarea']); all_buttons_and_inputs_on_page = soup.find_all(['button', 'input']);
    # --- Connexion ---
    champs_identifiants_trouves_login = []; possible_username_texts = ['user', 'login', 'email', 'mail', 'e-mail', 'identifier', 'account', 'pseudo', 'username', 'userid', 'identifiant', 'adresse électronique']
    for el in all_inputs_and_textareas:
        is_username_field = False; el_type = el.get('type', '').lower() if el.name == 'input' else 'textarea'
        if el_type not in ['text', 'email', 'tel', 'search', 'textarea', 'url']: continue
        el_name = el.get('name', '').lower(); el_placeholder = el.get('placeholder', '').lower(); el_id = el.get('id', '').lower(); el_aria_label = el.get('aria-label', '').lower()
        if any(term in el_name for term in possible_username_texts): is_username_field = True
        if not is_username_field and any(term in el_placeholder for term in possible_username_texts): is_username_field = True
        if not is_username_field and any(term in el_id for term in possible_username_texts): is_username_field = True
        if not is_username_field and any(term in el_aria_label for term in possible_username_texts): is_username_field = True
        if not is_username_field and el_id:
            label_for_el = soup.find('label', {'for': el_id})
            if label_for_el and label_for_el.string and any(term in label_for_el.string.lower() for term in possible_username_texts): is_username_field = True
        if not is_username_field:
            parent_label = el.find_parent('label')
            if parent_label and parent_label.string and any(term in parent_label.string.lower() for term in possible_username_texts): is_username_field = True
            elif parent_label and any(term in parent_label.get_text(strip=True).lower() for term in possible_username_texts): is_username_field = True
        if is_username_field and 'search' in el_type and not any(term in (el_name + el_placeholder + el_id + el_aria_label) for term in ['user', 'login', 'email', 'account']): is_username_field = False 
        if is_username_field: champs_identifiants_trouves_login.append(el)
    champs_mdp_trouves = soup.find_all('input', {'type': 'password'})
    boutons_soumission_login_trouves = []; possible_button_login_texts = ['log in', 'login', 'sign in', 'signin', 'connect', 'connexion', 'entrer', 'valider', 'ok', 'se connecter', 'continuer']
    for btn in all_buttons_and_inputs_on_page:
        btn_tag = btn.name.lower(); btn_type = btn.get('type', '').lower(); is_potential_submit = False
        if btn_tag == 'button' and btn_type in ['submit', 'button', '']: is_potential_submit = True
        elif btn_tag == 'input' and btn_type in ['submit', 'button', 'image']: is_potential_submit = True
        if is_potential_submit:
            btn_text = (btn.get_text(strip=True) or btn.get('value','') or btn.get('aria-label','')).lower(); btn_name = btn.get('name', '').lower(); btn_id = btn.get('id', '').lower()
            if any(term_search in btn_text for term_search in ['search', 'rechercher', 'loupe']): continue
            if any(term in btn_text for term in possible_button_login_texts) or any(term in btn_name for term in possible_button_login_texts) or any(term in btn_id for term in possible_button_login_texts) or (is_potential_submit and not btn_text and any(key in (btn_id+btn_name) for key in ['login','submit'])):
                boutons_soumission_login_trouves.append(btn)
    print(f"[Analyse Connexion] Éléments bruts: {len(champs_identifiants_trouves_login)} ID, {len(champs_mdp_trouves)} MDP, {len(boutons_soumission_login_trouves)} Boutons Login.")
    if champs_identifiants_trouves_login and champs_mdp_trouves and boutons_soumission_login_trouves:
        for idx, champ_mdp_iter in enumerate(champs_mdp_trouves):
            champ_id_associe = champs_identifiants_trouves_login[0]; bouton_associe = boutons_soumission_login_trouves[0]
            form_simule_details = {"id_formulaire_page": f"sim_login_mechanism_{idx+1}", "champ_identifiant": {"tag": champ_id_associe.name, "type": champ_id_associe.get('type', 'text') if champ_id_associe.name == 'input' else 'textarea', "name": champ_id_associe.get('name'), "id": champ_id_associe.get('id'), "placeholder": champ_id_associe.get('placeholder'), "locator_hint": get_locator_hint(champ_id_associe)}, "champ_mot_de_passe": {"tag": champ_mdp_iter.name, "type": champ_mdp_iter.get('type'), "name": champ_mdp_iter.get('name'), "id": champ_mdp_iter.get('id'), "placeholder": champ_mdp_iter.get('placeholder'), "locator_hint": get_locator_hint(champ_mdp_iter)}, "bouton_soumission": {"tag": bouton_associe.name, "type": bouton_associe.get('type'), "text": bouton_associe.get_text(strip=True) or bouton_associe.get('value') or bouton_associe.get('aria-label',''), "id": bouton_associe.get('id'), "name": bouton_associe.get('name'), "locator_hint": get_locator_hint(bouton_associe)}}
            fonctionnalites_retournees["formulaires_connexion"].append(form_simule_details)
    if not fonctionnalites_retournees["formulaires_connexion"]: print("[INFO] Aucun mécanisme de connexion (email/mdp) simulé n'a pu être assemblé.")
    # Connexions Sociales
    connexions_sociales_trouvees = []; services_sociaux_deja_ajoutes = set(); social_keywords = ['google', 'facebook', 'apple', 'twitter', 'github', 'linkedin', 'microsoft', 'amazon']; login_verb_keywords = ['sign in', 'signin', 'login', 'log in', 'continue', 'connect', 'connexion', 'connecter', 'continuer', 'avec']
    for element in soup.find_all(['button', 'a', 'div']):
        element_text_raw = element.get_text(strip=True); element_text_lower = element_text_raw.lower();
        element_id = element.get('id', '').lower(); element_class = " ".join(element.get('class', [])).lower(); element_aria_label = element.get('aria-label', '').lower(); element_title = element.get('title', '').lower()
        combined_text = " ".join([element_text_lower, element_id, element_class, element_aria_label, element_title]); identified_service = None; has_login_verb = any(verb in combined_text for verb in login_verb_keywords)
        if has_login_verb:
            for service in social_keywords:
                if service in combined_text: identified_service = service.capitalize(); break
        if identified_service and identified_service not in services_sociaux_deja_ajoutes:
            social_login_details = {"id_social_login": f"social_login_{identified_service.lower()}", "service": identified_service, "element_text": element_text_raw, "tag_name": element.name, "locator_hint": get_locator_hint(element)}
            connexions_sociales_trouvees.append(social_login_details); services_sociaux_deja_ajoutes.add(identified_service); 
            print(f"[INFO] Bouton de connexion sociale '{safe_str_for_console(identified_service)}' détecté ('{safe_str_for_console(social_login_details['element_text'])}').")
    fonctionnalites_retournees["connexions_sociales"] = connexions_sociales_trouvees
    if not connexions_sociales_trouvees: print("[INFO] Aucun bouton de connexion sociale unique n'a été détecté.")
    # Recherche
    barres_recherche_trouvees = []; possible_search_input_texts = ['search', 'query', 'q', 'recherche', 'keyword', 'motcle', 'keywords', 'requête', 'rechercher sur']; possible_search_button_texts = ['search', 'rechercher', 'go', 'find', 'trouver', 'ok', 'submit', 'loupe']
    champs_recherche_candidats = []
    for el in all_inputs_and_textareas:
        el_type = el.get('type', '').lower() if el.name == 'input' else 'textarea'; el_name = el.get('name', '').lower(); el_placeholder = el.get('placeholder', '').lower(); el_id = el.get('id', '').lower(); el_title = el.get('title','').lower(); el_aria_label = el.get('aria-label','').lower()
        is_search_field = False
        if any(term in el_name for term in possible_search_input_texts): is_search_field = True
        if not is_search_field and any(term in el_placeholder for term in possible_search_input_texts): is_search_field = True
        if not is_search_field and any(term in el_id for term in possible_search_input_texts): is_search_field = True
        if not is_search_field and any(term in el_title for term in possible_search_input_texts): is_search_field = True
        if not is_search_field and any(term in el_aria_label for term in possible_search_input_texts): is_search_field = True
        if is_search_field and el_type not in ['text', 'search', 'textarea', 'url', 'tel', 'email']: is_search_field = False
        if is_search_field: champs_recherche_candidats.append(el)
    boutons_recherche_candidats = []
    for btn in all_buttons_and_inputs_on_page:
        btn_tag = btn.name.lower(); btn_type = btn.get('type', '').lower(); is_potential_search_submit = False
        if btn_tag == 'button' and btn_type in ['submit', 'button', '']: is_potential_search_submit = True
        elif btn_tag == 'input' and btn_type in ['submit', 'button', 'image']: is_potential_search_submit = True
        if is_potential_search_submit:
            btn_text = (btn.get_text(strip=True) or btn.get('value','') or btn.get('aria-label','')).lower()
            if any(term in btn_text for term in possible_search_button_texts) or (not btn_text and btn_type == 'submit'): 
                boutons_recherche_candidats.append(btn)
    print(f"[Analyse Recherche - Pré-association] Candidats: {len(champs_recherche_candidats)} champ(s), {len(boutons_recherche_candidats)} bouton(s).")
    processed_search_buttons_assoc = set() 
    for search_field_candidate in champs_recherche_candidats:
        associated_button = None; parent_form = search_field_candidate.find_parent('form')
        if parent_form:
            for btn_in_form in parent_form.find_all(['button', 'input']):
                if btn_in_form in boutons_recherche_candidats and btn_in_form not in processed_search_buttons_assoc:
                    associated_button = btn_in_form; break
        if not associated_button:
            for btn_candidate in boutons_recherche_candidats:
                if btn_candidate not in processed_search_buttons_assoc and btn_candidate not in boutons_soumission_login_trouves: 
                    associated_button = btn_candidate; break
            if not associated_button and boutons_recherche_candidats:
                 for btn_candidate in boutons_recherche_candidats:
                     if btn_candidate not in processed_search_buttons_assoc:
                        associated_button = btn_candidate; break
        if associated_button:
            details_barre_recherche = {"id_barre_recherche": f"sim_searchbar_{len(barres_recherche_trouvees)+1}", "champ_recherche": {"tag": search_field_candidate.name, "type": search_field_candidate.get('type') if search_field_candidate.name == 'input' else 'textarea', "name": search_field_candidate.get('name'), "id": search_field_candidate.get('id'), "placeholder": search_field_candidate.get('placeholder'), "aria-label": search_field_candidate.get('aria-label'), "title": search_field_candidate.get('title'), "locator_hint": get_locator_hint(search_field_candidate)}, "bouton_recherche": {"tag": associated_button.name, "type": associated_button.get('type'), "text": associated_button.get_text(strip=True) or associated_button.get('value') or associated_button.get('aria-label'), "id": associated_button.get('id'), "name": associated_button.get('name'), "locator_hint": get_locator_hint(associated_button)}}
            barres_recherche_trouvees.append(details_barre_recherche); processed_search_buttons_assoc.add(associated_button); 
            print(f"[INFO] Barre de recherche simulée (associée) #{len(barres_recherche_trouvees)} construite pour le champ {safe_str_for_console(get_locator_hint(search_field_candidate))}.")
    fonctionnalites_retournees["barres_recherche"] = barres_recherche_trouvees
    if not barres_recherche_trouvees: print("[INFO] Aucune barre de recherche (avec bouton associé par proximité) n'a pu être assemblée.")
    # Panier
    elements_panier_trouves = []; possible_cart_texts_attributes = ['cart', 'panier', 'basket', 'caddie', 'sac', 'checkout', 'mon panier', 'votre panier', 'trolley']; possible_cart_icon_classes = ['fa-shopping-cart', 'fa-shopping-basket', 'fa-shopping-bag', 'cart-icon', 'icon-cart', 'shopping-cart', 'minicart']
    potential_cart_elements = soup.find_all(['a', 'button', 'span', 'div', 'i'])
    for el in potential_cart_elements:
        el_text_raw = el.get_text(strip=True); el_text = el_text_raw.lower(); el_href = el.get('href', '').lower(); el_id = el.get('id', '').lower(); el_class = " ".join(el.get('class', [])).lower(); el_aria_label = el.get('aria-label', '').lower(); el_title = el.get('title', '').lower()
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
                if added_el_detail["element_text"] == el_text_raw and added_el_detail.get("locator_hint") == get_locator_hint(el): 
                    already_added = True; break
            if not already_added:
                cart_el_details = {"id_panier_element": f"sim_cart_el_{len(elements_panier_trouves)+1}", "tag_name": el.name, "element_text": el_text_raw, "href": el.get('href') if el.name == 'a' else None, "attributes": { "id": el.get('id'), "class": el.get('class'), "aria-label": el.get('aria-label'), "title": el.get('title')}, "locator_hint": get_locator_hint(el)}
                elements_panier_trouves.append(cart_el_details); print(f"[INFO] Élément de panier simulé #{len(elements_panier_trouves)} ('{safe_str_for_console(cart_el_details['element_text'])}') construit.")
    fonctionnalites_retournees["elements_panier"] = elements_panier_trouves
    if not elements_panier_trouves: print("[INFO] Aucun élément de panier simulé n'a pu être assemblé.")
    # Navigation
    menus_navigation_trouves = []; nav_tags = soup.find_all('nav'); potential_menu_uls = soup.find_all('ul', {'role': ['menu', 'menubar', 'navigation', 'listbox', 'tree']}); common_menu_classes_ids = ['menu', 'nav', 'navbar', 'navigation', 'main-menu', 'nav-menu', 'top-menu', 'primary-menu', 'site-navigation']
    for ul_candidate in soup.find_all('ul'):
        current_id = ul_candidate.get('id', '').lower(); current_classes = " ".join(ul_candidate.get('class', [])).lower()
        if any(term in current_id for term in common_menu_classes_ids) or any(term in current_classes for term in common_menu_classes_ids):
            if ul_candidate not in potential_menu_uls: potential_menu_uls.append(ul_candidate)
    all_menu_containers = nav_tags + potential_menu_uls; 
    menu_item_id_counter = 0; processed_hrefs_in_menu = set()
    for container_idx, menu_container in enumerate(all_menu_containers):
        menu_links_in_container = []; list_items = menu_container.find_all('li', recursive=False) 
        temp_links = []
        if list_items:
            for li in list_items:
                link = li.find('a', href=True, recursive=False) 
                if not link:
                    span_child = li.find(['span', 'div'], recursive=False)
                    if span_child: link = span_child.find('a', href=True, recursive=False)
                if link: temp_links.append(link)
        if not temp_links:
            direct_links_in_container = menu_container.find_all('a', href=True, recursive=True)
            for dl in direct_links_in_container:
                parent_names = [p.name for p in dl.parents if p.name != 'body' and p != menu_container]
                if not any(p_name in ['p', 'footer', 'aside', 'address'] for p_name in parent_names):
                    temp_links.append(dl)
        unique_links_for_this_container = {}
        for link_candidate in temp_links:
            key = (link_candidate.get_text(strip=True), link_candidate.get('href'))
            if key[0] and key[1] and len(key[0]) < 100 : unique_links_for_this_container[key] = link_candidate
        menu_links_in_container = list(unique_links_for_this_container.values())
        if menu_links_in_container:
            current_menu_links = []
            for link in menu_links_in_container:
                link_text_raw = link.get_text(strip=True); link_href = link.get('href')
                if link_text_raw and link_href and not link_href.startswith(('#', 'javascript:')) and link_href not in processed_hrefs_in_menu:
                    menu_item_id_counter += 1
                    menu_item_details = {"id_menu_item": f"menu_item_{menu_item_id_counter}", "texte_lien": link_text_raw, "href": link_href, "tag_name": link.name, "parent_container_info": f"Menu Container #{container_idx+1} ({menu_container.name})", "locator_hint": get_locator_hint(link)}
                    current_menu_links.append(menu_item_details); processed_hrefs_in_menu.add(link_href)
            if current_menu_links: menus_navigation_trouves.extend(current_menu_links)
    fonctionnalites_retournees["menus_navigation"] = menus_navigation_trouves
    if not menus_navigation_trouves: print("[INFO] Aucun lien de menu significatif n'a été assemblé.")
    else: print(f"[INFO] Total de {len(menus_navigation_trouves)} liens de menu significatifs trouvés.")
    print(f"[INFO Fin Analyse] Connexion trad: {len(fonctionnalites_retournees['formulaires_connexion'])}, Social: {len(fonctionnalites_retournees['connexions_sociales'])}, Recherche: {len(fonctionnalites_retournees['barres_recherche'])}, Panier: {len(fonctionnalites_retournees['elements_panier'])}, Nav: {len(fonctionnalites_retournees['menus_navigation'])}")
    return fonctionnalites_retournees

def parse_locator_string(locator_str):
    """
    Parse une chaîne de locator_hint pour obtenir la stratégie By et la valeur.
    Exemple: "XPath: //button[@id='login']" -> (By.XPATH, "//button[@id='login']")
    Retourne (None, None) si le parsing échoue.
    """
    if not locator_str or ':' not in locator_str:
        return None, None
    
    parts = locator_str.split(':', 1)
    strategy_str = parts[0].strip().upper()
    locator_value = parts[1].strip()

    if strategy_str == "XPATH":
        return By.XPATH, locator_value
    elif strategy_str == "NAME":
        return By.NAME, locator_value
    elif strategy_str == "ID": 
        return By.ID, locator_value
    elif strategy_str == "CSS": 
        return By.CSS_SELECTOR, locator_value
    # Ajoutez d'autres stratégies si votre get_locator_hint les génère (ex: LINK_TEXT, CLASS_NAME)
    else:
        print(f"[AVERTISSEMENT] Stratégie de localisation non reconnue ou non supportée pour l'automatisation : {strategy_str}")
        return None, None

def apply_max_tests_filter(test_list, max_tests):
    # ... (Identique)
    if max_tests is not None and max_tests > 0 and len(test_list) > max_tests:
        return test_list[:max_tests]
    return test_list

def add_default_tracking_fields(test_case_dict):
    """Ajoute les champs de suivi par défaut à un cas de test."""
    test_case_dict["Statut"] = "Non Testé"
    test_case_dict["Résultat Obtenu"] = ""
    test_case_dict["Date Résultat"] = ""
    # Le champ ActionableElementLocator sera ajouté directement dans les générateurs si applicable
    return test_case_dict

def generer_cas_tests_connexion(form_details, url_page, base_id="CT_LOGIN", max_tests=None):
    cas_tests_potentiels = []
    champ_id_details = form_details.get("champ_identifiant", {}); champ_mdp_details = form_details.get("champ_mot_de_passe", {}); bouton_soumission_details = form_details.get("bouton_soumission", {})
    desc_identifiant = f"'{safe_str_for_console(champ_id_details.get('name') or champ_id_details.get('id') or champ_id_details.get('placeholder', 'identifiant'))}' (Indicateur: {safe_str_for_console(champ_id_details.get('locator_hint', 'N/A'))})"
    desc_mdp = f"'{safe_str_for_console(champ_mdp_details.get('name') or champ_mdp_details.get('id') or champ_mdp_details.get('placeholder', 'mot de passe'))}' (Indicateur: {safe_str_for_console(champ_mdp_details.get('locator_hint', 'N/A'))})"
    desc_bouton = f"'{safe_str_for_console(bouton_soumission_details.get('text') or 'soumission')}' (Indicateur: {safe_str_for_console(bouton_soumission_details.get('locator_hint', 'N/A'))})"
    precondition = f"L'utilisateur est sur la page {safe_str_for_console(url_page)} où un mécanisme de connexion ({safe_str_for_console(form_details.get('id_formulaire_page', 'N/A'))}) est identifié."
    
    actionable_locator = bouton_soumission_details.get('locator_hint')

    cas_tests_potentiels.append(add_default_tracking_fields({
        "ID du cas de test": f"{base_id}_VALID_001", 
        "Titre du cas de test": "Vérifier la connexion avec des identifiants valides", 
        "Préconditions": precondition, 
        "Étapes de test": (f"1. Entrer un nom d'utilisateur valide dans le champ {desc_identifiant}.\n2. Entrer un mot de passe valide dans le champ {desc_mdp}.\n3. Cliquer sur le bouton {desc_bouton}."), 
        "Données de test": "Nom d'utilisateur: [identifiant_valide]\nMot de passe: [mdp_valide]", 
        "Résultat attendu": "L'utilisateur est connecté avec succès et redirigé.", 
        "Priorité": "Élevée",
        "ActionableElementLocator": actionable_locator 
    }))
    cas_tests_potentiels.append(add_default_tracking_fields({
        "ID du cas de test": f"{base_id}_INVALID_PWD_002", 
        "Titre du cas de test": "Vérifier la connexion avec un mot de passe incorrect", 
        "Préconditions": precondition, 
        "Étapes de test": (f"1. Entrer un nom d'utilisateur valide dans le champ {desc_identifiant}.\n2. Entrer un mot de passe INVALIDE dans le champ {desc_mdp}.\n3. Cliquer sur le bouton {desc_bouton}."), 
        "Données de test": "Nom d'utilisateur: [identifiant_valide]\nMot de passe: [mdp_invalide]", 
        "Résultat attendu": "Message d'erreur affiché. Non connecté.", 
        "Priorité": "Élevée",
        "ActionableElementLocator": actionable_locator
    }))
    cas_tests_potentiels.append(add_default_tracking_fields({
        "ID du cas de test": f"{base_id}_EMPTY_FIELDS_003", 
        "Titre du cas de test": "Vérifier la connexion avec des champs vides", 
        "Préconditions": precondition, 
        "Étapes de test": (f"1. Laisser le champ {desc_identifiant} vide.\n2. Laisser le champ {desc_mdp} vide.\n3. Cliquer sur le bouton {desc_bouton}."), 
        "Données de test": "Nom d'utilisateur: \nMot de passe: ", 
        "Résultat attendu": "Messages d'erreur pour champs obligatoires ou connexion échouée.", 
        "Priorité": "Moyenne",
        "ActionableElementLocator": actionable_locator
    }))
    return apply_max_tests_filter(cas_tests_potentiels, max_tests)

def generer_cas_tests_social_login(social_login_details, url_page, base_id="CT_SOCIAL", max_tests=None):
    cas_tests_potentiels = []
    service_name = social_login_details.get("service", "Inconnu"); element_text_raw = social_login_details.get("element_text", f"bouton de connexion {service_name}"); locator_hint = social_login_details.get("locator_hint", "N/A")
    desc_element_social = f"'{safe_str_for_console(element_text_raw)}' (Service: {safe_str_for_console(service_name)}, Indicateur: {safe_str_for_console(locator_hint)})"
    precondition = f"L'utilisateur est sur la page {safe_str_for_console(url_page)} où un bouton de connexion sociale pour '{safe_str_for_console(service_name)}' est visible."
    
    cas_tests_potentiels.append(add_default_tracking_fields({
        "ID du cas de test": f"{base_id}_{service_name.upper()}_PRESENCE_001", 
        "Titre du cas de test": f"Connexion Sociale: Vérifier présence et cliquabilité du bouton '{safe_str_for_console(service_name)}'", 
        "Préconditions": f"L'utilisateur est sur une page proposant la connexion via {safe_str_for_console(service_name)}.", 
        "Étapes de test": f"1. Repérer le bouton de connexion {desc_element_social}.\n2. Vérifier qu'il est cliquable.", 
        "Données de test": "N/A", 
        "Résultat attendu": f"Le bouton de connexion via {safe_str_for_console(service_name)} est présent, visible et interactif.", 
        "Priorité": "Élevée",
        "ActionableElementLocator": locator_hint # Potentially clickable for presence
    }))
    cas_tests_potentiels.append(add_default_tracking_fields({
        "ID du cas de test": f"{base_id}_{service_name.upper()}_OAUTH_002", 
        "Titre du cas de test": f"Connexion Sociale: Vérifier l'initiation du flux d'authentification '{safe_str_for_console(service_name)}'", 
        "Préconditions": precondition, 
        "Étapes de test": f"1. Cliquer sur le bouton de connexion {desc_element_social}.", 
        "Données de test": "N/A", 
        "Résultat attendu": f"Le flux d'authentification pour {safe_str_for_console(service_name)} est initié.", 
        "Priorité": "Élevée",
        "ActionableElementLocator": locator_hint # This is the primary click action
    }))
    return apply_max_tests_filter(cas_tests_potentiels, max_tests)

def generer_cas_tests_recherche(search_bar_details, url_page, base_id="CT_SEARCH", max_tests=None):
    cas_tests_potentiels = []
    champ_recherche_details = search_bar_details.get("champ_recherche", {}); bouton_recherche_details = search_bar_details.get("bouton_recherche", {})
    desc_champ_recherche = f"'{safe_str_for_console(champ_recherche_details.get('name') or champ_recherche_details.get('id') or champ_recherche_details.get('placeholder', 'recherche'))}' (Indicateur: {safe_str_for_console(champ_recherche_details.get('locator_hint', 'N/A'))})"
    desc_bouton_recherche = f"'{safe_str_for_console(bouton_recherche_details.get('text') or 'recherche')}' (Indicateur: {safe_str_for_console(bouton_recherche_details.get('locator_hint', 'N/A'))})"
    precondition = f"L'utilisateur est sur la page {safe_str_for_console(url_page)} où une barre de recherche ({safe_str_for_console(search_bar_details.get('id_barre_recherche', 'N/A'))}) est identifiée."
    
    actionable_locator_search_button = bouton_recherche_details.get('locator_hint')

    cas_tests_potentiels.append(add_default_tracking_fields({
        "ID du cas de test": f"{base_id}_VALID_RESULTS_001", 
        "Titre du cas de test": "Vérifier la recherche avec un terme valide (résultats attendus)", 
        "Préconditions": precondition, 
        "Étapes de test": (f"1. Entrer un terme de recherche pertinent dans {desc_champ_recherche}.\n2. Cliquer sur le bouton {desc_bouton_recherche}."), 
        "Données de test": "Terme de recherche: [terme_valide_avec_resultats]", 
        "Résultat attendu": "Les résultats de recherche pertinents sont affichés.", 
        "Priorité": "Élevée",
        "ActionableElementLocator": actionable_locator_search_button
    }))
    cas_tests_potentiels.append(add_default_tracking_fields({
        "ID du cas de test": f"{base_id}_VALID_NO_RESULTS_002", 
        "Titre du cas de test": "Vérifier la recherche avec un terme valide (aucun résultat attendu)", 
        "Préconditions": precondition, 
        "Étapes de test": (f"1. Entrer un terme de recherche peu commun dans {desc_champ_recherche}.\n2. Cliquer sur le bouton {desc_bouton_recherche}."), 
        "Données de test": "Terme de recherche: [terme_valide_sans_resultats]", 
        "Résultat attendu": "Un message indique qu'aucun résultat n'a été trouvé.", 
        "Priorité": "Moyenne",
        "ActionableElementLocator": actionable_locator_search_button
    }))
    cas_tests_potentiels.append(add_default_tracking_fields({
        "ID du cas de test": f"{base_id}_EMPTY_003", 
        "Titre du cas de test": "Vérifier la recherche avec un champ vide", 
        "Préconditions": precondition, 
        "Étapes de test": (f"1. Laisser le champ {desc_champ_recherche} vide.\n2. Cliquer sur le bouton {desc_bouton_recherche}."), 
        "Données de test": "Terme de recherche: ", 
        "Résultat attendu": "Aucune action de recherche ou message d'erreur.", 
        "Priorité": "Moyenne",
        "ActionableElementLocator": actionable_locator_search_button
    }))
    return apply_max_tests_filter(cas_tests_potentiels, max_tests)

def generer_cas_tests_panier(cart_element_details, url_page, base_id="CT_CART", max_tests=None):
    cas_tests_potentiels = []
    element_texte_raw = cart_element_details.get("element_text", "l'élément du panier"); locator_hint_panier = cart_element_details.get("locator_hint", "N/A")
    desc_element_panier = f"'{safe_str_for_console(element_texte_raw)}' (Indicateur: {safe_str_for_console(locator_hint_panier)})"
    precondition = f"L'utilisateur est sur la page {safe_str_for_console(url_page)} où un élément de panier ({desc_element_panier}) est visible."
    
    cas_tests_potentiels.append(add_default_tracking_fields({
        "ID du cas de test": f"{base_id}_ACCESS_VIEW_001", 
        "Titre du cas de test": f"Vérifier l'accès et l'affichage du panier via {desc_element_panier}", 
        "Préconditions": precondition, "Étapes de test": f"1. Cliquer sur l'élément du panier {desc_element_panier}.", 
        "Données de test": "N/A - Panier supposé vide.", 
        "Résultat attendu": "La page du panier s'affiche. Si vide, un message l'indique.", 
        "Priorité": "Élevée",
        "ActionableElementLocator": locator_hint_panier
    }))
    cas_tests_potentiels.append(add_default_tracking_fields({
        "ID du cas de test": f"{base_id}_PRESENCE_CLICKABLE_002", 
        "Titre du cas de test": f"Vérifier la présence et la cliquabilité de {desc_element_panier}", 
        "Préconditions": f"L'utilisateur est sur une page où {desc_element_panier} devrait être visible (ex: {safe_str_for_console(url_page)}).", 
        "Étapes de test": (f"1. Repérer {desc_element_panier}.\n2. Vérifier qu'il est cliquable."), 
        "Données de test": "N/A", 
        "Résultat attendu": "L'élément du panier est présent, visible et interactif.", 
        "Priorité": "Moyenne",
        "ActionableElementLocator": locator_hint_panier 
    }))
    return apply_max_tests_filter(cas_tests_potentiels, max_tests)

def generer_cas_tests_navigation(nav_link_details, url_page, base_id="CT_NAV", max_tests=None):
    cas_tests_potentiels = []
    link_text_raw = nav_link_details.get("texte_lien", "Lien inconnu"); link_href = nav_link_details.get("href", "#"); locator_hint_nav = nav_link_details.get("locator_hint", "N/A")
    desc_lien_nav = f"'{safe_str_for_console(link_text_raw)}' (Cible: {safe_str_for_console(link_href)}, Indicateur: {safe_str_for_console(locator_hint_nav)})"
    precondition_base = f"L'utilisateur est sur la page {safe_str_for_console(url_page)}."
    id_suffix = nav_link_details.get('id_menu_item','item').replace('menu_item_','')

    cas_tests_potentiels.append(add_default_tracking_fields({
        "ID du cas de test": f"{base_id}_{id_suffix}_PRESENCE_001", 
        "Titre du cas de test": f"Navigation: Vérifier présence/visibilité du lien {desc_lien_nav}", 
        "Préconditions": precondition_base, 
        "Étapes de test": f"1. Rechercher visuellement le lien de menu {desc_lien_nav}.", 
        "Données de test": "N/A", 
        "Résultat attendu": f"Le lien de menu {desc_lien_nav} est présent, visible et correctement libellé.", 
        "Priorité": "Élevée",
        "ActionableElementLocator": locator_hint_nav # For presence check, could be used to highlight
    }))
    cas_tests_potentiels.append(add_default_tracking_fields({
        "ID du cas de test": f"{base_id}_{id_suffix}_CLICK_002", 
        "Titre du cas de test": f"Navigation: Vérifier clic et redirection du lien {desc_lien_nav}", 
        "Préconditions": f"{precondition_base} Le lien {desc_lien_nav} est visible.", 
        "Étapes de test": f"1. Cliquer sur le lien de menu {desc_lien_nav}.", 
        "Données de test": "N/A", 
        "Résultat attendu": (f"Redirection vers une page valide ({safe_str_for_console(link_href)}). Page chargée sans erreur."), 
        "Priorité": "Élevée",
        "ActionableElementLocator": locator_hint_nav # This is the primary click action
    }))
    return apply_max_tests_filter(cas_tests_potentiels, max_tests)


# --- Classe de l'Application GUI ---
class TestGenApp:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("TestCasesGen v0.3") # Version
        self.root.geometry("1250x900") 
        
        self.current_url_analyzed = "" 
        self.SAVE_DIR = "test_sessions" 
        if not os.path.exists(self.SAVE_DIR):
            os.makedirs(self.SAVE_DIR)

        style = ttk.Style()
        try: style.theme_use('clam')
        except tk.TclError: print("Thème ttk 'clam' non trouvé.")

        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        self.file_menu = tk.Menu(menubar, tearoff=0) 
        menubar.add_cascade(label="Fichier", menu=self.file_menu)
        self.file_menu.add_command(label="Charger une Session de Test", command=self.charger_session)
        self.file_menu.add_command(label="Sauvegarder la Session de Test", command=self.sauvegarder_session, state=tk.DISABLED) 
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exporter en CSV", command=self.export_to_csv, state=tk.DISABLED) 

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Aide", menu=help_menu)
        help_menu.add_command(label="À propos du développeur", command=self.show_developer_info)
        help_menu.add_separator()
        help_menu.add_command(label="Signaler un bug", command=self.report_bug)

        url_frame = ttk.LabelFrame(self.root, text="URL du Site Web"); url_frame.pack(padx=10, pady=5, fill="x")
        ttk.Label(url_frame, text="URL:").pack(side=tk.LEFT, padx=5)
        self.url_entry = ttk.Entry(url_frame, width=60); self.url_entry.pack(side=tk.LEFT, padx=5, expand=True, fill="x")
        self.url_entry.insert(0, "https://www.demoblaze.com/")
        self.analyze_button = ttk.Button(url_frame, text="Analyser et Générer Nouveaux Tests", command=self.start_analysis_thread); self.analyze_button.pack(side=tk.LEFT, padx=(5,0), pady=5)
        
        config_outer_frame = ttk.LabelFrame(self.root, text="Options de Génération des Cas de Test"); config_outer_frame.pack(padx=10, pady=5, fill="x")
        config_frame = ttk.Frame(config_outer_frame); config_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(config_frame, text="Max Tests / Élément (0=tous):").grid(row=0, column=0, padx=(0,5), pady=2, sticky="w")
        self.global_max_tests_var = tk.StringVar(value="0"); self.global_max_tests_entry = ttk.Entry(config_frame, textvariable=self.global_max_tests_var, width=5); self.global_max_tests_entry.grid(row=0, column=1, padx=5, pady=2, sticky="w")
        ttk.Label(config_frame, text="Max Liens Nav. à Traiter (0=tous):").grid(row=0, column=2, padx=(10,5), pady=2, sticky="w")
        self.max_nav_links_to_process_var = tk.StringVar(value="10"); self.max_nav_links_to_process_entry = ttk.Entry(config_frame, textvariable=self.max_nav_links_to_process_var, width=5); self.max_nav_links_to_process_entry.grid(row=0, column=3, padx=5, pady=2, sticky="w")
        ttk.Label(config_frame, text="Max Tests Spécifiques (0=global):").grid(row=1, column=0, columnspan=4, padx=(0,5), pady=(5,2), sticky="w")
        row_spec = 2; self.specific_filters_vars = {}
        for idx, (feature_key, feature_label) in enumerate([("login", "Connexion:"), ("search", "Recherche:"), ("cart", "Panier:"), ("nav_link", "Par Lien Nav.:")]):
            r, c_offset = divmod(idx, 2)
            ttk.Label(config_frame, text=feature_label).grid(row=row_spec + r, column=c_offset*2, padx=(20 if c_offset==0 else 10, 5), pady=2, sticky="w")
            var = tk.StringVar(value="0"); entry = ttk.Entry(config_frame, textvariable=var, width=5); entry.grid(row=row_spec + r, column=c_offset*2 + 1, padx=5, pady=2, sticky="w")
            self.specific_filters_vars[feature_key] = var
        
        main_content_frame = ttk.Frame(self.root); main_content_frame.pack(padx=10, pady=5, expand=True, fill="both")
        results_frame = ttk.LabelFrame(main_content_frame, text="Cas de Test Générés et Suivi"); results_frame.pack(pady=(0,5), expand=True, fill="both")
        
        columns = ("id_test", "titre", "preconditions", "etapes", "donnees", "attendu", "priorite", "statut", "resultat_obtenu", "date_resultat")
        self.tree = ttk.Treeview(results_frame, columns=columns, show="headings")
        
        self.tree.tag_configure("Priority.Élevée", foreground="red") 
        self.tree.tag_configure("Priority.Moyenne", foreground="orange")
        self.tree.tag_configure("Priority.Faible", foreground="green")
        self.tree.tag_configure("Status.Passé", background="#DFF0D8") 
        self.tree.tag_configure("Status.Échoué", background="#F2DEDE") 
        self.tree.tag_configure("Status.Non Testé", background="white")

        col_config = { 
            "id_test": ("ID Cas Test", 100), "titre": ("Titre Cas Test", 180), 
            "preconditions": ("Préconditions", 150), "etapes": ("Étapes de Test", 250), 
            "donnees": ("Données Test", 120), "attendu": ("Résultat Attendu", 180), 
            "priorite": ("Priorité", 70),
            "statut": ("Statut", 80), 
            "resultat_obtenu": ("Résultat Obtenu", 150),
            "date_resultat": ("Date Résultat", 120)
        }
        for col_id, (col_text, col_width) in col_config.items():
            self.tree.heading(col_id, text=col_text)
            self.tree.column(col_id, width=col_width, anchor=tk.W, minwidth=50) 
        
        vsb = ttk.Scrollbar(results_frame, orient="vertical", command=self.tree.yview); hsb = ttk.Scrollbar(results_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set); vsb.pack(side='right', fill='y'); hsb.pack(side='bottom', fill='x')
        self.tree.pack(expand=True, fill='both')

        self.tree_context_menu = tk.Menu(self.root, tearoff=0)
        self.tree_context_menu.add_command(label="Marquer comme Passé", command=self.marquer_statut_passe)
        self.tree_context_menu.add_command(label="Marquer comme Échoué", command=self.marquer_statut_echoue)
        self.tree_context_menu.add_command(label="Saisir Résultat Obtenu", command=self.saisir_resultat_obtenu)
        self.tree_context_menu.add_separator()
        self.tree_context_menu.add_command(label="Exécuter Clic (Automatisé)", command=self.execute_selected_click_auto) # MODIFIÉ ICI
        self.tree_context_menu.add_separator()
        self.tree_context_menu.add_command(label="Effacer Statut/Résultat", command=self.effacer_statut_resultat)
        self.tree.bind("<Button-3>", self.show_tree_context_menu)
        
        self.status_bar = ttk.Label(self.root, text="Prêt. Développé par Chihi Amine.", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(5,0))
        self.generated_test_cases_data = []
        self.selected_tree_item_iid = None 

    def show_tree_context_menu(self, event):
        item_iid = self.tree.identify_row(event.y)
        if item_iid:
            self.tree.selection_set(item_iid)
            self.selected_tree_item_iid = item_iid 
            
            # Activer/Désactiver l'option "Exécuter Clic (Automatisé)"
            tc_index, tc_data = self._get_test_case_by_iid(self.selected_tree_item_iid)
            if tc_data and tc_data.get("ActionableElementLocator"):
                actionable_locator_str = tc_data.get("ActionableElementLocator")
                strategy, locator_value = parse_locator_string(actionable_locator_str)
                if strategy and locator_value:
                    self.tree_context_menu.entryconfig("Exécuter Clic (Automatisé)", state=tk.NORMAL)
                else:
                    self.tree_context_menu.entryconfig("Exécuter Clic (Automatisé)", state=tk.DISABLED)
            else:
                self.tree_context_menu.entryconfig("Exécuter Clic (Automatisé)", state=tk.DISABLED)

            self.tree_context_menu.post(event.x_root, event.y_root)
        else:
            self.selected_tree_item_iid = None

    def _get_test_case_by_iid(self, iid_to_find):
        for index, tc in enumerate(self.generated_test_cases_data):
            if tc.get("_tree_iid_") == iid_to_find: 
                return index, tc
        return None, None

    def _refresh_treeview_item(self, test_case_id_value): # Utilisé par effacer_statut_resultat
        """Rafraîchit un item spécifique dans le Treeview basé sur son ID de cas de test."""
        tc_index_to_refresh = -1
        item_iid_to_refresh = None

        for index, tc_candidate in enumerate(self.generated_test_cases_data):
            if tc_candidate.get("ID du cas de test") == test_case_id_value:
                tc_index_to_refresh = index
                item_iid_to_refresh = tc_candidate.get("_tree_iid_")
                break
        
        if tc_index_to_refresh != -1 and item_iid_to_refresh and self.tree.exists(item_iid_to_refresh):
            tc = self.generated_test_cases_data[tc_index_to_refresh]
            self.tree.item(item_iid_to_refresh, values=(
                safe_str_for_console(tc.get("ID du cas de test", "")), 
                safe_str_for_console(tc.get("Titre du cas de test", "")), 
                safe_str_for_console(tc.get("Préconditions", "")),
                safe_str_for_console(tc.get("Étapes de test", "")), 
                safe_str_for_console(tc.get("Données de test", "")), 
                safe_str_for_console(tc.get("Résultat attendu", "")),
                safe_str_for_console(tc.get("Priorité", "")),
                safe_str_for_console(tc.get("Statut", "")),
                safe_str_for_console(tc.get("Résultat Obtenu", "")),
                safe_str_for_console(tc.get("Date Résultat", ""))
            ))
            self.apply_row_coloring(item_iid_to_refresh, tc.get("Priorité", ""), tc.get("Statut", ""))
        else:
            print(f"Avertissement: Impossible de rafraîchir l'item avec ID {test_case_id_value}, non trouvé ou iid manquant.")


    def _update_treeview_item_and_data(self, tc_index, new_status, new_resultat_obtenu=None):
        if tc_index is None or tc_index >= len(self.generated_test_cases_data):
            return

        tc = self.generated_test_cases_data[tc_index]
        item_iid = tc.get("_tree_iid_")

        if not item_iid or not self.tree.exists(item_iid):
            print(f"AVERTISSEMENT: iid '{item_iid}' non trouvé dans le Treeview pour le cas de test à l'index {tc_index}.")
            return

        tc["Statut"] = new_status
        if new_status != "Non Testé" or (new_resultat_obtenu and new_resultat_obtenu.strip() != ""):
             tc["Date Résultat"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else: # Si on remet à Non Testé et pas de résultat, on efface la date
             tc["Date Résultat"] = ""

        if new_resultat_obtenu is not None:
            tc["Résultat Obtenu"] = new_resultat_obtenu
        
        self.tree.item(item_iid, values=(
            safe_str_for_console(tc.get("ID du cas de test", "")), 
            safe_str_for_console(tc.get("Titre du cas de test", "")), 
            safe_str_for_console(tc.get("Préconditions", "")),
            safe_str_for_console(tc.get("Étapes de test", "")), 
            safe_str_for_console(tc.get("Données de test", "")), 
            safe_str_for_console(tc.get("Résultat attendu", "")),
            safe_str_for_console(tc.get("Priorité", "")),
            safe_str_for_console(tc.get("Statut", "")),
            safe_str_for_console(tc.get("Résultat Obtenu", "")),
            safe_str_for_console(tc.get("Date Résultat", ""))
        ))
        self.apply_row_coloring(item_iid, tc.get("Priorité", ""), tc.get("Statut", ""))
        print(f"Cas de test '{tc.get('ID du cas de test')}' mis à jour: Statut='{tc['Statut']}', Résultat='{tc['Résultat Obtenu']}'")

    def marquer_statut_passe(self):
        if self.selected_tree_item_iid:
            tc_index, tc_data = self._get_test_case_by_iid(self.selected_tree_item_iid)
            if tc_index is not None:
                resultat_actuel = tc_data.get("Résultat Obtenu", "")
                if not resultat_actuel or tc_data.get("Statut") == "Échoué": # Si vide ou était échoué, on met un message par défaut
                    resultat_actuel = "Test passé manuellement."
                self._update_treeview_item_and_data(tc_index, "Passé", resultat_actuel)


    def marquer_statut_echoue(self):
        if self.selected_tree_item_iid:
            tc_index, tc_data = self._get_test_case_by_iid(self.selected_tree_item_iid)
            if tc_index is not None:
                resultat = simpledialog.askstring("Résultat Obtenu", "Veuillez entrer le résultat obtenu pour l'échec :", 
                                                  initialvalue=tc_data.get("Résultat Obtenu",""), parent=self.root)
                if resultat is not None: # Si l'utilisateur clique sur "OK", même avec un champ vide
                    self._update_treeview_item_and_data(tc_index, "Échoué", resultat)
                # Si l'utilisateur clique sur "Annuler", resultat est None, on ne fait rien.

    def saisir_resultat_obtenu(self):
        if self.selected_tree_item_iid:
            tc_index, tc_data = self._get_test_case_by_iid(self.selected_tree_item_iid)
            if tc_index is not None:
                resultat = simpledialog.askstring("Saisir Résultat Obtenu", "Entrez le résultat obtenu :",
                                                 initialvalue=tc_data.get("Résultat Obtenu",""), parent=self.root)
                if resultat is not None: 
                    current_status = tc_data.get("Statut", "Non Testé")
                    self._update_treeview_item_and_data(tc_index, current_status, resultat)

    def effacer_statut_resultat(self):
        if self.selected_tree_item_iid:
            tc_index, tc_data = self._get_test_case_by_iid(self.selected_tree_item_iid)
            if tc_index is not None:
                self._update_treeview_item_and_data(tc_index, "Non Testé", "") # Efface aussi la date via _update_treeview_item_and_data
                # Pas besoin d'appeler _refresh_treeview_item ici, _update_treeview_item_and_data fait le travail.


    def execute_selected_click_auto(self):
        if not self.selected_tree_item_iid:
            messagebox.showwarning("Aucune sélection", "Veuillez sélectionner un cas de test dans le tableau.")
            return

        tc_index, tc_data = self._get_test_case_by_iid(self.selected_tree_item_iid)
        if tc_index is None or tc_data is None:
            messagebox.showerror("Erreur", "Cas de test non trouvé dans les données internes.")
            return

        actionable_locator_str = tc_data.get("ActionableElementLocator")
        if not actionable_locator_str:
            messagebox.showinfo("Non applicable", "Ce cas de test n'a pas de localisateur actionnable défini pour l'automatisation du clic.")
            return

        strategy, locator_value = parse_locator_string(actionable_locator_str)

        if not strategy or not locator_value:
            messagebox.showerror("Erreur de Localisateur", f"Impossible de parser le localisateur : '{actionable_locator_str}'. Vérifiez son format (ex: 'XPath: //valeur', 'Name: nom').")
            return

        if not self.current_url_analyzed:
            messagebox.showerror("URL Manquante", "Aucune URL n'est actuellement définie pour cette session (chargez ou analysez une page).")
            return
        
        if not messagebox.askyesno("Confirmer Exécution Automatisée", 
                                   f"Ceci va ouvrir un navigateur Chrome, naviguer vers :\n{self.current_url_analyzed}\n\net tenter de cliquer sur l'élément identifié par :\nStratégie: {strategy}\nLocalisateur: {locator_value}\n\nLe statut du test sera mis à jour. Voulez-vous continuer ?"):
            return

        self.status_bar.config(text=f"Exécution auto du clic pour {tc_data.get('ID du cas de test')}...")
        self.root.update_idletasks()

        driver = None
        new_status = "Échoué" # Par défaut
        result_message = "L'action n'a pas pu être complétée."

        try:
            options_chrome_auto = webdriver.ChromeOptions()
            options_chrome_auto.add_argument("--start-maximized")
            options_chrome_auto.add_argument('--log-level=3')
            # Assurez-vous que le navigateur est visible, donc pas d'option --headless ici.
            # Vous pouvez ajouter d'autres options si nécessaire, comme ignorer les erreurs de certificat.
            # options_chrome_auto.add_argument('--ignore-certificate-errors')

            service_chrome_auto = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service_chrome_auto, options=options_chrome_auto)
            
            driver.get(self.current_url_analyzed)
            driver.implicitly_wait(10) 

            print(f"[AUTO-CLIC] Recherche de l'élément : Stratégie='{strategy}', Valeur='{locator_value}'")
            element_to_click = driver.find_element(strategy, locator_value)
            
            # Optionnel: scroll et petite attente si l'élément n'est pas immédiatement interactif
            # driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element_to_click)
            # time.sleep(1) 

            if not element_to_click.is_displayed():
                result_message = f"Élément trouvé mais non visible. Le clic peut échouer."
                print(f"[AUTO-CLIC AVERTISSEMENT] {result_message}")
                # Laisser Selenium tenter le clic, il pourrait gérer certains cas.
            elif not element_to_click.is_enabled():
                result_message = f"Élément trouvé mais désactivé. Clic impossible."
                print(f"[AUTO-CLIC ERREUR] {result_message}")
                # new_status reste "Échoué"
            else:
                element_to_click.click()
                print("[AUTO-CLIC] Clic exécuté par Selenium.")
                time.sleep(2) # Laisser le temps de voir l'effet du clic. Pour des tests robustes, utiliser des attentes explicites.
                new_status = "Passé"
                result_message = "Clic exécuté avec succès via Selenium."
            
        except webdriver.common.exceptions.NoSuchElementException:
            result_message = f"Erreur Selenium: Élément non trouvé ({strategy}: {locator_value})"
            print(f"[AUTO-CLIC ERREUR] {result_message}")
        except webdriver.common.exceptions.ElementNotInteractableException:
            result_message = f"Erreur Selenium: Élément trouvé mais non interactif ({strategy}: {locator_value}). Il peut être masqué ou désactivé."
            print(f"[AUTO-CLIC ERREUR] {result_message}")
        except webdriver.common.exceptions.TimeoutException:
            result_message = f"Erreur Selenium: Timeout lors de l'attente ou du chargement de page."
            print(f"[AUTO-CLIC ERREUR] {result_message}")
        except Exception as e:
            result_message = f"Erreur inattendue lors de l'auto-clic: {safe_str_for_console(str(e))}"
            print(f"[AUTO-CLIC ERREUR MAJEURE] {result_message}")
            import traceback
            traceback.print_exc()
        finally:
            if driver:
                try:
                    driver.quit()
                    print("[AUTO-CLIC] Navigateur Selenium fermé.")
                except Exception as e_quit:
                    print(f"[AUTO-CLIC ERREUR] Erreur lors de la fermeture du driver: {e_quit}")
            
            self._update_treeview_item_and_data(tc_index, new_status, result_message)
            final_status_message = f"Clic auto pour {tc_data.get('ID du cas de test')}: {new_status}."
            self.status_bar.config(text=final_status_message)
            
            if new_status == "Passé":
                messagebox.showinfo("Exécution Automatisée Réussie", f"{final_status_message}\n\nRésultat: {result_message}")
            else:
                messagebox.showerror("Échec de l'Exécution Automatisée", f"{final_status_message}\n\nRésultat: {result_message}")


    def apply_row_coloring(self, item_id, priority, status):
        # ... (Identique)
        tags_to_apply = []
        if priority == "Élevée": tags_to_apply.append("Priority.Élevée")
        elif priority == "Moyenne": tags_to_apply.append("Priority.Moyenne")
        elif priority == "Faible": tags_to_apply.append("Priority.Faible")

        if status == "Passé": tags_to_apply.append("Status.Passé")
        elif status == "Échoué": tags_to_apply.append("Status.Échoué")
        else: tags_to_apply.append("Status.Non Testé")
        
        try:
            if self.tree.exists(item_id):
                self.tree.item(item_id, tags=tuple(tags_to_apply))
            else:
                print(f"Tentative d'appliquer des tags à un item inexistant : {item_id}")
        except tk.TclError as e:
            print(f"Erreur Tcl lors de l'application des tags à {item_id}: {e}")

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
        except Exception as e: messagebox.showerror("Erreur", f"Impossible d'ouvrir le client de messagerie.\nErreur: {safe_str_for_console(e)}\nEmail: amine.chihi@hotmail.fr")
    
    def get_config_value(self, tk_var, default_value=None): # ... (Identique)
        val_str = ""; 
        try:
            val_str = tk_var.get()
            if not val_str: return default_value
            val_int = int(val_str)
            if val_int < 0: return default_value # Allow 0
            return val_int
        except ValueError:
            if val_str: messagebox.showwarning("Configuration Invalide", f"La valeur '{safe_str_for_console(val_str)}' pour un filtre n'est pas un nombre entier valide. Le filtre sera ignoré ou la valeur globale/par défaut sera utilisée.")
            print(f"Valeur de configuration invalide (non-numérique): '{safe_str_for_console(val_str)}'. Utilisation de la valeur par défaut: {default_value}.")
            return default_value
        except Exception as e: 
            print(f"Erreur inattendue lors de la lecture de la configuration Tkinter ({safe_str_for_console(tk_var)}): {safe_str_for_console(e)}. Utilisation de la valeur par défaut: {default_value}.")
            return default_value

    def start_analysis_thread(self): # ... (Identique)
        self.current_url_analyzed = self.url_entry.get(); 
        if not self.current_url_analyzed or not (self.current_url_analyzed.startswith("http://") or self.current_url_analyzed.startswith("https://")):
            messagebox.showerror("URL Invalide", "Veuillez entrer une URL valide."); return
        try:
            self.g_max_tc = self.get_config_value(self.global_max_tests_var) 
            self.g_max_nav_links_to_process = self.get_config_value(self.max_nav_links_to_process_var)
            self.s_login_max_tc = self.get_config_value(self.specific_filters_vars["login"], default_value=self.g_max_tc)
            self.s_search_max_tc = self.get_config_value(self.specific_filters_vars["search"], default_value=self.g_max_tc)
            self.s_cart_max_tc = self.get_config_value(self.specific_filters_vars["cart"], default_value=self.g_max_tc)
            self.s_nav_link_max_tc = self.get_config_value(self.specific_filters_vars["nav_link"], default_value=self.g_max_tc)
            print("-" * 30 + "\nValeurs de configuration des filtres ACTIVES pour cette analyse:") 
            print(f"  Limite Globale Max Tests / Élément: {self.g_max_tc if self.g_max_tc is not None else 'Tous (par défaut du générateur)'}") 
            print(f"  Max Liens Nav. à Traiter: {self.g_max_nav_links_to_process if self.g_max_nav_links_to_process is not None else 'Tous'}")
            print(f"  Max Tests pour Connexion: {self.s_login_max_tc if self.s_login_max_tc is not None else 'Global/Tous'}")
            print(f"  Max Tests pour Recherche: {self.s_search_max_tc if self.s_search_max_tc is not None else 'Global/Tous'}")
            print(f"  Max Tests pour Panier: {self.s_cart_max_tc if self.s_cart_max_tc is not None else 'Global/Tous'}")
            print(f"  Max Tests par Lien de Nav.: {self.s_nav_link_max_tc if self.s_nav_link_max_tc is not None else 'Global/Tous'}")
            print("-" * 30)
        except KeyError as e_key: messagebox.showerror("Erreur de Configuration Interne", f"Clé de filtre spécifique manquante : {e_key}"); self.analyze_button.config(state=tk.NORMAL); return
        except Exception as e_conf: messagebox.showerror("Erreur de Configuration", f"Erreur imprévue lors de la lecture des options de filtrage: {e_conf}"); self.analyze_button.config(state=tk.NORMAL); return
        self.analyze_button.config(state=tk.DISABLED); self.file_menu.entryconfig("Sauvegarder la Session de Test", state=tk.DISABLED); self.file_menu.entryconfig("Exporter en CSV", state=tk.DISABLED)
        self.status_bar.config(text=f"Analyse de {self.current_url_analyzed} en cours...")
        self.tree.delete(*self.tree.get_children()); self.generated_test_cases_data = []
        thread = threading.Thread(target=self.run_analysis, args=(self.current_url_analyzed,)); thread.daemon = True; thread.start()

    def run_analysis(self, url): # ... (Identique)
        try:
            print(f"Lancement de l'analyse pour l'URL : {safe_str_for_console(url)}")
            contenu_html = recuperer_contenu_page_avec_selenium(url)
            all_test_cases_for_url = []
            if contenu_html:
                fonctionnalites = analyser_page_pour_fonctionnalites(contenu_html, url)
                if fonctionnalites.get("formulaires_connexion"):
                    for i, form_data in enumerate(fonctionnalites["formulaires_connexion"]):
                        all_test_cases_for_url.extend(generer_cas_tests_connexion(form_data, fonctionnalites["url_page"], base_id=f"CT_LOGIN_MEC_{i+1}", max_tests=self.s_login_max_tc))
                if fonctionnalites.get("connexions_sociales"):
                    for i, social_data in enumerate(fonctionnalites["connexions_sociales"]):
                        all_test_cases_for_url.extend(generer_cas_tests_social_login(social_data, fonctionnalites["url_page"], base_id=f"CT_SOCIAL_{social_data.get('service','').upper()}_{i+1}", max_tests=self.s_login_max_tc)) # Utiliser s_login_max_tc pour les logins sociaux aussi, ou un filtre dédié
                if fonctionnalites.get("barres_recherche"):
                    for i, search_data in enumerate(fonctionnalites["barres_recherche"]):
                        all_test_cases_for_url.extend(generer_cas_tests_recherche(search_data, fonctionnalites["url_page"], base_id=f"CT_SEARCH_BAR_{i+1}", max_tests=self.s_search_max_tc))
                if fonctionnalites.get("elements_panier"):
                    for i, cart_data in enumerate(fonctionnalites["elements_panier"]):
                        all_test_cases_for_url.extend(generer_cas_tests_panier(cart_data, fonctionnalites["url_page"], base_id=f"CT_CART_EL_{i+1}", max_tests=self.s_cart_max_tc))
                if fonctionnalites.get("menus_navigation"): 
                    liens_nav_a_traiter = fonctionnalites["menus_navigation"]
                    if self.g_max_nav_links_to_process is not None and self.g_max_nav_links_to_process > 0 and len(liens_nav_a_traiter) > self.g_max_nav_links_to_process: # Ajout > 0
                        print(f"[INFO] Limitation du nombre de liens de navigation traités à {self.g_max_nav_links_to_process} sur {len(liens_nav_a_traiter)} trouvés.")
                        liens_nav_a_traiter = liens_nav_a_traiter[:self.g_max_nav_links_to_process]
                    for i, nav_link_data in enumerate(liens_nav_a_traiter):
                        all_test_cases_for_url.extend(generer_cas_tests_navigation(nav_link_data, fonctionnalites["url_page"], base_id=f"CT_NAV_LINK_{nav_link_data.get('id_menu_item','').replace('menu_item_','')}", max_tests=self.s_nav_link_max_tc))
                self.root.after(0, self.update_gui_with_results, all_test_cases_for_url, fonctionnalites.get('titre_page', 'Titre inconnu'), True) 
            else:
                self.root.after(0, self.update_gui_with_error, f"Impossible de récupérer le contenu de {safe_str_for_console(url)}.")
        except Exception as e:
            print(f"Erreur majeure pendant l'analyse : {safe_str_for_console(e)}"); import traceback; traceback.print_exc()
            self.root.after(0, self.update_gui_with_error, f"Erreur d'analyse : {safe_str_for_console(e)}")
        finally:
            self.root.after(0, self.finalize_analysis_ui)
            
    def update_gui_with_results(self, test_cases, page_title, is_new_analysis=False):
        self.status_bar.config(text=f"Analyse terminée: {safe_str_for_console(page_title)}. {len(test_cases)} cas de test affichés.")
        if not test_cases and is_new_analysis : 
             messagebox.showinfo("Résultats", "Aucun cas de test pertinent n'a pu être généré pour cette analyse.")
        elif not test_cases and not is_new_analysis: 
             messagebox.showinfo("Résultats", "Aucun cas de test dans la session chargée.")
        
        if is_new_analysis or not self.generated_test_cases_data: 
            self.tree.delete(*self.tree.get_children())

        self.generated_test_cases_data = test_cases 
        
        item_inserted_count = 0
        for i, tc in enumerate(self.generated_test_cases_data): 
            values = (
                safe_str_for_console(tc.get("ID du cas de test", "")), safe_str_for_console(tc.get("Titre du cas de test", "")), 
                safe_str_for_console(tc.get("Préconditions", "")), safe_str_for_console(tc.get("Étapes de test", "")), 
                safe_str_for_console(tc.get("Données de test", "")), safe_str_for_console(tc.get("Résultat attendu", "")),
                safe_str_for_console(tc.get("Priorité", "")),
                safe_str_for_console(tc.get("Statut", "Non Testé")),      
                safe_str_for_console(tc.get("Résultat Obtenu", "")), 
                safe_str_for_console(tc.get("Date Résultat", ""))    
            )
            priority_value = tc.get("Priorité", ""); status_value = tc.get("Statut", "Non Testé"); current_tags = [] 
            if priority_value == "Élevée": current_tags.append("Priority.Élevée")
            elif priority_value == "Moyenne": current_tags.append("Priority.Moyenne")
            elif priority_value == "Faible": current_tags.append("Priority.Faible")
            if status_value == "Passé": current_tags.append("Status.Passé")
            elif status_value == "Échoué": current_tags.append("Status.Échoué")
            else: current_tags.append("Status.Non Testé")
            try:
                item_id_from_tc = tc.get("ID du cas de test") 
                # Gérer l'iid pour les nouvelles analyses et le chargement
                item_iid_to_use = tc.get("_tree_iid_")
                if not item_iid_to_use or self.tree.exists(item_iid_to_use) and not is_new_analysis: # Si iid existe déjà ET qu'on ne fait pas une nouvelle analyse (ex: bug potentiel de re-insertion)
                    # S'il n'y a pas d'iid (chargement d'une ancienne session) OU si c'est une nouvelle analyse, on génère/stocke
                    item_iid_to_use = f"iid_{item_id_from_tc}_{i}_{int(time.time()*1000)}" # Plus unique
                
                if is_new_analysis or not tc.get("_tree_iid_"): # Stocker l'iid si nouvelle analyse ou si non existant (chargement)
                     tc["_tree_iid_"] = item_iid_to_use


                self.tree.insert("", tk.END, iid=item_iid_to_use, values=values, tags=tuple(current_tags))
                item_inserted_count += 1
            except Exception as e_insert: print(f"[ERREUR GUI] Erreur lors de l'insertion du cas de test ID '{safe_str_for_console(item_id_from_tc)}': {safe_str_for_console(values)}\n[ERREUR GUI] Exception: {safe_str_for_console(e_insert)}")
        
        self.tree.update_idletasks(); self.root.update_idletasks()
        if item_inserted_count > 0: 
            self.file_menu.entryconfig("Sauvegarder la Session de Test", state=tk.NORMAL)
            self.file_menu.entryconfig("Exporter en CSV", state=tk.NORMAL)
        else:
            self.file_menu.entryconfig("Sauvegarder la Session de Test", state=tk.DISABLED)
            self.file_menu.entryconfig("Exporter en CSV", state=tk.DISABLED)
            if len(self.generated_test_cases_data) > 0 : messagebox.showwarning("Affichage", "Des données ont été préparées mais n'ont pas pu être affichées.")

    def update_gui_with_error(self, error_message): # ... (Identique)
        safe_error_message = safe_str_for_console(error_message)
        self.status_bar.config(text=f"Erreur : {safe_error_message}"); 
        messagebox.showerror("Erreur d'Analyse", safe_error_message); 
        self.file_menu.entryconfig("Sauvegarder la Session de Test", state=tk.DISABLED)
        self.file_menu.entryconfig("Exporter en CSV", state=tk.DISABLED)

    def finalize_analysis_ui(self): # ... (Identique)
        self.analyze_button.config(state=tk.NORMAL); current_status = self.status_bar.cget("text")
        if self.generated_test_cases_data and "Erreur" not in current_status : 
            self.file_menu.entryconfig("Sauvegarder la Session de Test", state=tk.NORMAL)
            self.file_menu.entryconfig("Exporter en CSV", state=tk.NORMAL)
        else: 
            self.file_menu.entryconfig("Sauvegarder la Session de Test", state=tk.DISABLED)
            self.file_menu.entryconfig("Exporter en CSV", state=tk.DISABLED)
        if "Analyse de" in current_status and "en cours" not in current_status: self.status_bar.config(text="Prêt. Analyse terminée (vérifiez les résultats).")
        elif not self.generated_test_cases_data and "Erreur" not in current_status: self.status_bar.config(text="Prêt. Aucune donnée pertinente trouvée ou générée.")
    
    def sauvegarder_session(self): # MODIFIÉ pour inclure l'URL
        if not self.generated_test_cases_data:
            messagebox.showwarning("Sauvegarde", "Aucun cas de test à sauvegarder.")
            return

        url_part = self.current_url_analyzed.split('//')[-1].replace('/', '_').replace(':', '_').replace('?','_').replace('=','_').replace('.','_')
        url_part = "".join(c if c.isalnum() or c in ['_'] else '_' for c in url_part)[:50] # Nettoyage plus strict
        
        suggested_filename = f"session_{url_part}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        
        filepath = filedialog.asksaveasfilename(
            initialdir=self.SAVE_DIR, initialfile=suggested_filename,
            defaultextension=".json", filetypes=[("Fichiers JSON", "*.json"), ("Tous", "*.*")],
            title="Sauvegarder la session de test"
        )
        if not filepath: return

        try:
            # Préparer les données pour la sauvegarde, s'assurer que _tree_iid_ est bien géré
            # Il est préférable de ne pas sauvegarder _tree_iid_ car il est spécifique à la session GUI
            data_to_save = []
            for tc in self.generated_test_cases_data:
                tc_copy = tc.copy()
                if "_tree_iid_" in tc_copy:
                    del tc_copy["_tree_iid_"] # Ne pas sauvegarder l'iid interne du Treeview
                data_to_save.append(tc_copy)

            session_data = {
                "version_outil": "0.3", # Pour la compatibilité future
                "url_analysee": self.current_url_analyzed, 
                "date_sauvegarde": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "cas_de_test": data_to_save 
            }
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("Sauvegarde Réussie", f"Session sauvegardée dans:\n{filepath}")
            self.status_bar.config(text=f"Session sauvegardée : {filepath}")
        except Exception as e:
            messagebox.showerror("Erreur de Sauvegarde", f"Impossible de sauvegarder:\n{safe_str_for_console(e)}")

    def charger_session(self):
        filepath = filedialog.askopenfilename(
            initialdir=self.SAVE_DIR, defaultextension=".json",
            filetypes=[("Fichiers JSON", "*.json"), ("Tous les fichiers", "*.*")],
            title="Charger une session de test"
        )
        if not filepath: return

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            loaded_url = session_data.get("url_analysee", "")
            loaded_tests = session_data.get("cas_de_test", [])

            # Assurer que les champs par défaut sont présents si le fichier est d'une ancienne version
            for tc in loaded_tests:
                if "Statut" not in tc: tc["Statut"] = "Non Testé"
                if "Résultat Obtenu" not in tc: tc["Résultat Obtenu"] = ""
                if "Date Résultat" not in tc: tc["Date Résultat"] = ""
                # ActionableElementLocator peut être absent des anciennes sauvegardes

            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, loaded_url)
            self.current_url_analyzed = loaded_url

            self.tree.delete(*self.tree.get_children()) 
            self.generated_test_cases_data = loaded_tests 

            self.update_gui_with_results(self.generated_test_cases_data, 
                                         f"Session chargée ({len(loaded_tests)} tests)", # Titre plus concis
                                         is_new_analysis=False) 
            
            messagebox.showinfo("Chargement Réussi", f"Session chargée depuis:\n{filepath}")
            self.status_bar.config(text=f"Session chargée : {filepath}")
            
            if self.generated_test_cases_data:
                self.file_menu.entryconfig("Sauvegarder la Session de Test", state=tk.NORMAL)
                self.file_menu.entryconfig("Exporter en CSV", state=tk.NORMAL)
            else:
                self.file_menu.entryconfig("Sauvegarder la Session de Test", state=tk.DISABLED)
                self.file_menu.entryconfig("Exporter en CSV", state=tk.DISABLED)

        except FileNotFoundError: messagebox.showerror("Erreur", "Fichier non trouvé.")
        except json.JSONDecodeError: messagebox.showerror("Erreur", "Fichier JSON invalide ou corrompu.")
        except Exception as e:
            messagebox.showerror("Erreur de Chargement", f"Impossible de charger la session:\n{safe_str_for_console(e)}")
            import traceback
            traceback.print_exc()

    def export_to_csv(self): # ... (Identique)
        if not self.generated_test_cases_data: messagebox.showwarning("Exportation CSV", "Aucun cas de test à exporter."); return
        # Inclure ActionableElementLocator si on veut l'exporter, sinon le laisser hors des fieldnames.
        fieldnames = ["ID du cas de test", "Titre du cas de test", "Préconditions", "Étapes de test", 
                      "Données de test", "Résultat attendu", "Priorité", "Statut", 
                      "Résultat Obtenu", "Date Résultat", "Commentaires", "ActionableElementLocator"]
        filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")], title="Enregistrer les cas de test sous...")
        if not filepath: return
        try:
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile: # utf-8-sig pour Excel
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';', extrasaction='ignore', quoting=csv.QUOTE_ALL)
                writer.writeheader()
                for test_case_data in self.generated_test_cases_data:
                    row_to_write = {key: safe_str_for_console(test_case_data.get(key, "")) for key in fieldnames}
                    writer.writerow(row_to_write)
            messagebox.showinfo("Exportation Réussie", f"Les cas de test ont été exportés avec succès dans :\n{filepath}"); self.status_bar.config(text=f"Exportation réussie vers {filepath}")
        except Exception as e:
            print(f"Erreur lors de l'exportation CSV : {e}"); messagebox.showerror("Erreur d'Exportation", f"Une erreur est survenue lors de l'exportation:\n{safe_str_for_console(e)}"); self.status_bar.config(text="Erreur lors de l'exportation CSV.")


# ----- Point d'entrée principal de l'application -----
if __name__ == "__main__":
    main_window = tk.Tk()
    app = TestGenApp(main_window)
    main_window.mainloop()
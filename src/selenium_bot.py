from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
import time
import logging
import random
import re

logging.basicConfig(level=logging.INFO)


class GladiatusBot:
    EXPEDITION_LOCATIONS = {
        "grimwood": 0,
        "pirate harbour": 1,
        "misty mountains": 2,
        "wolf cave": 3,
        "ancient temple": 4,
        "barbarian village": 5,
        "bandit camp": 6,
        "voodoo temple": 0,
        "bridge": 1,
        "blood cave": 2,
        "lost harbour": 3,
        "umpokta tribe": 4,
        "caravan": 5,
        "mesoai-oasis": 6,
    }
    DUNGEON_LOCATIONS = EXPEDITION_LOCATIONS

    def __init__(self, headless=True, timeout=15):
        options = Options()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, timeout)

    def _click_element(self, by, value, timeout=10):
        for attempt in range(3):
            try:
                el = WebDriverWait(self.driver, timeout).until(EC.element_to_be_clickable((by, value)))
                el.click()
                return True
            except StaleElementReferenceException:
                time.sleep(0.3)
                continue
            except Exception:
                time.sleep(0.3)
                continue
        return False

    def wait_for_page_ready(self, timeout=10):
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            return True
        except Exception:
            return False

    def _wait_for_condition(self, predicate, timeout=10, poll_interval=0.3):
        end = time.time() + timeout
        while time.time() < end:
            try:
                if predicate():
                    return True
            except Exception:
                pass
            time.sleep(poll_interval)
        return False

    def _wait_for_ui_settle(self, timeout=8):
        self.wait_for_page_ready(timeout)
        time.sleep(0.25)
        self.close_overlays()
        return self.wait_for_page_ready(3)

    def _safe_click(self, element):
        try:
            element.click()
            return True
        except Exception:
            try:
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except Exception:
                return False

    def _wait_for_page_context(self, expected_elements=None, url_keywords=None, timeout=10, poll_interval=0.3):
        expected_elements = expected_elements or []
        url_keywords = url_keywords or []

        def matches():
            self.wait_for_page_ready(3)
            current_url = (self.driver.current_url or "").lower()
            if any(keyword.lower() in current_url for keyword in url_keywords):
                return True

            for by, value in expected_elements:
                elements = self.driver.find_elements(by, value)
                if any(el.is_displayed() for el in elements):
                    return True
            return False

        if not self._wait_for_condition(matches, timeout=timeout, poll_interval=poll_interval):
            return False

        self._wait_for_ui_settle()
        return True

    def login(self, base_url, username, password):
        driver = self.driver
        driver.get(base_url)
        self.wait_for_page_ready(8)
        
        # Close cookie banner if present
        try:
            cookie_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept')]")))
            cookie_btn.click()
            self.wait_for_page_ready(3)
        except Exception:
            pass
        
        # Click on "Log in" tab (first tab in tabsList)
        if not self._click_element(By.CSS_SELECTOR, "#loginRegisterTabs .tabsList li:first-child", timeout=8):
            logging.error("Failed to click login tab")
            return False
        
        # Try multiple selectors for login form and inputs
        user_candidates = [
            (By.NAME, "email"),
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.ID, "email"),
        ]
        pass_candidates = [
            (By.NAME, "password"),
            (By.CSS_SELECTOR, "input[type='password']"),
            (By.ID, "password"),
        ]
        
        # Wait for inputs to be clickable
        user_el = None
        pass_el = None
        for by, value in user_candidates:
            try:
                user_el = self.wait.until(EC.element_to_be_clickable((by, value)))
                break
            except Exception:
                continue
        
        for by, value in pass_candidates:
            try:
                pass_el = self.wait.until(EC.element_to_be_clickable((by, value)))
                break
            except Exception:
                continue

        if not user_el or not pass_el:
            logging.error("Could not find email or password input fields")
            return False

        try:
            # Debug: log the values being used
            logging.info(f"Attempting login with username: {username}")
            logging.info(f"Password: {password}")
            
            # Click email field and type using send_keys (simulates real keyboard input)
            user_el.click()
            time.sleep(0.15)
            # Select all and delete first
            user_el.send_keys(Keys.CONTROL + 'a')
            time.sleep(0.05)
            user_el.send_keys(Keys.DELETE)
            time.sleep(0.05)
            user_el.send_keys(username)
            time.sleep(0.15)
            
            pass_el.click()
            time.sleep(0.15)
            pass_el.send_keys(Keys.CONTROL + 'a')
            time.sleep(0.05)
            pass_el.send_keys(Keys.DELETE)
            time.sleep(0.05)
            pass_el.send_keys(password)
            time.sleep(0.15)

            submit_candidates = [
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.XPATH, "//button[contains(text(), 'Log')]"),
                (By.XPATH, "//button[contains(text(), 'Login')]"),
            ]
            submit_btn = None
            for by, value in submit_candidates:
                try:
                    submit_btn = self.wait.until(EC.element_to_be_clickable((by, value)))
                    break
                except Exception:
                    continue
            
            if submit_btn:
                submit_btn.click()
            else:
                pass_el.submit()

            self.wait_for_page_ready(8)
            return True
        except Exception as e:
            logging.error(f"Login failed: {e}")
            return False

    def close_overlays(self):
        closed_any = False
        selectors = [
            (By.XPATH, "//a[contains(@onclick,'MAX_simplepop') or normalize-space(text())='x']"),
            (By.XPATH, "//button[contains(@onclick,'MAX_simplepop') or contains(normalize-space(.),'Close') or normalize-space(.)='x']"),
            (By.CSS_SELECTOR, ".openX_int_closeButton a"),
            (By.XPATH, "//div[contains(@class,'openX_interstitial')]//a[contains(@onclick,'close') or normalize-space(text())='x']"),
            (By.CSS_SELECTOR, "#blackoutDialognotification .blackoutDialog_buttons input[type='submit']"),
            (By.CSS_SELECTOR, "#blackoutDialognotification #linknotification"),
            (By.CSS_SELECTOR, "#blackoutDialognotification #linkcancelnotification"),
            (By.CSS_SELECTOR, "#blackoutDialogbod #linkbod"),
            (By.CSS_SELECTOR, "#blackoutDialogLoginBonus #linkLoginBonus"),
            (By.CSS_SELECTOR, "#blackoutDialogLoginBonus .loginbonus_buttons input[type='button']"),
            (By.XPATH, "//div[@id='blackoutDialogLoginBonus']//input[@type='button' and contains(@value,'Bonus')]"),
        ]
        for _ in range(2):
            for by, value in selectors:
                try:
                    elements = self.driver.find_elements(by, value)
                    for el in elements:
                        if el.is_displayed() and el.is_enabled():
                            try:
                                el.click()
                                closed_any = True
                                time.sleep(0.2)
                            except Exception:
                                continue
                except Exception:
                    continue
            time.sleep(0.2)
        return closed_any

    def _switch_to_new_tab(self, old_handles, timeout=6):
        start = time.time()
        while time.time() - start < timeout:
            handles = self.driver.window_handles
            if len(handles) > len(old_handles):
                for handle in handles:
                    if handle not in old_handles:
                        self.driver.switch_to.window(handle)
                        self.wait_for_page_ready(8)
                        return True
            time.sleep(0.2)
        return False

    def _wait_for_expedition_ui(self, timeout=12, poll_interval=0.5):
        start = time.time()
        while time.time() - start < timeout:
            try:
                if self._has_expedition_ui():
                    return True
                txt_els = self.driver.find_elements(By.ID, "cooldown_bar_text_expedition")
                if txt_els and any('go to' in (txt.text or '').strip().lower() for txt in txt_els):
                    return True
            except Exception:
                pass
            time.sleep(poll_interval)
        return False

    def _wait_for_dungeon_attack_elements(self, timeout=10, poll_interval=0.5):
        start = time.time()
        while time.time() - start < timeout:
            try:
                candidates = self.driver.find_elements(By.XPATH, "//*[contains(@onclick, 'startFight(')]")
                if not candidates:
                    candidates = self.driver.find_elements(By.CSS_SELECTOR, "img[src*='combatloc.gif'], a[href*='startFight'], button[onclick*='startFight']")
                visible = [el for el in candidates if el.is_displayed() and el.is_enabled()]
                if visible:
                    return visible
            except Exception:
                pass
            time.sleep(poll_interval)
        return []

    def _wait_for_post_attack_navigation(self, previous_url, logger_callback=None, timeout=15, poll_interval=0.5):
        start = time.time()
        while time.time() - start < timeout:
            try:
                self._wait_for_ui_settle(timeout=5)
                current_url = self.driver.current_url
                if current_url != previous_url:
                    if logger_callback:
                        logger_callback("Attack navigation completed.")
                    return True
            except Exception:
                pass
            time.sleep(poll_interval)
        if logger_callback:
            logger_callback("Post-attack page load wait timed out.")
        return False

    def _wait_for_circus_rows(self, timeout=10, poll_interval=0.5):
        start = time.time()
        while time.time() - start < timeout:
            try:
                rows = self.driver.find_elements(By.CSS_SELECTOR, "#own3 tr, table#own3 tr, table[name='own3'] tr")
                if rows:
                    return rows
            except Exception:
                pass
            time.sleep(poll_interval)
        return []

    def _parse_number_from_text(self, text):
        if not text:
            return None
        digits = ''.join(ch for ch in text if ch.isdigit())
        try:
            return int(digits) if digits else None
        except Exception:
            return None

    def click_last_played_button(self):
        candidates = [
            (By.XPATH, "//button[normalize-space()='Last Played']"),
            (By.XPATH, "//a[normalize-space()='Last Played']"),
            (By.XPATH, "//button[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'last played')]"),
            (By.XPATH, "//a[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'last played')]"),
        ]

        prior_handles = self.driver.window_handles
        for by, value in candidates:
            try:
                elements = self.driver.find_elements(by, value)
                for el in elements:
                    if el.is_displayed() and el.is_enabled():
                        try:
                            if not self._safe_click(el):
                                continue
                            if self._switch_to_new_tab(prior_handles):
                                self.close_overlays()
                                return True
                            return self._wait_for_ui_settle(timeout=6)
                        except Exception:
                            continue
            except Exception:
                continue
        return False

    def ensure_game_tab(self, timeout=3):
        """Switch to a window/tab that looks like the game (has expedition UI).
        Returns True if switched or current tab already looks correct."""
        try:
            # Quick check current
            if self._has_expedition_ui():
                return True

            start = time.time()
            for handle in self.driver.window_handles:
                try:
                    self.driver.switch_to.window(handle)
                    if self._has_expedition_ui():
                        return True
                except Exception:
                    continue
                if time.time() - start > timeout:
                    break
            return False
        except Exception:
            return False

    def _has_expedition_ui(self):
        try:
            # presence of expedition attempts or expedition buttons
            if self.driver.find_elements(By.CSS_SELECTOR, "#expeditionpoints_value, #expeditionpoints_value_point, button.expedition_button"):
                return True
            return False
        except Exception:
            return False

    def get_expedition_attempts(self):
        """Returns (current, maximum) attempt counts or (None, None) if not found."""
        try:
            # Try split form: two spans
            try:
                cur_el = self.driver.find_element(By.ID, "expeditionpoints_value_point")
                max_el = self.driver.find_element(By.ID, "expeditionpoints_value_pointmax")
                cur = int(cur_el.text.strip())
                mx = int(max_el.text.strip())
                return cur, mx
            except Exception:
                pass

            # Try single element like '23 / 24'
            try:
                el = self.driver.find_element(By.ID, "expeditionpoints_value")
                txt = el.text.strip()
                if "/" in txt:
                    parts = txt.split("/")
                    cur = int(parts[0].strip())
                    mx = int(parts[1].strip())
                    return cur, mx
            except Exception:
                pass

            return None, None
        except Exception:
            return None, None

    def get_hp_status(self):
        """Return current/max HP and percent — fresh read from the header HP bar."""
        try:
            hp = self.driver.execute_script(
                """
                var result = {current: null, max: null, percent: null};
                var bar = document.getElementById('header_values_hp_bar');
                var pctEl = document.getElementById('header_values_hp_percent');
                if (bar) {
                    var v = bar.getAttribute('data-value');
                    var m = bar.getAttribute('data-max-value');
                    if (v && m) {
                        result.current = parseInt(v, 10);
                        result.max = parseInt(m, 10);
                        if (result.max) {
                            result.percent = Math.round(result.current * 100 / result.max);
                        }
                    }
                    var style = bar.getAttribute('style') || '';
                    var wm = style.match(/width:\\s*(\\d+(?:\\.\\d+)?)\\s*%/);
                    if (wm) {
                        var wp = Math.round(parseFloat(wm[1]));
                        if (result.percent === null || wp > result.percent) {
                            result.percent = wp;
                        }
                    }
                }
                if (pctEl) {
                    var txt = (pctEl.textContent || pctEl.innerText || '').replace('%', '').trim();
                    var tp = parseInt(txt, 10);
                    if (!isNaN(tp)) {
                        if (result.percent === null || tp > result.percent) {
                            result.percent = tp;
                        }
                    }
                }
                return result;
                """
            )
            if hp and hp.get("percent") is not None:
                return {
                    "current": hp.get("current"),
                    "max": hp.get("max"),
                    "percent": int(hp["percent"]),
                }
        except Exception:
            pass

        try:
            bar = self.driver.find_element(By.ID, "header_values_hp_bar")
            value = bar.get_attribute("data-value")
            maximum = bar.get_attribute("data-max-value")
            percent = None
            current = None
            max_hp = None

            if value and maximum:
                current = int(value)
                max_hp = int(maximum)
                percent = int(round(current * 100 / max_hp)) if max_hp else None

            style = bar.get_attribute("style") or ""
            width_match = re.search(r"width:\s*(\d+(?:\.\d+)?)\s*%", style)
            if width_match:
                width_percent = int(round(float(width_match.group(1))))
                if percent is None or width_percent > percent:
                    percent = width_percent

            percent_el = self.driver.find_element(By.ID, "header_values_hp_percent")
            percent_text = (percent_el.text or percent_el.get_attribute("textContent") or "").strip().replace("%", "")
            if percent_text.isdigit():
                text_percent = int(percent_text)
                if percent is None or text_percent > percent:
                    percent = text_percent

            return {"current": current, "max": max_hp, "percent": percent}
        except Exception:
            return {"current": None, "max": None, "percent": None}

    def _format_hp_log(self, hp):
        if not hp or hp.get("percent") is None:
            return "?"
        if hp.get("current") is not None and hp.get("max") is not None:
            return f"{hp['current']}/{hp['max']} ({hp['percent']}%)"
        return f"{hp['percent']}%"

    def _refresh_overview_for_hp(self, logger_callback=None):
        """Re-open Overview so the header HP bar reloads from the server."""
        try:
            candidates = [
                (By.CSS_SELECTOR, "a.menuitem[title='Overview']"),
                (By.XPATH, "//a[contains(@class,'menuitem') and contains(@href,'mod=overview')]"),
            ]
            for by, value in candidates:
                if self._click_element(by, value, timeout=3):
                    self.wait_for_page_ready(5)
                    time.sleep(0.5)
                    if logger_callback:
                        logger_callback("Overview refreshed — re-reading HP bar")
                    return True
        except Exception:
            pass
        return False

    def _wait_for_hp_after_refill(self, before_percent, min_hp_percent, timeout=10, logger_callback=None):
        """Poll the HP bar after using a pot; refresh Overview if the bar looks stale."""
        end = time.time() + timeout
        latest = self.get_hp_status()

        while time.time() < end:
            latest = self.get_hp_status()
            pct = latest.get("percent") if latest else None
            if pct is not None:
                if pct > min_hp_percent:
                    return latest, True
                if before_percent is not None and pct > before_percent:
                    return latest, True
            time.sleep(0.5)

        self._refresh_overview_for_hp(logger_callback)
        for _ in range(8):
            latest = self.get_hp_status()
            pct = latest.get("percent") if latest else None
            if logger_callback and pct is not None:
                logger_callback(f"HP bar re-read: {self._format_hp_log(latest)}")
            if pct is not None:
                if pct > min_hp_percent:
                    return latest, True
                if before_percent is not None and pct > before_percent:
                    return latest, True
            time.sleep(0.5)

        return latest, False

    def is_expedition_ready(self):
        """Return True if the expedition cooldown bar indicates readiness."""
        try:
            try:
                txt_el = self.driver.find_elements(By.ID, "cooldown_bar_text_expedition")
                if txt_el:
                    txt = txt_el[0].text.strip().lower()
                    if txt.startswith('go to') or 'go to expedition' in txt:
                        return True
            except Exception:
                pass

            try:
                fill_el = self.driver.find_elements(By.ID, "cooldown_bar_fill_expedition")
                if fill_el:
                    cls = fill_el[0].get_attribute('class') or ''
                    if 'cooldown_bar_fill_ready' in cls:
                        return True
            except Exception:
                pass

            return False
        except Exception:
            return False

    def is_dungeon_ready(self):
        """Return True if the dungeon cooldown bar indicates readiness."""
        try:
            try:
                txt_el = self.driver.find_elements(By.ID, "cooldown_bar_text_dungeon")
                if txt_el:
                    txt = txt_el[0].text.strip().lower()
                    if txt.startswith('go to') or 'go to dungeon' in txt:
                        return True
            except Exception:
                pass

            try:
                fill_el = self.driver.find_elements(By.ID, "cooldown_bar_fill_dungeon")
                if fill_el:
                    cls = fill_el[0].get_attribute('class') or ''
                    if 'cooldown_bar_fill_ready' in cls:
                        return True
            except Exception:
                pass

            return False
        except Exception:
            return False

    def _legacy_open_dungeon_and_random_attack(self, logger_callback=None, max_retries=3):
        """Open the dungeon page (via cooldown bar link) and click a random minimap attack.
        Returns True if an attack element was clicked."""
        try:
            if logger_callback:
                logger_callback("Ensuring game tab is active for dungeon...")

            if not self.ensure_game_tab():
                if logger_callback:
                    logger_callback("Could not find game tab for dungeon")
                return False

            # Try to find the dungeon cooldown link and click it
            try:
                link = None
                candidates = [
                    (By.CSS_SELECTOR, "#cooldown_bar_dungeon a.cooldown_bar_link"),
                    (By.CSS_SELECTOR, "a.cooldown_bar_link[href*='mod=dungeon']"),
                    (By.CSS_SELECTOR, "a.cooldown_bar_link[href*='loc=1']"),
                ]
                for by, sel in candidates:
                    try:
                        els = self.driver.find_elements(by, sel)
                        for e in els:
                            if e.is_displayed() and e.is_enabled():
                                link = e
                                break
                        if link:
                            break
                    except Exception:
                        continue

                if not link:
                    if logger_callback:
                        logger_callback("Dungeon link not found")
                    return False

                if not self._safe_click(link):
                    if logger_callback:
                        logger_callback("Failed to click dungeon link")
                    return False

                if not self._wait_for_page_context(
                    expected_elements=[
                        (By.XPATH, "//*[contains(@onclick, 'startFight(')]"),
                        (By.CSS_SELECTOR, "img[src*='combatloc.gif'], a[href*='startFight'], button[onclick*='startFight']"),
                        (By.XPATH, "//input[@type='submit' and @value='Normal']"),
                    ],
                    url_keywords=["mod=dungeon"],
                    timeout=15,
                ):
                    if logger_callback:
                        logger_callback("Dungeon page did not open in time")
                    return False
            except Exception:
                if logger_callback:
                    logger_callback("Error navigating to dungeon page")
                return False

            visible = self._wait_for_dungeon_attack_elements(timeout=10)
            if not visible:
                # If no mobs, check if we need to re-enter the dungeon
                try:
                    enter_btn = None
                    enter_candidates = [
                        (By.XPATH, "//input[@type='submit' and @value='Normal']"),
                        (By.CSS_SELECTOR, "input[name='dif1']"),
                        (By.CSS_SELECTOR, "input.button1[value='Normal']")
                    ]
                    for by, sel in enter_candidates:
                        try:
                            els = self.driver.find_elements(by, sel)
                            for e in els:
                                if e.is_displayed() and e.is_enabled():
                                    enter_btn = e
                                    break
                            if enter_btn:
                                break
                        except Exception:
                            continue

                    if enter_btn:
                        if logger_callback:
                            logger_callback("Dungeon appears finished. Re-entering on Normal difficulty...")
                        if not self._safe_click(enter_btn):
                            if logger_callback:
                                logger_callback("Failed to re-enter dungeon on Normal difficulty")
                        else:
                            self._wait_for_page_context(
                                expected_elements=[
                                    (By.XPATH, "//*[contains(@onclick, 'startFight(')]"),
                                    (By.CSS_SELECTOR, "img[src*='combatloc.gif'], a[href*='startFight'], button[onclick*='startFight']"),
                                ],
                                url_keywords=["mod=dungeon"],
                                timeout=12,
                            )
                            # Wait again for mobs to appear after re-entering
                            visible = self._wait_for_dungeon_attack_elements(timeout=15)
                except Exception:
                    pass

            if not visible:
                if logger_callback:
                    logger_callback("No dungeon attack elements became available")
                return False

            tries = 0
            while tries < max_retries and visible:
                try:
                    el = random.choice(visible)
                    previous_url = self.driver.current_url
                    try:
                        if not self._safe_click(el):
                            raise RuntimeError("click failed")
                        if logger_callback:
                            logger_callback("Clicked dungeon minimap attack element")
                        self._wait_for_post_attack_navigation(previous_url, logger_callback=logger_callback, timeout=15)
                        self.navigate_to_overview(logger_callback=logger_callback)
                        return True
                    except StaleElementReferenceException:
                        tries += 1
                        visible = [c for c in self._wait_for_dungeon_attack_elements(timeout=5) if c.is_displayed()]
                        continue
                    except Exception:
                        tries += 1
                        visible = [c for c in self._wait_for_dungeon_attack_elements(timeout=5) if c.is_displayed()]
                        continue
                except Exception:
                    tries += 1
                    time.sleep(0.3)
                    visible = [c for c in self._wait_for_dungeon_attack_elements(timeout=5) if c.is_displayed()]
                    continue

            if logger_callback:
                logger_callback("No clickable dungeon attack element found after retries")
            return False
        except Exception as e:
            if logger_callback:
                logger_callback(f"Error in open_dungeon_and_random_attack: {e}")
            return False

    def attempt_dungeon_if_ready(self, dungeon_location="Voodoo Temple", dungeon_difficulty="Normal", logger_callback=None):
        """If dungeon cooldown indicates ready, navigate and click a random attack.
        Returns dict with result."""
        info = {"clicked": False, "message": ""}
        try:
            if not self.ensure_game_tab():
                info["message"] = "Could not find game tab for dungeon"
                if logger_callback:
                    logger_callback(info["message"])
                return info

            ready = self.is_dungeon_ready()
            if not ready:
                info["message"] = "Dungeon not ready"
                if logger_callback:
                    logger_callback(info["message"])
                return info

            if logger_callback:
                logger_callback("Dungeon ready — opening and clicking a random minimap attack...")

            clicked = self.open_dungeon_and_random_attack(
                dungeon_location=dungeon_location,
                dungeon_difficulty=dungeon_difficulty,
                logger_callback=logger_callback,
            )
            info["clicked"] = bool(clicked)
            info["message"] = "Clicked" if clicked else "No clickable attack found"
            if logger_callback:
                logger_callback(info["message"])
            return info
        except Exception as e:
            info["message"] = f"Error in attempt_dungeon_if_ready: {e}"
            if logger_callback:
                logger_callback(info["message"])
            return info

    def is_circus_ready(self):
        """Return True if the Circus Turma cooldown bar indicates readiness."""
        try:
            try:
                txt_el = self.driver.find_elements(By.ID, "cooldown_bar_text_ct")
                if txt_el:
                    txt = txt_el[0].text.strip().lower()
                    if txt.startswith('to circus turma') or 'to circus turma' in txt:
                        return True
            except Exception:
                pass

            try:
                fill_el = self.driver.find_elements(By.ID, "cooldown_bar_fill_ct")
                if fill_el:
                    cls = fill_el[0].get_attribute('class') or ''
                    if 'cooldown_bar_fill_ready' in cls:
                        return True
            except Exception:
                pass

            try:
                link_els = self.driver.find_elements(By.XPATH, "//a[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'circus turma')]")
                for link in link_els:
                    if link.is_displayed() and link.is_enabled():
                        return True
            except Exception:
                pass

            return False
        except Exception:
            return False

    def open_circus_and_attack_lowest_level(self, logger_callback=None, max_retries=3):
        """Open Circus Turma page and attack the lowest level opponent."""
        try:
            if logger_callback:
                logger_callback("Ensuring game tab is active for Circus Turma...")

            if not self.ensure_game_tab():
                if logger_callback:
                    logger_callback("Could not find game tab for Circus Turma")
                return False

            link = None
            candidates = [
                (By.CSS_SELECTOR, "#cooldown_bar_ct a.cooldown_bar_link"),
                (By.CSS_SELECTOR, "a.cooldown_bar_link[href*='aType=3']"),
                (By.XPATH, "//a[contains(@href,'submod=serverArena') and contains(@href,'aType=3')]")
            ]
            for by, sel in candidates:
                try:
                    els = self.driver.find_elements(by, sel)
                    for e in els:
                        if e.is_displayed() and e.is_enabled():
                            link = e
                            break
                    if link:
                        break
                except Exception:
                    continue

            if not link:
                if logger_callback:
                    logger_callback("Circus Turma link not found")
                return False

            if not self._safe_click(link):
                if logger_callback:
                    logger_callback("Failed to click Circus Turma link")
                return False

            if not self._wait_for_page_context(
                expected_elements=[
                    (By.CSS_SELECTOR, "#own3 tr, table#own3 tr, table[name='own3'] tr"),
                ],
                url_keywords=["submod=serverarena", "atype=3"],
                timeout=12,
            ):
                if logger_callback:
                    logger_callback("Circus Turma page did not open in time")
                return False

            self._wait_for_circus_rows(timeout=10)

            tries = 0
            while tries < max_retries:
                try:
                    tables = self.driver.find_elements(By.CSS_SELECTOR, "#own3, table#own3, table[name='own3'], table[class*='arena']")
                    rows = []
                    for table in tables:
                        try:
                            rows.extend(table.find_elements(By.CSS_SELECTOR, "tr"))
                        except Exception:
                            continue

                    if not rows:
                        rows = self.driver.find_elements(By.CSS_SELECTOR, "#own3 tr, table#own3 tr, table[name='own3'] tr, tr")

                    candidates = []
                    for row in rows:
                        try:
                            cols = row.find_elements(By.TAG_NAME, "td")
                            if len(cols) < 3:
                                continue

                            # Determine a numeric level from row cells
                            level = None
                            for col in cols:
                                level = self._parse_number_from_text(col.text)
                                if level is not None:
                                    break
                            if level is None:
                                continue

                            # Prefer an explicit attack button, otherwise use the last clickable cell
                            attack_btn = None
                            try:
                                attack_btn = row.find_element(By.CSS_SELECTOR, ".attack, button.attack, a.attack, div.attack")
                            except Exception:
                                pass

                            if not attack_btn or not attack_btn.is_displayed():
                                try:
                                    attack_btn = row.find_element(By.XPATH, ".//*[contains(@onclick,'attack') or contains(@onclick,'Fight') or contains(@onclick,'startFight') or contains(@onclick,'serverArena')]")
                                except Exception:
                                    attack_btn = None

                            if not attack_btn or not attack_btn.is_displayed():
                                # Fallback to any visible clickable element in the last cell
                                try:
                                    last_cell = cols[-1]
                                    clickables = last_cell.find_elements(By.XPATH, ".//a|.//button|.//div|.//span")
                                    for item in clickables:
                                        if item.is_displayed() and item.is_enabled():
                                            attack_btn = item
                                            break
                                except Exception:
                                    attack_btn = None

                            if not attack_btn or not attack_btn.is_displayed():
                                continue

                            candidates.append((level, attack_btn))
                        except Exception:
                            continue

                    if not candidates:
                        tries += 1
                        time.sleep(0.5)
                        continue

                    lowest = min(level for level, _ in candidates)
                    lowest_buttons = [btn for level, btn in candidates if level == lowest]
                    chosen = random.choice(lowest_buttons)

                    try:
                        if not self._safe_click(chosen):
                            raise RuntimeError("click failed")
                        if logger_callback:
                            logger_callback(f"Clicked Circus Turma attack for lowest level {lowest}")
                        self._wait_for_ui_settle(timeout=10)
                        self.navigate_to_overview(logger_callback=logger_callback)
                        return True
                    except StaleElementReferenceException:
                        tries += 1
                        time.sleep(0.3)
                        continue
                    except Exception:
                        tries += 1
                        time.sleep(0.3)
                        continue
                except Exception:
                    tries += 1
                    time.sleep(0.5)
                    continue

            if logger_callback:
                logger_callback("No Circus Turma attack button found after retries")
            return False
        except Exception as e:
            if logger_callback:
                logger_callback(f"Error in open_circus_and_attack_lowest_level: {e}")
            return False

    def attempt_circus_if_ready(self, logger_callback=None):
        info = {"clicked": False, "message": ""}
        try:
            if not self.ensure_game_tab():
                info["message"] = "Could not find game tab for Circus Turma"
                if logger_callback:
                    logger_callback(info["message"])
                return info

            ready = self.is_circus_ready()
            if not ready:
                info["message"] = "Circus Turma not ready"
                if logger_callback:
                    logger_callback(info["message"])
                return info

            if logger_callback:
                logger_callback("Circus Turma ready — opening and attacking lowest level...")

            clicked = self.open_circus_and_attack_lowest_level(logger_callback=logger_callback)
            info["clicked"] = bool(clicked)
            info["message"] = "Clicked" if clicked else "No Circus Turma attack found"
            if logger_callback:
                logger_callback(info["message"])
            return info
        except Exception as e:
            info["message"] = f"Error in attempt_circus_if_ready: {e}"
            if logger_callback:
                logger_callback(info["message"])
            return info

    def attempt_expedition_if_ready(self, expedition_location="Voodoo Temple", expedition_target=1, logger_callback=None):
        """Check cooldown bar; if ready and attempts > 0 perform one expedition click.
        Returns a dict describing the single click attempt."""
        info = {"clicked": False, "attempts_before": None, "attempts_after": None, "message": ""}
        try:
            if logger_callback:
                logger_callback("Ensuring game tab is active...")

            if not self.ensure_game_tab():
                info["message"] = "Could not find game tab"
                if logger_callback:
                    logger_callback(info["message"])
                return info

            # close overlays
            try:
                closed = self.close_overlays()
                if logger_callback:
                    logger_callback(f"Closed overlays: {closed}")
            except Exception:
                pass

            # If not ready, report and exit
            ready = self.is_expedition_ready()
            if not ready:
                info["message"] = "Expedition cooldown not ready"
                if logger_callback:
                    logger_callback(info["message"])
                return info

            # read attempts
            cur, mx = self.get_expedition_attempts()
            info["attempts_before"] = cur
            if cur is None:
                info["message"] = "Could not read expedition attempts"
                if logger_callback:
                    logger_callback(info["message"])
                return info

            if cur <= 0:
                info["message"] = "No expedition attempts left"
                if logger_callback:
                    logger_callback(info["message"])
                return info

            # perform click
            if logger_callback:
                logger_callback(
                    f"Expedition ready and attempts available: {cur} / {mx} — opening {expedition_location} and clicking target {expedition_target}..."
                )
            previous_url = self.driver.current_url
            if not self.open_expedition_location(expedition_location, logger_callback=logger_callback):
                info["message"] = f"Could not open expedition location: {expedition_location}"
                if logger_callback:
                    logger_callback(info["message"])
                return info
            clicked = self.click_expedition_target(expedition_target=expedition_target, logger_callback=logger_callback)
            info["clicked"] = clicked
            if clicked:
                if logger_callback:
                    logger_callback("Clicked expedition button, waiting for post-click navigation and expedition UI...")
                self._wait_for_post_attack_navigation(previous_url, logger_callback=logger_callback, timeout=12)
                self._wait_for_ui_settle(timeout=8)
                self.navigate_to_overview(logger_callback=logger_callback)
            cur2, mx2 = self.get_expedition_attempts()
            info["attempts_after"] = cur2
            info["message"] = f"Clicked: {clicked}, attempts now: {cur2} / {mx2}"
            if logger_callback:
                logger_callback(info["message"])
            return info
        except Exception as e:
            info["message"] = f"Error during attempt_expedition_if_ready: {e}"
            if logger_callback:
                logger_callback(info["message"])
            return info

    def click_leftmost_expedition(self):
        """Click the first enabled expedition button. Returns True if clicked."""
        return self.click_expedition_target(expedition_target=1)

    def _normalize_expedition_location(self, expedition_location):
        if isinstance(expedition_location, int):
            for label, loc in self.EXPEDITION_LOCATIONS.items():
                if loc == expedition_location:
                    return label, loc

        if isinstance(expedition_location, str):
            normalized = expedition_location.strip().lower()
            if normalized.isdigit():
                for label, loc in self.EXPEDITION_LOCATIONS.items():
                    if str(loc) == normalized:
                        return label, loc
            for label, loc in self.EXPEDITION_LOCATIONS.items():
                if normalized == label:
                    return label, loc

        return "grimwood", self.EXPEDITION_LOCATIONS["grimwood"]

    def open_country_map(self, logger_callback=None):
        """Open the country map submenu from the main menu."""
        try:
            candidates = [
                (By.CSS_SELECTOR, "a.submenuswitch[href*='submod=country']"),
                (By.XPATH, "//a[contains(@class,'submenuswitch') and contains(@href,'submod=country')]"),
            ]
            for by, value in candidates:
                try:
                    elements = self.driver.find_elements(by, value)
                    for el in elements:
                        if el.is_displayed() and el.is_enabled():
                            if self._safe_click(el):
                                if self._wait_for_page_context(
                                    expected_elements=[
                                        (By.CSS_SELECTOR, "#submenu2 a.menuitem[href*='mod=location']"),
                                        (By.CSS_SELECTOR, "a.menuitem[href*='mod=location']"),
                                    ],
                                    url_keywords=["mod=map", "submod=country"],
                                    timeout=10,
                                ):
                                    if logger_callback:
                                        logger_callback("Opened country map submenu")
                                    return True
                except Exception:
                    continue
            if logger_callback:
                logger_callback("Country map submenu switch not found")
            return False
        except Exception as e:
            if logger_callback:
                logger_callback(f"Error opening country map submenu: {e}")
            return False

    def open_city_map(self, logger_callback=None):
        """Open the city submenu from the main map navigation."""
        try:
            candidates = [
                (By.CSS_SELECTOR, "a.submenuswitch[href*='submod=city']"),
                (By.XPATH, "//a[contains(@class,'submenuswitch') and contains(@href,'submod=city')]"),
                (By.XPATH, "//div[contains(@class,'menutab_city')]//a[contains(@class,'submenuswitch')]"),
            ]
            for by, value in candidates:
                try:
                    elements = self.driver.find_elements(by, value)
                    for el in elements:
                        if el.is_displayed() and el.is_enabled():
                            if self._safe_click(el):
                                if self._wait_for_page_context(
                                    expected_elements=[
                                        (By.CSS_SELECTOR, "a.menuitem[href*='mod=inventory'][href*='sub=3']"),
                                        (By.CSS_SELECTOR, "a.menuitem[href*='mod=inventory']"),
                                    ],
                                    url_keywords=["mod=map", "submod=city"],
                                    timeout=10,
                                ):
                                    if logger_callback:
                                        logger_callback("Opened city submenu")
                                    return True
                except Exception:
                    continue
            if logger_callback:
                logger_callback("City submenu switch not found")
            return False
        except Exception as e:
            if logger_callback:
                logger_callback(f"Error opening city submenu: {e}")
            return False

    def open_general_goods(self, logger_callback=None):
        """Open General goods from the city menu."""
        try:
            candidates = [
                (By.CSS_SELECTOR, "a.menuitem[href*='mod=inventory'][href*='sub=3']"),
                (By.XPATH, "//a[contains(@class,'menuitem') and contains(@href,'mod=inventory') and contains(@href,'sub=3')]"),
                (By.XPATH, "//a[contains(normalize-space(.), 'General goods')]"),
            ]
            for by, value in candidates:
                try:
                    elements = self.driver.find_elements(by, value)
                    for el in elements:
                        if el.is_displayed() and el.is_enabled():
                            if self._safe_click(el):
                                if self._wait_for_page_context(
                                    expected_elements=[
                                        (By.CSS_SELECTOR, "#shop_nav"),
                                        (By.CSS_SELECTOR, "#shop, #inv"),
                                    ],
                                    url_keywords=["mod=inventory", "sub=3"],
                                    timeout=12,
                                ):
                                    if logger_callback:
                                        logger_callback("Opened General goods")
                                    return True
                except Exception:
                    continue
            if logger_callback:
                logger_callback("General goods menu item not found")
            return False
        except Exception as e:
            if logger_callback:
                logger_callback(f"Error opening General goods: {e}")
            return False

    def open_shop_tab_two(self, logger_callback=None):
        """Open the second shop tab where refill items are expected."""
        try:
            candidates = [
                (By.CSS_SELECTOR, "#shop_nav a[href*='subsub=1']"),
                (By.XPATH, "//div[@id='shop_nav']//a[contains(@href,'subsub=1')]"),
            ]
            for by, value in candidates:
                try:
                    elements = self.driver.find_elements(by, value)
                    for el in elements:
                        if el.is_displayed() and el.is_enabled():
                            if self._safe_click(el):
                                if self._wait_for_page_context(
                                    expected_elements=[
                                        (By.CSS_SELECTOR, "#shop"),
                                        (By.CSS_SELECTOR, "#shop .item-i"),
                                    ],
                                    url_keywords=["mod=inventory", "sub=3", "subsub=1"],
                                    timeout=12,
                                ):
                                    if logger_callback:
                                        logger_callback("Opened shop tab II")
                                    return True
                except Exception:
                    continue
            if logger_callback:
                logger_callback("Shop tab II not found")
            return False
        except Exception as e:
            if logger_callback:
                logger_callback(f"Error opening shop tab II: {e}")
            return False

    def _parse_int_attr(self, element, attr_name, default=None):
        try:
            value = element.get_attribute(attr_name)
            if value is None:
                return default
            return int(str(value).strip())
        except Exception:
            return default

    def _get_inventory_occupancy(self, grid_element):
        occupancy = set()
        for item in grid_element.find_elements(By.CSS_SELECTOR, ".item-i"):
            try:
                if not item.is_displayed():
                    continue
                start_x = self._parse_int_attr(item, "data-position-x", 1)
                start_y = self._parse_int_attr(item, "data-position-y", 1)
                size_x = self._parse_int_attr(item, "data-measurement-x", 1)
                size_y = self._parse_int_attr(item, "data-measurement-y", 1)
                if start_x is None or start_y is None:
                    continue
                for x in range(start_x, start_x + max(1, size_x or 1)):
                    for y in range(start_y, start_y + max(1, size_y or 1)):
                        occupancy.add((x, y))
            except Exception:
                continue
        return occupancy

    def _get_visible_inventory_dropareas(self, timeout=3, limit=12, logger_callback=None, log_missing=True):
        try:
            grid = None
            candidates = []
            end = time.time() + timeout
            while time.time() < end:
                try:
                    grid = self.driver.find_element(By.ID, "inv")
                    if not grid.is_displayed():
                        time.sleep(0.15)
                        continue
                except StaleElementReferenceException:
                    time.sleep(0.15)
                    continue
                except Exception:
                    time.sleep(0.15)
                    continue

                candidates = []
                try:
                    empty_slots = grid.find_elements(By.CSS_SELECTOR, ".ui-droppable.grid-droparea")
                except StaleElementReferenceException:
                    time.sleep(0.15)
                    continue

                for slot in empty_slots:
                    try:
                        if slot.is_displayed():
                            candidates.append(slot)
                    except StaleElementReferenceException:
                        continue
                    except Exception:
                        continue

                if candidates:
                    return grid, candidates[:limit]

                time.sleep(0.15)

            if logger_callback and log_missing:
                logger_callback("No visible inventory dropareas found")
            return grid, candidates
        except Exception as e:
            if logger_callback:
                logger_callback(f"Error finding inventory dropareas: {e}")
            return None, []

    def _get_droparea_key(self, slot):
        try:
            style = (slot.get_attribute("style") or "").strip()
            if style:
                return style
        except Exception:
            pass
        try:
            location = slot.location
            return f"{location.get('x')}:{location.get('y')}"
        except Exception:
            return None

    def _get_visible_healing_item_count(self, timeout=2):
        try:
            return len(self.find_healing_items(timeout=timeout))
        except Exception:
            return None

    def _read_visible_healing_item_count(self, timeout=1.5, refresh_view=False):
        """Read the visible refill pot count from the current inventory view."""
        if refresh_view:
            try:
                self.ensure_avatar_visible(logger_callback=None)
            except Exception:
                pass
            try:
                self.open_first_inventory_bag(logger_callback=None)
            except Exception:
                pass
            time.sleep(0.2)

        count = self._get_visible_healing_item_count(timeout=timeout)
        if count is not None:
            return count

        try:
            self.ensure_avatar_visible(logger_callback=None)
        except Exception:
            pass
        try:
            self.open_first_inventory_bag(logger_callback=None)
        except Exception:
            pass
        time.sleep(0.2)
        return self._get_visible_healing_item_count(timeout=timeout)

    def _wait_for_visible_healing_item_count(self, previous_count=None, timeout=1.5, refresh_view=False):
        """Wait briefly for the visible refill pot count to stabilize after a drag."""
        end = time.time() + timeout
        last_count = None
        while time.time() < end:
            count = self._read_visible_healing_item_count(timeout=0.5, refresh_view=refresh_view)
            if count is not None:
                last_count = count
                if previous_count is None or count != previous_count:
                    return count
            time.sleep(0.12)
        return last_count

    def _publish_refill_pot_count(self, count, count_update_callback=None):
        if count_update_callback is None or count is None:
            return
        try:
            count_update_callback(count)
        except Exception:
            pass

    def find_shop_refill_items(self, timeout=5):
        """Find visible refill items in the shop tab."""
        end = time.time() + timeout
        while time.time() < end:
            try:
                items = self.driver.find_elements(
                    By.XPATH,
                    "//div[@id='shop' and contains(@class,'ui-droppable-grid')]//div[contains(@class,'item-i') and @data-content-type='64']",
                )
                visible = [item for item in items if item.is_displayed()]
                if visible:
                    return visible
            except Exception:
                pass
            time.sleep(0.3)
        return []

    def drag_shop_item_to_inventory(self, item_element, logger_callback=None):
        """Drag a shop item into the first free slot in the inventory grid."""
        before_count = None
        released_to_slot = False
        item_disappeared = lambda: False
        try:
            from selenium.webdriver.common.action_chains import ActionChains

            before_count = self._read_visible_healing_item_count(timeout=1, refresh_view=True)
            if logger_callback:
                logger_callback(f"Refill pot drag starting; visible count before drag: {before_count}")
            tried_slot_keys = set()
            attempts = 2
            saw_dropareas = False
            blocked = False

            def item_disappeared():
                try:
                    return (not item_element.is_displayed()) or (item_element.get_attribute("data-item-id") is None)
                except StaleElementReferenceException:
                    return True
                except Exception:
                    return True

            for attempt in range(attempts):
                if logger_callback:
                    logger_callback(f"Refill pot drag attempt {attempt + 1}/{attempts}")

                # Start a real drag motion so the game reveals valid drop areas.
                drag_start = ActionChains(self.driver)
                drag_start.click_and_hold(item_element)
                drag_start.move_by_offset(10, 10)
                drag_start.pause(0.1)
                drag_start.perform()
                time.sleep(0.25)

                grid, candidates = self._get_visible_inventory_dropareas(
                    timeout=2,
                    limit=10,
                    logger_callback=logger_callback,
                    log_missing=False,
                )
                if logger_callback:
                    logger_callback(
                        f"Refill pot drag attempt {attempt + 1}/{attempts}: revealed {len(candidates)} dropareas"
                    )
                if not candidates:
                    try:
                        ActionChains(self.driver).release().perform()
                    except Exception:
                        pass
                    if logger_callback:
                        logger_callback(
                            f"Refill pot drag attempt {attempt + 1}/{attempts}: no dropareas available after reveal"
                        )
                    if attempt == attempts - 1:
                        blocked = True
                        break
                    continue
                saw_dropareas = True

                target_slot = None
                for slot in candidates:
                    slot_key = self._get_droparea_key(slot)
                    if slot_key and slot_key in tried_slot_keys:
                        continue
                    target_slot = slot
                    if slot_key:
                        tried_slot_keys.add(slot_key)
                    break

                if target_slot is None:
                    if logger_callback:
                        logger_callback(
                            f"Refill pot drag attempt {attempt + 1}/{attempts}: all revealed dropareas were already tried"
                        )
                    try:
                        ActionChains(self.driver).release().perform()
                    except Exception:
                        pass
                    if attempt == attempts - 1:
                        blocked = True
                        break
                    continue

                actions = ActionChains(self.driver)
                actions.move_to_element(target_slot)
                actions.pause(0.15)
                actions.release()
                actions.perform()
                released_to_slot = True
                if logger_callback:
                    logger_callback(
                        f"Refill pot drag attempt {attempt + 1}/{attempts}: released onto slot {self._get_droparea_key(target_slot) or 'unknown'}"
                    )
                time.sleep(0.25)

                after_count = self._wait_for_visible_healing_item_count(
                    previous_count=before_count,
                    timeout=1.5,
                    refresh_view=True,
                )
                if logger_callback:
                    logger_callback(
                        f"Refill pot drag attempt {attempt + 1}/{attempts}: count after drag check is {after_count}"
                    )
                if after_count is not None and before_count is not None and after_count > before_count:
                    if logger_callback:
                        logger_callback("Dragged shop item into empty slot")
                    return "success"

                if item_disappeared():
                    if logger_callback:
                        logger_callback(
                            "Shop item disappeared after drag; counting this as a purchased refill pot"
                        )
                    return "inferred_success"

                try:
                    ActionChains(self.driver).release().perform()
                except Exception:
                    pass

            final_count = self._read_visible_healing_item_count(timeout=1, refresh_view=True)
            if logger_callback:
                logger_callback(
                    f"Refill pot drag finished; before={before_count}, final visible count={final_count}, released={released_to_slot}, blocked={blocked}"
                )
            if final_count is not None and before_count is not None and final_count > before_count:
                if logger_callback:
                    logger_callback("Dragged shop item into empty slot")
                return "success"

            if logger_callback and not saw_dropareas:
                logger_callback("No visible inventory dropareas found")

            if blocked or not saw_dropareas:
                return "blocked"

            if logger_callback:
                logger_callback("Dragged shop item into inventory, but count did not change")
            return "attempted" if released_to_slot else "failed"
        except Exception as e:
            after_count = self._wait_for_visible_healing_item_count(
                previous_count=before_count,
                timeout=1.5,
                refresh_view=True,
            )
            if logger_callback:
                logger_callback(
                    f"Refill pot drag exception state; before={before_count}, after={after_count}, released={released_to_slot}"
                )
            if after_count is not None and before_count is not None and after_count > before_count:
                if logger_callback:
                    logger_callback("Dragged shop item into empty slot")
                return "success"
            if released_to_slot and item_disappeared():
                if logger_callback:
                    logger_callback(
                        "Shop item disappeared during drag exception handling; counting this as a purchased refill pot"
                    )
                return "inferred_success"
            if logger_callback:
                logger_callback(f"Error dragging shop item into inventory: {e}")
            return "attempted" if released_to_slot else "failed"

    def buy_refill_pots(self, min_item_count=10, logger_callback=None, count_update_callback=None):
        """Buy refill pots from General goods until inventory count reaches the target."""
        try:
            if not self.ensure_game_tab():
                if logger_callback:
                    logger_callback("Could not find game tab for refill pot purchase")
                return False

            if not self.open_city_map(logger_callback=logger_callback):
                return False

            if not self.open_general_goods(logger_callback=logger_callback):
                return False

            if not self.ensure_avatar_visible(logger_callback=logger_callback):
                return False

            if not self.open_first_inventory_bag(logger_callback=logger_callback):
                return False

            if not self.open_shop_tab_two(logger_callback=logger_callback):
                return False

            current_count = self._read_visible_healing_item_count(timeout=2, refresh_view=True)
            if current_count is None:
                if logger_callback:
                    logger_callback("Could not read current refill pot count")
                return False
            self._publish_refill_pot_count(current_count, count_update_callback)

            if current_count >= min_item_count:
                if logger_callback:
                    logger_callback(f"Refill pots already at {current_count}, no purchase needed")
                return True

            items = self.find_shop_refill_items()
            if not items:
                if logger_callback:
                    logger_callback("No refill pots found in shop")
                return False

            if logger_callback:
                logger_callback(f"Refill pots below {min_item_count} ({current_count}), buying from shop...")

            loop_index = 0
            while current_count < min_item_count:
                loop_index += 1
                items = self.find_shop_refill_items(timeout=2)
                if logger_callback:
                    logger_callback(
                        f"Refill pot buy cycle {loop_index}: target={min_item_count}, current={current_count}, shop items visible={len(items)}"
                    )
                if not items:
                    if logger_callback:
                        logger_callback("No refill pots left in shop")
                    break

                item = items[0]
                try:
                    if not item.is_displayed():
                        if logger_callback:
                            logger_callback("Stopped buying refill pots because shop item is no longer visible")
                        break
                except StaleElementReferenceException:
                    if logger_callback:
                        logger_callback("Stopped buying refill pots because shop item became stale")
                    break

                previous_count = current_count
                move_result = self.drag_shop_item_to_inventory(item, logger_callback=logger_callback)
                current_count = self._wait_for_visible_healing_item_count(
                    previous_count=previous_count,
                    timeout=2.5,
                    refresh_view=True,
                )
                if current_count is None:
                    current_count = self._read_visible_healing_item_count(timeout=1.5, refresh_view=True)
                if current_count is None:
                    current_count = previous_count
                if current_count <= previous_count and move_result == "inferred_success":
                    current_count = previous_count + 1
                    if logger_callback:
                        logger_callback(
                            f"Refill pot buy cycle {loop_index}: inferred count advanced to {current_count} from shop item removal"
                        )
                self._publish_refill_pot_count(current_count, count_update_callback)
                if logger_callback:
                    logger_callback(
                        f"Refill pot buy cycle {loop_index} result: move_result={move_result}, previous={previous_count}, current={current_count}"
                    )

                if current_count >= min_item_count:
                    if logger_callback:
                        logger_callback(f"Refill pot count updated to {current_count}")
                    break

                if current_count > previous_count:
                    if logger_callback:
                        logger_callback(f"Refill pot count updated to {current_count}")
                    continue

                if move_result == "blocked":
                    if logger_callback:
                        logger_callback("Stopped buying refill pots because inventory has no usable empty slot")
                    break

                if logger_callback:
                    logger_callback("Stopped buying refill pots because drag did not increase refill pot count")
                break

            if not self.navigate_to_overview(logger_callback=logger_callback):
                if logger_callback:
                    logger_callback("Could not return to overview after refill pot purchase")

            final_count = self.get_healing_item_count(logger_callback=logger_callback)
            self._publish_refill_pot_count(final_count, count_update_callback)
            if logger_callback:
                logger_callback(
                    f"Refill pot purchase final recount on overview: {final_count} / target {min_item_count}"
                )
            if final_count is not None and final_count >= min_item_count:
                if logger_callback:
                    logger_callback(f"Refill pot purchase complete: {final_count}")
                return True

            if logger_callback:
                logger_callback(
                    f"Refill pot purchase ended at {final_count if final_count is not None else 'unknown'}"
                )
            return False
        except Exception as e:
            if logger_callback:
                logger_callback(f"Error buying refill pots: {e}")
            return False

    def attempt_buy_refill_pots_if_needed(self, min_item_count=10, logger_callback=None, count_update_callback=None):
        """Buy refill pots only when the current inventory count is below threshold."""
        try:
            if not self.ensure_game_tab():
                if logger_callback:
                    logger_callback("Could not find game tab for refill pot purchase")
                return

            current_count = self.get_healing_item_count(logger_callback=logger_callback)
            if current_count is None:
                if logger_callback:
                    logger_callback("Could not read refill pot count")
                return
            self._publish_refill_pot_count(current_count, count_update_callback)

            if current_count >= min_item_count:
                if logger_callback:
                    logger_callback(f"Refill pots OK ({current_count}), purchase not needed")
                return

            if logger_callback:
                logger_callback(f"Refill pots below {min_item_count} ({current_count}), buying...")

            success = self.buy_refill_pots(
                min_item_count=min_item_count,
                logger_callback=logger_callback,
                count_update_callback=count_update_callback,
            )
            if logger_callback:
                logger_callback("Refill pot buy: successful" if success else "Refill pot buy: failed")
        except Exception as e:
            if logger_callback:
                logger_callback(f"Refill pot buy: failed ({e})")

    def _open_country_map_location(self, loc, label, page_name, expected_url_keywords, expected_elements, logger_callback=None):
        try:
            if not self.ensure_game_tab():
                if logger_callback:
                    logger_callback(f"Could not find game tab for {page_name}")
                return False

            self.close_overlays()

            if logger_callback:
                logger_callback(f"Opening {page_name} location: {label}")

            if not self.open_country_map(logger_callback=logger_callback):
                return False

            candidates = [
                (By.CSS_SELECTOR, f"#submenu2 a.menuitem[href*='mod=location'][href*='loc={loc}']"),
                (By.CSS_SELECTOR, f"a.menuitem[href*='mod=location'][href*='loc={loc}']"),
                (By.XPATH, f"//a[contains(@class,'menuitem') and contains(@href,'mod=location') and contains(@href,'loc={loc}')]"),
                (By.XPATH, f"//a[contains(normalize-space(.), '{label}')]"),
            ]

            for by, value in candidates:
                try:
                    elements = self.driver.find_elements(by, value)
                    for el in elements:
                        if el.is_displayed() and el.is_enabled():
                            previous_url = self.driver.current_url
                            if self._safe_click(el):
                                if self._wait_for_page_context(
                                    expected_elements=expected_elements,
                                    url_keywords=expected_url_keywords,
                                    timeout=12,
                                ):
                                    return True
                                if self.driver.current_url != previous_url:
                                    return True
                except Exception:
                    continue

            if logger_callback:
                logger_callback(f"{page_name} location '{label}' not found")
            return False
        except Exception as e:
            if logger_callback:
                logger_callback(f"Error opening {page_name} location: {e}")
            return False

    def open_expedition_location(self, expedition_location, logger_callback=None):
        """Open the selected expedition location from the country map submenu."""
        try:
            label, loc = self._normalize_expedition_location(expedition_location)
            return self._open_country_map_location(
                loc=loc,
                label=label,
                page_name="expedition",
                expected_url_keywords=[f"loc={loc}", "mod=location"],
                expected_elements=[
                    (By.CSS_SELECTOR, "button.expedition_button"),
                    (By.CSS_SELECTOR, "#expedition_list .expedition_box"),
                ],
                logger_callback=logger_callback,
            )
        except Exception as e:
            if logger_callback:
                logger_callback(f"Error opening expedition location: {e}")
            return False

    def _normalize_dungeon_location(self, dungeon_location):
        if isinstance(dungeon_location, int):
            for label, loc in self.DUNGEON_LOCATIONS.items():
                if loc == dungeon_location:
                    return label, loc

        if isinstance(dungeon_location, str):
            normalized = dungeon_location.strip().lower()
            if normalized.isdigit():
                for label, loc in self.DUNGEON_LOCATIONS.items():
                    if str(loc) == normalized:
                        return label, loc
            for label, loc in self.DUNGEON_LOCATIONS.items():
                if normalized == label:
                    return label, loc

        return "grimwood", self.DUNGEON_LOCATIONS["grimwood"]

    def _normalize_dungeon_difficulty(self, dungeon_difficulty):
        if isinstance(dungeon_difficulty, str):
            normalized = dungeon_difficulty.strip().lower()
            if normalized == "advanced":
                return "Advanced", "dif2"
        return "Normal", "dif1"

    def open_dungeon_location(self, dungeon_location, logger_callback=None):
        """Open the selected dungeon location from the country map submenu."""
        try:
            label, loc = self._normalize_dungeon_location(dungeon_location)
            return self._open_country_map_location(
                loc=loc,
                label=label,
                page_name="dungeon",
                expected_url_keywords=[f"loc={loc}", "mod=location"],
                expected_elements=[
                    (By.XPATH, "//*[contains(@onclick, 'startFight(')]"),
                    (By.CSS_SELECTOR, "img[src*='combatloc.gif'], a[href*='startFight'], button[onclick*='startFight']"),
                ],
                logger_callback=logger_callback,
            )
        except Exception as e:
            if logger_callback:
                logger_callback(f"Error opening dungeon location: {e}")
            return False

    def open_dungeon_tab(self, logger_callback=None):
        """Click the top Dungeon tab after a location is selected."""
        try:
            candidates = [
                (By.CSS_SELECTOR, "ul#mainnav a.awesome-tabs[href*='mod=dungeon']"),
                (By.CSS_SELECTOR, "a.awesome-tabs[href*='mod=dungeon']"),
                (By.XPATH, "//ul[@id='mainnav']//a[contains(@class,'awesome-tabs') and contains(@href,'mod=dungeon')]"),
            ]
            for by, value in candidates:
                try:
                    elements = self.driver.find_elements(by, value)
                    for el in elements:
                        if el.is_displayed() and el.is_enabled():
                            if self._safe_click(el):
                                if self._wait_for_page_context(
                                    expected_elements=[
                                        (By.CSS_SELECTOR, "input.button1[name='dif1'], input.button1[name='dif2']"),
                                        (By.CSS_SELECTOR, "form[action*='mod=dungeon']"),
                                    ],
                                    url_keywords=["mod=dungeon"],
                                    timeout=12,
                                ):
                                    if logger_callback:
                                        logger_callback("Opened Dungeon tab")
                                    return True
                except Exception:
                    continue
            if logger_callback:
                logger_callback("Dungeon tab not found")
            return False
        except Exception as e:
            if logger_callback:
                logger_callback(f"Error opening Dungeon tab: {e}")
            return False

    def _click_dungeon_difficulty(self, dungeon_difficulty="Normal", logger_callback=None):
        """Click Normal or Advanced if the Enter Dungeon card is present."""
        try:
            label, name = self._normalize_dungeon_difficulty(dungeon_difficulty)
            candidates = [
                (By.CSS_SELECTOR, f"input.button1[name='{name}']"),
                (By.CSS_SELECTOR, f"input[name='{name}']"),
                (By.XPATH, f"//input[@type='submit' and @name='{name}']"),
                (By.XPATH, f"//input[@type='submit' and @value='{label}']"),
            ]
            for by, value in candidates:
                try:
                    elements = self.driver.find_elements(by, value)
                    for el in elements:
                        if el.is_displayed() and el.is_enabled():
                            if self._safe_click(el):
                                if logger_callback:
                                    logger_callback(f"Selected dungeon difficulty: {label}")
                                return True
                except Exception:
                    continue
            return False
        except Exception as e:
            if logger_callback:
                logger_callback(f"Error selecting dungeon difficulty: {e}")
            return False

    def click_expedition_target(self, expedition_target=1, logger_callback=None):
        """Click the selected expedition target by 1-based expedition box index."""
        try:
            try:
                target_index = int(expedition_target)
            except (TypeError, ValueError):
                target_index = 1
            target_index = max(1, min(4, target_index))

            boxes = self.driver.find_elements(By.CSS_SELECTOR, "#expedition_list .expedition_box")
            if boxes and len(boxes) >= target_index:
                try:
                    box = boxes[target_index - 1]
                    if box.is_displayed():
                        buttons = box.find_elements(By.CSS_SELECTOR, "button.expedition_button")
                        for button in buttons:
                            try:
                                if button.is_displayed() and button.is_enabled():
                                    return self._safe_click(button)
                            except Exception:
                                continue
                        if logger_callback:
                            logger_callback(f"Expedition target {target_index} is visible but not clickable")
                        return False
                except Exception:
                    pass

            buttons = self.driver.find_elements(By.CSS_SELECTOR, "button.expedition_button")
            if buttons and len(buttons) >= target_index:
                try:
                    button = buttons[target_index - 1]
                    if button.is_displayed() and button.is_enabled():
                        return self._safe_click(button)
                except Exception:
                    pass

            try:
                links = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    "#cooldown_bar_expedition a.cooldown_bar_link, a.cooldown_bar_link[href*='mod=location'][href*='loc=2']",
                )
                for l in links:
                    try:
                        if l.is_displayed() and l.is_enabled():
                            if not self._safe_click(l):
                                continue
                            if not self._wait_for_page_context(
                                expected_elements=[
                                    (By.CSS_SELECTOR, "button.expedition_button"),
                                    (By.CSS_SELECTOR, "#expeditionpoints_value, #expeditionpoints_value_point"),
                                ],
                                url_keywords=["mod=location", "loc=2"],
                                timeout=10,
                            ):
                                return False
                            return self.click_expedition_target(expedition_target=target_index, logger_callback=logger_callback)
                    except Exception:
                        continue
            except Exception:
                pass

            return False
        except Exception:
            return False

    def open_dungeon_and_random_attack(self, dungeon_location="1", dungeon_difficulty="Normal", logger_callback=None, max_retries=3):
        """Open the dungeon location and click a random minimap attack.
        Returns True if an attack element was clicked."""
        try:
            if logger_callback:
                logger_callback("Ensuring game tab is active for dungeon...")

            if not self.ensure_game_tab():
                if logger_callback:
                    logger_callback("Could not find game tab for dungeon")
                return False

            if dungeon_location is not None:
                if not self.open_dungeon_location(dungeon_location, logger_callback=logger_callback):
                    return False
                if not self.open_dungeon_tab(logger_callback=logger_callback):
                    return False
            else:
                try:
                    link = None
                    candidates = [
                        (By.CSS_SELECTOR, "#cooldown_bar_dungeon a.cooldown_bar_link"),
                        (By.CSS_SELECTOR, "a.cooldown_bar_link[href*='mod=dungeon']"),
                        (By.CSS_SELECTOR, "a.cooldown_bar_link[href*='loc=1']"),
                    ]
                    for by, sel in candidates:
                        try:
                            els = self.driver.find_elements(by, sel)
                            for e in els:
                                if e.is_displayed() and e.is_enabled():
                                    link = e
                                    break
                            if link:
                                break
                        except Exception:
                            continue

                    if not link:
                        if logger_callback:
                            logger_callback("Dungeon link not found")
                        return False

                    if not self._safe_click(link):
                        if logger_callback:
                            logger_callback("Failed to click dungeon link")
                        return False

                    if not self._wait_for_page_context(
                        expected_elements=[
                            (By.XPATH, "//*[contains(@onclick, 'startFight(')]"),
                            (By.CSS_SELECTOR, "img[src*='combatloc.gif'], a[href*='startFight'], button[onclick*='startFight']"),
                            (By.XPATH, "//input[@type='submit' and @value='Normal']"),
                        ],
                        url_keywords=["mod=dungeon"],
                        timeout=15,
                    ):
                        if logger_callback:
                            logger_callback("Dungeon page did not open in time")
                        return False
                except Exception:
                    if logger_callback:
                        logger_callback("Error navigating to dungeon page")
                    return False

            self._click_dungeon_difficulty(dungeon_difficulty, logger_callback=logger_callback)

            visible = self._wait_for_dungeon_attack_elements(timeout=10)
            if not visible:
                try:
                    enter_btn = None
                    enter_candidates = [
                        (By.XPATH, "//input[@type='submit' and @value='Normal']"),
                        (By.CSS_SELECTOR, "input[name='dif1']"),
                        (By.CSS_SELECTOR, "input.button1[value='Normal']")
                    ]
                    for by, sel in enter_candidates:
                        try:
                            els = self.driver.find_elements(by, sel)
                            for e in els:
                                if e.is_displayed() and e.is_enabled():
                                    enter_btn = e
                                    break
                            if enter_btn:
                                break
                        except Exception:
                            continue

                    if enter_btn:
                        if logger_callback:
                            logger_callback("Dungeon appears finished. Re-entering on Normal difficulty...")
                        if not self._safe_click(enter_btn):
                            if logger_callback:
                                logger_callback("Failed to re-enter dungeon on Normal difficulty")
                        else:
                            self._wait_for_page_context(
                                expected_elements=[
                                    (By.XPATH, "//*[contains(@onclick, 'startFight(')]"),
                                    (By.CSS_SELECTOR, "img[src*='combatloc.gif'], a[href*='startFight'], button[onclick*='startFight']"),
                                ],
                                url_keywords=["mod=dungeon"],
                                timeout=12,
                            )
                            visible = self._wait_for_dungeon_attack_elements(timeout=15)
                except Exception:
                    pass

            if not visible:
                if logger_callback:
                    logger_callback("No dungeon attack elements became available")
                return False

            tries = 0
            while tries < max_retries and visible:
                try:
                    el = random.choice(visible)
                    previous_url = self.driver.current_url
                    try:
                        if not self._safe_click(el):
                            raise RuntimeError("click failed")
                        if logger_callback:
                            logger_callback("Clicked dungeon minimap attack element")
                        self._wait_for_post_attack_navigation(previous_url, logger_callback=logger_callback, timeout=15)
                        self.navigate_to_overview(logger_callback=logger_callback)
                        return True
                    except StaleElementReferenceException:
                        tries += 1
                        visible = [c for c in self._wait_for_dungeon_attack_elements(timeout=5) if c.is_displayed()]
                        continue
                    except Exception:
                        tries += 1
                        visible = [c for c in self._wait_for_dungeon_attack_elements(timeout=5) if c.is_displayed()]
                        continue
                except Exception:
                    tries += 1
                    time.sleep(0.3)
                    visible = [c for c in self._wait_for_dungeon_attack_elements(timeout=5) if c.is_displayed()]
                    continue

            if logger_callback:
                logger_callback("No clickable dungeon attack element found after retries")
            return False
        except Exception as e:
            if logger_callback:
                logger_callback(f"Error in open_dungeon_and_random_attack: {e}")
            return False

    def is_hp_above_threshold(self, min_hp_percent):
        """Return True if current HP percent is strictly above min_hp_percent."""
        hp = self.get_hp_status()
        if hp and hp.get("percent") is not None:
            return hp["percent"] > min_hp_percent
        return False

    def navigate_to_overview(self, logger_callback=None):
        """Navigate to Overview where inventory items are visible."""
        try:
            if not self.ensure_game_tab():
                if logger_callback:
                    logger_callback("Could not find game tab for Overview")
                return False

            self.close_overlays()

            candidates = [
                (By.CSS_SELECTOR, "a.menuitem[title='Overview']"),
                (By.XPATH, "//a[contains(@class,'menuitem') and contains(@href,'mod=overview')]"),
            ]
            for by, value in candidates:
                if self._click_element(by, value, timeout=5):
                    self.wait_for_page_ready(5)
                    time.sleep(0.3)
                    if logger_callback:
                        logger_callback("Navigated to Overview")
                    return True

            if logger_callback:
                logger_callback("Overview menu item not found")
            return False
        except Exception as e:
            if logger_callback:
                logger_callback(f"Error navigating to Overview: {e}")
            return False

    def open_first_inventory_bag(self, logger_callback=None):
        """Open the first inventory bag before searching for healing items."""
        try:
            bag_candidates = [
                (By.CSS_SELECTOR, "a.awesome-tabs.current[data-bag-number='512']"),
                (By.CSS_SELECTOR, "a.awesome-tabs[data-bag-number='512']"),
                (By.XPATH, "//a[contains(@class, 'awesome-tabs') and @data-bag-number='512']"),
            ]
            for by, value in bag_candidates:
                try:
                    bag = self.driver.find_element(by, value)
                    if bag.is_displayed():
                        if "current" not in (bag.get_attribute("class") or ""):
                            self._safe_click(bag)
                            time.sleep(0.5)
                        if logger_callback:
                            logger_callback("Opened first inventory bag")
                        return True
                except Exception:
                    continue

            if logger_callback:
                logger_callback("First inventory bag not found")
            return False
        except Exception as e:
            if logger_callback:
                logger_callback(f"Error opening first inventory bag: {e}")
            return False

    def ensure_avatar_visible(self, logger_callback=None):
        """Select the standard battle doll so the avatar drop target is visible."""
        try:
            avatar_candidates = [
                (By.XPATH, "//div[contains(@class, 'charmercsel') and contains(@class, 'active') and .//div[contains(@class, 'doll1')]]"),
                (By.XPATH, "//div[contains(@class, 'charmercsel') and .//div[contains(@class, 'doll1')]]"),
                (By.XPATH, "//div[contains(@class, 'charmercsel') and contains(@onclick, 'doll=1')]"),
            ]
            for by, value in avatar_candidates:
                try:
                    avatar = self.driver.find_element(by, value)
                    if avatar.is_displayed():
                        if "active" not in (avatar.get_attribute("class") or ""):
                            self._safe_click(avatar)
                            time.sleep(0.5)
                        if logger_callback:
                            logger_callback("Selected standard battle avatar")
                        return True
                except Exception:
                    continue

            if logger_callback:
                logger_callback("Standard battle avatar not found")
            return False
        except Exception as e:
            if logger_callback:
                logger_callback(f"Error selecting avatar: {e}")
            return False

    def find_healing_items(self, timeout=5):
        """Find all healing items (content-type 64) in inventory."""
        end = time.time() + timeout
        while time.time() < end:
            try:
                items = self.driver.find_elements(
                    By.XPATH,
                    "//div[@data-container-number='512' and @data-content-type='64' and contains(@class, 'item-i')]",
                )
                visible = [item for item in items if item.is_displayed()]
                if visible:
                    return visible
            except Exception:
                pass
            time.sleep(0.3)
        return []

    def get_healing_item_count(self, timeout=5, logger_callback=None):
        """Return the number of healing items visible in the first inventory bag."""
        try:
            if not self.open_first_inventory_bag(logger_callback=logger_callback):
                return None
            items = self.find_healing_items(timeout=timeout)
            return len(items)
        except Exception as e:
            if logger_callback:
                logger_callback(f"Error reading healing item count: {e}")
            return None

    def drag_item_to_avatar(self, item_element, logger_callback=None):
        """Drag a healing item to the avatar drop zone."""
        try:
            avatar_drop = self.driver.find_element(
                By.XPATH,
                "//div[@data-container-number='8'][@class and contains(@class, 'ui-droppable')]",
            )
            if not avatar_drop.is_displayed():
                if logger_callback:
                    logger_callback("Avatar drop zone not visible")
                return False

            from selenium.webdriver.common.action_chains import ActionChains

            actions = ActionChains(self.driver)
            actions.click_and_hold(item_element).move_to_element(avatar_drop).release().perform()
            time.sleep(0.5)

            if logger_callback:
                logger_callback("Dragged healing item to avatar")
            return True
        except Exception as e:
            if logger_callback:
                logger_callback(f"Error dragging item to avatar: {e}")
            return False

    def refill_hp(self, min_hp_percent=25, logger_callback=None):
        """Navigate to Overview, use a healing item on avatar, verify HP above threshold."""
        try:
            if not self.navigate_to_overview(logger_callback=logger_callback):
                return False

            if not self.open_first_inventory_bag(logger_callback=logger_callback):
                return False

            if not self.ensure_avatar_visible(logger_callback=logger_callback):
                return False

            items = self.find_healing_items()
            if not items:
                if logger_callback:
                    logger_callback("No healing items found in inventory")
                return False

            item = items[0]
            if logger_callback:
                logger_callback("Using healing item...")

            hp_before = self.get_hp_status()
            before_percent = hp_before.get("percent") if hp_before else None

            if not self.drag_item_to_avatar(item, logger_callback=logger_callback):
                return False

            self.wait_for_page_ready(5)
            self.close_overlays()

            hp, ok = self._wait_for_hp_after_refill(
                before_percent, min_hp_percent, timeout=10, logger_callback=logger_callback
            )
            if ok:
                if logger_callback:
                    logger_callback(f"HP refill successful — bar: {self._format_hp_log(hp)}")
                return True

            if logger_callback:
                logger_callback(
                    f"HP refill failed — bar: {self._format_hp_log(hp)} "
                    f"(was {before_percent}%, need >{min_hp_percent}%)"
                )
            return False
        except Exception as e:
            if logger_callback:
                logger_callback(f"Error in refill_hp: {e}")
            return False

    def attempt_refill_hp_if_needed(self, min_hp_percent=25, logger_callback=None):
        """If HP is at or below threshold, navigate to Overview and use a pot once."""
        try:
            if not self.ensure_game_tab():
                if logger_callback:
                    logger_callback("Could not find game tab for HP refill")
                    logger_callback("HP refill: başarısız")
                return

            hp = self.get_hp_status()
            if not hp or hp.get("percent") is None:
                if logger_callback:
                    logger_callback("Could not read HP status")
                    logger_callback("HP refill: başarısız")
                return

            if hp["percent"] > min_hp_percent:
                if logger_callback:
                    logger_callback(f"HP OK ({hp['percent']}%), refill not needed")
                return

            if logger_callback:
                logger_callback(f"HP below {min_hp_percent}% ({hp['percent']}%), attempting refill...")

            success = self.refill_hp(min_hp_percent=min_hp_percent, logger_callback=logger_callback)
            if logger_callback:
                logger_callback("HP refill: başarılı" if success else "HP refill: başarısız")
        except Exception as e:
            if logger_callback:
                logger_callback(f"HP refill: başarısız ({e})")

    def quit(self):
        try:
            self.driver.quit()
        except Exception:
            pass

"""Klien Google Flow lewat Playwright + Chrome yang sudah terpasang (tanpa unduh browser). Sesi login disimpan di profil Chrome
khusus (default ~/.google-flow-creator/browser-profile); pengguna login sendiri SEKALI lewat `autopost flow login`, kata sandi
tidak pernah disentuh program. Satu profil hanya boleh dipakai satu Chrome: tutup MCP Flow/jendela Flow lain sebelum menjalankan.

generate_batch: lampirkan foto produk sebagai referensi, isi prompt, submit semua klip, tunggu, unduh 720p Original (gratis,
tanpa upscale berbayar). Pemakaian kredit dijaga: pemanggil wajib menyetujui total kredit (approve_credits)."""
import os, re, socket, time
import urllib.parse
from pathlib import Path

HOME = "https://flow.google.com/?hl=en"
VIEW = {"width": 1280, "height": 900}
PLUS = (359, 843)                 # tombol "+" di kotak prompt (lampirkan media)
PILL = (810, 842)                 # ringkasan pengaturan ("Video · 720p · 10s ...")
SEARCH = (640, 212)               # kotak cari aset di dialog lampiran
FIRST_ROW = (500, 258)            # baris pertama hasil pencarian aset
ADD_TO_PROMPT = (818, 726)
UPLOAD = (315, 733)
CREDITS_RE = re.compile(r"(?:will use|akan menggunakan)\s+(\d+)\s+(?:credits?|kredit)\b", re.I)
PROGRESS_RE = re.compile(r"\b\d{1,3}%")
LAST = {"credits": 0, "balance": None}      # kredit batch terakhir (anggaran --approve-credits lintas link)


class FlowError(Exception):
    pass


class GenBlocked(FlowError):
    pass


class CreditsLow(FlowError):
    """Saldo kredit akun Flow ini kurang untuk batch; pemanggil boleh pindah ke akun Flow lain."""
    def __init__(self, balance, need):
        super().__init__(f"kredit akun Flow kurang: sisa {balance}, butuh {need}")
        self.balance, self.need = balance, need


from .paths import get_flow_profile_dir, get_app_data_dir


def default_profile():
    env_p = os.environ.get("FLOW_PROFILE")
    if env_p:
        return Path(env_p)
    # Check legacy local path for backward compatibility if it exists
    legacy = Path.home() / ".google-flow-creator" / "browser-profile"
    if (legacy / "Default").exists():
        return legacy
    return get_flow_profile_dir("default")


def parse_credits(text):
    """Read the displayed per-render quote in English or Indonesian."""
    m = CREDITS_RE.search(text or "")
    return int(m.group(1)) if m else None


def is_generating(text):
    """Ada persentase (mis. '31%') di halaman = masih ada klip yang dirender."""
    return bool(PROGRESS_RE.search(text or ""))


def check_settings(text):
    """Pastikan pengaturan Flow sesuai rencana; mengembalikan daftar masalah (kosong = aman)."""
    issues = []
    for label, pattern in FLOW_OPTIONS:
        if not re.search(r"(?<!\w)(?:" + pattern + r")(?!\w)", text or "", re.I):
            issues.append(label)
    return issues


BALANCE_RE = re.compile(r"(\d[\d,.]*)\s+Google Flow credits", re.I)


def parse_balance(text):
    """'545 Google Flow credits' (menu akun) -> 545."""
    m = BALANCE_RE.search(text or "")
    return int(re.sub(r"[,.]", "", m.group(1))) if m else None


def read_credits(pg):
    """Buka menu 'Account details' di beranda Flow dan baca sisa kredit; None jika tidak terbaca."""
    pg.goto(HOME); pg.wait_for_timeout(5000)
    if pg.get_by_label("Account details").count() == 0:
        return None
    pg.get_by_label("Account details").first.click(); pg.wait_for_timeout(2500)
    bal = parse_balance(pg.evaluate("document.body.innerText"))
    pg.keyboard.press("Escape"); pg.wait_for_timeout(500)
    return bal


def credit_budget(n_clips, per_clip):
    return n_clips * per_clip


def _playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise FlowError("Playwright belum terpasang: pip install playwright (memakai Chrome yang sudah ada, tanpa unduhan browser)")
    return sync_playwright()


def _open(p, profile, headless=None, offscreen=False, chrome_exe=None):
    if headless is None:
        headless = os.environ.get("FLOW_HEADLESS", "1").lower() not in ("", "0", "false", "no")
    try:
        args = ["--window-size=1280,1000", "--force-device-scale-factor=1"]
        if offscreen or os.environ.get("FLOW_OFFSCREEN"):
            args.append("--window-position=-3200,-3200")
        exe = chrome_exe or os.environ.get("CHROME_PATH")
        if os.environ.get("FLOW_USE_PLAYWRIGHT_CHROMIUM", "").lower() in ("1", "true", "yes"):
            where = {}
        else:
            where = {"executable_path": exe} if exe else {"channel": "chrome"}
        return p.chromium.launch_persistent_context(str(profile), headless=headless, viewport=VIEW, accept_downloads=True, args=args, **where)
    except Exception as e:
        raise FlowError("Chrome profil Flow tidak bisa dibuka. Tutup semua jendela Chrome Flow/MCP Flow yang memakai profil yang sama, "
                        f"lalu ulangi. ({str(e)[:120]})")


def _page(ctx):
    return ctx.pages[0] if ctx.pages else ctx.new_page()


def signed_in(page):
    return page.locator("[aria-label^='Google Account'], [aria-label^='Akun Google']").count() > 0


GOOGLE_SESSION_COOKIES = frozenset({
    'SID', 'HSID', 'SSID', 'APISID', 'SAPISID',
    '__Secure-1PSID', '__Secure-3PSID',
})


def has_google_session(cookies):
    """Detect a live Google sign-in without relying on Flow's changing avatar UI."""
    now = time.time()
    return any(
        str(cookie.get('name')) in GOOGLE_SESSION_COOKIES
        and str(cookie.get('domain', '')).lstrip('.').lower().endswith('google.com')
        and not (isinstance(cookie.get('expires'), (int, float)) and 0 < cookie['expires'] < now)
        for cookie in cookies
    )


def chrome_path():
    """Chrome terpasang (untuk login manual tanpa kendali otomatis)."""
    import shutil, sys
    if os.environ.get('FLOW_USE_PLAYWRIGHT_CHROMIUM', '').lower() in ('1', 'true', 'yes'):
        with _playwright() as playwright:
            executable = playwright.chromium.executable_path
        if Path(executable).is_file():
            return executable
        raise FlowError('Chromium Playwright belum terpasang di server')
    if sys.platform == "darwin":
        from . import osx
        return osx.chrome_path()
    cands = [os.environ.get("CHROME_PATH"), shutil.which("chrome"), shutil.which("google-chrome"), r"C:\Program Files\Google\Chrome\Application\chrome.exe",
             r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
             str(Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "Application" / "chrome.exe")]
    return next((c for c in cands if c and os.path.isfile(c)), None)


def _debug_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def _wait_desktop_login_close(browser, process, page, context, cookies, deadline, log):
    log('Login terdeteksi. Tutup Chrome setelah selesai untuk menyimpan sesi dan melanjutkan generate.')
    while time.monotonic() < deadline and process.poll() is None and browser.is_connected():
        try:
            cookies = context.cookies([HOME]) or cookies
            page.wait_for_timeout(500)
        except Exception:
            break
    return cookies


def login(profile=None, wait_s=900, log=print, spawn=None, verify=None, save_session=None):
    """Buka Chrome biasa, amati login melalui CDP lokal, simpan sesi, lalu tutup Chrome.

    Aplikasi tidak membaca kata sandi atau kode verifikasi. Parameter `verify` tetap
    mendukung pemanggil lama yang menutup Chrome secara manual.
    """
    if (os.environ.get('FLOW_VIDEO_REMOTE', '').lower() in ('1', 'true', 'yes')
            and os.environ.get('FLOW_VIDEO_DESKTOP', '').lower() not in ('1', 'true', 'yes')):
        raise FlowError('Login interaktif tidak tersedia di Modal. Login Google Flow di PC, '
                        'lalu gunakan Impor cookie Flow pada dashboard untuk menambahkan akun.')
    profile = Path(profile or default_profile())
    profile.mkdir(parents=True, exist_ok=True)
    exe = chrome_path()
    if not exe and not spawn:
        raise FlowError("Google Chrome tidak ditemukan; pasang Chrome lalu ulangi")
    port = _debug_port()
    argv = [exe, f"--user-data-dir={profile}", f"--remote-debugging-port={port}",
            "--remote-debugging-address=127.0.0.1", "--remote-allow-origins=*",
            "--no-first-run", "--no-default-browser-check", "--new-window", HOME]
    if hasattr(os, "geteuid") and os.geteuid() == 0:      # Chrome menolak jalan sebagai root (VPS) tanpa --no-sandbox
        argv.insert(1, "--no-sandbox")
    if os.environ.get('FLOW_VIDEO_DESKTOP', '').lower() in ('1', 'true', 'yes'):
        log('Chrome dibuka di desktop Modal. Buka desktop untuk login; tutup Chrome setelah selesai.')
    else:
        log("Chrome dibuka. Silakan login ke Google Flow; jendela akan tertutup otomatis setelah sesi tersimpan.")
    import subprocess
    proc = (spawn or subprocess.Popen)(argv)

    # Kompatibilitas untuk pemanggil lama dan pengujian berbasis proses palsu.
    if verify is not None:
        try:
            proc.wait(timeout=wait_s)
        except subprocess.TimeoutExpired:
            proc.terminate()
            raise FlowError("batas waktu login habis")
        if not verify(profile):
            raise FlowError("belum terdeteksi login ke Google Flow")
        log("Login terdeteksi, sesi tersimpan.")
        return True

    browser = None
    deadline = time.monotonic() + wait_s
    try:
        with _playwright() as playwright:
            while time.monotonic() < deadline and browser is None:
                if proc.poll() is not None:
                    raise FlowError("jendela Chrome ditutup sebelum login terdeteksi")
                try:
                    browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}", timeout=1500)
                except Exception:
                    time.sleep(0.5)
            if browser is None:
                raise FlowError("Chrome tidak dapat dipantau untuk menyimpan sesi login")

            while time.monotonic() < deadline:
                if proc.poll() is not None or not browser.is_connected():
                    raise FlowError("jendela Chrome ditutup sebelum login terdeteksi")
                contexts = browser.contexts
                context = contexts[0] if contexts else None
                pages = context.pages if context else []
                page = next((item for item in pages if urllib.parse.urlparse(item.url).hostname == 'flow.google.com'), None)
                try:
                    if page:
                        cookies = context.cookies([HOME])
                        if not (signed_in(page) or has_google_session(cookies)):
                            time.sleep(1)
                            continue
                        if not cookies or not has_google_session(cookies):
                            raise FlowError("login terdeteksi tetapi sesi Google Flow kosong")
                        log("Login terdeteksi. Menyimpan sesi terenkripsi...")
                        if save_session:
                            save_session(cookies)
                        if os.environ.get('FLOW_VIDEO_DESKTOP', '').lower() in ('1', 'true', 'yes'):
                            cookies = _wait_desktop_login_close(
                                browser, proc, page, context, cookies, deadline, log)
                            if save_session:
                                save_session(cookies)
                            log('Sesi desktop tersimpan. Siap melanjutkan generate.')
                        else:
                            log("Sesi tersimpan. Menutup jendela Chrome...")
                        if browser.is_connected():
                            browser.close()
                        browser = None
                        if proc.poll() is None:
                            proc.terminate()
                        try:
                            proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                        return cookies
                except FlowError:
                    raise
                except Exception:
                    pass
                time.sleep(1)
            raise FlowError("batas waktu login habis")
    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass
        if proc.poll() is None:
            proc.terminate()


def status(profile=None, with_credits=False):
    """True/False login; dengan with_credits=True -> (login, sisa kredit atau None)."""
    profile = Path(profile or default_profile())
    if not profile.exists():
        return (False, None) if with_credits else False
    try:
        with _playwright() as p:
            ctx = _open(p, profile)
            try:
                pg = _page(ctx); pg.goto(HOME); pg.wait_for_timeout(6000)
                # Flow's avatar label is not stable across UI variants. A valid
                # Google session cookie is the durable signal used by login too.
                ok = signed_in(pg) or has_google_session(ctx.cookies())
                if not with_credits:
                    return ok
                return ok, (read_credits(pg) if ok else None)
            finally:
                ctx.close()
    except FlowError:
        raise
    except Exception as exc:
        # Playwright timeouts/network errors must reach callers as FlowError so
        # account selection skips this account instead of failing the whole job.
        raise FlowError(f'Status akun Flow tidak dapat dibaca: {exc}') from exc


def _videos_tab(pg):
    """Filter 'Videos' di sidebar; belum ada di proyek yang masih kosong (lalu semua media = tanpa video)."""
    tab = pg.get_by_text("Videos", exact=True)
    if tab.count() == 0:
        return False
    tab.first.click()
    pg.wait_for_timeout(2500)
    return True


_TILES_JS = """() => [...document.querySelectorAll('*')].filter(e => e.children.length === 0 && e.textContent.trim() === 'play_circle')
  .map(e => { let t = e, r = t.getBoundingClientRect();
              while (t.parentElement && (r.width < 100 || r.height < 100)) { t = t.parentElement; r = t.getBoundingClientRect(); }
              return [r.x + r.width / 2, r.y + r.height / 2, r.width, r.height]; })
  .filter(c => c[2] >= 100 && c[2] < 500 && c[3] >= 100 && c[1] > 60)"""


def _tiles(pg):
    """Pusat tile video yang terlihat, urut baris lalu kolom (terbaru di depan)."""
    uniq = {(round(c[0]), round(c[1])): c for c in pg.evaluate(_TILES_JS)}        # satu tile bisa punya dua ikon play
    return sorted(uniq.values(), key=lambda c: (round(c[1] / 40), c[0]))


def _video_count(pg):
    return len(_tiles(pg))


NET_ERR_RE = re.compile(r"ERR_NAME_NOT_RESOLVED|ERR_INTERNET_DISCONNECTED|ERR_NETWORK_CHANGED|ERR_CONNECTION|ERR_TIMED_OUT|Page\.goto: Timeout", re.I)


def is_net_error(exc):
    return bool(NET_ERR_RE.search(str(exc)))


def wait_online(max_s=300, log=print):
    """Tunggu DNS/internet PC pulih (hotspot sering putus-nyambung). True bila flow.google.com bisa diselesaikan sebelum batas waktu."""
    import socket
    end = time.time() + max_s
    while time.time() < end:
        try:
            socket.setdefaulttimeout(6)
            socket.getaddrinfo("flow.google.com", 443)
            return True
        except OSError:
            log("internet PC belum pulih, menunggu...")
            time.sleep(10)
    return False


def _clear_overlays(pg, log=print):
    """Akun Flow baru membuka proyek dengan pengantar ("Got it") dan panel Agent di kanan yang menutupi kolom prompt video biasa.
    Tutup pengantar, tutup panel Agent, dan matikan toggle Agent supaya kolom prompt dan chip pengaturan video yang terlihat."""
    for _ in range(3):
        try:
            pg.get_by_role("button", name="Got it").first.click(timeout=1500); pg.wait_for_timeout(700)
        except Exception:
            break
    try:
        if pg.get_by_text("Untitled session").count() or pg.get_by_text("What would you like to create?").count():
            pg.get_by_role("button", name="Close").first.click(timeout=3000); pg.wait_for_timeout(1200)
            log("panel Agent ditutup")
    except Exception:
        pass
    try:
        ag = pg.get_by_role("button", name="Agent")
        if ag.count() and ag.first.get_attribute("aria-pressed") == "true":
            ag.first.click(timeout=3000); pg.wait_for_timeout(1000)
            log("mode Agent dimatikan")
    except Exception:
        pass


def _new_project(pg):
    pg.goto(HOME); pg.wait_for_timeout(5000)
    trigger = pg.get_by_text(re.compile(r"^(New project|Project baru|Proyek baru|Mulai sesi baru|Start Creating)$", re.I))
    if not trigger.count():
        trigger = pg.get_by_label(re.compile(r"^(New project|Project baru|Proyek baru|Mulai sesi baru|Start Creating)$", re.I))
    if not trigger.count():
        raise FlowError('Tombol proyek baru tidak ditemukan di halaman Flow')
    trigger.first.click()
    pg.wait_for_url(re.compile(r"/project/"), timeout=30000)
    pg.wait_for_timeout(4000)
    _clear_overlays(pg)
    return pg.url


def _upload_file(pg, ref):
    """Unggah foto referensi; klik koordinat dulu, lalu tombol bertulisan Upload, terakhir input file langsung."""
    # Port dari flowgen.js terbaru: UI agentik menampilkan tombol dengan ikon
    # dan teks "Upload media", sehingga pencarian exact-text versi lama gagal.
    modern = pg.get_by_role(
        'button', name=re.compile(r'Upload media|Unggah media', re.I))
    for index in range(modern.count()):
        node = modern.nth(index)
        if not node.is_visible():
            continue
        try:
            with pg.expect_file_chooser(timeout=8000) as fc:
                node.click()
            fc.value.set_files(str(ref))
            return
        except Exception:
            pg.wait_for_timeout(1000)
    for how in ("xy", "text", "text"):
        try:
            with pg.expect_file_chooser(timeout=8000) as fc:
                if how == "xy":
                    pg.mouse.click(*UPLOAD)
                else:
                    pg.get_by_text(re.compile(r"^\s*(Upload( image)?|Unggah)\s*$", re.I)).first.click()
            fc.value.set_files(str(ref))
            return
        except Exception:
            pg.wait_for_timeout(1500)
    inp = pg.locator("input[type=file]")
    if inp.count():
        inp.first.set_input_files(str(ref))
        return
    raise RuntimeError("unggah referensi gagal: tidak ada pemilih file")


def _attach_ref(pg, ref, uploaded):
    try:
        btn = pg.get_by_label(re.compile(r"Tambahkan bahan ke kotak perintah|Add ingredients? to (?:the )?prompt box", re.I))
        if btn.count() and btn.first.is_visible():
            btn.first.click()
        else:
            pg.mouse.click(*PLUS)
    except Exception:
        pg.mouse.click(*PLUS)
    pg.wait_for_timeout(2000)
    if ref.name not in uploaded:
        _upload_file(pg, ref)
        pg.wait_for_timeout(8000)
        agree = pg.get_by_role(
            'button', name=re.compile(r'^(I agree|Saya setuju)$', re.I))
        if agree.count() and agree.first.is_visible():
            agree.first.click()
            pg.wait_for_timeout(1500)
        uploaded.add(ref.name)
    search = pg.get_by_role('textbox', name=re.compile(
        r'Search assets|Telusuri aset|Cari aset', re.I))
    if search.count() and search.first.is_visible():
        search.first.fill(ref.stem)
        pg.wait_for_timeout(2500)
    assets = pg.locator('button:visible').filter(
        has_text=re.compile(re.escape(ref.name), re.I))
    if not assets.count():
        raise FlowError(
            f'Foto referensi {ref.name} tidak ditemukan di aset Flow; generate dibatalkan')
    ingredient = pg.get_by_role(
        'button', name=re.compile(r'^(Ingredient|Bahan)', re.I))

    def attached():
        return any(ingredient.nth(i).is_visible() for i in range(ingredient.count()))

    # Uploaded assets can already be selected. Clicking a selected card toggles
    # it off and disables Add to prompt in Flow's selection picker.
    asset = assets.last
    selected = any(asset.get_attribute(a) == 'true'
                   for a in ('aria-selected', 'aria-checked', 'aria-pressed'))
    selected = selected or asset.get_attribute('data-state') in ('checked', 'selected', 'on')
    if not selected:
        # Flow overlays the card with a transparent rename input.
        asset.click(force=True, timeout=10000)
    add = pg.get_by_role('button', name=re.compile(
        r'^(?:Add to prompt|Tambahkan ke perintah|Tambahkan ke prompt)$', re.I))
    # Wait for upload processing/selection state to enable the action. Newer
    # pickers attach directly on the card click and need no Add action.
    clicked = False
    for _ in range(60):
        if attached():
            return
        if not clicked:
            for index in range(add.count()):
                button = add.nth(index)
                if button.is_visible() and button.is_enabled():
                    button.click(timeout=10000)
                    clicked = True
                    break
        pg.wait_for_timeout(500)
    if not clicked:
        raise FlowError(
            f'Tombol Add to prompt tidak aktif untuk {ref.name}; generate dibatalkan')
    raise FlowError(
        f'Lampiran {ref.name} belum terverifikasi di composer Flow; generate dibatalkan')


def _open_settings(pg):
    """Utamakan label tombol; koordinat hanya cadangan untuk UI lama."""
    pg.keyboard.press("Escape")
    trigger = pg.get_by_label(re.compile(
        r"^(Settings trigger|Pemicu setelan)$", re.I))
    for i in range(trigger.count()):
        node = trigger.nth(i)
        if node.is_visible():
            node.click(timeout=4000)
            pg.wait_for_timeout(1200)
            return
    summary = pg.get_by_role('button').filter(has_text=re.compile(
        r'(?:Video|Image|Gambar)[\s\S]*[x\u00d7]\s*\d+', re.I))
    for i in range(summary.count()):
        if summary.nth(i).is_visible():
            summary.nth(i).click(timeout=4000)
            pg.wait_for_timeout(1200)
            return
    trigger = pg.get_by_label(re.compile(r"^(Settings|Setelan)$", re.I))
    for i in range(trigger.count()):
        if trigger.nth(i).is_visible():
            trigger.nth(i).click(timeout=4000)
            pg.wait_for_timeout(1200)
            return
    # Autopost fallback to coordinate PILL
    try:
        pg.mouse.click(*PILL)
        pg.wait_for_timeout(1200)
        return
    except Exception:
        pass
    raise FlowError('Tombol setelan composer Flow tidak ditemukan; generate belum dikirim')


FLOW_OPTIONS = (
    ("Video", r"Video"),
    ("Ingredients", r"Ingredients|Bahan"),
    ("Omni 1.1 Flash", r"Omni\s+1\.1\s+Flash"),
    ("9:16", r"9\s*:\s*16"),
    ("720p", r"720\s*p"),
    ("10s", r"10\s*(?:s|sec(?:onds)?|detik|dtk)"),
    ("x1", r"[x×]\s*1|1\s*[x×]"),
)


def _choose_setting(pg, pattern):
    # Try accessible roles first (radio, tab, button, menuitemradio, option)
    # Allows for optional icon prefix or bounded label text (e.g. "videocam Video" or "Video")
    regex = re.compile(r"(?:^|\b|\s)(?:" + pattern + r")(?:\b|\s|$)", re.I)
    for role in ('radio', 'tab', 'button', 'menuitemradio', 'option'):
        controls = pg.get_by_role(role, name=regex)
        for index in range(controls.count()):
            node = controls.nth(index)
            if node.is_visible() and node.is_enabled():
                is_selected = any(node.get_attribute(a) == 'true' for a in ('aria-checked', 'aria-selected', 'aria-pressed'))
                if not is_selected:
                    is_selected = node.get_attribute('data-state') in ('checked', 'selected', 'on', 'active')
                if is_selected:
                    return True
                node.click(timeout=4000)
                pg.wait_for_timeout(500)
                return True
    if pattern.startswith('Omni'):
        family = pg.get_by_role('button', name='Select model family')
        if family.count():
            if re.search(pattern, family.first.inner_text(), re.I):
                return True
            family.first.click()
            option = pg.get_by_role('menuitem', name=re.compile(pattern, re.I))
            if option.count():
                option.first.click()
                return True
    options = pg.get_by_text(regex)
    for i in range(options.count()):
        node = options.nth(i)
        if not node.is_visible() or not node.is_enabled():
            continue
        is_selected = any(node.get_attribute(a) == "true" for a in ("aria-selected", "aria-checked", "aria-pressed"))
        if not is_selected:
            try:
                is_selected = node.evaluate("""el => {
                    const c = el.closest('button, [role="radio"], [role="tab"], [role="button"], label') || el;
                    return ['aria-selected', 'aria-checked', 'aria-pressed'].some(a => c.getAttribute(a) === 'true') ||
                           ['checked', 'on', 'active', 'selected'].includes(c.getAttribute('data-state')) ||
                           !!c.querySelector('input:checked');
                }""")
            except Exception:
                is_selected = False
        if is_selected:
            return True
        node.click(timeout=4000)
        pg.wait_for_timeout(500)
        return True
    return False


def ensure_settings(pg, log=print):
    """Pilih model sebelum resolusi/durasi; jangan lanjut bila opsi wajib gagal."""
    _open_settings(pg)
    try:
        for label, pattern in FLOW_OPTIONS:
            selected = False
            for attempt in range(2):
                if attempt:
                    _open_settings(pg)
                try:
                    selected = _choose_setting(pg, pattern)
                    if not selected and label == "Omni 1.1 Flash":
                        if _choose_setting(pg, r"Model|(?:Omni|Veo)\b[^\n]*"):
                            selected = _choose_setting(pg, pattern)
                except Exception:
                    selected = False
                if selected:
                    break
            if not selected:
                raise FlowError(f"pengaturan Flow: '{label}' tidak tersedia atau tidak bisa dipilih. "
                                "Periksa pilihan model dan pengaturan pada akun/proyek Flow ini; generate belum dikirim.")
            log(f"pengaturan Flow: {label}")
    finally:
        pg.keyboard.press("Escape"); pg.wait_for_timeout(500)


def ensure_single_output(pg):
    """Require a selected x1 control, not merely an available x1 option."""
    _open_settings(pg)
    try:
        pattern = r"[x×]\s*1|1\s*[x×]"
        if not _choose_setting(pg, pattern):
            raise FlowError('Jumlah output x1 tidak tersedia; generate dibatalkan.')
        selected = pg.get_by_text(re.compile(r"^\s*(?:" + pattern + r")\s*$", re.I)).evaluate_all("""nodes => nodes.filter(n => {
            if (!n.getClientRects().length) return false;
            const control = n.closest('button, [role="radio"], [role="option"], [role="menuitemradio"], label') || n;
            return [n, control].some(e => ['aria-selected', 'aria-checked', 'aria-pressed'].some(a => e.getAttribute(a) === 'true') || ['checked', 'on', 'active'].includes(e.getAttribute('data-state'))) || !!control.querySelector('input:checked');
        }).map(n => n.textContent)""")
        if not selected:
            raise FlowError('Jumlah output x1 belum terkonfirmasi aktif; generate dibatalkan agar tidak membuat dua video.')
    finally:
        pg.keyboard.press('Escape')
        pg.wait_for_timeout(500)


def _settings_text(pg):
    _open_settings(pg)
    text = pg.evaluate("document.body.innerText")
    pg.keyboard.press("Escape"); pg.wait_for_timeout(500)
    return text


def _prompt_box(pg):
    composer = pg.get_by_role('textbox', name=re.compile(
        r'Apa yang ingin Anda buat|What do you want', re.I))
    if composer.count():
        return composer.first
    return pg.locator("textarea:visible, [contenteditable='true']:visible, [role='textbox']:visible").last


def _agentic_composer(pg):
    box = pg.get_by_role('textbox', name=re.compile(
        r'Apa yang ingin Anda buat|What do you want', re.I))
    submit = pg.get_by_role('button', name=re.compile(
        r'Mulai pembuatan|Start generation', re.I))
    return bool(box.count() and submit.count())


def _start_generation(pg, log=print, on_submit=None, on_rpc_request=None,
                      agentic=False):
    """Klik sekali, catat ketidakpastian sebelum submit, lalu tunggu konfirmasi."""
    btn = pg.get_by_role("button", name=re.compile(
        r"^(Start generation|Mulai pembuatan)$", re.I))
    if not hasattr(btn, 'count') or btn.count() == 0:
        alt = pg.locator("[aria-label*='Start generation'], [aria-label*='Mulai pembuatan'], button:has-text('Start generation'), button:has-text('Mulai pembuatan')")
        if hasattr(alt, 'count') and alt.count() > 0:
            btn = alt
    def capture(request):
        if not on_rpc_request or request.method != 'POST' or '/data/batchexecute' not in request.url:
            return
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(request.url).query)
        form = urllib.parse.parse_qs(request.post_data or '')
        # Deliberately omit Cookie headers, CSRF `at`, session id and request counter.
        on_rpc_request({
            'rpcids': query.get('rpcids', [''])[0],
            'source_path': query.get('source-path', [''])[0],
            'f_req': form.get('f.req', [''])[0],
        })
    ensure_single_output(pg)
    if on_rpc_request:
        pg.on('request', capture)
    for attempt in range(1):
        enabled = False
        for w in range(35):                                     # tombol aktif setelah prompt + referensi siap
            try:
                if btn.first.is_enabled():
                    enabled = True
                    break
            except Exception:
                pass
            if w in (8, 18):
                try:
                    tb = _prompt_box(pg)
                    tb.click(timeout=1500)
                    pg.keyboard.press("End")
                    pg.keyboard.press("Space")
                    pg.keyboard.press("Backspace")
                except Exception:
                    pass
            pg.wait_for_timeout(1000)
        if not enabled:
            if on_rpc_request:
                pg.remove_listener('request', capture)
            raise FlowError("Tombol Generate belum aktif; render belum dikirim")
        # Persist uncertainty BEFORE the click: a timeout may occur after Google accepts it.
        if on_submit:
            on_submit()
        LAST['sent'] = True
        # A click timeout can occur after the server accepted it. Never dispatch
        # a second click (or Enter) as recovery.
        btn.first.click(timeout=10000)
        if agentic:
            pg.wait_for_timeout(2500)
            return
        for _ in range(25):
            pg.wait_for_timeout(2500)
            body = pg.evaluate("document.body.innerText")
            body_str = "" if body is None or not isinstance(body, (str, bytes)) else str(body)
            if is_generating(body_str) or re.search(r"Generating|Creating|Sedang membuat|Processing", body_str, re.I):
                if on_rpc_request:
                    pg.remove_listener('request', capture)
                return
            if re.search(r"^Failed$", body_str, re.M):
                why = re.search(r"^Failed" + chr(10) + r"(.+?)$", body_str, re.M)
                raise GenBlocked(f"Flow langsung menandai Failed: {(why.group(1) if why else '')[:140]}")
    raise FlowError('Status setelah klik generate belum pasti. Periksa proyek; tidak dikirim ulang otomatis.')


def generate_batch(jobs, profile=None, approve_credits=None, project_url=None, timeout_s=1800,
                   log=print, on_submit=None, on_rpc_request=None, headless=None,
                   offscreen=False, chrome_exe=None, details=None):
    """jobs = [{"prompt": str, "ref": Path foto referensi, "out": Path .mp4}]. Mengembalikan daftar Path hasil (urut sama).
    Mengirim SEMUA klip lalu menunggu bersamaan. approve_credits wajib >= total kredit (batas pengaman pemakaian kredit)."""
    if not jobs:
        return []
    LAST.update(sent=False, project_url=None, credits=0, balance=None)
    profile = Path(profile or default_profile())
    n = len(jobs)
    with _playwright() as p:
        ctx = _open(p, profile, headless=headless, offscreen=offscreen,
                    chrome_exe=chrome_exe)
        try:
            pg = _page(ctx)
            if project_url:
                pg.goto(project_url); pg.wait_for_timeout(5000); _clear_overlays(pg, log)
            else:
                pg.goto(HOME); pg.wait_for_timeout(5000)
                if not (signed_in(pg) or has_google_session(ctx.cookies())):
                    raise FlowError("belum login Flow: jalankan `autopost flow login`")
                project_url = _new_project(pg)
            LAST['project_url'] = project_url
            log(f"proyek Flow: {project_url}")
            # Match Autopost: choose and validate real UI settings; do not infer
            # model/duration/cost from the presence of a generic composer.
            ensure_settings(pg, log)
            text = _settings_text(pg)
            issues = check_settings(text)
            if issues:
                raise FlowError("pengaturan Flow belum sesuai (" + ", ".join(issues) + "). Periksa model, durasi, rasio, resolusi, dan jumlah keluaran.")
            per = parse_credits(text)
            if per is None:
                raise FlowError("biaya kredit per klip tidak terbaca; generate belum dikirim")
            total = credit_budget(n, per)
            log(f"{n} klip x {per} kredit = {total} kredit")
            if approve_credits is None or total > approve_credits:
                raise FlowError(f"butuh persetujuan kredit: total {total} kredit (setujui dengan --approve-credits {total})")
            LAST["balance"] = read_credits(pg)
            if LAST["balance"] is not None and LAST["balance"] < total:
                raise CreditsLow(LAST["balance"], total)
            pg.goto(project_url); pg.wait_for_timeout(4000); _clear_overlays(pg, log)
            LAST["credits"] = total
            if details is not None:
                details.update(credits=total, balance=LAST["balance"],
                               project_url=project_url)
            _videos_tab(pg)
            base = _video_count(pg)
            pg.goto(project_url); pg.wait_for_timeout(4000); _clear_overlays(pg, log)
            uploaded = set()
            for i, j in enumerate(jobs, 1):
                for ref in (j.get("refs") or ([j["ref"]] if j.get("ref") else [])):
                    _attach_ref(pg, Path(ref), uploaded)
                prompt = j["prompt"]
                tb = _prompt_box(pg)
                try:
                    tb.click(timeout=3000)
                    pg.keyboard.press("ControlOrMeta+A")
                    pg.keyboard.press("Backspace")
                except Exception:
                    pass
                tb.fill(prompt)
                try:
                    tb.dispatch_event("input")
                    tb.dispatch_event("change")
                except Exception:
                    pass
                pg.wait_for_timeout(800)
                if pg.get_by_role("button", name=re.compile(
                        r"Start generation|Mulai pembuatan", re.I)).count() == 0:
                    raise FlowError("tombol Start generation tidak ditemukan; UI Flow berubah")
                _start_generation(pg, log, on_submit=on_submit,
                                  on_rpc_request=on_rpc_request)
                LAST["sent"] = True
                log(f"klip {i}/{n} dikirim"); pg.wait_for_timeout(3000)
            end = time.time() + timeout_s
            ready, stable, last, got = False, 0, -1, 0
            while time.time() < end:
                pg.wait_for_timeout(15000)
                pg.reload(); pg.wait_for_timeout(6000)
                _videos_tab(pg)
                body = pg.evaluate("document.body.innerText")
                gen = is_generating(body)
                cnt = _video_count(pg)
                nfail = len(re.findall(r"^Failed$", body, re.M))
                if nfail and not gen and cnt - base + nfail >= n:        # sisanya ditandai Failed oleh Flow: jangan menunggu 30 menit
                    why = re.search(r"^Failed" + chr(10) + r"(.+?)$", body, re.M)
                    got = cnt - base
                    if got <= 0:
                        raise GenBlocked(f"Flow menandai generate Failed: {(why.group(1) if why else '')[:140]}")
                    log(f"PERINGATAN: {nfail} klip Failed di Flow; lanjut dengan {got} yang jadi")
                    ready = True; break
                if not gen and cnt >= base + n:
                    got = n; ready = True; break
                stable = stable + 1 if (not gen and cnt == last and cnt > base) else 0
                last = cnt
                if stable >= 4:                       # tidak ada yang dirender lagi dan jumlah tetap: sisanya gagal/ditolak Flow
                    got = cnt - base; ready = True
                    log(f"PERINGATAN: hanya {got} dari {n} klip jadi (sisanya gagal/ditolak Flow); periksa kecocokan tiap hasil")
                    break
            if not ready:
                raise FlowError(f"klip belum selesai dalam {timeout_s // 60} menit (atau ada yang gagal/ditolak Flow); cek proyek: {project_url}")
            jobs = jobs[:got]
            return _download(pg, project_url, jobs, log)
        finally:
            ctx.close()


def _download(pg, project_url, jobs, log=print):
    n = len(jobs)
    outs = []
    for k, j in enumerate(jobs):                      # tile terbaru di urutan pertama: klip ke-k ada di posisi n-1-k
        pg.goto(project_url); pg.wait_for_timeout(5000); _clear_overlays(pg, log); _videos_tab(pg)
        tiles = _tiles(pg)
        if len(tiles) < n:
            raise FlowError(f"hanya {len(tiles)} video terlihat di proyek, butuh {n}: {project_url}")
        x, y = tiles[n - 1 - k][:2]
        pg.mouse.click(x, y); pg.wait_for_timeout(3000)
        btn = pg.get_by_label("Download media").first
        with pg.expect_download(timeout=60000) as d:
            btn.click()
            pg.wait_for_timeout(1000)
            try:
                mp4_opt = pg.locator("[role='menuitem'], [role='option']").filter(
                    has_text=re.compile(r"720p|Ukuran asli|Original size", re.I)
                ).first
                if mp4_opt.is_visible():
                    mp4_opt.click()
                else:
                    orig = pg.get_by_text("Original size").first
                    if orig.is_visible():
                        orig.click()
                    else:
                        pg.locator("[role='menuitem'], [role='option']").first.click()
            except Exception:
                pass
        out = Path(j["out"]); out.parent.mkdir(parents=True, exist_ok=True)
        d.value.save_as(str(out)); outs.append(out)
        log(f"klip {k + 1}/{n} diunduh: {out.name}")
    return outs


def download_batch(jobs, project_url, profile=None, log=print):
    """Pemulihan: unduh klip dari proyek Flow yang sudah selesai (tanpa kredit baru)."""
    profile = Path(profile or default_profile())
    with _playwright() as p:
        ctx = _open(p, profile)
        try:
            return _download(_page(ctx), project_url, jobs, log)
        finally:
            ctx.close()

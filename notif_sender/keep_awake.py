from playwright.sync_api import sync_playwright

url = 'https://ttfl-doctor.streamlit.app/'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(url, wait_until="domcontentloaded")
    try:
        page.get_by_test_id("wakeup-button-viewer").click(timeout=10_000)
    except Exception:
        pass  # app was already awake
    # Community Cloud serves the app inside an iframe
    (page.frame_locator('iframe[title="streamlitApp"]')
         .locator('[data-testid="stApp"]')
         .wait_for(timeout=120_000))
    
    page.wait_for_timeout(5_000)
    browser.close()
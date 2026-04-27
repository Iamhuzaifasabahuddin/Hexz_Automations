from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException
import os
import time

# Add all your Streamlit URLs here
STREAMLIT_URLS = [
    "https://blinkdigitallytickets.streamlit.app/",
    "https://blinkdigitally.streamlit.app/",
    "https://hexzbudget.streamlit.app/",
    "https://hexzridetracker.streamlit.app/",
]

def wake_app(driver, url):
    print(f"\n🌐 Opening: {url}")
    try:
        driver.get(url)

        wait = WebDriverWait(driver, 15)

        try:
            button = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(),'Yes, get this app back up')]")
                )
            )
            print("⚡ Wake-up button found. Clicking...")
            button.click()

            try:
                wait.until(
                    EC.invisibility_of_element_located(
                        (By.XPATH, "//button[contains(text(),'Yes, get this app back up')]")
                    )
                )
                print("✅ App wake triggered successfully")
            except TimeoutException:
                print("❌ Button didn’t disappear (wake may have failed)")

        except TimeoutException:
            print("✅ No wake button → app already active")

    except Exception as e:
        print(f"❌ Error with {url}: {e}")


def main():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    try:
        for url in STREAMLIT_URLS:
            wake_app(driver, url)
            time.sleep(10)
    finally:
        driver.quit()
        print("\n🏁 All apps processed.")


if __name__ == "__main__":
    main()
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import pandas as pd
import time

# --- SETUP FIREFOX HEADLESS BROWSER ---
options = webdriver.FirefoxOptions()
options.add_argument("--headless")
driver = webdriver.Firefox(options=options)


# --- INITIALIZE ---
url = "https://dalonline.dal.ca/PROD/fysktime.P_DisplaySchedule?s_term=202620&s_subj=CSCI&s_district=100"
driver.get(url)
time.sleep(2)  # let the JS load

all_html_pages = []

# --- PAGINATION LOOP ---
while True:
    # Wait and capture current page source
    time.sleep(1)
    html = driver.page_source
    all_html_pages.append(html)

    # Try to find and click the "next 20 CSCI classes >>" link
    try:
        next_link = driver.find_element(By.LINK_TEXT, "next 20 CSCI classes >>")
        next_link.click()
    except:
        print("✅ No more pages. Stopping.")
        break

# --- CLOSE BROWSER ---
driver.quit()

# --- PARSE ALL PAGES ---
day_labels = ["M", "T", "W", "R", "F"]
all_data = []

def extract_data_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.find_all("tr")
    current_course_title = None
    page_data = []

    for row in rows:
        cols = row.find_all("td")
        col_classes = [c.get("class", []) for c in cols]
        col_text = [col.get_text(strip=True).replace('\xa0', ' ') for col in cols]

        if any("detthdr" in c for classes in col_classes for c in classes):
            for col in cols:
                if "CSCI" in col.text:
                    current_course_title = col.get_text(strip=True)
                    break
            continue

        if not col_text or "NOTE" in col_text[0]:
            continue

        if len(col_text) >= 23 and col_text[1].isdigit():
            try:
                crn = col_text[1]
                course_type = col_text[3]
                time_slot = col_text[11]
                location = col_text[12]

                try:
                    enrollment_cell = cols[14]  # Get the <td> element itself
                    enrollment_lines = enrollment_cell.find_all("p")

                    # If <p> contains <br>, we use .stripped_strings to safely pull the numbers
                    enrollment_numbers = [
                        int(s.strip())
                        for s in enrollment_cell.stripped_strings
                        if s.strip().isdigit()
                    ]

                    current_enrollment = sum(enrollment_numbers)
                except Exception as e:
                    print(f"⚠️ Couldn't parse enrollment: {e}")
                    current_enrollment = 0



                instructor = col_text[20]

                days = []
                for idx, val in enumerate(col_text[6:11]):
                    if val:
                        days.append(day_labels[idx])

                page_data.append({
                    "Course Title": current_course_title,
                    "CRN": crn,
                    "Type": course_type,
                    "Days": ",".join(days),
                    "Time": time_slot,
                    "Location": location,
                    "Current Enrollment": current_enrollment,
                    "Instructor": instructor
                })
            except Exception as e:
                print(f"⚠️ Skipping malformed row: {e}")
                continue
    return page_data

# Process all collected pages
for page_html in all_html_pages:
    page_data = extract_data_from_html(page_html)
    all_data.extend(page_data)

# --- SAVE TO CSV ---
df = pd.DataFrame(all_data)
df.to_csv("data/CSCI_full_schedule.csv", index=False)
print(f"✅ Scraped and saved {len(df)} rows to 'CSCI_full_schedule.csv'")

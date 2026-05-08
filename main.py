import os
import sys

from doc88 import app as doc88_app

URLS_FILE = "urls.txt"


def is_doc88_url(url: str) -> bool:
    return "doc88.com/p-" in url or "doc88.piglin.eu.org/p-" in url


def load_urls() -> list[str]:
    if not os.path.isfile(URLS_FILE):
        return []
    with open(URLS_FILE, "r", encoding="utf-8") as file:
        return [line.strip() for line in file if line.strip() and not line.startswith("#")]


def save_urls(urls: list[str]) -> None:
    with open(URLS_FILE, "w", encoding="utf-8") as file:
        for url in urls:
            file.write(url + "\n")


def main() -> None:
    app_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
    os.chdir(app_dir)
    print("DocExtractor")

    while True:
        urls = load_urls()
        if urls:
            url = urls[0]
        else:
            try:
                url = input("请输入网址：")
            except KeyboardInterrupt:
                break

        if is_doc88_url(url):
            ok = doc88_app.run(url)
            if ok and urls:
                save_urls(urls[1:])
        else:
            print("Unsupported URL.")
            ok = False

        if not ok:
            try:
                user_input = input("Error occurred. Continue? (Y/n): ")
            except KeyboardInterrupt:
                break
            if user_input not in {"Y", "y", ""}:
                break


if __name__ == "__main__":
    main()

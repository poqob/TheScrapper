import re
from urllib.parse import urlparse

import requests.exceptions
from socid_extractor import parse, extract
from typing import List

_PHONE_SINGLE = r"\+?\d{10,13}"
_PHONE_GROUPED = (
    r"(?:\+?\d{1,4}\s?)?"
    r"(?:\(\d{2,4}\)\s?)?"
    r"\d{2,4}"
    r"(?:[\s\-\.]\d{2,4}){1,4}"
)
_PHONE_PATTERN = r"(?<!\d)(?:" + _PHONE_SINGLE + r"|" + _PHONE_GROUPED + r")(?!\d)"
_EMAIL_PATTERN = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,24}"

_PHONE_REGEX = re.compile(_PHONE_PATTERN)
_EMAIL_REGEX = re.compile(_EMAIL_PATTERN)


class InfoReader:
    """
    InfoReader Class
    """

    def __init__(self, content: dict = None, social_path: str = "./socials.txt") -> None:
        """Contructor

        Args:
            content (dict): [description]. Defaults to None.
            social_path (str): [description]. Defaults to "./socials.txt".
        """

        if content is None:
            content: dict = {
                "text": [],
                "urls": []
            }

        self.content: dict = content
        self.social_path: str = social_path
        self.res: dict = {
            "phone": _PHONE_PATTERN,
            "email": _EMAIL_PATTERN,
        }

    def getPhoneNumber(self) -> list:
        """getPhoneNumber function

        Returns:
            list: [description]
        """
        numbers: list = []
        seen: set = set()
        texts: list = self.content["text"]

        for text in texts:
            for n in text.split("\n"):
                for match in _PHONE_REGEX.findall(n):
                    digits = re.sub(r"\D", "", match)
                    if 9 <= len(digits) <= 15 and digits not in seen:
                        seen.add(digits)
                        numbers.append(digits)

        return list(numbers)

    def getEmails(self) -> list:
        """getEmails Function

        Returns:
            list: [description]
        """
        emails: list = []
        seen: set = set()
        texts: object = self.content["text"]

        for text in texts:
            for s in text.split("\n"):
                for match in _EMAIL_REGEX.findall(s):
                    if match not in seen:
                        seen.add(match)
                        emails.append(match)

        for link in self.content["urls"]:
            if link is None:
                continue
            if "mailto:" in link:
                email = link.replace("mailto:", "").strip().split("?")[0]
                if email and email not in seen:
                    seen.add(email)
                    emails.append(email)

        return emails

    def getSocials(self) -> list:
        """getSocials Function

        Returns:
            list: [description]
        """
        sm_accounts: list = []
        with open(self.social_path, "r", encoding="utf-8") as f:
            socials = [line.strip().lower() for line in f.readlines() if line.strip()]

        target = self.content.get("target", "")
        target_host = urlparse(target).netloc.lower() if target else ""

        for url in self.content["urls"]:
            if url is None:
                continue

            parsed_host = urlparse(url).netloc.lower()
            lowered_url = url.lower()
            for social_host in socials:
                if social_host in lowered_url:
                    # When the target itself is on a social platform, internal links
                    # from the same host are usually noisy for --social-extract.
                    if target_host and parsed_host and parsed_host == target_host:
                        continue
                    sm_accounts.append(url)
        return list(dict.fromkeys(sm_accounts))

    def getSocialsInfo(self) -> List[dict]:
        urls = self.getSocials()
        sm_info = []
        for url in urls:
            try:
                text, _ = parse(url)
                sm_info.append({"url": url, "info": extract(text)})
            except Exception:  # Quick fix for now
                pass
        return sm_info

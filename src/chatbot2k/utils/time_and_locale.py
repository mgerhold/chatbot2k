from typing import Final
from zoneinfo import available_timezones


def get_common_timezones() -> list[str]:
    """Return a curated list of commonly used timezones."""
    all_timezones: Final = available_timezones()
    # Filter to common zones (exclude deprecated and uncommon ones)
    common_prefixes: Final = {
        "America/",
        "Europe/",
        "Asia/",
        "Australia/",
        "Pacific/",
        "Africa/",
    }
    timezones: Final = sorted(
        tz for tz in all_timezones if any(tz.startswith(prefix) for prefix in common_prefixes) or tz == "UTC"
    )
    # Put UTC first.
    if "UTC" in timezones:
        timezones.remove("UTC")
        timezones.insert(0, "UTC")
    return timezones


def get_common_locales() -> list[tuple[str, str]]:
    """Return a list of common locales as (code, display_name) tuples."""
    return [
        ("de_DE.UTF-8", "German (Germany)"),
        ("de_AT.UTF-8", "German (Austria)"),
        ("de_CH.UTF-8", "German (Switzerland)"),
        ("en_US.UTF-8", "English (United States)"),
        ("en_GB.UTF-8", "English (United Kingdom)"),
        ("en_CA.UTF-8", "English (Canada)"),
        ("en_AU.UTF-8", "English (Australia)"),
        ("fr_FR.UTF-8", "French (France)"),
        ("fr_CA.UTF-8", "French (Canada)"),
        ("fr_BE.UTF-8", "French (Belgium)"),
        ("fr_CH.UTF-8", "French (Switzerland)"),
        ("es_ES.UTF-8", "Spanish (Spain)"),
        ("es_MX.UTF-8", "Spanish (Mexico)"),
        ("es_AR.UTF-8", "Spanish (Argentina)"),
        ("it_IT.UTF-8", "Italian (Italy)"),
        ("pt_PT.UTF-8", "Portuguese (Portugal)"),
        ("pt_BR.UTF-8", "Portuguese (Brazil)"),
        ("nl_NL.UTF-8", "Dutch (Netherlands)"),
        ("nl_BE.UTF-8", "Dutch (Belgium)"),
        ("pl_PL.UTF-8", "Polish (Poland)"),
        ("ru_RU.UTF-8", "Russian (Russia)"),
        ("ja_JP.UTF-8", "Japanese (Japan)"),
        ("ko_KR.UTF-8", "Korean (South Korea)"),
        ("zh_CN.UTF-8", "Chinese (Simplified, China)"),
        ("zh_TW.UTF-8", "Chinese (Traditional, Taiwan)"),
        ("sv_SE.UTF-8", "Swedish (Sweden)"),
        ("da_DK.UTF-8", "Danish (Denmark)"),
        ("no_NO.UTF-8", "Norwegian (Norway)"),
        ("fi_FI.UTF-8", "Finnish (Finland)"),
        ("tr_TR.UTF-8", "Turkish (Turkey)"),
        ("ar_SA.UTF-8", "Arabic (Saudi Arabia)"),
        ("he_IL.UTF-8", "Hebrew (Israel)"),
        ("hi_IN.UTF-8", "Hindi (India)"),
        ("th_TH.UTF-8", "Thai (Thailand)"),
    ]

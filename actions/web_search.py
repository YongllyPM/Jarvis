import requests
import json

_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

def _search_ddg(query: str, max_results: int = 5) -> list[dict]:
    url = "https://html.duckduckgo.com/html/"
    data = {"q": query}
    headers = {"User-Agent": _USER_AGENT}
    try:
        r = requests.post(url, data=data, headers=headers, timeout=10)
        r.raise_for_status()
    except Exception as e:
        return [{"error": f"Error conectando a DuckDuckGo: {e}"}]

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    for a in soup.select("a.result__a"):
        if len(results) >= max_results:
            break
        href = a.get("href", "")
        # DuckDuckGo redirects — extract real URL
        if "//duckduckgo.com/l/?uddg=" in href:
            from urllib.parse import parse_qs, urlparse
            parsed = urlparse(href)
            qs = parse_qs(parsed.query)
            href = qs.get("uddg", [href])[0]
        title = a.get_text(strip=True)
        snippet_tag = a.find_parent("div", class_="result__body")
        snippet = ""
        if snippet_tag:
            sp = snippet_tag.select_one("a.result__snippet")
            if sp:
                snippet = sp.get_text(strip=True)
        results.append({"title": title, "url": href, "snippet": snippet})
    if not results:
        results.append({"info": f"No se encontraron resultados para '{query}'."})
    return results


def _compare_items(items: list[str], aspect: str = "") -> str:
    result_lines = []
    for item in items:
        r = _search_ddg(f"{item} {aspect}".strip(), max_results=3)
        lines = []
        for entry in r:
            lines.append(f"  - {entry.get('title', '')}: {entry.get('snippet', '')}")
        result_lines.append(f"=== {item} ===\n" + "\n".join(lines))
    return "\n\n".join(result_lines)


def web_search(parameters: dict, player=None) -> str:
    query = parameters.get("query", "")
    mode = parameters.get("mode", "search")
    items = parameters.get("items", [])
    aspect = parameters.get("aspect", "")

    if not query and not items:
        return "Necesito una consulta para buscar."

    try:
        if mode == "compare" and items:
            return _compare_items(items, aspect)
        results = _search_ddg(query)
        out = []
        for r in results:
            if "error" in r:
                return r["error"]
            out.append(f"{r['title']}\n{r['url']}\n{r['snippet']}\n")
        return "\n".join(out) if out else f"No encontré resultados para '{query}'."
    except Exception as e:
        return f"Error en búsqueda web: {e}"
